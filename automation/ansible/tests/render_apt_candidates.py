#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined


def main() -> int:
    output_directory = Path(sys.argv[1])
    output_directory.mkdir(parents=True, exist_ok=True)
    template_directory = (
        Path(__file__).resolve().parents[1]
        / "roles"
        / "unattended_upgrades"
        / "templates"
    )
    environment = Environment(
        loader=FileSystemLoader(template_directory),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )
    environment.filters["ternary"] = (
        lambda value, true, false: true if value else false
    )

    policy = environment.get_template("50unattended-upgrades.j2").render(
        unattended_upgrades_origin_patterns=[
            "origin=Debian,codename=${distro_codename}-security,label=Debian-Security"
        ],
        unattended_upgrades_remove_unused_dependencies=True,
        unattended_upgrades_automatic_reboot=False,
        unattended_upgrades_mail="",
    )
    periodic = environment.get_template("20auto-upgrades.j2").render()

    (output_directory / "50unattended-upgrades").write_text(policy, encoding="utf-8")
    (output_directory / "20auto-upgrades").write_text(periodic, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
