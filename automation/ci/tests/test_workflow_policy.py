from __future__ import annotations

import unittest
from pathlib import Path

import yaml


CI_ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class WorkflowBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.promote_path = CI_ROOT / "forgejo" / "promote.yml"
        cls.validate_path = CI_ROOT / "forgejo" / "validate.yml"
        cls.promote_text = cls.promote_path.read_text(encoding="utf-8")
        cls.validate_text = cls.validate_path.read_text(encoding="utf-8")
        cls.promote = load_yaml(cls.promote_path)
        cls.validate = load_yaml(cls.validate_path)

    def test_promotion_is_manual_main_only_and_serialized(self) -> None:
        self.assertIn("workflow_dispatch:", self.promote_text)
        self.assertNotIn("pull_request:", self.promote_text)
        self.assertNotIn("\n  push:", self.promote_text)
        self.assertFalse(self.promote["concurrency"]["cancel-in-progress"])
        for job in self.promote["jobs"].values():
            self.assertEqual("github.ref == 'refs/heads/main'", job["if"])

    def test_operation_is_an_explicit_deploy_or_rollback_choice(self) -> None:
        self.assertIn("type: choice", self.promote_text)
        self.assertIn("- deploy", self.promote_text)
        self.assertIn("- rollback", self.promote_text)
        self.assertEqual(
            2,
            self.promote_text.count(
                '[[ "$OPERATION" == "deploy" || "$OPERATION" == "rollback" ]]'
            ),
        )
        self.assertIn(
            '"${OPERATION} example-api ${VALIDATED_REVISION}"', self.promote_text
        )

    def test_validation_and_promotion_use_separate_jobs(self) -> None:
        jobs = self.promote["jobs"]
        self.assertEqual({"validate-revision", "promote"}, set(jobs))
        self.assertEqual("validate-revision", jobs["promote"]["needs"])
        self.assertEqual("validation", jobs["validate-revision"]["runs-on"])
        self.assertEqual("promotion", jobs["promote"]["runs-on"])

    def test_deployment_secret_is_confined_to_promotion(self) -> None:
        validation = yaml.safe_dump(self.promote["jobs"]["validate-revision"])
        promotion = yaml.safe_dump(self.promote["jobs"]["promote"])
        self.assertNotIn("secrets.", validation)
        self.assertNotIn("DEPLOY_KEY", validation)
        self.assertIn("secrets.RESTRICTED_DEPLOY_KEY", promotion)
        self.assertNotIn("secrets.RESTRICTED_DEPLOY_KEY", self.validate_text)

    def test_repository_tokens_are_scoped_to_fetch_steps(self) -> None:
        validation_job = self.promote["jobs"]["validate-revision"]
        promotion_job = self.promote["jobs"]["promote"]
        pull_request_job = self.validate["jobs"]["validate"]
        self.assertNotIn("TOKEN", validation_job["env"])
        self.assertNotIn("TOKEN", promotion_job["env"])
        self.assertNotIn("TOKEN", pull_request_job["env"])
        self.assertIn("TOKEN", validation_job["steps"][0]["env"])
        self.assertIn("TOKEN", promotion_job["steps"][0]["env"])
        self.assertIn("TOKEN", pull_request_job["steps"][0]["env"])
        self.assertIn("unset TOKEN auth", validation_job["steps"][0]["run"])
        self.assertNotIn("TOKEN", promotion_job["steps"][1]["env"])

    def test_same_full_sha_crosses_validation_boundary(self) -> None:
        self.assertIn(
            "revision: ${{ steps.validate.outputs.revision }}", self.promote_text
        )
        self.assertIn(
            "VALIDATED_REVISION: ${{ needs.validate-revision.outputs.revision }}",
            self.promote_text,
        )
        self.assertIn(
            'test "$VALIDATED_REVISION" = "$REQUESTED_REVISION"', self.promote_text
        )
        self.assertGreaterEqual(
            self.promote_text.count('=~ ^[0-9a-f]{40}$'), 2
        )
        self.assertIn(
            'checkout --detach "$REQUESTED_REVISION"', self.promote_text
        )
        self.assertIn(
            'test "$(git -C "$repository" rev-parse HEAD)" = "$REQUESTED_REVISION"',
            self.promote_text,
        )

    def test_both_jobs_check_protected_main_ancestry(self) -> None:
        self.assertEqual(2, self.promote_text.count("merge-base --is-ancestor"))
        self.assertEqual(
            2, self.promote_text.count("refs/remotes/origin/main") // 2
        )

    def test_promotion_job_executes_no_checked_out_repository_content(self) -> None:
        promotion = yaml.safe_dump(self.promote["jobs"]["promote"])
        self.assertNotIn("checkout --detach", promotion)
        self.assertNotIn("docker compose", promotion)
        self.assertNotIn("services/example-api", promotion)
        self.assertIn(
            'git init "$metadata"',
            self.promote["jobs"]["promote"]["steps"][0]["run"],
        )

    def test_runner_workspaces_are_fresh_and_key_cleanup_is_armed_first(self) -> None:
        self.assertIn("RUNNER_TEMP", self.promote_text)
        self.assertNotIn("git init repository", self.promote_text)
        request_step = self.promote["jobs"]["promote"]["steps"][1]["run"]
        self.assertLess(request_step.index("umask 077"), request_step.index("DEPLOY_KEY"))
        self.assertLess(request_step.index("trap "), request_step.index("printf '%s\\n'"))
        self.assertIn("mktemp -d", request_step)

    def test_ssh_request_requires_pinned_host_identity(self) -> None:
        self.assertIn("StrictHostKeyChecking=yes", self.promote_text)
        self.assertIn(
            'UserKnownHostsFile="$ssh_dir/known_hosts"', self.promote_text
        )
        self.assertIn("vars.DEPLOY_HOST_KEY", self.promote_text)
        self.assertNotIn("ssh-keyscan", self.promote_text)
        self.assertNotIn("StrictHostKeyChecking=no", self.promote_text)
        self.assertIn("apps-01.example.com", self.promote_text)


class TargetBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sshd = (CI_ROOT / "target" / "sshd_config.example").read_text(
            encoding="utf-8"
        )
        cls.sudoers = (CI_ROOT / "target" / "sudoers.example").read_text(
            encoding="utf-8"
        )
        cls.authorized_keys = (
            CI_ROOT / "target" / "authorized_keys.example"
        ).read_text(encoding="utf-8")
        cls.helper = (CI_ROOT / "target" / "restricted_deploy.py").read_text(
            encoding="utf-8"
        )

    def test_ssh_account_is_source_restricted_and_forced(self) -> None:
        self.assertEqual("Match User deploy-request", self.sshd.splitlines()[0])
        self.assertIn(
            "ForceCommand sudo -n /usr/local/sbin/restricted-deploy", self.sshd
        )
        self.assertIn("DisableForwarding yes", self.sshd)
        self.assertIn("PermitTTY no", self.sshd)
        self.assertIn("PasswordAuthentication no", self.sshd)
        self.assertIn('from="192.0.2.40"', self.authorized_keys)
        self.assertIn("restrict", self.authorized_keys)
        self.assertIn(
            'command="sudo -n /usr/local/sbin/restricted-deploy"',
            self.authorized_keys,
        )

    def test_sudo_policy_allows_only_the_forced_helper(self) -> None:
        lines = [line for line in self.sudoers.splitlines() if line.strip()]
        self.assertEqual(4, len(lines))
        self.assertIn("env_reset", lines[0])
        self.assertIn("secure_path=", lines[1])
        self.assertIn('env_keep += "SSH_ORIGINAL_COMMAND"', lines[2])
        self.assertTrue(
            lines[3].endswith(
                "NOPASSWD: /usr/local/sbin/restricted-deploy"
            )
        )
        self.assertNotIn("ALL=(ALL)", self.sudoers)

    def test_helper_uses_fixed_commands_and_sanitized_subprocess_environment(self) -> None:
        self.assertIn('"/usr/bin/git"', self.helper)
        self.assertIn('"/usr/bin/docker"', self.helper)
        self.assertIn('"/usr/bin/curl"', self.helper)
        self.assertIn("env=COMMAND_ENV", self.helper)
        self.assertNotIn("shell=True", self.helper)
        self.assertTrue(self.helper.startswith("#!/usr/bin/python3\n"))
        self.assertIn("required path must not be a symlink", self.helper)
        self.assertIn('lock_file=Path("/run/example-deploy/', self.helper)
        self.assertIn("os.O_NOFOLLOW", self.helper)


if __name__ == "__main__":
    unittest.main()
