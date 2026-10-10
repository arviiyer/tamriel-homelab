#!/usr/bin/env python3
"""Exercise clean, finding, and error exits using an inert custom signature."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parent


def main():
    with tempfile.TemporaryDirectory(prefix="clamav-example-") as directory:
        path = Path(directory)
        scan = path / "scan"
        scan.mkdir()
        marker = b"An ordinary text file used to test a local ClamAV signature.\n"
        signature = path / "marker.hdb"
        signature.write_text(f"{hashlib.md5(marker, usedforsecurity=False).hexdigest()}:{len(marker)}:Example.Marker\n")
        override = path / "test.yml"
        override.write_text(json.dumps({"services": {"clamav": {"volumes": [
            f"{signature}:/fixture/marker.hdb:ro"
        ]}}}))
        env = dict(os.environ, SCAN_PATH=str(scan))
        command = ["docker", "compose", "-p", "clamav-test-" + uuid.uuid4().hex[:10],
                   "-f", str(ROOT / "compose.yml"), "-f", str(override)]

        def compose(*args, check=True):
            return subprocess.run([*command, *args], env=env, check=check,
                                  capture_output=True, text=True, timeout=300)

        def check_scan(target, expected):
            result = compose("run", "--rm", "--no-deps", "--entrypoint", "clamscan",
                             "clamav", "--database=/fixture/marker.hdb", "--recursive",
                             "--infected", target, check=False)
            assert result.returncode == expected, result.stdout + result.stderr

        try:
            compose("config", "--quiet")
            (scan / "clean.txt").write_text("A different ordinary file.\n")
            check_scan("/scan", 0)
            (scan / "marker.txt").write_bytes(marker)
            check_scan("/scan", 1)
            assert (scan / "marker.txt").read_bytes() == marker
            check_scan("/missing-directory", 2)
            print("PASS: ClamAV clean/finding/error exits and read-only source files")
        finally:
            compose("down", "--volumes", "--remove-orphans")


if __name__ == "__main__":
    main()
