#!/usr/bin/env python3
"""Generate private PJSIP configuration without logging environment values."""
import os
import json
from pathlib import Path
import sys


def setting(name, default="", required=False):
    value = os.environ.get("ASTERISK_" + name, default)
    if required and (not value or value.startswith("REPLACE_")):
        raise ValueError("ASTERISK_" + name + " must be configured")
    # Prevent config-line injection and ambiguous Asterisk escape sequences.
    if any(ord(c) < 32 for c in value) or "\\" in value:
        raise ValueError("ASTERISK_" + name + " contains unsupported control characters or backslashes")
    return value.replace(";", "\\;")


def render():
    mode = setting("MODE", "local")
    if mode == "local":
        return Path("/etc/asterisk/pjsip.local.conf").read_text()
    if mode != "vodafone":
        raise ValueError("ASTERISK_MODE must be local or vodafone")
    names = ("BIND", "REGISTRAR", "SIP_USER", "SIP_DOMAIN", "AUTH_USERNAME", "SIP_PASSWORD", "INBOUND_SBC")
    v = {name: setting(name, required=True) for name in names}
    if v["INBOUND_SBC"] in ("0.0.0.0/0", "::/0"):
        raise ValueError("ASTERISK_INBOUND_SBC must not allow all sources")
    expiration = setting("REGISTRATION_EXPIRATION", "3600")
    if not expiration.isascii() or not expiration.isdecimal() or not 60 <= int(expiration) <= 86400:
        raise ValueError("ASTERISK_REGISTRATION_EXPIRATION must be 60..86400 seconds")
    dtmf_mode = setting("DTMF_MODE", "auto")
    if dtmf_mode not in ("auto", "auto_info", "rfc4733", "inband", "info"):
        raise ValueError("ASTERISK_DTMF_MODE must be auto, auto_info, rfc4733, inband or info")
    nat = ""
    for env, option in (("LOCAL_NET", "local_net"), ("PUBLIC_IP", "external_signaling_address"), ("PUBLIC_IP", "external_media_address")):
        value = setting(env)
        if value:
            nat += f"{option} = {value}\n"
    proxy = setting("OUTBOUND_PROXY")
    proxy = f"outbound_proxy = sip:{proxy}\\;lr\n" if proxy else ""
    return f"""[global]
type = global
endpoint_identifier_order = ip
[transport-udp]
type = transport
protocol = udp
bind = {v['BIND']}
{nat}
[vodafone-auth]
type = auth
auth_type = userpass
username = {v['AUTH_USERNAME']}
password = {v['SIP_PASSWORD']}
[vodafone-registration]
type = registration
transport = transport-udp
outbound_auth = vodafone-auth
server_uri = sip:{v['REGISTRAR']}
client_uri = sip:{v['SIP_USER']}@{v['SIP_DOMAIN']}
contact_user = ivr
retry_interval = 60
forbidden_retry_interval = 600
expiration = {expiration}
{proxy}
[vodafone]
type = endpoint
transport = transport-udp
context = from-vodafone
outbound_auth = vodafone-auth
from_user = {v['SIP_USER']}
from_domain = {v['SIP_DOMAIN']}
disallow = all
allow = alaw,ulaw
dtmf_mode = {dtmf_mode}
direct_media = no
rtp_symmetric = yes
force_rport = yes
rewrite_contact = yes
{proxy}
[vodafone-identify]
type = identify
endpoint = vodafone
match = {v['INBOUND_SBC']}
"""


def main():
    os.umask(0o077)
    from menu import build_config
    try:
        config = render()
        menu_config = build_config()
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    target = Path("/run/asterisk/pjsip.conf")
    target.write_text(config)
    target.chmod(0o600)
    menu_target = Path("/run/asterisk/menu.json")
    menu_target.write_text(json.dumps(menu_config))
    menu_target.chmod(0o600)
    # Avoid forwarding credentials to Asterisk's process environment.
    for key in list(os.environ):
        if key.startswith("ASTERISK_"):
            del os.environ[key]
    os.execvp("asterisk", ["asterisk", "-f", "-C", "/etc/asterisk/asterisk.conf"])


if __name__ == "__main__":
    sys.exit(main())
