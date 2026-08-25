#!/usr/bin/env python3
"""Run an offline, unprivileged restore drill against synthetic archives."""

from __future__ import annotations

import os
import stat
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


RECOVERY_ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(RECOVERY_ROOT))
sys.path.insert(0, str(TEST_ROOT))

import restore  # noqa: E402
from archive_factory import MemberSpec, corrupt_archive, create_archive  # noqa: E402


def require_rejected(operation) -> None:
    try:
        operation()
    except restore.RecoveryError:
        return
    raise RuntimeError("synthetic rejection scenario unexpectedly succeeded")


def run_drill() -> None:
    if os.geteuid() == 0:
        raise RuntimeError("the isolated restore drill must not run as root")

    model = restore.load_model(RECOVERY_ROOT / "recovery-model.json")
    print("PASS synthetic recovery model validation")

    temporary_path: Path | None = None
    with tempfile.TemporaryDirectory(prefix="synthetic-recovery-drill-") as temporary_name:
        root = Path(temporary_name)
        temporary_path = root
        valid = create_archive(root)
        preflight = restore.verify_archive(
            model,
            "service-local-state",
            valid.path,
            valid.sha256,
        )
        if preflight.archive_sha256 != valid.sha256:
            raise RuntimeError("verified synthetic archive digest differs")
        destination = root / "valid-restore"
        verified = restore.restore_archive(
            model,
            "service-local-state",
            valid.path,
            valid.sha256,
            destination,
        )
        for verified_file in verified.files:
            target = destination.joinpath(*verified_file.relative_path.parts)
            if target.read_bytes() != verified_file.data:
                raise RuntimeError("restored synthetic bytes differ")
            if stat.S_IMODE(target.stat().st_mode) != 0o640:
                raise RuntimeError("restored synthetic file mode differs")
        expected_files = {
            str(verified_file.relative_path) for verified_file in verified.files
        }
        observed_files = {
            str(path.relative_to(destination))
            for path in destination.rglob("*")
            if path.is_file()
        }
        if observed_files != expected_files:
            raise RuntimeError("restored synthetic inventory differs")
        directories = [destination, *(path for path in destination.rglob("*") if path.is_dir())]
        if any(stat.S_IMODE(path.stat().st_mode) != 0o750 for path in directories):
            raise RuntimeError("restored synthetic directory mode differs")
        print("PASS valid archive verification and isolated restore")

        corrupted = corrupt_archive(root, valid)
        corrupted_destination = root / "corrupted-restore"
        require_rejected(
            lambda: restore.restore_archive(
                model,
                "service-local-state",
                corrupted.path,
                valid.sha256,
                corrupted_destination,
            )
        )
        print("PASS corrupted archive rejection with original external digest")

        outside = root / "outside.txt"
        traversal = create_archive(
            root,
            files={"../outside.txt": b"synthetic traversal\n"},
        )
        traversal_destination = root / "traversal-restore"
        require_rejected(
            lambda: restore.restore_archive(
                model,
                "service-local-state",
                traversal.path,
                traversal.sha256,
                traversal_destination,
            )
        )
        print("PASS traversal archive rejection")

        symlink = create_archive(
            root,
            members=[
                MemberSpec(
                    "service-local-state/config/application.json",
                    kind="symlink",
                    linkname="../../outside.txt",
                ),
                MemberSpec("service-local-state/state/records.txt", b"alpha\nbeta\n"),
            ],
        )
        symlink_destination = root / "symlink-restore"
        require_rejected(
            lambda: restore.restore_archive(
                model,
                "service-local-state",
                symlink.path,
                symlink.sha256,
                symlink_destination,
            )
        )
        print("PASS symlink archive rejection")

        wrong_boundary = create_archive(root, boundary="shared-bulk-data")
        boundary_destination = root / "boundary-restore"
        require_rejected(
            lambda: restore.restore_archive(
                model,
                "service-local-state",
                wrong_boundary.path,
                wrong_boundary.sha256,
                boundary_destination,
            )
        )
        print("PASS wrong-boundary archive rejection")

        staging_failure_destination = root / "staging-failure-restore"
        with patch(
            "restore._write_staged_file",
            side_effect=OSError("synthetic staging failure"),
        ):
            require_rejected(
                lambda: restore.restore_archive(
                    model,
                    "service-local-state",
                    valid.path,
                    valid.sha256,
                    staging_failure_destination,
                )
            )
        print("PASS failed-staging cleanup")

        failed_destinations = (
            corrupted_destination,
            traversal_destination,
            symlink_destination,
            boundary_destination,
            staging_failure_destination,
        )
        if any(os.path.lexists(path) for path in (*failed_destinations, outside)):
            raise RuntimeError("a rejected archive changed an asserted path")
        if list(root.glob(".*.recovery-*")):
            raise RuntimeError("a restore staging directory remains")
        print("PASS failed destination and outside-path absence")

    if temporary_path is None or temporary_path.exists():
        raise RuntimeError("temporary drill workspace was not removed")
    print("PASS temporary workspace cleanup")


def main() -> int:
    try:
        run_drill()
    except Exception:
        print("FAIL isolated synthetic restore drill", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
