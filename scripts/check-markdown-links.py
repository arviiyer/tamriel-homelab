#!/usr/bin/env python3
from __future__ import annotations

import html
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


# Match destinations rather than labels so both targets in a linked image are
# checked. Support inline links/images, angle-bracket paths, and optional titles.
LINK_PATTERN = re.compile(
    r'''\]\(\s*(?:<(?P<angle>[^>\n]+)>|'''
    r'''(?P<bare>(?:\\.|[^\s()\\]|\([^()\n]*\))+))'''
    r'''\s*(?:"[^"\n]*"|'[^'\n]*'|\([^()\n]*\))?\s*\)'''
)
INLINE_CODE_PATTERN = re.compile(r"(?<!`)(`+)(?!`).*?(?<!`)\1(?!`)", re.DOTALL)


def prose(content: str) -> str:
    """Exclude fenced and indented code examples from link and heading checks."""
    lines: list[str] = []
    fence = ""
    for line in content.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if (
                marker
                and marker[1][0] == fence[0]
                and len(marker[1]) >= len(fence)
                and not marker[2].strip()
            ):
                fence = ""
            lines.append("")
        elif marker:
            fence = marker[1]
            lines.append("")
        elif line.startswith(("    ", "\t")):
            lines.append("")
        else:
            lines.append(line)
    return "\n".join(lines)


def heading_slug(heading: str) -> str:
    heading = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    heading = re.sub(r"<[^>]*>", "", heading)
    heading = html.unescape(heading).replace("`", "").replace("*", "").replace("~", "")
    heading = re.sub(r"(?<!\w)(_+)(.+?)\1(?!\w)", r"\2", heading)
    return re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")


def heading_anchors(content: str) -> set[str]:
    """Build GitHub-style anchors for ATX/Setext headings, including duplicates."""
    anchors: set[str] = set()
    previous = ""
    for line in prose(content).splitlines():
        match = re.match(r"^ {0,3}#{1,6}[ \t]+(.+)$", line)
        heading = None
        if match:
            heading = re.sub(r"[ \t]+#+[ \t]*$", "", match[1]).strip()
        elif previous.strip() and re.fullmatch(r" {0,3}(?:=+|-+)[ \t]*", line):
            heading = previous.strip()
        previous = line
        if heading is None:
            continue
        base = heading_slug(heading)
        anchor = base
        suffix = 0
        while anchor in anchors:
            suffix += 1
            anchor = f"{base}-{suffix}"
        anchors.add(anchor)
    return anchors


def iter_markdown_files(repo_root: Path) -> list[Path]:
    return sorted(
        path
        for path in repo_root.rglob("*.md")
        if ".git" not in path.parts
    )


def local_target(raw_target: str) -> tuple[str, str] | None:
    target = raw_target.strip().strip("<>")
    if not target:
        return None
    target = re.sub(r"\\([() ])", r"\1", target)
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None
    return unquote(parsed.path), unquote(parsed.fragment)


def check_links(repo_root: Path) -> list[str]:
    failures: list[str] = []
    anchors: dict[Path, set[str]] = {}

    for document in iter_markdown_files(repo_root):
        content = document.read_text(encoding="utf-8")
        content = INLINE_CODE_PATTERN.sub("", prose(content))
        for match in LINK_PATTERN.finditer(content):
            raw_target = match["angle"] or match["bare"]
            target = local_target(raw_target)
            if target is None:
                continue

            path_part, fragment = target
            resolved = (document.parent / path_part).resolve() if path_part else document
            relative_document = document.relative_to(repo_root)
            if not resolved.exists():
                failures.append(f"{relative_document}: missing target {raw_target}")
                continue
            if not fragment:
                continue
            if resolved.is_dir():
                resolved = resolved / "README.md"
                if not resolved.is_file():
                    failures.append(f"{relative_document}: no README for {raw_target}")
                    continue
            if resolved.suffix.lower() not in (".md", ".markdown"):
                continue
            if resolved not in anchors:
                anchors[resolved] = heading_anchors(resolved.read_text(encoding="utf-8"))
            if fragment not in anchors[resolved]:
                failures.append(f"{relative_document}: missing heading {raw_target}")
    return failures


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    failures = check_links(repo_root)

    if failures:
        print("Markdown link validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("Markdown link validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
