from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from collections import deque
from pathlib import Path
from unittest.mock import patch


CI_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CI_ROOT / "target"))

from restricted_deploy import (  # noqa: E402
    DeploymentController,
    DeploymentError,
    Request,
    Settings,
    State,
    SystemAdapter,
    parse_request,
    read_state,
)


CURRENT_REVISION = "a" * 40
TARGET_REVISION = "b" * 40
POLICY_VIOLATION_REVISION = "c" * 40
UNREACHABLE_REVISION = "d" * 40


def compose_model(version: str, **service_changes: object) -> dict[str, object]:
    service = {
        "image": (
            f"registry.example.com/example-api:{version}@sha256:"
            f"{version[0] * 64}"
        ),
        "ports": ["8080:8080"],
        **service_changes,
    }
    return {"services": {"example-api": service}}


class FakeAdapter:
    def __init__(self) -> None:
        self.models = {
            CURRENT_REVISION: compose_model("a1"),
            TARGET_REVISION: compose_model("b2"),
            POLICY_VIOLATION_REVISION: compose_model("c3", privileged=True),
            UNREACHABLE_REVISION: compose_model("d4"),
        }
        self.reachable = {
            CURRENT_REVISION,
            TARGET_REVISION,
            POLICY_VIOLATION_REVISION,
        }
        self.ancestor_pairs = {
            (CURRENT_REVISION, TARGET_REVISION),
            (CURRENT_REVISION, POLICY_VIOLATION_REVISION),
        }
        self.health_results: deque[bool] = deque()
        self.fetch_count = 0
        self.pull_calls: list[str] = []
        self.apply_calls: list[str] = []
        self.fail_pull = False
        self.fail_apply = False

    def _serialized(self, revision: str) -> str:
        return json.dumps(self.models[revision], sort_keys=True) + "\n"

    def fetch_protected_ref(self) -> None:
        self.fetch_count += 1

    def revision_exists(self, revision: str) -> bool:
        return revision in self.models

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        if descendant == "refs/remotes/origin/main":
            return ancestor in self.reachable
        return ancestor == descendant or (ancestor, descendant) in self.ancestor_pairs

    def extract_compose(self, revision: str, destination: Path) -> None:
        destination.write_text(self._serialized(revision), encoding="utf-8")

    def render_model(self, compose_file: Path) -> dict[str, object]:
        return json.loads(compose_file.read_text(encoding="utf-8"))

    def pull(self, compose_file: Path) -> None:
        self.pull_calls.append(compose_file.read_text(encoding="utf-8"))
        if self.fail_pull:
            raise DeploymentError("synthetic pull failure")

    def apply(self, compose_file: Path) -> None:
        self.apply_calls.append(compose_file.read_text(encoding="utf-8"))
        if self.fail_apply:
            self.fail_apply = False
            raise DeploymentError("synthetic apply failure")

    def healthy(self) -> bool:
        return self.health_results.popleft() if self.health_results else True


class FailBeforeStateWriteController(DeploymentController):
    def _write_state(self, state: State) -> None:
        raise OSError("synthetic state write failure")


class PostReplaceSyncFailureController(DeploymentController):
    def _write_state(self, state: State) -> None:
        with patch(
            "restricted_deploy.fsync_directory",
            side_effect=OSError("synthetic directory sync failure"),
        ):
            super()._write_state(state)


class RestrictedCommandTests(unittest.TestCase):
    def test_accepts_only_full_sha_allowlisted_requests(self) -> None:
        self.assertEqual(
            Request("deploy", "example-api", TARGET_REVISION),
            parse_request(f"deploy example-api {TARGET_REVISION}"),
        )
        self.assertEqual(
            Request("rollback", "example-api", TARGET_REVISION),
            parse_request(f"rollback example-api {TARGET_REVISION}"),
        )

        rejected = (
            "",
            "deploy example-api main",
            f"deploy other-service {TARGET_REVISION}",
            f"deploy example-api {TARGET_REVISION[:12]}",
            f"deploy example-api {TARGET_REVISION.upper()}",
            f" deploy example-api {TARGET_REVISION}",
            f"deploy example-api {TARGET_REVISION}; id",
            f"delete example-api {TARGET_REVISION}",
        )
        for command in rejected:
            with self.subTest(command=command):
                with self.assertRaises(DeploymentError):
                    parse_request(command)


class SystemAdapterGitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.working = cls.root / "working"
        cls.bare = cls.root / "apps.git"
        cls.compose_path = cls.working / "services" / "example-api" / "compose.yml"

        cls._git("init", "--initial-branch=main", str(cls.working), cwd=cls.root)
        cls._git("config", "user.name", "Synthetic Test", cwd=cls.working)
        cls._git("config", "user.email", "test@example.com", cwd=cls.working)
        cls.compose_path.parent.mkdir(parents=True)
        cls._write_compose("a1")
        cls._git("add", ".", cwd=cls.working)
        cls._git("commit", "-m", "initial", cwd=cls.working)
        cls.current = cls._git("rev-parse", "HEAD", cwd=cls.working).stdout.strip()

        cls._git("switch", "--create", "unreviewed", cwd=cls.working)
        cls._write_compose("c3")
        cls._git("commit", "-am", "unreviewed", cwd=cls.working)
        cls.unreviewed = cls._git(
            "rev-parse", "HEAD", cwd=cls.working
        ).stdout.strip()

        cls._git("switch", "main", cwd=cls.working)
        cls._write_compose("b2")
        cls._git("commit", "-am", "promoted", cwd=cls.working)
        cls.target = cls._git("rev-parse", "HEAD", cwd=cls.working).stdout.strip()
        cls._git("clone", "--bare", str(cls.working), str(cls.bare), cwd=cls.root)

        cls.settings = Settings(
            service_name="example-api",
            repository_dir=cls.bare,
            state_file=cls.root / "state.json",
            pending_file=cls.root / "pending.json",
            live_compose_file=cls.root / "compose.yml",
            repository_compose_path="services/example-api/compose.yml",
            protected_ref="refs/remotes/origin/main",
            lock_file=cls.root / "deploy.lock",
            project_directory=cls.root,
            health_url="http://127.0.0.1:8080/health",
        )
        cls.adapter = SystemAdapter(cls.settings)
        cls.adapter.fetch_protected_ref()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    @classmethod
    def _git(
        cls, *arguments: str, cwd: Path
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
        )

    @classmethod
    def _write_compose(cls, version: str) -> None:
        cls.compose_path.write_text(
            json.dumps(compose_model(version), sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_real_git_graph_enforces_protected_main_ancestry(self) -> None:
        self.assertTrue(self.adapter.revision_exists(self.current))
        self.assertTrue(self.adapter.revision_exists(self.target))
        self.assertTrue(self.adapter.revision_exists(self.unreviewed))
        self.assertTrue(self.adapter.is_ancestor(self.current, self.target))
        self.assertTrue(
            self.adapter.is_ancestor(self.target, self.settings.protected_ref)
        )
        self.assertFalse(
            self.adapter.is_ancestor(self.unreviewed, self.settings.protected_ref)
        )

    def test_extracts_definition_from_exact_real_revision(self) -> None:
        destination = self.root / "extracted-compose.yml"
        self.adapter.extract_compose(self.target, destination)
        self.assertEqual(
            compose_model("b2"),
            json.loads(destination.read_text(encoding="utf-8")),
        )


class DeploymentTransactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.service_dir = self.root / "service"
        self.state_dir = self.root / "state"
        self.service_dir.mkdir()
        self.state_dir.mkdir()
        self.settings = Settings(
            service_name="example-api",
            repository_dir=self.root / "apps.git",
            state_file=self.state_dir / "example-api.json",
            pending_file=self.state_dir / "example-api.pending.json",
            live_compose_file=self.service_dir / "compose.yml",
            repository_compose_path="services/example-api/compose.yml",
            protected_ref="refs/remotes/origin/main",
            lock_file=self.root / "deploy.lock",
            project_directory=self.service_dir,
            health_url="http://127.0.0.1:8080/health",
        )
        self.adapter = FakeAdapter()
        self._set_state(CURRENT_REVISION, None)
        self._set_live(CURRENT_REVISION)
        self.controller = DeploymentController(self.settings, self.adapter)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _set_state(self, current: str, previous: str | None) -> None:
        self.settings.state_file.write_text(
            json.dumps({"current": current, "previous": previous}) + "\n",
            encoding="utf-8",
        )

    def _set_live(self, revision: str) -> None:
        self.settings.live_compose_file.write_text(
            self.adapter._serialized(revision), encoding="utf-8"
        )

    def _deploy(self, revision: str = TARGET_REVISION) -> State:
        return self.controller.run(Request("deploy", "example-api", revision))

    def test_promotes_state_only_after_successful_health_check(self) -> None:
        result = self._deploy()

        self.assertEqual(State(TARGET_REVISION, CURRENT_REVISION), result)
        self.assertEqual(result, read_state(self.settings.state_file))
        self.assertEqual(
            self.adapter._serialized(TARGET_REVISION),
            self.settings.live_compose_file.read_text(encoding="utf-8"),
        )
        self.assertEqual(1, len(self.adapter.pull_calls))
        self.assertEqual(1, len(self.adapter.apply_calls))
        self.assertFalse(self.settings.pending_file.exists())

    def test_rejects_revision_outside_protected_main(self) -> None:
        with self.assertRaisesRegex(DeploymentError, "not reachable"):
            self._deploy(UNREACHABLE_REVISION)

        self.assertEqual(State(CURRENT_REVISION, None), read_state(self.settings.state_file))
        self.assertFalse(self.adapter.apply_calls)
        self.assertFalse(self.settings.pending_file.exists())

    def test_rejects_non_forward_deployment(self) -> None:
        self._set_state(TARGET_REVISION, CURRENT_REVISION)
        self._set_live(TARGET_REVISION)

        with self.assertRaisesRegex(DeploymentError, "must descend"):
            self._deploy(POLICY_VIOLATION_REVISION)

        self.assertFalse(self.adapter.apply_calls)

    def test_rejects_live_configuration_drift(self) -> None:
        self.settings.live_compose_file.write_text("drifted\n", encoding="utf-8")

        with self.assertRaisesRegex(DeploymentError, "has drifted"):
            self._deploy()

        self.assertFalse(self.adapter.pull_calls)
        self.assertFalse(self.adapter.apply_calls)

    def test_rejects_change_outside_image_digest_policy(self) -> None:
        with self.assertRaisesRegex(DeploymentError, "more than"):
            self._deploy(POLICY_VIOLATION_REVISION)

        self.assertFalse(self.adapter.pull_calls)
        self.assertFalse(self.adapter.apply_calls)

    def test_failed_health_check_restores_recorded_revision(self) -> None:
        self.adapter.health_results.extend((False, True))

        with self.assertRaisesRegex(DeploymentError, "recorded current revision"):
            self._deploy()

        self.assertEqual(State(CURRENT_REVISION, None), read_state(self.settings.state_file))
        self.assertEqual(
            self.adapter._serialized(CURRENT_REVISION),
            self.settings.live_compose_file.read_text(encoding="utf-8"),
        )
        self.assertEqual(2, len(self.adapter.apply_calls))
        self.assertFalse(self.settings.pending_file.exists())

    def test_recovery_failure_retains_pending_transaction(self) -> None:
        self.adapter.health_results.extend((False, False))

        with self.assertRaisesRegex(DeploymentError, "automatic recovery both failed"):
            self._deploy()

        self.assertEqual(State(CURRENT_REVISION, None), read_state(self.settings.state_file))
        self.assertTrue(self.settings.pending_file.exists())

    def test_pull_failure_does_not_open_transaction(self) -> None:
        self.adapter.fail_pull = True

        with self.assertRaisesRegex(DeploymentError, "synthetic pull failure"):
            self._deploy()

        self.assertEqual(State(CURRENT_REVISION, None), read_state(self.settings.state_file))
        self.assertFalse(self.settings.pending_file.exists())
        self.assertFalse(self.adapter.apply_calls)

    def test_state_commit_failure_restores_recorded_revision(self) -> None:
        controller = FailBeforeStateWriteController(self.settings, self.adapter)

        with self.assertRaisesRegex(DeploymentError, "state commit failed"):
            controller.run(Request("deploy", "example-api", TARGET_REVISION))

        self.assertEqual(State(CURRENT_REVISION, None), read_state(self.settings.state_file))
        self.assertEqual(2, len(self.adapter.apply_calls))
        self.assertEqual(
            self.adapter._serialized(CURRENT_REVISION),
            self.settings.live_compose_file.read_text(encoding="utf-8"),
        )
        self.assertFalse(self.settings.pending_file.exists())

    def test_post_replace_sync_failure_retains_pending_recovery_state(self) -> None:
        controller = PostReplaceSyncFailureController(self.settings, self.adapter)

        with self.assertRaisesRegex(DeploymentError, "durability is ambiguous"):
            controller.run(Request("deploy", "example-api", TARGET_REVISION))

        self.assertEqual(
            State(TARGET_REVISION, CURRENT_REVISION),
            read_state(self.settings.state_file),
        )
        self.assertEqual(1, len(self.adapter.apply_calls))
        self.assertTrue(self.settings.pending_file.exists())

        result = self.controller.run(
            Request("deploy", "example-api", TARGET_REVISION)
        )
        self.assertEqual(State(TARGET_REVISION, CURRENT_REVISION), result)
        self.assertFalse(self.settings.pending_file.exists())

    def test_rollback_uses_recorded_previous_revision(self) -> None:
        self._set_state(TARGET_REVISION, CURRENT_REVISION)
        self._set_live(TARGET_REVISION)

        result = self.controller.run(
            Request("rollback", "example-api", TARGET_REVISION)
        )

        self.assertEqual(State(CURRENT_REVISION, TARGET_REVISION), result)
        self.assertEqual(result, read_state(self.settings.state_file))
        self.assertEqual(
            self.adapter._serialized(CURRENT_REVISION),
            self.settings.live_compose_file.read_text(encoding="utf-8"),
        )

    def test_rollback_rejects_stale_current_revision_guard(self) -> None:
        self._set_state(TARGET_REVISION, CURRENT_REVISION)
        self._set_live(TARGET_REVISION)

        with self.assertRaisesRegex(DeploymentError, "guard revision"):
            self.controller.run(
                Request("rollback", "example-api", CURRENT_REVISION)
            )

        self.assertEqual(State(TARGET_REVISION, CURRENT_REVISION), read_state(self.settings.state_file))
        self.assertFalse(self.adapter.apply_calls)

    def test_interrupted_transaction_is_recovered_before_new_attempt(self) -> None:
        self.settings.pending_file.write_text(
            json.dumps(
                {
                    "operation": "deploy",
                    "source": CURRENT_REVISION,
                    "target": TARGET_REVISION,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self._set_live(TARGET_REVISION)

        result = self._deploy()

        self.assertEqual(State(TARGET_REVISION, CURRENT_REVISION), result)
        self.assertEqual(2, len(self.adapter.apply_calls))
        self.assertEqual(
            self.adapter._serialized(CURRENT_REVISION), self.adapter.apply_calls[0]
        )
        self.assertEqual(
            self.adapter._serialized(TARGET_REVISION), self.adapter.apply_calls[1]
        )
        self.assertFalse(self.settings.pending_file.exists())

    def test_completed_transaction_metadata_is_cleaned_idempotently(self) -> None:
        self._set_state(TARGET_REVISION, CURRENT_REVISION)
        self._set_live(TARGET_REVISION)
        self.settings.pending_file.write_text(
            json.dumps(
                {
                    "operation": "deploy",
                    "source": CURRENT_REVISION,
                    "target": TARGET_REVISION,
                }
            )
            + "\n",
            encoding="utf-8",
        )

        result = self._deploy()

        self.assertEqual(State(TARGET_REVISION, CURRENT_REVISION), result)
        self.assertFalse(self.adapter.apply_calls)
        self.assertFalse(self.settings.pending_file.exists())


if __name__ == "__main__":
    unittest.main()
