#!/usr/bin/env python3
"""Synchronize the live UniFi inventory into NetBox without storing credentials."""

import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from ipaddress import ip_interface


def required(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def slug(value):
    value = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return value[:100] or "unnamed"


class JsonApi:
    def __init__(self, base_url, headers=None, insecure=False):
        self.base_url = base_url.rstrip("/") + "/"
        self.headers = headers or {}
        self.context = ssl._create_unverified_context() if insecure else ssl.create_default_context()
        self.cookies = urllib.request.HTTPCookieProcessor()
        self.opener = urllib.request.build_opener(
            self.cookies, urllib.request.HTTPSHandler(context=self.context)
        )

    def request(self, path, method="GET", body=None, query=None):
        url = urllib.parse.urljoin(self.base_url, path.lstrip("/"))
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Accept": "application/json", **self.headers}
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=30) as response:
                content = response.read()
                return json.loads(content) if content else None
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")
            raise RuntimeError(f"{method} {url} returned {error.code}: {detail[:1000]}") from error


class NetBox:
    def __init__(self, url, token, host=None, insecure=False):
        headers = {"Authorization": f"Bearer {token}"}
        if host:
            headers["Host"] = host
        self.api = JsonApi(url.rstrip("/") + "/api/", headers, insecure)

    def ensure(self, endpoint, lookup, payload):
        result = self.api.request(endpoint, query=lookup)
        matches = result.get("results", result) if isinstance(result, dict) else result
        if matches:
            obj = matches[0]
            return self.api.request(f"{endpoint}{obj['id']}/", "PATCH", payload)
        return self.api.request(endpoint, "POST", payload)

    def get(self, endpoint, **query):
        result = self.api.request(endpoint, query=query)
        matches = result.get("results", result) if isinstance(result, dict) else result
        return matches[0] if matches else None


def unifi_inventory():
    api = JsonApi(required("UNIFI_URL"), insecure=True)
    api.request(
        "/api/auth/login",
        "POST",
        {"username": required("UNIFI_USERNAME"), "password": required("UNIFI_PASSWORD"), "remember": False},
    )
    site = os.environ.get("UNIFI_SITE", "default")

    def data(path):
        return api.request(f"/proxy/network/api/s/{site}/{path}").get("data", [])

    return {
        "devices": data("stat/device"),
        "clients": data("stat/sta"),
        "networks": data("rest/networkconf"),
        "wlans": data("rest/wlanconf"),
    }


