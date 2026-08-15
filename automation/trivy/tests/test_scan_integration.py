from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


TRIVY_ROOT = Path(__file__).resolve().parents[1]


FAKE_TRIVY = r"""#!/usr/bin/env python3
import json
import os
import pathlib
import sys

command = sys.argv[1]
if os.environ.get("FAKE_TRIVY_FAIL") == command:
    sys.exit(23)

output = pathlib.Path(sys.argv[sys.argv.index("--output") + 1])
if command == "image":
    document = {"SchemaVersion": 2, "ArtifactName": sys.argv[-1], "ArtifactType": "container_image", "ReportID": "test-image", "Results": []}
elif command == "config":
    document = {"SchemaVersion": 2, "ArtifactName": sys.argv[-1], "ArtifactType": "filesystem", "ReportID": "test-config", "Results": []}
else:
    document = {"SchemaVersion": 2, "ArtifactName": sys.argv[-1], "ArtifactType": "repository", "ReportID": "test-repo", "Results": []}
output.write_text(json.dumps(document), encoding="utf-8")
"""

FAKE_CURL = """#!/bin/sh
if [ "${FAKE_CURL_FAIL:-}" = "1" ]; then
    exit 22
fi
exit 0
"""


class ScanIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.source = self.root / "source"
        self.source.mkdir()
        subprocess.run(["git", "init", "-b", "main"], cwd=self.source, check=True, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.source,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test Fixture"],
            cwd=self.source,
            check=True,
        )
        (self.source / "compose.yaml").write_text(
            "services:\n  api:\n    image: alpine:3.20\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", "compose.yaml"], cwd=self.source, check=True)
        subprocess.run(
            ["git", "commit", "-m", "add fixture"],
            cwd=self.source,
            check=True,
            capture_output=True,
        )

        self.repositories = self.root / "repositories.tsv"
        self.repositories.write_text(
            f"apps\t{self.source}\tmain\n", encoding="utf-8"
        )
        self.baseline = self.root / "baseline"

        fake_bin = self.root / "bin"
        fake_bin.mkdir()
        fake_trivy = fake_bin / "trivy"
        fake_trivy.write_text(FAKE_TRIVY, encoding="utf-8")
        fake_trivy.chmod(fake_trivy.stat().st_mode | stat.S_IXUSR)
        fake_curl = fake_bin / "curl"
        fake_curl.write_text(FAKE_CURL, encoding="utf-8")
        fake_curl.chmod(fake_curl.stat().st_mode | stat.S_IXUSR)

        self.environment = os.environ.copy()
        self.environment.update(
            {
                "PATH": f"{fake_bin}:{self.environment['PATH']}",
                "REPOSITORIES_FILE": str(self.repositories),
                "BASELINE_DIR": str(self.baseline),
            }
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_scan(self, **environment: str) -> subprocess.CompletedProcess[str]:
        scan_environment = self.environment | environment
        return subprocess.run(
            ["bash", str(TRIVY_ROOT / "scan.sh")],
            env=scan_environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def baseline_hashes(self) -> dict[str, str]:
        return {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(self.baseline.glob("*.json"))
        }

    def test_complete_scan_promotes_a_baseline(self) -> None:
        result = self.run_scan(INITIALIZE_BASELINE="1")

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue((self.baseline / "apps-misconfig.json").is_file())
        self.assertTrue((self.baseline / "apps-secret.json").is_file())
        self.assertTrue((self.baseline / "_baseline.json").is_file())
        self.assertTrue((self.baseline / "_delta-report.json").is_file())
        vulnerability_files = list(self.baseline.glob("apps--*-vuln.json"))
        self.assertEqual(1, len(vulnerability_files))
        document = json.loads(vulnerability_files[0].read_text(encoding="utf-8"))
        self.assertEqual("alpine:3.20", document["ArtifactName"])

    def test_failed_image_scan_preserves_previous_baseline(self) -> None:
        first = self.run_scan(INITIALIZE_BASELINE="1")
        self.assertEqual(0, first.returncode, first.stderr)
        previous_hashes = self.baseline_hashes()

        failed = self.run_scan(FAKE_TRIVY_FAIL="image")

        self.assertNotEqual(0, failed.returncode)
        self.assertIn("previous baseline preserved", failed.stderr)
        self.assertEqual(previous_hashes, self.baseline_hashes())

    def test_unresolved_compose_image_preserves_previous_baseline(self) -> None:
        first = self.run_scan(INITIALIZE_BASELINE="1")
        self.assertEqual(0, first.returncode, first.stderr)
        previous_hashes = self.baseline_hashes()
        (self.source / "compose.yaml").write_text(
            "services:\n  api:\n    image: ${API_IMAGE}\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", "compose.yaml"], cwd=self.source, check=True)
        subprocess.run(
            ["git", "commit", "-m", "break fixture"],
            cwd=self.source,
            check=True,
            capture_output=True,
        )

        failed = self.run_scan()

        self.assertNotEqual(0, failed.returncode)
        self.assertEqual(previous_hashes, self.baseline_hashes())

    def test_failed_findings_push_restores_previous_baseline(self) -> None:
        first = self.run_scan(INITIALIZE_BASELINE="1")
        self.assertEqual(0, first.returncode, first.stderr)
        previous_hashes = self.baseline_hashes()
        (self.source / "compose.yaml").write_text(
            "services:\n  api:\n    image: alpine:3.21\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", "compose.yaml"], cwd=self.source, check=True)
        subprocess.run(
            ["git", "commit", "-m", "change image"],
            cwd=self.source,
            check=True,
            capture_output=True,
        )

        failed = self.run_scan(
            PUSHGATEWAY_URL="https://metrics.example.com",
            FAKE_CURL_FAIL="1",
        )

        self.assertNotEqual(0, failed.returncode)
        self.assertIn("inspect local baseline state", failed.stderr)
        self.assertEqual(previous_hashes, self.baseline_hashes())

    def test_missing_baseline_requires_explicit_initialization(self) -> None:
        result = self.run_scan()

        self.assertNotEqual(0, result.returncode)
        self.assertIn("INITIALIZE_BASELINE=1", result.stderr)
        self.assertFalse(self.baseline.exists())

    def test_rejects_overlapping_scan_for_same_baseline(self) -> None:
        lock_path = self.root / ".trivy-scan.lock"
        lock_path.touch()
        holder = subprocess.Popen(
            ["flock", str(lock_path), "sleep", "5"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            time.sleep(0.1)
            result = self.run_scan(INITIALIZE_BASELINE="1")
        finally:
            holder.terminate()
            holder.wait(timeout=5)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("another scan is already running", result.stderr)

    def test_rejects_credentials_embedded_in_clone_url(self) -> None:
        self.repositories.write_text(
            "apps\thttps://user@git.example.com/platform/apps.git\tmain\n",
            encoding="utf-8",
        )

        result = self.run_scan()

        self.assertNotEqual(0, result.returncode)
        self.assertIn("clone URLs must not contain userinfo", result.stderr)
        self.assertFalse(self.baseline.exists())


if __name__ == "__main__":
    unittest.main()
