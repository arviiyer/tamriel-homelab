from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined


FALCO_ROOT = Path(__file__).resolve().parents[1]


def render_config() -> str:
    defaults = yaml.safe_load(
        (FALCO_ROOT / "roles" / "falco" / "defaults" / "main.yml").read_text(
            encoding="utf-8"
        )
    )
    defaults["falco_sidekick_url"] = "http://security-01.example.com:2801"
    rules = (
        FALCO_ROOT / "roles" / "falco" / "files" / "falco_rules.local.yaml"
    ).read_bytes()
    defaults["falco_rules_digest"] = hashlib.sha256(rules).hexdigest()

    environment = Environment(
        loader=FileSystemLoader(FALCO_ROOT / "roles" / "falco" / "templates"),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )
    environment.filters["to_json"] = json.dumps
    template = environment.get_template("falco.yaml.j2")
    return template.render(**defaults)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(render_config(), encoding="utf-8")


if __name__ == "__main__":
    main()
