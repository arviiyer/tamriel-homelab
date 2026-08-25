#!/usr/bin/env python3
"""Validate and restore bounded synthetic recovery archives."""

from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import errno
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import shutil
import stat
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import NoReturn


SCHEMA_VERSION = 1
CLASSIFICATION = "synthetic-public-example"
BOUNDARY_NAMES = {"service-local-state", "shared-bulk-data"}
MODEL_KEYS = {"schema_version", "classification", "boundaries"}
BOUNDARY_KEYS = {
    "authority",
    "included",
    "excluded",
    "copy",
    "illustrative_retention",
    "restore_target",
    "manual_replacement_gate",
}
COPY_KEYS = {"archive_root", "format", "integrity"}
RETENTION_KEYS = {"classification", "generations"}
MANIFEST_KEYS = {
    "schema_version",
    "classification",
    "backup_id",
    "created_at",
    "boundary",
    "files",
    "file_count",
    "total_size",
}
FILE_KEYS = {"path", "size", "sha256"}

MAX_MODEL_SIZE = 64 * 1024
MAX_ARCHIVE_SIZE = 8 * 1024 * 1024
MAX_MANIFEST_SIZE = 64 * 1024
MAX_FILE_COUNT = 128
MAX_FILE_SIZE = 1024 * 1024
MAX_TOTAL_SIZE = 4 * 1024 * 1024
MAX_PATH_LENGTH = 255

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
TIMESTAMP_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
BACKUP_ID_PATTERN = re.compile(
    r"^synthetic-[0-9]{8}T[0-9]{6}Z-[a-z0-9](?:[a-z0-9-]{0,30}[a-z0-9])?$"
)
PATH_COMPONENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")

RENAME_NOREPLACE = 1


class RecoveryError(RuntimeError):
    """Raised when an input or recovery policy check fails."""


class UsageError(RuntimeError):
    """Raised for command-line usage errors."""


@dataclass(frozen=True)
class VerifiedFile:
    archive_path: str
    relative_path: PurePosixPath
    data: bytes
    sha256: str


@dataclass(frozen=True)
class VerifiedArchive:
    archive_sha256: str
    backup_id: str
    boundary: str
    created_at: str
    files: tuple[VerifiedFile, ...]
    total_size: int


class RecoveryArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise UsageError(message)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RecoveryError("JSON contains a duplicate object key")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> NoReturn:
    raise RecoveryError("JSON contains a non-standard numeric constant")


def _load_json(data: bytes, label: str) -> object:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RecoveryError(f"{label} is not valid UTF-8") from error
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except RecoveryError:
        raise
    except json.JSONDecodeError as error:
        raise RecoveryError(f"{label} is not valid JSON") from error


