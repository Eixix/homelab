#!/usr/bin/env python3
"""Check IVR readiness without exposing SIP configuration in Docker health logs."""
import os
import re
import subprocess
import sys


def cli(command):
    result = subprocess.run(["asterisk", "-rx", command], capture_output=True,
                            text=True, timeout=2, check=True)
    return result.stdout


def healthy(mode):
    if mode not in ("local", "vodafone"):
        return False
    modules = cli("module show like chan_pjsip.so")
    if not re.search(r"chan_pjsip\.so[^\n]*\bRunning\b", modules):
        return False
    if "Playback(custom/test)" not in cli("dialplan show ivr"):
        return False
    endpoints = cli("pjsip show endpoints")
    endpoint = "local-test" if mode == "local" else "vodafone"
    if not re.search(r"^\s*Endpoint:\s+" + endpoint + r"\s", endpoints, re.MULTILINE):
        return False
    if mode == "vodafone":
        registrations = cli("pjsip show registrations")
        return bool(re.search(r"^\s*vodafone-registration/[^\n]*\bRegistered\b",
                              registrations, re.MULTILINE))
    return True


def main():
    try:
        ok = healthy(os.environ.get("ASTERISK_MODE", "local"))
    except (OSError, subprocess.SubprocessError):
        ok = False
    if not ok:
        print("Asterisk IVR is not ready")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
