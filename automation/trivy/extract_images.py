#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml


COMPOSE_NAMES = {
    "compose.yaml",
    "compose.yml",
    "docker-compose.yaml",
    "docker-compose.yml",
}


class ComposeError(ValueError):
    pass


def compose_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.name in COMPOSE_NAMES and ".git" not in path.parts
    )


def extract_images(root: Path) -> list[str]:
    images: set[str] = set()

    for path in compose_files(root):
        try:
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as error:
            raise ComposeError(f"cannot parse {path}: {error}") from error

        if document is None:
            continue
        if not isinstance(document, dict):
            raise ComposeError(f"{path}: top-level Compose document must be a mapping")

        services = document.get("services", {})
        if not isinstance(services, dict):
            raise ComposeError(f"{path}: services must be a mapping")

        for service_name, service in services.items():
            if not isinstance(service, dict):
                raise ComposeError(f"{path}: service {service_name!r} must be a mapping")

            image = service.get("image")
            if image is None:
                continue
            if not isinstance(image, str) or not image.strip():
                raise ComposeError(f"{path}: service {service_name!r} has an invalid image")

            image = image.strip()
            if "${" in image:
                raise ComposeError(
                    f"{path}: service {service_name!r} has an unresolved image variable"
                )
            images.add(image)

    return sorted(images)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract unique, fully resolved image references from Compose files"
    )
    parser.add_argument("root", type=Path, help="Repository root to inspect")
    args = parser.parse_args()

    try:
        for image in extract_images(args.root):
            print(image)
    except ComposeError as error:
        print(f"extract-images: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
