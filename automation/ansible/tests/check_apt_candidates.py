#!/usr/bin/env python3
from __future__ import annotations

import sys


EXPECTED_ORIGIN = (
    'Unattended-Upgrade::Origins-Pattern:: '
    '"origin=Debian,codename=${distro_codename}-security,label=Debian-Security";'
)


def values(lines: list[str], prefix: str) -> list[str]:
    lowered_prefix = prefix.lower()
    return [line for line in lines if line.lower().startswith(lowered_prefix)]


def main() -> int:
    lines = sys.stdin.read().splitlines()
    assert values(lines, "Unattended-Upgrade::Origins-Pattern::") == [EXPECTED_ORIGIN]
    assert values(lines, "Unattended-Upgrade::Allowed-Origins::") == []
    assert values(lines, "Unattended-Upgrade::Automatic-Reboot ") == [
        'Unattended-Upgrade::Automatic-Reboot "false";'
    ]
    assert values(lines, "APT::Periodic::Unattended-Upgrade ") == [
        'APT::Periodic::Unattended-Upgrade "1";'
    ]
    print("Debian apt policy compatibility passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
