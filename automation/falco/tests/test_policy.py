from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import yaml

from render_config import render_config


FALCO_ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def nested_tasks(tasks: list[dict[str, object]]) -> list[dict[str, object]]:
    flattened: list[dict[str, object]] = []
    for task in tasks:
        flattened.append(task)
        for section in ("block", "rescue", "always"):
            if section in task:
                flattened.extend(nested_tasks(task[section]))
    return flattened


class FalcoConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rendered = render_config()
        cls.config = yaml.safe_load(cls.rendered)

    def test_uses_modern_ebpf_and_container_context(self) -> None:
        self.assertEqual("modern_ebpf", self.config["engine"]["kind"])
        self.assertFalse(self.config["watch_config_files"])
        self.assertEqual("notice", self.config["priority"])
        self.assertRegex(
            self.config["rules_files"][1],
            r"^/etc/falco/ansible-rules/[a-f0-9]{64}\.yaml$",
        )
        self.assertEqual(["container"], self.config["load_plugins"])
        plugin = self.config["plugins"][0]
        self.assertEqual("container", plugin["name"])
        self.assertEqual(
            "/usr/share/falco/plugins/libcontainer.so", plugin["library_path"]
        )

    def test_emits_structured_events_to_parameterized_endpoint(self) -> None:
        self.assertTrue(self.config["json_output"])
        self.assertTrue(self.config["json_include_output_fields_property"])
        self.assertTrue(self.config["http_output"]["enabled"])
        self.assertEqual(
            "http://security-01.example.com:2801",
            self.config["http_output"]["url"],
        )
        self.assertNotIn("security-01.example.com", (
            FALCO_ROOT / "roles" / "falco" / "templates" / "falco.yaml.j2"
        ).read_text(encoding="utf-8"))

    def test_keeps_local_audit_copy_and_bounds_output_queue(self) -> None:
        self.assertTrue(self.config["syslog_output"]["enabled"])
        self.assertFalse(self.config["file_output"]["enabled"])
        self.assertGreater(self.config["outputs_queue"]["capacity"], 0)
        self.assertEqual("127.0.0.1", self.config["webserver"]["listen_address"])


class TuningPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = load_yaml(
            FALCO_ROOT
            / "roles"
            / "falco"
            / "files"
            / "falco_rules.local.yaml"
        )

    def test_only_appends_exceptions_to_named_upstream_rules(self) -> None:
        self.assertGreaterEqual(len(self.rules), 2)
        for rule in self.rules:
            self.assertEqual({"exceptions": "append"}, rule["override"])
            self.assertNotIn("condition", rule)
            self.assertNotIn("enabled", rule)
            self.assertTrue(rule["rule"])

    def test_exceptions_require_process_and_workload_context(self) -> None:
        process_fields = {"proc.name", "proc.exepath", "proc.pname", "proc.cmdline"}
        for rule in self.rules:
            for exception in rule["exceptions"]:
                fields = exception["fields"]
                self.assertGreaterEqual(len(fields), 3)
                self.assertTrue(process_fields.intersection(fields))
                self.assertIn("container.image.repository", fields)
                self.assertEqual(len(fields), len(exception["comps"]))
                for values in exception["values"]:
                    self.assertEqual(len(fields), len(values))

    def test_exceptions_have_no_wildcards_or_broad_operators(self) -> None:
        for rule in self.rules:
            for exception in rule["exceptions"]:
                self.assertTrue(all(comp == "=" for comp in exception["comps"]))
                flattened_values = [
                    str(value)
                    for values in exception["values"]
                    for value in values
                ]
                self.assertTrue(all("*" not in value for value in flattened_values))
                self.assertTrue(all(value.strip() for value in flattened_values))


class DeploymentPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tasks = nested_tasks(
            load_yaml(FALCO_ROOT / "roles" / "falco" / "tasks" / "main.yml")
        )
        cls.names = {task.get("name") for task in cls.tasks}

    def test_deployment_is_serial_and_fail_stop(self) -> None:
        play = load_yaml(FALCO_ROOT / "playbooks" / "falco.yml")[0]
        self.assertEqual("falco_sensors", play["hosts"])
        self.assertEqual(1, play["serial"])
        self.assertTrue(play["any_errors_fatal"])
        self.assertEqual(0, play["max_fail_percentage"])

    def test_role_validates_before_commit_and_rolls_back(self) -> None:
        self.assertIn("Validate candidate configuration and rules together", self.names)
        self.assertIn("Stage the immutable local-rules release", self.names)
        self.assertIn("Install the validated Falco configuration", self.names)
        self.assertIn("Wait for the Falco process health endpoint", self.names)
        self.assertIn("Verify the Falco webserver remains healthy", self.names)
        self.assertIn("Restore the previous Falco configuration", self.names)
        self.assertIn("Restart Falco with the previous policy", self.names)
        self.assertIn("Stop after restoring the previous Falco policy", self.names)

        validate_index = next(
            index
            for index, task in enumerate(self.tasks)
            if task.get("name") == "Validate candidate configuration and rules together"
        )
        commit_index = next(
            index
            for index, task in enumerate(self.tasks)
            if task.get("name") == "Install the validated Falco configuration"
        )
        self.assertLess(validate_index, commit_index)

    def test_role_pins_package_trust_and_disables_mutating_updater(self) -> None:
        defaults = load_yaml(FALCO_ROOT / "roles" / "falco" / "defaults" / "main.yml")
        self.assertRegex(defaults["falco_package_version"], r"^\d+\.\d+\.\d+$")
        self.assertRegex(
            defaults["falco_package_key_checksum"], r"^sha256:[a-f0-9]{64}$"
        )
        self.assertEqual("", defaults["falco_sidekick_url"])
        self.assertIn("Disable automatic ruleset mutation", self.names)

        package_task = next(
            task
            for task in self.tasks
            if task.get("name") == "Install the exact Falco package version"
        )
        self.assertEqual(
            "falco={{ falco_package_version }}",
            package_task["ansible.builtin.apt"]["name"],
        )
        self.assertEqual(
            "no", package_task["environment"]["FALCOCTL_ENABLED"]
        )
        self.assertEqual("none", package_task["environment"]["FALCO_DRIVER_CHOICE"])

        prerequisite_task = next(
            task
            for task in self.tasks
            if task.get("name") == "Install Falco repository and BPF prerequisites"
        )
        self.assertIn("procps", prerequisite_task["ansible.builtin.apt"]["name"])

    def test_example_inventory_is_synthetic_and_sets_endpoint(self) -> None:
        inventory = load_yaml(FALCO_ROOT / "inventory.example.yml")
        sensors = inventory["all"]["children"]["falco_sensors"]
        addresses = [host["ansible_host"] for host in sensors["hosts"].values()]
        self.assertTrue(
            all(
                address.startswith(("192.0.2.", "198.51.100.", "203.0.113."))
                for address in addresses
            )
        )
        self.assertEqual(
            "http://security-01.example.com:2801",
            sensors["vars"]["falco_sidekick_url"],
        )


class FalcosidekickTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.compose_path = FALCO_ROOT / "falcosidekick" / "compose.yml"
        cls.compose_text = cls.compose_path.read_text(encoding="utf-8")
        cls.service = load_yaml(cls.compose_path)["services"]["falcosidekick"]

    def test_image_is_versioned_and_digest_pinned(self) -> None:
        self.assertRegex(
            self.service["image"],
            r"^falcosecurity/falcosidekick:\d+\.\d+\.\d+@sha256:[a-f0-9]{64}$",
        )

    def test_container_drops_privilege_and_uses_read_only_root(self) -> None:
        self.assertEqual("1234:1234", self.service["user"])
        self.assertTrue(self.service["read_only"])
        self.assertEqual(["ALL"], self.service["cap_drop"])
        self.assertIn("no-new-privileges:true", self.service["security_opt"])
        self.assertNotIn("env_file", self.service)

    def test_routing_contract_is_explicit(self) -> None:
        environment = self.service["environment"]
        self.assertEqual("notice", environment["LOKI_MINIMUMPRIORITY"])
        self.assertEqual("json", environment["LOKI_FORMAT"])
        self.assertEqual("warning", environment["ALERTMANAGER_MINIMUMPRIORITY"])
        self.assertEqual("/api/v2/alerts", environment["ALERTMANAGER_ENDPOINT"])
        self.assertEqual(
            "environment:example", environment["ALERTMANAGER_EXTRALABELS"]
        )
        self.assertEqual("environment:example", environment["CUSTOMFIELDS"])
        self.assertIn("${LOKI_URL:?", environment["LOKI_HOSTPORT"])
        self.assertIn("${ALERTMANAGER_URL:?", environment["ALERTMANAGER_HOSTPORT"])

    def test_example_environment_uses_public_identifiers(self) -> None:
        environment = (FALCO_ROOT / "falcosidekick" / "environment.example").read_text(
            encoding="utf-8"
        )
        self.assertIn("198.51.100.24", environment)
        self.assertEqual(2, environment.count("example.com"))
        self.assertNotRegex(environment, r"(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.")


class SyntheticEventTests(unittest.TestCase):
    def test_fixtures_match_both_routing_thresholds(self) -> None:
        priorities = set()
        for fixture in ("falco-event.json", "falco-notice-event.json"):
            event = json.loads(
                (FALCO_ROOT / "tests" / "fixtures" / fixture).read_text(
                    encoding="utf-8"
                )
            )
            required = {
                "hostname",
                "output",
                "priority",
                "rule",
                "source",
                "tags",
                "time",
                "output_fields",
            }
            self.assertTrue(required.issubset(event))
            self.assertEqual("syscall", event["source"])
            priorities.add(event["priority"].lower())
            self.assertTrue(event["hostname"].endswith("-01"))
            self.assertRegex(event["time"], r"^\d{4}-\d{2}-\d{2}T")

        self.assertEqual({"notice", "warning"}, priorities)


if __name__ == "__main__":
    unittest.main()
