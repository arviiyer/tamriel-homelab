from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


RECOVERY_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = RECOVERY_ROOT / "recovery-model.json"
RESTORE_SCRIPT = RECOVERY_ROOT / "restore.py"
sys.path.insert(0, str(RECOVERY_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import restore  # noqa: E402
from archive_factory import (  # noqa: E402
    DEFAULT_FILES,
    MemberSpec,
    build_manifest,
    compress_archive,
    create_archive,
    create_raw_archive,
)


class TemporaryRecoveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.model = restore.load_model(MODEL_PATH)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_model(self, payload: object) -> Path:
        path = self.root / "model.json"
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        return path

    def verify(self, fixture, boundary: str = "service-local-state"):
        return restore.verify_archive(
            self.model, boundary, fixture.path, fixture.sha256
        )

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(RESTORE_SCRIPT), *arguments],
            check=False,
            capture_output=True,
            text=True,
        )


class RecoveryModelTests(TemporaryRecoveryTest):
    def test_repository_model_has_the_exact_public_boundary_schema(self) -> None:
        self.assertEqual(1, self.model["schema_version"])
        self.assertEqual("synthetic-public-example", self.model["classification"])
        self.assertEqual(
            {"service-local-state", "shared-bulk-data"},
            set(self.model["boundaries"]),
        )
        self.assertNotIn("schedule", MODEL_PATH.read_text(encoding="utf-8").lower())

        result = self.run_cli("validate-model", "--model", str(MODEL_PATH))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            {
                "boundaries": ["service-local-state", "shared-bulk-data"],
                "classification": "synthetic-public-example",
                "schema_version": 1,
                "status": "valid",
            },
            json.loads(result.stdout),
        )
        self.assertEqual("", result.stderr)

    def test_rejects_malformed_duplicate_and_non_exact_model_json(self) -> None:
        malformed = self.root / "malformed.json"
        malformed.write_text("{not-json\n", encoding="utf-8")
        duplicate = self.root / "duplicate.json"
        duplicate.write_text(
            '{"schema_version":1,"schema_version":1,'
            '"classification":"synthetic-public-example","boundaries":{}}\n',
            encoding="utf-8",
        )
        extra = copy.deepcopy(self.model)
        extra["unexpected"] = True
        wrong_version = copy.deepcopy(self.model)
        wrong_version["schema_version"] = 2
        wrong_classification = copy.deepcopy(self.model)
        wrong_classification["classification"] = "private"
        missing_boundary = copy.deepcopy(self.model)
        del missing_boundary["boundaries"]["shared-bulk-data"]

        for path in (malformed, duplicate):
            with self.subTest(path=path.name):
                with self.assertRaises(restore.RecoveryError):
                    restore.load_model(path)
        for payload in (extra, wrong_version, wrong_classification, missing_boundary):
            with self.subTest(payload=payload):
                with self.assertRaises(restore.RecoveryError):
                    restore.load_model(self.write_model(payload))

    def test_rejects_invalid_boundary_policy_details(self) -> None:
        wrong_copy = copy.deepcopy(self.model)
        wrong_copy["boundaries"]["service-local-state"]["copy"]["format"] = "zip"
        overlap = copy.deepcopy(self.model)
        overlap["boundaries"]["service-local-state"]["excluded"] = ["config"]
        extra_field = copy.deepcopy(self.model)
        extra_field["boundaries"]["shared-bulk-data"]["schedule"] = "daily"
        timed_retention = copy.deepcopy(self.model)
        timed_retention["boundaries"]["shared-bulk-data"]["illustrative_retention"] = {
            "classification": "operational",
            "generations": ["current-example"],
        }

        for payload in (wrong_copy, overlap, extra_field, timed_retention):
            with self.subTest(payload=payload):
                with self.assertRaises(restore.RecoveryError):
                    restore.load_model(self.write_model(payload))


