#!/usr/bin/env python3
"""Read-only post-deploy checks. Never print container logs or configuration."""

import json
import subprocess
import sys
import time


def docker(*args):
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=False, timeout=30
    )
    if result.returncode:
        # Docker errors may contain interpolated configuration or credentials.
        raise RuntimeError("Docker command failed: " + " ".join(args[:2]))
    return result.stdout


def expected_services(services, selection):
    if selection == ["all"]:
        return set(services)
    expected = set()

    def include(name):
        if name in expected:
            return
        if name not in services:
            raise RuntimeError(f"Unknown Compose service: {name}")
        expected.add(name)
        for dependency in services[name].get("depends_on", {}):
            include(dependency)

    for name in selection:
        include(name)
    return expected


def failures(services, expected, containers):
    completed_jobs = {
        name
        for service in services.values()
        for name, dependency in service.get("depends_on", {}).items()
        if dependency.get("condition") == "service_completed_successfully"
    }
    seen = set()
    broken = []
    for container in containers:
        labels = container.get("Config", {}).get("Labels") or {}
        if labels.get("com.docker.compose.oneoff", "false").lower() == "true":
            continue
        service = labels.get("com.docker.compose.service", "unknown")
        seen.add(service)
        name = container["Name"].lstrip("/")
        state = container["State"]
        status = state["Status"]
        health = state.get("Health", {}).get("Status")
        if service in completed_jobs:
            ok = status == "exited" and state.get("ExitCode") == 0
        else:
            ok = status == "running" and not state.get("Paused", False)
            ok = ok and health in (None, "healthy")
        if not ok:
            detail = f"{name} ({service}): {status}"
            if health:
                detail += f", health={health}"
            if status == "exited":
                detail += f", exit_code={state.get('ExitCode')}"
            broken.append(detail)
    broken.extend(f"{name}: missing container" for name in sorted(expected - seen))
    return sorted(broken)


def main(selection, timeout=180, interval=5):
    config = json.loads(docker("compose", "--env-file", ".env", "--profile", "*", "config", "--format", "json"))
    services = config["services"]
    expected = expected_services(services, selection)
    deadline = time.monotonic() + timeout
    consecutive_passes = 0
    while True:
        ids = docker("ps", "-aq", "--filter", "label=com.docker.compose.project=homelab").split()
        containers = json.loads(docker("inspect", *ids)) if ids else []
        broken = failures(services, expected, containers)
        consecutive_passes = 0 if broken else consecutive_passes + 1
        if consecutive_passes >= 3:
            print("Smoke test passed: all expected containers are running/healthy or completed successfully.")
            return 0
        if time.monotonic() >= deadline:
            print("Post-deploy container smoke test failed:")
            for detail in broken:
                print(f"- {detail}")
            if not broken:
                print("- Containers did not remain ready for three consecutive checks.")
            return 1
        time.sleep(interval)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except (RuntimeError, subprocess.TimeoutExpired, ValueError, KeyError) as error:
        print(f"Smoke test could not complete ({type(error).__name__}). Check Docker access and Compose configuration.")
        sys.exit(1)