def _read_bounded_file(path: Path, limit: int, label: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise RecoveryError(f"{label} could not be opened safely") from error
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise RecoveryError(f"{label} must be a regular file")
        if metadata.st_size > limit:
            raise RecoveryError(f"{label} exceeds its size limit")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(64 * 1024, limit + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > limit:
                raise RecoveryError(f"{label} exceeds its size limit")
        return b"".join(chunks)
    except OSError as error:
        raise RecoveryError(f"{label} could not be read safely") from error
    finally:
        os.close(descriptor)


def _require_exact_keys(value: object, keys: set[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        raise RecoveryError(f"{label} has an unexpected schema")
    return value


def _require_text(value: object, label: str, maximum: int = 300) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise RecoveryError(f"{label} must be a non-empty bounded string")
    if not value.isascii() or any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise RecoveryError(f"{label} must contain printable ASCII only")
    return value


def _safe_relative_parts(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, str) or not value or len(value) > MAX_PATH_LENGTH:
        raise RecoveryError(f"{label} is not a safe relative path")
    if "\\" in value or value.startswith("/") or value.endswith("/"):
        raise RecoveryError(f"{label} is not a safe relative path")
    parts = value.split("/")
    if any(
        part in {"", ".", ".."} or PATH_COMPONENT_PATTERN.fullmatch(part) is None
        for part in parts
    ):
        raise RecoveryError(f"{label} is not a safe relative path")
    return tuple(parts)


def _validate_path_list(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise RecoveryError(f"{label} must be a non-empty list")
    paths: list[str] = []
    for item in value:
        _safe_relative_parts(item, label)
        if item in paths:
            raise RecoveryError(f"{label} contains a duplicate path")
        paths.append(item)
    if paths != sorted(paths):
        raise RecoveryError(f"{label} must be sorted")
    return tuple(paths)


def _paths_overlap(left: str, right: str) -> bool:
    return left == right or left.startswith(f"{right}/") or right.startswith(f"{left}/")


def validate_model(payload: object) -> dict[str, object]:
    model = _require_exact_keys(payload, MODEL_KEYS, "recovery model")
    if type(model["schema_version"]) is not int or model["schema_version"] != SCHEMA_VERSION:
        raise RecoveryError("recovery model schema_version must be 1")
    if model["classification"] != CLASSIFICATION:
        raise RecoveryError("recovery model classification is invalid")

    boundaries = model["boundaries"]
    if not isinstance(boundaries, dict) or set(boundaries) != BOUNDARY_NAMES:
        raise RecoveryError("recovery model must define exactly the two public boundaries")

    for boundary_name in sorted(BOUNDARY_NAMES):
        boundary = _require_exact_keys(
            boundaries[boundary_name], BOUNDARY_KEYS, f"{boundary_name} boundary"
        )
        _require_text(boundary["authority"], f"{boundary_name} authority")
        included = _validate_path_list(
            boundary["included"], f"{boundary_name} included"
        )
        excluded = _validate_path_list(
            boundary["excluded"], f"{boundary_name} excluded"
        )
        if any(_paths_overlap(left, right) for left in included for right in excluded):
            raise RecoveryError(f"{boundary_name} included and excluded roots overlap")

        copy_policy = _require_exact_keys(
            boundary["copy"], COPY_KEYS, f"{boundary_name} copy policy"
        )
        if copy_policy != {
            "archive_root": boundary_name,
            "format": "uncompressed-tar",
            "integrity": "external-sha256",
        }:
            raise RecoveryError(f"{boundary_name} copy policy is invalid")

        retention = _require_exact_keys(
            boundary["illustrative_retention"],
            RETENTION_KEYS,
            f"{boundary_name} illustrative retention",
        )
        if retention["classification"] != "illustrative-only":
            raise RecoveryError(f"{boundary_name} retention must be illustrative only")
        generations = retention["generations"]
        if not isinstance(generations, list) or not generations:
            raise RecoveryError(f"{boundary_name} generations must be a non-empty list")
        observed_generations: set[str] = set()
        for generation in generations:
            _safe_relative_parts(generation, f"{boundary_name} generation")
            if generation in observed_generations:
                raise RecoveryError(f"{boundary_name} generations contain a duplicate")
            observed_generations.add(generation)

        _require_text(boundary["restore_target"], f"{boundary_name} restore target")
        _require_text(
            boundary["manual_replacement_gate"],
            f"{boundary_name} manual replacement gate",
        )
    return model


def load_model(path: Path) -> dict[str, object]:
    return validate_model(
        _load_json(_read_bounded_file(path, MAX_MODEL_SIZE, "recovery model"), "recovery model")
    )


def _validate_timestamp(value: object) -> str:
    if not isinstance(value, str) or TIMESTAMP_PATTERN.fullmatch(value) is None:
        raise RecoveryError("manifest created_at must be a canonical UTC timestamp")
    try:
        parsed = dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise RecoveryError("manifest created_at must be a canonical UTC timestamp") from error
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise RecoveryError("manifest created_at must be a canonical UTC timestamp")
    return value


def _validate_manifest(
    payload: object, model: dict[str, object], selected_boundary: str
) -> tuple[dict[str, object], tuple[dict[str, object], ...]]:
    manifest = _require_exact_keys(payload, MANIFEST_KEYS, "archive manifest")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != SCHEMA_VERSION:
        raise RecoveryError("archive manifest schema_version must be 1")
    if manifest["classification"] != CLASSIFICATION:
        raise RecoveryError("archive manifest classification is invalid")
    if selected_boundary not in BOUNDARY_NAMES:
        raise RecoveryError("selected boundary is not defined by the recovery model")
    if manifest["boundary"] != selected_boundary:
        raise RecoveryError("archive boundary does not match the selected boundary")

    created_at = _validate_timestamp(manifest["created_at"])
    backup_id = manifest["backup_id"]
    if not isinstance(backup_id, str) or BACKUP_ID_PATTERN.fullmatch(backup_id) is None:
        raise RecoveryError("manifest backup_id is not a conservative synthetic identifier")
    timestamp_token = created_at.replace("-", "").replace(":", "")
    if not backup_id.startswith(f"synthetic-{timestamp_token}-"):
        raise RecoveryError("manifest backup_id timestamp does not match created_at")

    files_value = manifest["files"]
    if not isinstance(files_value, list) or not files_value:
        raise RecoveryError("archive manifest files must be a non-empty list")
    if len(files_value) > MAX_FILE_COUNT:
        raise RecoveryError("archive manifest exceeds the file-count limit")
    if type(manifest["file_count"]) is not int or manifest["file_count"] != len(files_value):
        raise RecoveryError("archive manifest file_count does not match its inventory")
    if type(manifest["total_size"]) is not int or not 0 <= manifest["total_size"] <= MAX_TOTAL_SIZE:
        raise RecoveryError("archive manifest total_size is invalid or exceeds its limit")

    boundary_policy = model["boundaries"][selected_boundary]
    archive_root = boundary_policy["copy"]["archive_root"]
    included_roots = tuple(boundary_policy["included"])
    files: list[dict[str, object]] = []
    paths: list[str] = []
    calculated_total = 0
    for index, raw_file in enumerate(files_value):
        entry = _require_exact_keys(raw_file, FILE_KEYS, f"manifest file {index}")
        parts = _safe_relative_parts(entry["path"], f"manifest file {index} path")
        if parts[0] != archive_root or len(parts) < 3:
            raise RecoveryError("manifest file is outside the selected archive root")
        relative = "/".join(parts[1:])
        if not any(relative.startswith(f"{root}/") for root in included_roots):
            raise RecoveryError("manifest file is outside the boundary's included roots")
        size = entry["size"]
        if type(size) is not int or not 0 <= size <= MAX_FILE_SIZE:
            raise RecoveryError("manifest file size is invalid or exceeds its limit")
        digest = entry["sha256"]
        if not isinstance(digest, str) or SHA256_PATTERN.fullmatch(digest) is None:
            raise RecoveryError("manifest file SHA-256 is invalid")
        path = entry["path"]
        if path in paths:
            raise RecoveryError("archive manifest contains a duplicate file path")
        paths.append(path)
        calculated_total += size
        if calculated_total > MAX_TOTAL_SIZE:
            raise RecoveryError("archive manifest exceeds the total-size limit")
        files.append(entry)

    if paths != sorted(paths):
        raise RecoveryError("archive manifest inventory must be sorted by path")
    path_set = set(paths)
    for path in paths:
        parents = PurePosixPath(path).parents
        if any(str(parent) in path_set for parent in parents if str(parent) != "."):
            raise RecoveryError("archive manifest contains a parent-file collision")
    if calculated_total != manifest["total_size"]:
        raise RecoveryError("archive manifest total_size does not match its inventory")
    return manifest, tuple(files)


def _read_tar_member(archive: tarfile.TarFile, member: tarfile.TarInfo, limit: int) -> bytes:
    handle = archive.extractfile(member)
    if handle is None:
        raise RecoveryError("archive regular-file data is unavailable")
    try:
        data = handle.read(limit + 1)
        if len(data) > limit:
            raise RecoveryError("archive member exceeds its size limit")
        if len(data) != member.size:
            raise RecoveryError("archive member data is truncated")
        return data
    except (OSError, tarfile.TarError) as error:
        raise RecoveryError("archive member data could not be read") from error
    finally:
        handle.close()


def verify_archive(
    model: dict[str, object], selected_boundary: str, archive_path: Path, expected_sha256: str
) -> VerifiedArchive:
    validate_model(model)
    if SHA256_PATTERN.fullmatch(expected_sha256) is None:
        raise RecoveryError("external SHA-256 must be 64 lowercase hexadecimal characters")
    archive_bytes = _read_bounded_file(archive_path, MAX_ARCHIVE_SIZE, "archive")
    observed_sha256 = hashlib.sha256(archive_bytes).hexdigest()
    if not hmac.compare_digest(observed_sha256, expected_sha256):
        raise RecoveryError("archive does not match the external SHA-256")

    try:
        archive = tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:", errorlevel=2)
    except (tarfile.TarError, OSError, ValueError) as error:
        raise RecoveryError("archive is not a valid uncompressed tar file") from error

    try:
        members: dict[str, tarfile.TarInfo] = {}
        for member in archive:
            if len(members) >= MAX_FILE_COUNT + 1:
                raise RecoveryError("archive exceeds the member-count limit")
            _safe_relative_parts(member.name, "archive member path")
            if member.name in members:
                raise RecoveryError("archive contains a duplicate member")
            if member.issparse():
                raise RecoveryError("archive sparse members are not allowed")
            if not member.isreg():
                raise RecoveryError("archive members must all be regular files")
            member_limit = MAX_MANIFEST_SIZE if member.name == "manifest.json" else MAX_FILE_SIZE
            if member.size < 0 or member.size > member_limit:
                raise RecoveryError("archive member exceeds its size limit")
            members[member.name] = member

        data_end = max(
            (
                member.offset_data
                + ((member.size + tarfile.BLOCKSIZE - 1) // tarfile.BLOCKSIZE)
                * tarfile.BLOCKSIZE
                for member in members.values()
            ),
            default=0,
        )
        trailer = archive_bytes[data_end:]
        if (
            len(trailer) < tarfile.BLOCKSIZE * 2
            or len(trailer) % tarfile.BLOCKSIZE != 0
            or any(trailer)
        ):
            raise RecoveryError("archive contains data after its final member")

        manifest_member = members.get("manifest.json")
        if manifest_member is None:
            raise RecoveryError("archive must contain exactly one manifest.json")
        manifest_data = _read_tar_member(archive, manifest_member, MAX_MANIFEST_SIZE)
        manifest, inventory = _validate_manifest(
            _load_json(manifest_data, "archive manifest"), model, selected_boundary
        )

        expected_members = {"manifest.json", *(entry["path"] for entry in inventory)}
        if set(members) != expected_members:
            raise RecoveryError("archive members do not exactly match the manifest inventory")

        verified_files: list[VerifiedFile] = []
        observed_total = 0
        for entry in inventory:
            path = entry["path"]
            member = members[path]
            if member.size != entry["size"]:
                raise RecoveryError("archive member size does not match the manifest")
            data = _read_tar_member(archive, member, MAX_FILE_SIZE)
            digest = hashlib.sha256(data).hexdigest()
            if not hmac.compare_digest(digest, entry["sha256"]):
                raise RecoveryError("archive member SHA-256 does not match the manifest")
            parts = PurePosixPath(path).parts
            verified_files.append(
                VerifiedFile(
                    archive_path=path,
                    relative_path=PurePosixPath(*parts[1:]),
                    data=data,
                    sha256=digest,
                )
            )
            observed_total += len(data)
        if observed_total != manifest["total_size"]:
            raise RecoveryError("verified file bytes do not match manifest total_size")
        return VerifiedArchive(
            archive_sha256=observed_sha256,
            backup_id=manifest["backup_id"],
            boundary=selected_boundary,
            created_at=manifest["created_at"],
            files=tuple(verified_files),
            total_size=observed_total,
        )
    except (tarfile.TarError, OSError, ValueError) as error:
        raise RecoveryError("archive structure could not be read safely") from error
    finally:
        archive.close()


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_staged_file(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o640)
    try:
        os.fchmod(descriptor, 0o640)
        offset = 0
        while offset < len(data):
            offset += os.write(descriptor, data[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_rename_no_replace(
    parent_descriptor: int, source_name: str, destination_name: str
) -> None:
    library = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(library, "renameat2", None)
    if renameat2 is None:
        raise RecoveryError("atomic no-replace rename is unavailable on this platform")
    renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameat2.restype = ctypes.c_int
    result = renameat2(
        parent_descriptor,
        os.fsencode(source_name),
        parent_descriptor,
        os.fsencode(destination_name),
        RENAME_NOREPLACE,
    )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number == errno.EEXIST:
        raise RecoveryError("restore destination already exists")
    raise RecoveryError("atomic no-replace rename failed")


def _entry_exists(parent_descriptor: int, name: str) -> bool:
    try:
        os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return False
    except OSError as error:
        raise RecoveryError("restore destination could not be checked safely") from error
    return True


def _parent_path_matches_descriptor(path: Path, descriptor: int) -> bool:
    try:
        path_metadata = path.stat(follow_symlinks=False)
        descriptor_metadata = os.fstat(descriptor)
    except OSError:
        return False
    return (
        stat.S_ISDIR(path_metadata.st_mode)
        and path_metadata.st_dev == descriptor_metadata.st_dev
        and path_metadata.st_ino == descriptor_metadata.st_ino
    )


def _create_staging_directory(
    parent_descriptor: int, destination_name: str
) -> tuple[str, Path]:
    proc_parent = Path(f"/proc/self/fd/{parent_descriptor}")
    if not proc_parent.is_dir():
        raise RecoveryError("stable parent-directory access is unavailable")
    for _ in range(128):
        staging_name = f".{destination_name}.recovery-{secrets.token_hex(8)}"
        try:
            os.mkdir(staging_name, mode=0o700, dir_fd=parent_descriptor)
        except FileExistsError:
            continue
        except OSError as error:
            raise RecoveryError("restore staging directory could not be created") from error
        return staging_name, proc_parent / staging_name
    raise RecoveryError("restore staging name could not be allocated")


def _fsync_parent_descriptor(descriptor: int) -> None:
    os.fsync(descriptor)


def restore_verified(verified: VerifiedArchive, destination: Path) -> None:
    if destination.name in {"", ".", ".."} or PATH_COMPONENT_PATTERN.fullmatch(destination.name) is None:
        raise RecoveryError("restore destination must have a conservative final path component")
    parent = destination.parent
    if parent.is_symlink():
        raise RecoveryError("restore destination parent must not be a symlink")
    parent_flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        parent_descriptor = os.open(parent, parent_flags)
    except OSError as error:
        raise RecoveryError("restore destination parent is unavailable") from error

    staging: Path | None = None
    staging_name: str | None = None
    installed = False
    try:
        parent_metadata = os.fstat(parent_descriptor)
        if not stat.S_ISDIR(parent_metadata.st_mode):
            raise RecoveryError("restore destination parent must be a directory")
        if parent_metadata.st_uid != os.geteuid() or parent_metadata.st_mode & 0o022:
            raise RecoveryError(
                "restore destination parent must be owned by the restore identity "
                "and not group- or world-writable"
            )
        if _entry_exists(parent_descriptor, destination.name):
            raise RecoveryError("restore destination already exists")
        staging_name, staging = _create_staging_directory(
            parent_descriptor, destination.name
        )
        os.chmod(staging, 0o700)
        created_directories = {staging}
        for verified_file in verified.files:
            target = staging.joinpath(*verified_file.relative_path.parts)
            current = staging
            for component in verified_file.relative_path.parts[:-1]:
                current = current / component
                if current not in created_directories:
                    current.mkdir(mode=0o750)
                    os.chmod(current, 0o750)
                    created_directories.add(current)
            _write_staged_file(target, verified_file.data)

        for directory in sorted(created_directories, key=lambda item: len(item.parts), reverse=True):
            if directory == staging:
                continue
            os.chmod(directory, 0o750)
            _fsync_directory(directory)
        os.chmod(staging, 0o750)
        _fsync_directory(staging)
        if not _parent_path_matches_descriptor(parent, parent_descriptor):
            raise RecoveryError("restore destination parent changed during staging")
        if _entry_exists(parent_descriptor, destination.name):
            raise RecoveryError("restore destination already exists")
        _atomic_rename_no_replace(
            parent_descriptor, staging_name, destination.name
        )
        installed = True
        try:
            _fsync_parent_descriptor(parent_descriptor)
        except OSError as error:
            raise RecoveryError(
                "restore was published but parent synchronization failed; "
                "destination retained for review"
            ) from error
    except RecoveryError:
        raise
    except OSError as error:
        raise RecoveryError("restore transaction failed") from error
    finally:
        if staging is not None and not installed and os.path.lexists(staging):
            shutil.rmtree(staging)
            try:
                _fsync_parent_descriptor(parent_descriptor)
            except OSError:
                pass
        os.close(parent_descriptor)


def restore_archive(
    model: dict[str, object],
    selected_boundary: str,
    archive_path: Path,
    expected_sha256: str,
    destination: Path,
) -> VerifiedArchive:
    verified = verify_archive(model, selected_boundary, archive_path, expected_sha256)
    restore_verified(verified, destination)
    return verified


def _success_payload(verified: VerifiedArchive, status: str) -> dict[str, object]:
    return {
        "archive_sha256": verified.archive_sha256,
        "backup_id": verified.backup_id,
        "boundary": verified.boundary,
        "created_at": verified.created_at,
        "file_count": len(verified.files),
        "status": status,
        "total_size": verified.total_size,
    }


def _build_parser() -> RecoveryArgumentParser:
    parser = RecoveryArgumentParser(prog="recovery", add_help=True)
    commands = parser.add_subparsers(dest="command", required=True)

    validate_parser = commands.add_parser("validate-model")
    validate_parser.add_argument("--model", required=True, type=Path)

    for command in ("verify", "restore"):
        command_parser = commands.add_parser(command)
        command_parser.add_argument("--model", required=True, type=Path)
        command_parser.add_argument("--boundary", required=True)
        command_parser.add_argument("--archive", required=True, type=Path)
        command_parser.add_argument("--sha256", required=True)
        if command == "restore":
            command_parser.add_argument("--destination", required=True, type=Path)
    return parser


def main(arguments: list[str]) -> int:
    options = _build_parser().parse_args(arguments)
    model = load_model(options.model)
    if options.command == "validate-model":
        print(
            json.dumps(
                {
                    "boundaries": sorted(BOUNDARY_NAMES),
                    "classification": CLASSIFICATION,
                    "schema_version": SCHEMA_VERSION,
                    "status": "valid",
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0

    if options.command == "verify":
        verified = verify_archive(model, options.boundary, options.archive, options.sha256)
        payload = _success_payload(verified, "verified")
    else:
        verified = restore_archive(
            model,
            options.boundary,
            options.archive,
            options.sha256,
            options.destination,
        )
        payload = _success_payload(verified, "restored")
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    return 0


def _safe_error_text(error: Exception) -> str:
    return "".join(
        character if character.isprintable() and character not in "\r\n" else "?"
        for character in str(error)
    )


def entrypoint(arguments: list[str]) -> int:
    try:
        return main(arguments)
    except UsageError as error:
        print(f"recovery: ERROR: {_safe_error_text(error)}", file=sys.stderr)
        return 2
    except RecoveryError as error:
        print(f"recovery: ERROR: {_safe_error_text(error)}", file=sys.stderr)
        return 1
    except Exception:
        print("recovery: ERROR: unexpected recovery failure", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(entrypoint(sys.argv[1:]))