class ArchiveVerificationTests(TemporaryRecoveryTest):
    def test_valid_archive_verifies_with_deterministic_cli_output(self) -> None:
        fixture = create_archive(self.root)
        verified = self.verify(fixture)
        self.assertEqual("service-local-state", verified.boundary)
        self.assertEqual(fixture.sha256, verified.archive_sha256)
        self.assertEqual(
            sum(len(data) for data in fixture.files.values()), verified.total_size
        )

        arguments = (
            "verify",
            "--model",
            str(MODEL_PATH),
            "--boundary",
            "service-local-state",
            "--archive",
            str(fixture.path),
            "--sha256",
            fixture.sha256,
        )
        first = self.run_cli(*arguments)
        second = self.run_cli(*arguments)
        self.assertEqual(0, first.returncode, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual("verified", json.loads(first.stdout)["status"])
        self.assertEqual("", first.stderr)

    def test_restore_installs_exact_bytes_and_fixed_modes(self) -> None:
        fixture = create_archive(self.root)
        destination = self.root / "restored-state"
        verified = restore.restore_archive(
            self.model,
            "service-local-state",
            fixture.path,
            fixture.sha256,
            destination,
        )

        self.assertEqual(0o750, stat.S_IMODE(destination.stat().st_mode))
        for verified_file in verified.files:
            target = destination.joinpath(*verified_file.relative_path.parts)
            self.assertEqual(verified_file.data, target.read_bytes())
            self.assertEqual(0o640, stat.S_IMODE(target.stat().st_mode))
            for parent in target.parents:
                if parent == destination.parent:
                    break
                self.assertEqual(0o750, stat.S_IMODE(parent.stat().st_mode))

    def test_existing_destination_is_never_overwritten(self) -> None:
        fixture = create_archive(self.root)
        destination = self.root / "existing"
        destination.mkdir()
        marker = destination / "marker.txt"
        marker.write_text("keep\n", encoding="utf-8")

        with self.assertRaisesRegex(restore.RecoveryError, "already exists"):
            restore.restore_archive(
                self.model,
                "service-local-state",
                fixture.path,
                fixture.sha256,
                destination,
            )
        self.assertEqual("keep\n", marker.read_text(encoding="utf-8"))
        self.assertFalse(list(self.root.glob(".existing.recovery-*")))

    def test_restore_rejects_a_symlinked_destination_parent(self) -> None:
        fixture = create_archive(self.root)
        actual_parent = self.root / "actual-parent"
        actual_parent.mkdir()
        linked_parent = self.root / "linked-parent"
        linked_parent.symlink_to(actual_parent, target_is_directory=True)

        with self.assertRaisesRegex(restore.RecoveryError, "parent must not be a symlink"):
            restore.restore_archive(
                self.model,
                "service-local-state",
                fixture.path,
                fixture.sha256,
                linked_parent / "restored-state",
            )

        self.assertFalse((actual_parent / "restored-state").exists())
        self.assertFalse(list(actual_parent.glob(".restored-state.recovery-*")))

    def test_restore_rejects_a_shared_writable_destination_parent(self) -> None:
        fixture = create_archive(self.root)
        shared_parent = self.root / "shared-parent"
        shared_parent.mkdir(mode=0o777)
        shared_parent.chmod(0o777)

        with self.assertRaisesRegex(
            restore.RecoveryError, "not group- or world-writable"
        ):
            restore.restore_archive(
                self.model,
                "service-local-state",
                fixture.path,
                fixture.sha256,
                shared_parent / "restored-state",
            )

        self.assertFalse((shared_parent / "restored-state").exists())
        self.assertFalse(list(shared_parent.glob(".restored-state.recovery-*")))

    def test_parent_replacement_cannot_redirect_restore_publication(self) -> None:
        fixture = create_archive(self.root)
        parent = self.root / "parent"
        parent.mkdir()
        moved_parent = self.root / "moved-parent"
        attacker_parent = self.root / "attacker-parent"
        attacker_parent.mkdir()
        original_writer = restore._write_staged_file
        replaced = False

        def replace_parent(path: Path, data: bytes) -> None:
            nonlocal replaced
            if not replaced:
                parent.rename(moved_parent)
                parent.symlink_to(attacker_parent, target_is_directory=True)
                replaced = True
            original_writer(path, data)

        with patch("restore._write_staged_file", side_effect=replace_parent):
            with self.assertRaisesRegex(restore.RecoveryError, "parent changed"):
                restore.restore_archive(
                    self.model,
                    "service-local-state",
                    fixture.path,
                    fixture.sha256,
                    parent / "restored-state",
                )

        self.assertFalse((attacker_parent / "restored-state").exists())
        self.assertFalse((moved_parent / "restored-state").exists())
        self.assertFalse(list(moved_parent.glob(".restored-state.recovery-*")))

    def test_rejects_wrong_boundary_and_wrong_archive_root(self) -> None:
        shared = create_archive(self.root, boundary="shared-bulk-data")
        wrong_root_files = {
            "shared-bulk-data/catalog/index.txt": b"wrong root\n"
        }
        wrong_root = create_archive(
            self.root,
            boundary="service-local-state",
            files=wrong_root_files,
        )

        with self.assertRaisesRegex(restore.RecoveryError, "boundary does not match"):
            self.verify(shared)
        with self.assertRaisesRegex(restore.RecoveryError, "outside the selected archive root"):
            self.verify(wrong_root)

    def test_external_digest_is_required_and_archive_open_does_not_follow_symlinks(self) -> None:
        fixture = create_archive(self.root)
        with self.assertRaisesRegex(restore.RecoveryError, "external SHA-256"):
            restore.verify_archive(self.model, "service-local-state", fixture.path, "A" * 64)
        with self.assertRaisesRegex(restore.RecoveryError, "does not match"):
            restore.verify_archive(
                self.model, "service-local-state", fixture.path, "0" * 64
            )

        linked = self.root / "linked.tar"
        linked.symlink_to(fixture.path)
        with self.assertRaisesRegex(restore.RecoveryError, "opened safely"):
            restore.verify_archive(
                self.model, "service-local-state", linked, fixture.sha256
            )

    def test_rejects_malformed_and_duplicate_manifest_json(self) -> None:
        duplicate = (
            b'{"schema_version":1,"schema_version":1,'
            b'"classification":"synthetic-public-example"}\n'
        )
        fixtures = (
            create_archive(self.root, manifest_bytes=b"{not-json\n"),
            create_archive(self.root, manifest_bytes=duplicate),
        )
        for fixture in fixtures:
            with self.subTest(path=fixture.path.name):
                with self.assertRaises(restore.RecoveryError):
                    self.verify(fixture)

    def test_rejects_compressed_and_malformed_tar_archives(self) -> None:
        compressed = compress_archive(self.root, create_archive(self.root))
        malformed = create_raw_archive(self.root, b"not a tar archive\n")

        for fixture in (compressed, malformed):
            with self.subTest(path=fixture.path.name):
                with self.assertRaisesRegex(restore.RecoveryError, "uncompressed tar"):
                    self.verify(fixture)

    def test_rejects_nonzero_data_after_the_final_tar_member(self) -> None:
        fixture = create_archive(self.root)
        data = fixture.path.read_bytes() + b"unvalidated trailing content"
        trailing = create_raw_archive(self.root, data)

        with self.assertRaisesRegex(restore.RecoveryError, "after its final member"):
            self.verify(trailing)

    def test_rejects_non_exact_manifest_schema_timestamp_and_backup_id(self) -> None:
        base = build_manifest("service-local-state", DEFAULT_FILES["service-local-state"])
        extra = copy.deepcopy(base)
        extra["unexpected"] = True
        wrong_schema = copy.deepcopy(base)
        wrong_schema["schema_version"] = 2
        wrong_timestamp = copy.deepcopy(base)
        wrong_timestamp["created_at"] = "2026-08-24T12:00:00+00:00"
        wrong_id = copy.deepcopy(base)
        wrong_id["backup_id"] = "backup/../../private"
        mismatched_id = copy.deepcopy(base)
        mismatched_id["backup_id"] = "synthetic-20260825T120000Z-service-state"

        for manifest in (extra, wrong_schema, wrong_timestamp, wrong_id, mismatched_id):
            with self.subTest(manifest=manifest):
                with self.assertRaises(restore.RecoveryError):
                    self.verify(create_archive(self.root, manifest=manifest))

    def test_rejects_extra_missing_and_duplicate_archive_members(self) -> None:
        files = DEFAULT_FILES["service-local-state"]
        regular_members = [
            MemberSpec(path, data) for path, data in sorted(files.items())
        ]
        fixtures = (
            create_archive(
                self.root,
                members=[*regular_members, MemberSpec("service-local-state/config/extra.txt", b"extra")],
            ),
            create_archive(self.root, members=regular_members[:-1]),
            create_archive(self.root, members=[*regular_members, regular_members[0]]),
        )
        for fixture in fixtures:
            with self.subTest(path=fixture.path.name):
                with self.assertRaises(restore.RecoveryError):
                    self.verify(fixture)

    def test_rejects_manifest_size_and_digest_mismatches(self) -> None:
        files = DEFAULT_FILES["service-local-state"]
        bad_size = build_manifest("service-local-state", files)
        bad_size["files"][0]["size"] += 1
        bad_size["total_size"] += 1
        bad_digest = build_manifest("service-local-state", files)
        bad_digest["files"][0]["sha256"] = "0" * 64

        with self.assertRaisesRegex(restore.RecoveryError, "size does not match"):
            self.verify(create_archive(self.root, manifest=bad_size))
        with self.assertRaisesRegex(restore.RecoveryError, "SHA-256 does not match"):
            self.verify(create_archive(self.root, manifest=bad_digest))

    def test_rejects_unsafe_member_and_manifest_paths(self) -> None:
        unsafe_paths = (
            "../outside.txt",
            "/absolute.txt",
            "service-local-state/config/../outside.txt",
            "service-local-state\\config\\outside.txt",
            "service-local-state/config/control\n.txt",
            "service-local-state//config/file.txt",
        )
        for unsafe_path in unsafe_paths:
            with self.subTest(path=repr(unsafe_path)):
                fixture = create_archive(self.root, files={unsafe_path: b"unsafe\n"})
                with self.assertRaisesRegex(restore.RecoveryError, "safe relative path"):
                    self.verify(fixture)

    def test_rejects_every_special_tar_member_type(self) -> None:
        target = "service-local-state/config/application.json"
        other = "service-local-state/state/records.txt"
        for kind in (
            "directory",
            "symlink",
            "hardlink",
            "fifo",
            "character",
            "block",
            "sparse",
        ):
            with self.subTest(kind=kind):
                members = [
                    MemberSpec(target, b"x", kind=kind, linkname=other),
                    MemberSpec(other, b"alpha\nbeta\n"),
                ]
                fixture = create_archive(self.root, members=members)
                with self.assertRaises(restore.RecoveryError):
                    self.verify(fixture)

    def test_rejects_parent_file_collisions(self) -> None:
        files = {
            "service-local-state/config/item": b"parent\n",
            "service-local-state/config/item/child.txt": b"child\n",
        }
        with self.assertRaisesRegex(restore.RecoveryError, "parent-file collision"):
            self.verify(create_archive(self.root, files=files))

    def test_enforces_archive_manifest_count_file_and_total_limits(self) -> None:
        oversized_archive = create_raw_archive(
            self.root, b"x" * (restore.MAX_ARCHIVE_SIZE + 1)
        )
        oversized_manifest = create_archive(
            self.root,
            manifest_bytes=b"{" + b" " * restore.MAX_MANIFEST_SIZE + b"}",
        )
        too_many_files = {
            f"service-local-state/config/file-{index:03d}.txt": b"x"
            for index in range(restore.MAX_FILE_COUNT + 1)
        }
        oversized_file = {
            "service-local-state/config/large.bin": b"x" * (restore.MAX_FILE_SIZE + 1)
        }
        oversized_total = {
            f"service-local-state/config/large-{index}.bin": b"x" * restore.MAX_FILE_SIZE
            for index in range((restore.MAX_TOTAL_SIZE // restore.MAX_FILE_SIZE) + 1)
        }

        cases = (
            oversized_archive,
            oversized_manifest,
            create_archive(self.root, files=too_many_files),
            create_archive(self.root, files=oversized_file),
            create_archive(self.root, files=oversized_total),
        )
        for fixture in cases:
            with self.subTest(path=fixture.path.name):
                with self.assertRaisesRegex(restore.RecoveryError, "limit"):
                    self.verify(fixture)

    def test_failed_staging_is_cleaned_without_creating_destination(self) -> None:
        fixture = create_archive(self.root)
        verified = self.verify(fixture)
        destination = self.root / "failed-restore"

        with patch("restore._write_staged_file", side_effect=OSError("synthetic failure")):
            with self.assertRaisesRegex(restore.RecoveryError, "transaction failed"):
                restore.restore_verified(verified, destination)

        self.assertFalse(destination.exists())
        self.assertFalse(list(self.root.glob(".failed-restore.recovery-*")))

    def test_post_publication_sync_failure_is_explicit_and_retains_destination(self) -> None:
        fixture = create_archive(self.root)
        destination = self.root / "ambiguous-durability"

        with patch(
            "restore._fsync_parent_descriptor",
            side_effect=OSError("synthetic parent sync failure"),
        ):
            with self.assertRaisesRegex(
                restore.RecoveryError, "published but parent synchronization failed"
            ):
                restore.restore_archive(
                    self.model,
                    "service-local-state",
                    fixture.path,
                    fixture.sha256,
                    destination,
                )

        self.assertTrue(destination.is_dir())
        self.assertFalse(list(self.root.glob(".ambiguous-durability.recovery-*")))

    def test_cli_expected_errors_are_single_line_without_tracebacks(self) -> None:
        fixture = create_archive(self.root)
        usage = self.run_cli(
            "verify",
            "--model",
            str(MODEL_PATH),
            "--boundary",
            "service-local-state",
            "--archive",
            str(fixture.path),
        )
        rejected = self.run_cli(
            "verify",
            "--model",
            str(MODEL_PATH),
            "--boundary",
            "service-local-state",
            "--archive",
            str(fixture.path),
            "--sha256",
            "0" * 64,
        )

        for result, expected_code in ((usage, 2), (rejected, 1)):
            with self.subTest(code=expected_code):
                self.assertEqual(expected_code, result.returncode)
                self.assertEqual("", result.stdout)
                self.assertEqual(1, len(result.stderr.splitlines()))
                self.assertTrue(result.stderr.startswith("recovery: ERROR:"))
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
