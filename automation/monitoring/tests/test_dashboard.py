from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import yaml


MONITORING_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PATH = (
    MONITORING_ROOT / "grafana" / "dashboards" / "security-control-overview.json"
)
PROVISIONING_ROOT = MONITORING_ROOT / "grafana" / "provisioning"

PUBLIC_TRIVY_METRICS = {
    "trivy_fixed_vulnerabilities",
    "trivy_misconfigurations",
    "trivy_new_misconfigurations",
    "trivy_new_vulnerabilities",
    "trivy_scan_attempt_timestamp_seconds",
    "trivy_scan_last_success_timestamp_seconds",
    "trivy_scan_repository_success",
    "trivy_scan_success",
    "trivy_secrets",
    "trivy_vulnerabilities",
    "trivy_vulnerability_changes",
}


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class DashboardStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dashboard = load_json(DASHBOARD_PATH)
        cls.panels = cls.dashboard["panels"]
        cls.query_panels = [panel for panel in cls.panels if panel["type"] != "row"]

    def test_dashboard_has_stable_public_identity(self) -> None:
        self.assertIsNone(self.dashboard["id"])
        self.assertEqual("security-control-overview", self.dashboard["uid"])
        self.assertEqual("Security Control Overview", self.dashboard["title"])
        self.assertGreaterEqual(self.dashboard["schemaVersion"], 42)
        self.assertFalse(self.dashboard["editable"])
        self.assertEqual({"security", "trivy", "falco"}, set(self.dashboard["tags"]))

    def test_panel_ids_and_grid_positions_are_valid(self) -> None:
        ids = [panel["id"] for panel in self.panels]
        self.assertEqual(len(ids), len(set(ids)))

        occupied: set[tuple[int, int]] = set()
        for panel in self.panels:
            grid = panel["gridPos"]
            self.assertGreaterEqual(grid["x"], 0)
            self.assertGreaterEqual(grid["y"], 0)
            self.assertGreater(grid["w"], 0)
            self.assertGreater(grid["h"], 0)
            self.assertLessEqual(grid["x"] + grid["w"], 24)
            cells = {
                (x, y)
                for x in range(grid["x"], grid["x"] + grid["w"])
                for y in range(grid["y"], grid["y"] + grid["h"])
            }
            self.assertFalse(occupied.intersection(cells), panel["title"])
            occupied.update(cells)

    def test_every_query_panel_has_evidence_description_and_datasource(self) -> None:
        allowed_datasources = {"security-prometheus", "security-loki"}
        for panel in self.query_panels:
            self.assertTrue(panel["description"].strip(), panel["title"])
            self.assertIn(panel["datasource"]["uid"], allowed_datasources)
            self.assertTrue(panel["targets"], panel["title"])
            ref_ids = [target["refId"] for target in panel["targets"]]
            self.assertEqual(len(ref_ids), len(set(ref_ids)), panel["title"])
            for target in panel["targets"]:
                self.assertTrue(target["expr"].strip(), panel["title"])
                self.assertEqual(
                    panel["datasource"]["uid"], target["datasource"]["uid"]
                )

    def test_required_review_paths_are_visible(self) -> None:
        titles = {panel["title"] for panel in self.panels}
        required = {
            "Latest Scan Attempt",
            "Attempt Age",
            "Successful Baseline Age",
            "Failed Repositories",
            "New Critical Vulnerabilities",
            "New Fixable High Vulnerabilities",
            "Severity Increased to Critical",
            "High-impact Fixes Available",
            "Current Secret Findings",
            "New Critical Misconfigurations",
            "High-impact Findings by Workload",
            "Runtime Events",
            "Warning or Higher Events",
            "Runtime Event Rate by Priority",
            "Most Active Runtime Rules",
            "Recent Runtime Events",
        }
        self.assertTrue(required.issubset(titles))


class QueryReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        dashboard = load_json(DASHBOARD_PATH)
        cls.targets = [
            target
            for panel in dashboard["panels"]
            for target in panel.get("targets", [])
        ]
        cls.prometheus_targets = [
            target
            for target in cls.targets
            if target["datasource"]["uid"] == "security-prometheus"
        ]
        cls.loki_targets = [
            target
            for target in cls.targets
            if target["datasource"]["uid"] == "security-loki"
        ]

    def test_promql_references_only_published_metrics(self) -> None:
        used_metrics = {
            metric
            for target in self.prometheus_targets
            for metric in re.findall(r"\btrivy_[a-zA-Z0-9_]+", target["expr"])
        }
        self.assertTrue(used_metrics)
        self.assertTrue(used_metrics.issubset(PUBLIC_TRIVY_METRICS))
        self.assertNotIn("trivy_scan_timestamp_seconds", used_metrics)

        queries = "\n".join(target["expr"] for target in self.prometheus_targets)
        self.assertNotRegex(queries, r"\brepo\b")
        self.assertIn("repository", queries)

    def test_zero_finding_fallback_requires_a_successful_baseline(self) -> None:
        finding_targets = [
            target
            for target in self.prometheus_targets
            if any(
                metric in target["expr"]
                for metric in (
                    "trivy_new_vulnerabilities",
                    "trivy_vulnerability_changes",
                    "trivy_secrets",
                    "trivy_new_misconfigurations",
                )
            )
            and "High-impact Findings by Workload" not in target.get("legendFormat", "")
        ]
        self.assertTrue(finding_targets)
        for target in finding_targets:
            self.assertIn(
                "trivy_scan_last_success_timestamp_seconds", target["expr"]
            )

    def test_logql_uses_public_falco_stream_contract(self) -> None:
        self.assertTrue(self.loki_targets)
        for target in self.loki_targets:
            self.assertIn('source="syscall"', target["expr"])
            self.assertNotRegex(target["expr"], r'hostname="[^$]')

        queries = "\n".join(target["expr"] for target in self.loki_targets)
        self.assertIn('priority=~"Warning|Error|Critical|Alert|Emergency"', queries)


class ProvisioningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dashboard_provider = load_yaml(
            PROVISIONING_ROOT / "dashboards" / "security.yml"
        )
        cls.datasource_provider = load_yaml(
            PROVISIONING_ROOT / "datasources" / "security.yml"
        )

    def test_dashboard_provider_is_file_owned_and_read_only(self) -> None:
        provider = self.dashboard_provider["providers"][0]
        self.assertEqual("security-evidence", provider["name"])
        self.assertEqual("security-evidence", provider["folderUid"])
        self.assertEqual("file", provider["type"])
        self.assertTrue(provider["disableDeletion"])
        self.assertFalse(provider["allowUiUpdates"])
        self.assertGreater(provider["updateIntervalSeconds"], 10)
        self.assertEqual(
            "/var/lib/grafana/dashboards/security", provider["options"]["path"]
        )

    def test_datasources_have_stable_public_uids_and_no_credentials(self) -> None:
        datasources = self.datasource_provider["datasources"]
        self.assertEqual(
            {"security-prometheus", "security-loki"},
            {datasource["uid"] for datasource in datasources},
        )
        self.assertEqual(
            {"prometheus", "loki"},
            {datasource["type"] for datasource in datasources},
        )
        for datasource in datasources:
            self.assertIn("example.com", datasource["url"])
            self.assertFalse(datasource["editable"])
            self.assertNotIn("secureJsonData", datasource)
            self.assertNotIn("basicAuth", datasource)

    def test_dashboard_references_only_provisioned_datasources(self) -> None:
        dashboard = load_json(DASHBOARD_PATH)
        provisioned = {
            datasource["uid"] for datasource in self.datasource_provider["datasources"]
        }
        referenced = {
            panel["datasource"]["uid"]
            for panel in dashboard["panels"]
            if panel["type"] != "row"
        }
        self.assertEqual(provisioned, referenced)


class PublicationSafetyTests(unittest.TestCase):
    def test_artifacts_contain_no_private_identifiers(self) -> None:
        texts = [
            path.read_text(encoding="utf-8")
            for path in (
                DASHBOARD_PATH,
                PROVISIONING_ROOT / "dashboards" / "security.yml",
                PROVISIONING_ROOT / "datasources" / "security.yml",
            )
        ]
        combined = "\n".join(texts)
        self.assertNotRegex(
            combined,
            r"(?:10\.|192\.168\.|172\.(?:1[6-9]|2[0-9]|3[01])\.)",
        )
        self.assertNotRegex(combined, r"P[A-F0-9]{12,}")


if __name__ == "__main__":
    unittest.main()
