#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
SKIPPED_PREFIXES = ("#", "http://", "https://", "mailto:")


def iter_markdown_files(repo_root: Path) -> list[Path]:
    return sorted(
        path
        for path in repo_root.rglob("*.md")
        if ".git" not in path.parts
    )


def local_target(raw_target: str) -> str | None:
    target = raw_target.strip().strip("<>")
    if not target or target.startswith(SKIPPED_PREFIXES):
        return None

    path_part = target.split("#", maxsplit=1)[0]
    return unquote(path_part) if path_part else None


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    failures: list[str] = []

    for document in iter_markdown_files(repo_root):
        content = document.read_text(encoding="utf-8")
        for match in LINK_PATTERN.finditer(content):
            target = local_target(match.group(1))
            if target is None:
                continue

            resolved = (document.parent / target).resolve()
            if not resolved.exists():
                relative_document = document.relative_to(repo_root)
                failures.append(f"{relative_document}: missing target {target}")

    if failures:
        print("Markdown link validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("Markdown link validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