def main():
    inventory = unifi_inventory()
    api_token = required("NETBOX_API_TOKEN")
    if api_key := os.environ.get("NETBOX_API_KEY"):
        api_token = f"nbt_{api_key}.{api_token}"
    nb = NetBox(
        required("NETBOX_URL"),
        api_token,
        os.environ.get("NETBOX_HOST_HEADER"),
        os.environ.get("NETBOX_INSECURE", "false").lower() == "true",
    )

    site = nb.ensure("dcim/sites/", {"slug": "home"}, {"name": "Home", "slug": "home", "status": "active"})
    manufacturers = {}
    for name in ("Ubiquiti", "Generic"):
        manufacturers[name] = nb.ensure(
            "dcim/manufacturers/", {"slug": slug(name)}, {"name": name, "slug": slug(name)}
        )

    roles = {}
    for name, color in (
        ("Gateway", "e91e63"),
        ("Switch", "3f51b5"),
        ("Wireless AP", "00bcd4"),
        ("Server", "4caf50"),
        ("Network Client", "9e9e9e"),
    ):
        roles[name] = nb.ensure(
            "dcim/device-roles/", {"slug": slug(name)}, {"name": name, "slug": slug(name), "color": color}
        )

    role_for_type = {"udm": "Gateway", "usw": "Switch", "uap": "Wireless AP"}
    devices_by_name = {}
    interfaces = {}

    def ensure_type(model, manufacturer="Ubiquiti"):
        return nb.ensure(
            "dcim/device-types/",
            {"slug": slug(model)},
            {"manufacturer": manufacturers[manufacturer]["id"], "model": model, "slug": slug(model)},
        )

    def ensure_interface(device, name, interface_type="other", mac=None, description=""):
        payload = {"device": device["id"], "name": name, "type": interface_type, "description": description}
        if mac:
            payload["mac_address"] = mac
        interface = nb.ensure(
            "dcim/interfaces/", {"device_id": device["id"], "name": name}, payload
        )
        interfaces[(device["name"], name)] = interface
        return interface

    def assign_ip(address, interface, description=""):
        if not address:
            return None
        prefix = 128 if ":" in address else 32
        ip = nb.ensure(
            "ipam/ip-addresses/",
            {"address": f"{address}/{prefix}"},
            {
                "address": f"{address}/{prefix}",
                "status": "active",
                "description": description,
                "assigned_object_type": "dcim.interface",
                "assigned_object_id": interface["id"],
            },
        )
        return ip

    # Prefixes, VLANs, gateways, DNS, and DHCP ranges.
    network_ids = {}
    for network in inventory["networks"]:
        if network.get("purpose") not in ("corporate", "remote-user-vpn") or not network.get("ip_subnet"):
            continue
        iface = ip_interface(network["ip_subnet"])
        name = network["name"]
        network_ids[network.get("_id")] = name
        vlan = None
        if network.get("purpose") == "corporate":
            vid = int(network.get("vlan") or 1)
            vlan = nb.ensure(
                "ipam/vlans/",
                {"site_id": site["id"], "vid": vid},
                {"site": site["id"], "vid": vid, "name": name, "status": "active"},
            )
        description = f"UniFi {network.get('purpose')} network"
        dns = network.get("dhcpd_dns_1")
        if dns:
            description += f"; DNS {dns}"
        prefix_payload = {
            "prefix": str(iface.network),
            "status": "active",
            "description": description,
            "scope_type": "dcim.site",
            "scope_id": site["id"],
        }
        if vlan:
            prefix_payload["vlan"] = vlan["id"]
        nb.ensure("ipam/prefixes/", {"prefix": str(iface.network)}, prefix_payload)
        if network.get("dhcpd_start") and network.get("dhcpd_stop"):
            nb.ensure(
                "ipam/ip-ranges/",
                {"start_address": f"{network['dhcpd_start']}/{iface.network.prefixlen}"},
                {
                    "start_address": f"{network['dhcpd_start']}/{iface.network.prefixlen}",
                    "end_address": f"{network['dhcpd_stop']}/{iface.network.prefixlen}",
                    "status": "active",
                    "description": f"UniFi DHCP range for {name}",
                },
            )

    # Managed UniFi infrastructure.
    for source in inventory["devices"]:
        name = source.get("name") or source.get("hostname") or source["mac"]
        model = source.get("model") or source.get("type", "UniFi device")
        dtype = ensure_type(model)
        role = roles[role_for_type.get(source.get("type"), "Network Client")]
        device = nb.ensure(
            "dcim/devices/",
            {"site_id": site["id"], "name": name},
            {
                "site": site["id"],
                "name": name,
                "device_type": dtype["id"],
                "role": role["id"],
                "status": "active",
                "serial": source.get("serial", ""),
                "description": f"UniFi OS {source.get('version', '')}".strip(),
            },
        )
        devices_by_name[name] = device
        management = ensure_interface(device, "Management", "virtual", source.get("mac"))
        ip = assign_ip(source.get("ip"), management, f"Management IP for {name}")
        if ip and ":" not in source.get("ip", ""):
            nb.api.request(f"dcim/devices/{device['id']}/", "PATCH", {"primary_ip4": ip["id"]})
        for port in source.get("port_table", []):
            media = port.get("media", "")
            interface_type = "10gbase-x-sfpp" if "SFP+" in media else "1000base-t"
            ensure_interface(device, port.get("name") or f"Port {port['port_idx']}", interface_type)
        if source.get("type") == "uap":
            ensure_interface(device, "eth0", "1000base-t")

    # Physical uplinks reported by UniFi.
    source_by_name = {
        (source.get("name") or source.get("hostname") or source.get("mac")): source
        for source in inventory["devices"]
    }
    for source_name, source in source_by_name.items():
        uplink = source.get("uplink") or {}
        remote_name = uplink.get("uplink_device_name")
        remote_port_index = uplink.get("uplink_remote_port")
        if not remote_name or remote_port_index is None:
            continue
        if source.get("type") == "uap":
            local_name = "eth0"
        else:
            local_port = next((port for port in source.get("port_table", []) if port.get("is_uplink")), None)
            if not local_port:
                continue
            local_name = local_port.get("name") or f"Port {local_port['port_idx']}"
        remote_source = source_by_name.get(remote_name, {})
        remote_port = next(
            (port for port in remote_source.get("port_table", []) if port.get("port_idx") == remote_port_index),
            None,
        )
        if not remote_port:
            continue
        remote_interface_name = remote_port.get("name") or f"Port {remote_port_index}"
        local_interface = interfaces.get((source_name, local_name))
        remote_interface = interfaces.get((remote_name, remote_interface_name))
        if not local_interface or not remote_interface:
            continue
        local_detail = nb.api.request(f"dcim/interfaces/{local_interface['id']}/")
        remote_detail = nb.api.request(f"dcim/interfaces/{remote_interface['id']}/")
        if local_detail.get("cable") or remote_detail.get("cable"):
            continue
        nb.api.request(
            "dcim/cables/",
            "POST",
            {
                "a_terminations": [{"object_type": "dcim.interface", "object_id": local_interface["id"]}],
                "b_terminations": [{"object_type": "dcim.interface", "object_id": remote_interface["id"]}],
                "status": "connected",
                "label": f"UniFi uplink: {source_name} to {remote_name}",
            },
        )

    # Homelab server is authoritative even if absent from the active client list.
    server_name = os.environ.get("HOMELAB_SERVER_NAME", "sun")
    server_type = ensure_type(os.environ.get("HOMELAB_SERVER_MODEL", "Linux Docker Host"), "Generic")
    server = nb.ensure(
        "dcim/devices/",
        {"site_id": site["id"], "name": server_name},
        {
            "site": site["id"], "name": server_name, "device_type": server_type["id"],
            "role": roles["Server"]["id"], "status": "active",
            "description": os.environ.get("HOMELAB_SERVER_DESCRIPTION", "Homelab Docker host")
        },
    )
    devices_by_name[server_name] = server
    server_if = ensure_interface(server, "enp2s0", "1000base-t", os.environ.get("HOMELAB_SERVER_MAC"))
    server_ip = assign_ip(os.environ.get("HOMELAB_SERVER_IP", "10.0.0.2"), server_if, "DNS and application host")
    if server_ip:
        nb.api.request(f"dcim/devices/{server['id']}/", "PATCH", {"primary_ip4": server_ip["id"]})

    containers_file = os.environ.get("HOMELAB_CONTAINERS_FILE")
    if containers_file:
        with open(containers_file, encoding="utf-8") as handle:
            containers = json.load(handle)
        for container in containers:
            nb.ensure(
                "dcim/inventory-items/",
                {"device_id": server["id"], "name": container["name"]},
                {
                    "device": server["id"],
                    "name": container["name"],
                    "description": f"Container image {container.get('image', 'unknown')}; ports {container.get('ports') or 'internal only'}",
                    "discovered": True,
                },
            )

    # Active wired and wireless clients, with stable unique names and MAC/IP assignments.
    for source in inventory["clients"]:
        mac = source.get("mac")
        if not mac or source.get("ip") == os.environ.get("HOMELAB_SERVER_IP", "10.0.0.2"):
            continue
        label = source.get("name") or source.get("hostname") or source.get("oui") or "Client"
        name = f"{label}-{mac.replace(':', '')[-4:]}"
        dtype = ensure_type("UniFi Client", "Generic")
        device = nb.ensure(
            "dcim/devices/",
            {"site_id": site["id"], "name": name},
            {
                "site": site["id"], "name": name, "device_type": dtype["id"],
                "role": roles["Network Client"]["id"], "status": "active",
                "description": f"{label}; UniFi network {source.get('network', 'unknown')}"
            },
        )
        interface_name = "Ethernet" if source.get("is_wired") else "Wi-Fi"
        interface_type = "1000base-t" if source.get("is_wired") else "ieee802.11ax"
        interface = ensure_interface(device, interface_name, interface_type, mac)
        ip = assign_ip(source.get("ip"), interface, label)
        if ip and ":" not in source.get("ip", ""):
            nb.api.request(f"dcim/devices/{device['id']}/", "PATCH", {"primary_ip4": ip["id"]})

    # Wi-Fi SSIDs without storing passphrases.
    for wlan in inventory["wlans"]:
        nb.ensure(
            "wireless/wireless-lans/",
            {"ssid": wlan["name"]},
            {
                "ssid": wlan["name"], "status": "active" if wlan.get("enabled") else "disabled",
                "auth_type": "wpa-personal" if "psk" in wlan.get("security", "") else "open",
                "description": f"UniFi WLAN; network {network_ids.get(wlan.get('networkconf_id'), 'unknown')}"
            },
        )

    print(
        f"Synchronized {len(inventory['devices'])} UniFi devices, "
        f"{len(inventory['clients'])} active clients, {len(network_ids)} networks, "
        f"and {len(inventory['wlans'])} WLANs into NetBox."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(error, file=sys.stderr)
        raise
