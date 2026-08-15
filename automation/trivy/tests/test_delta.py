from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from shutil import copy2


TRIVY_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(TRIVY_ROOT))

import delta  # noqa: E402


def create_previous_baseline(parent: Path) -> Path:
    baseline = parent / "previous"
    baseline.mkdir()
    for path in (FIXTURES / "previous").glob("*.json"):
        copy2(path, baseline / path.name)
    delta.write_baseline_manifest(
        baseline / delta.BASELINE_MANIFEST,
        baseline,
        ["apps"],
        1_699_990_000,
    )
    return baseline


class DeltaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repositories = ["apps"]
        self.previous = delta.load_scan_directory(
            FIXTURES / "previous", self.repositories
        )
        self.current = delta.load_scan_directory(FIXTURES / "current", self.repositories)

    def test_metadata_change_does_not_create_new_and_fixed_findings(self) -> None:
        new, fixed = delta.compute_delta(
            self.current.vulnerabilities, self.previous.vulnerabilities
        )

        self.assertEqual(
            ["CVE-2026-1001"],
            sorted(finding.identity.vulnerability_id for finding in new),
        )
        self.assertEqual(
            ["CVE-2026-0999"],
            sorted(finding.identity.vulnerability_id for finding in fixed),
        )

    def test_metadata_change_emits_security_relevant_transitions(self) -> None:
        changes = delta.compute_vulnerability_changes(
            self.current.vulnerabilities, self.previous.vulnerabilities
        )

        self.assertEqual(
            ["fix_available", "severity_increased"],
            sorted(change.change for change in changes),
        )

    def test_misconfiguration_severity_change_is_not_new(self) -> None:
        new, _ = delta.compute_delta(
            self.current.misconfigurations, self.previous.misconfigurations
        )

        self.assertEqual(["DS-002"], [finding.identity.check_id for finding in new])

    def test_metrics_include_actionable_deltas_and_current_secrets(self) -> None:
        metrics = delta.build_findings_metrics(
            self.current,
            self.previous,
            self.repositories,
            scan_time=1_700_000_000,
            has_previous=True,
        )

        self.assertIn(
            'trivy_new_vulnerabilities{has_fix="true",image="registry.example.com/platform/api:1.0.0",repository="apps",severity="CRITICAL"} 1',
            metrics,
        )
        self.assertIn(
            'trivy_fixed_vulnerabilities{image="registry.example.com/platform/api:1.0.0",repository="apps",severity="HIGH"} 1',
            metrics,
        )
        self.assertIn(
            'trivy_new_misconfigurations{repository="apps",severity="CRITICAL"} 1',
            metrics,
        )
        self.assertIn(
            'trivy_vulnerability_changes{change="severity_increased",image="registry.example.com/platform/api:1.0.0",repository="apps",severity="HIGH"} 1',
            metrics,
        )
        self.assertIn(
            'trivy_vulnerability_changes{change="fix_available",image="registry.example.com/platform/api:1.0.0",repository="apps",severity="HIGH"} 1',
            metrics,
        )
        self.assertIn(
            'trivy_secrets{repository="apps",severity="HIGH"} 1', metrics
        )
        self.assertIn(
            "trivy_scan_last_success_timestamp_seconds 1700000000", metrics
        )

    def test_first_baseline_does_not_alert_on_every_existing_finding(self) -> None:
        metrics = delta.build_findings_metrics(
            self.current,
            delta.empty_results(),
            self.repositories,
            scan_time=1_700_000_000,
            has_previous=False,
        )

        self.assertNotIn("trivy_new_vulnerabilities{", metrics)
        self.assertNotIn("trivy_new_misconfigurations{", metrics)

    def test_empty_baseline_after_first_run_still_produces_new_findings(self) -> None:
        metrics = delta.build_findings_metrics(
            self.current,
            delta.empty_results(),
            self.repositories,
            scan_time=1_700_000_000,
            has_previous=True,
        )

        self.assertIn("trivy_new_vulnerabilities{", metrics)
        self.assertIn("trivy_new_misconfigurations{", metrics)

    def test_label_escaping_handles_quotes_backslashes_and_newlines(self) -> None:
        self.assertEqual('a\\\\b\\"c\\nd', delta.escape_label('a\\b"c\nd'))

    def test_invalid_json_is_a_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "apps-misconfig.json"
            path.write_text("not-json", encoding="utf-8")

            with self.assertRaises(delta.ScanDataError):
                delta.parse_misconfiguration_file(path)

    def test_schema_valid_report_without_results_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "apps-misconfig.json"
            path.write_text(
                '{"SchemaVersion": 2, "ArtifactName": "apps", "ArtifactType": "filesystem", "ReportID": "empty"}',
                encoding="utf-8",
            )

            self.assertEqual({}, delta.parse_misconfiguration_file(path))

    def test_missing_required_result_is_a_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "apps-misconfig.json").write_text('{"Results": []}', encoding="utf-8")

            with self.assertRaises(delta.ScanDataError):
                delta.load_scan_directory(path, ["apps"])

    def test_conflicting_duplicate_is_a_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "apps--duplicate-vuln.json"
            path.write_text(
                """
                {
                  "SchemaVersion": 2,
                  "ArtifactName": "example/image:1",
                  "ArtifactType": "container_image",
                  "ReportID": "duplicate-test",
                  "Results": [{
                    "Target": "os",
                    "Vulnerabilities": [
                      {"VulnerabilityID": "CVE-1", "PkgName": "pkg", "InstalledVersion": "1", "Severity": "LOW"},
                      {"VulnerabilityID": "CVE-1", "PkgName": "pkg", "InstalledVersion": "1", "Severity": "HIGH"}
                    ]
                  }]
                }
                """,
                encoding="utf-8",
            )

            with self.assertRaises(delta.ScanDataError):
                delta.parse_vulnerability_file(path)

    def test_cli_writes_metrics_from_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "metrics.prom"
            report = Path(directory) / "delta-report.json"
            manifest = Path(directory) / "_baseline.json"
            previous = create_previous_baseline(Path(directory))
            result = subprocess.run(
                [
                    sys.executable,
                    str(TRIVY_ROOT / "delta.py"),
                    "report",
                    "--current-dir",
                    str(FIXTURES / "current"),
                    "--last-dir",
                    str(previous),
                    "--repositories",
                    str(FIXTURES / "repositories.tsv"),
                    "--output",
                    str(output),
                    "--report-output",
                    str(report),
                    "--manifest-output",
                    str(manifest),
                    "--scan-time",
                    "1700000000",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("trivy_new_vulnerabilities", output.read_text(encoding="utf-8"))
            report_document = __import__("json").loads(report.read_text(encoding="utf-8"))
            self.assertEqual(
                "CVE-2026-1001",
                report_document["new_vulnerabilities"][0]["vulnerability_id"],
            )
            self.assertEqual(1, report_document["current_secret_count"])
            self.assertTrue(manifest.is_file())

    def test_missing_baseline_manifest_is_a_hard_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with self.assertRaises(delta.ScanDataError):
                delta.load_baseline(path, ["apps"])

    def test_baseline_repository_set_must_match_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline = create_previous_baseline(Path(directory))
            with self.assertRaises(delta.ScanDataError):
                delta.load_baseline(baseline, ["identity"])

    def test_baseline_file_inventory_detects_missing_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline = create_previous_baseline(Path(directory))
            (baseline / "apps--example-vuln.json").unlink()

            with self.assertRaises(delta.ScanDataError):
                delta.load_baseline(baseline, ["apps"])

    def test_baseline_digest_detects_modified_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            baseline = create_previous_baseline(Path(directory))
            (baseline / "apps-secret.json").write_text(
                '{"SchemaVersion": 2}', encoding="utf-8"
            )

            with self.assertRaises(delta.ScanDataError):
                delta.load_baseline(baseline, ["apps"])


if __name__ == "__main__":
    unittest.main()
