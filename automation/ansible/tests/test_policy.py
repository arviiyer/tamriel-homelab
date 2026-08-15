from __future__ import annotations

import configparser
import unittest
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined


ANSIBLE_ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def jinja_environment(template_directory: Path) -> Environment:
    environment = Environment(
        loader=FileSystemLoader(template_directory),
        undefined=StrictUndefined,
        autoescape=False,
        keep_trailing_newline=True,
    )
    environment.filters["ternary"] = lambda value, true, false: true if value else false
    return environment


def nested_tasks(tasks: list[dict[str, object]]) -> list[dict[str, object]]:
    flattened: list[dict[str, object]] = []
    for task in tasks:
        flattened.append(task)
        for section in ("block", "rescue", "always"):
            if section in task:
                flattened.extend(nested_tasks(task[section]))
    return flattened


class InventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.inventory = load_yaml(ANSIBLE_ROOT / "inventory.example.yml")

    def test_hypervisors_use_key_only_root_management(self) -> None:
        hypervisors = self.inventory["all"]["children"]["hypervisors"]

        self.assertEqual("root", hypervisors["vars"]["ansible_user"])
        self.assertFalse(hypervisors["vars"]["ansible_become"])
        self.assertEqual(
            "prohibit-password", hypervisors["vars"]["ssh_permit_root_login"]
        )
        self.assertEqual(["root"], hypervisors["vars"]["ssh_allowed_users"])
        self.assertTrue(self.inventory["all"]["vars"]["ssh_key_access_prevalidated"])
        self.assertTrue(
            self.inventory["all"]["vars"]["ssh_console_recovery_prevalidated"]
        )
        self.assertEqual(
            "192.0.2.100",
            self.inventory["all"]["vars"]["ssh_validation_source_address"],
        )
        self.assertEqual(
            "admin.example.com",
            self.inventory["all"]["vars"]["ssh_validation_source_host"],
        )

    def test_service_hosts_disable_root_login(self) -> None:
        inventory_all = self.inventory["all"]
        service_vms = inventory_all["children"]["service_vms"]

        self.assertEqual("operator", inventory_all["vars"]["ansible_user"])
        self.assertEqual("no", service_vms["vars"]["ssh_permit_root_login"])
        self.assertEqual(["operator"], inventory_all["vars"]["ssh_allowed_users"])

    def test_inventory_uses_documentation_only_addresses(self) -> None:
        addresses = []
        for group in self.inventory["all"]["children"].values():
            addresses.extend(
                host["ansible_host"] for host in group.get("hosts", {}).values()
            )

        self.assertTrue(addresses)
        self.assertTrue(
            all(
                address.startswith(("192.0.2.", "198.51.100.", "203.0.113."))
                for address in addresses
            )
        )


class SshPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        template_directory = (
            ANSIBLE_ROOT / "roles" / "ssh_hardening" / "templates"
        )
        cls.template = jinja_environment(template_directory).get_template(
            "00-ansible-hardening.conf.j2"
        )

    def render(self, permit_root_login: str, allowed_users: list[str]) -> str:
        return self.template.render(
            ssh_permit_root_login=permit_root_login,
            ssh_allowed_users=allowed_users,
            ssh_max_auth_tries=3,
            ssh_client_alive_interval=300,
            ssh_client_alive_count_max=2,
        )

    def test_service_policy_is_key_only_and_non_root(self) -> None:
        rendered = self.render("no", ["operator"])

        self.assertIn("PermitRootLogin no", rendered)
        self.assertIn("PasswordAuthentication no", rendered)
        self.assertIn("KbdInteractiveAuthentication no", rendered)
        self.assertIn("PubkeyAuthentication yes", rendered)
        self.assertIn("AuthenticationMethods publickey", rendered)
        self.assertIn("AllowUsers operator", rendered)

    def test_hypervisor_policy_preserves_key_only_root_access(self) -> None:
        rendered = self.render("prohibit-password", ["root"])

        self.assertIn("PermitRootLogin prohibit-password", rendered)
        self.assertIn("AllowUsers root", rendered)
        self.assertNotIn("AllowUsers operator", rendered)

    def test_unused_authentication_and_forwarding_are_disabled(self) -> None:
        rendered = self.render("no", ["operator"])

        for directive in (
            "KerberosAuthentication no",
            "GSSAPIAuthentication no",
            "X11Forwarding no",
            "PermitEmptyPasswords no",
        ):
            self.assertIn(directive, rendered)

    def test_role_uses_watchdog_rollback_and_context_validation(self) -> None:
        tasks = load_yaml(
            ANSIBLE_ROOT / "roles" / "ssh_hardening" / "tasks" / "main.yml"
        )
        flattened = nested_tasks(tasks)
        names = {task.get("name") for task in flattened}

        self.assertIn("Arm automatic SSH rollback", names)
        self.assertIn("Restore the previous SSH policy immediately", names)
        self.assertIn("Verify the changed effective SSH policy", names)
        self.assertIn("Verify the unchanged effective SSH policy", names)
        self.assertIn("Cancel the automatic SSH rollback timer", names)
        self.assertIn("Verify rollback units are inactive", names)
        self.assertIn("Require the candidate policy at the commit boundary", names)

        verify_tasks = load_yaml(
            ANSIBLE_ROOT
            / "roles"
            / "ssh_hardening"
            / "tasks"
            / "verify_effective.yml"
        )
        verify_names = {task.get("name") for task in verify_tasks}
        self.assertIn("Read effective SSH policy for every allowed user", verify_names)

        verify_command = verify_tasks[0]["ansible.builtin.command"]["argv"][-1]
        self.assertIn("host={{ ssh_validation_source_host }}", verify_command)
        self.assertIn("addr={{ ssh_validation_source_address }}", verify_command)

    def test_role_rejects_symlinked_and_recursive_dropins(self) -> None:
        tasks = load_yaml(
            ANSIBLE_ROOT / "roles" / "ssh_hardening" / "tasks" / "main.yml"
        )
        flattened = nested_tasks(tasks)
        names = {task.get("name") for task in flattened}

        self.assertIn("Reject symlinked OpenSSH drop-ins", names)
        conflict_task = next(
            task
            for task in flattened
            if task.get("name") == "Reject competing OpenSSH authentication policy"
        )
        assertions = conflict_task["ansible.builtin.assert"]["that"]
        self.assertTrue(any("Include" in assertion for assertion in assertions))
        self.assertTrue(any("Match" in assertion for assertion in assertions))

        primary_task = next(
            task
            for task in flattened
            if task.get("name") == "Require the distribution-managed include directive"
        )
        primary_assertions = primary_task["ansible.builtin.assert"]["that"]
        self.assertTrue(any("regex_findall" in assertion for assertion in primary_assertions))

    def test_role_refuses_check_mode(self) -> None:
        tasks = load_yaml(
            ANSIBLE_ROOT / "roles" / "ssh_hardening" / "tasks" / "main.yml"
        )
        first_assertions = tasks[0]["ansible.builtin.assert"]["that"]

        self.assertIn("not ansible_check_mode", first_assertions)


class UnattendedUpgradePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        template_directory = (
            ANSIBLE_ROOT / "roles" / "unattended_upgrades" / "templates"
        )
        environment = jinja_environment(template_directory)
        cls.policy_template = environment.get_template("50unattended-upgrades.j2")
        cls.periodic_template = environment.get_template("20auto-upgrades.j2")

    def test_policy_allows_security_origin_without_automatic_reboot(self) -> None:
        rendered = self.policy_template.render(
            unattended_upgrades_origin_patterns=[
                "origin=Debian,codename=${distro_codename}-security,label=Debian-Security"
            ],
            unattended_upgrades_remove_unused_dependencies=True,
            unattended_upgrades_automatic_reboot=False,
            unattended_upgrades_mail="",
        )

        self.assertIn(
            '"origin=Debian,codename=${distro_codename}-security,label=Debian-Security";',
            rendered,
        )
        self.assertIn("#clear Unattended-Upgrade::Allowed-Origins;", rendered)
        self.assertIn("#clear Unattended-Upgrade::Origins-Pattern;", rendered)
        self.assertIn("Unattended-Upgrade::Origins-Pattern", rendered)
        self.assertIn('Unattended-Upgrade::Automatic-Reboot "false";', rendered)
        self.assertNotIn("Unattended-Upgrade::Mail ", rendered)

    def test_periodic_policy_runs_daily_and_cleans_weekly(self) -> None:
        rendered = self.periodic_template.render()

        self.assertIn('APT::Periodic::Update-Package-Lists "1";', rendered)
        self.assertIn('APT::Periodic::Unattended-Upgrade "1";', rendered)
        self.assertIn('APT::Periodic::AutocleanInterval "7";', rendered)

    def test_role_parses_candidates_and_has_rollback(self) -> None:
        tasks = load_yaml(
            ANSIBLE_ROOT / "roles" / "unattended_upgrades" / "tasks" / "main.yml"
        )
        names = {task.get("name") for task in nested_tasks(tasks)}

        self.assertIn("Parse the isolated unattended-upgrades candidate", names)
        self.assertIn("Parse the isolated periodic-update candidate", names)
        self.assertIn("Restore the previous apt policies", names)
        self.assertIn("Verify effective unattended-upgrades controls", names)
        self.assertIn("Refuse unresolved apt-policy transaction state", names)


class ControlledUpgradeTests(unittest.TestCase):
    def setUp(self) -> None:
        playbook = load_yaml(ANSIBLE_ROOT / "playbooks" / "controlled-upgrade.yml")
        self.play = playbook[0]
        self.tasks = nested_tasks(self.play["tasks"])

    def test_rollout_is_serial_and_stops_on_failure(self) -> None:
        self.assertEqual(1, self.play["serial"])
        self.assertTrue(self.play["any_errors_fatal"])
        self.assertEqual(0, self.play["max_fail_percentage"])

    def test_playbook_reports_but_does_not_perform_reboots(self) -> None:
        modules = {
            key
            for task in self.tasks
            for key in task
            if key.startswith("ansible.builtin.")
        }

        self.assertIn("ansible.builtin.stat", modules)
        self.assertIn("ansible.builtin.debug", modules)
        self.assertNotIn("ansible.builtin.reboot", modules)

    def test_full_upgrade_and_cleanup_are_explicit(self) -> None:
        apt_tasks = [
            task["ansible.builtin.apt"]
            for task in self.tasks
            if "ansible.builtin.apt" in task
        ]
        upgrade_task = next(task for task in apt_tasks if task.get("upgrade") == "full")
        autoremove_task = next(task for task in apt_tasks if task.get("autoremove") is True)
        autoclean_task = next(task for task in apt_tasks if task.get("autoclean") is True)

        self.assertTrue(upgrade_task["force_apt_get"])
        self.assertTrue(autoremove_task["force_apt_get"])
        self.assertTrue(autoclean_task["force_apt_get"])

    def test_failure_path_reports_phase_and_stops_rollout(self) -> None:
        names = {task.get("name") for task in self.tasks}

        self.assertIn("Record the failed host upgrade outcome", names)
        self.assertIn("Report the failed host upgrade outcome", names)
        self.assertIn("Stop the rollout after a host package failure", names)

    def test_cleanup_phases_are_recorded_separately(self) -> None:
        facts = [
            task["ansible.builtin.set_fact"].get("controlled_upgrade_phase")
            for task in self.tasks
            if "ansible.builtin.set_fact" in task
        ]

        self.assertIn("unused-packages-removed", facts)
        self.assertIn("package-archives-cleaned", facts)


class AnsibleConfigurationTests(unittest.TestCase):
    def test_host_key_checking_remains_enabled(self) -> None:
        parser = configparser.ConfigParser()
        parser.read(ANSIBLE_ROOT / "ansible.cfg")

        self.assertTrue(parser.getboolean("defaults", "host_key_checking"))


if __name__ == "__main__":
    unittest.main()
