"""Build synthetic recovery tar archives in temporary test directories."""

from __future__ import annotations

import copy
import gzip
import hashlib
import io
import json
import os
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


CREATED_AT = "2026-08-24T12:00:00Z"
BACKUP_IDS = {
    "service-local-state": "synthetic-20260824T120000Z-service-state",
    "shared-bulk-data": "synthetic-20260824T120000Z-shared-data",
}
DEFAULT_FILES = {
    "service-local-state": {
        "service-local-state/config/application.json": b'{"mode":"synthetic"}\n',
        "service-local-state/state/records.txt": b"alpha\nbeta\n",
    },
    "shared-bulk-data": {
        "shared-bulk-data/catalog/index.txt": b"object-a\nobject-b\n",
        "shared-bulk-data/objects/object-a.txt": b"synthetic bulk content\n",
    },
}


@dataclass(frozen=True)
class MemberSpec:
    name: str
    data: bytes = b""
    kind: str = "file"
    linkname: str = ""


@dataclass(frozen=True)
class ArchiveFixture:
    path: Path
    sha256: str
    manifest: dict[str, object] | None
    files: dict[str, bytes]


def build_manifest(
    boundary: str, files: Mapping[str, bytes]
) -> dict[str, object]:
    inventory = [
        {
            "path": path,
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        }
        for path, data in sorted(files.items())
    ]
    return {
        "backup_id": BACKUP_IDS[boundary],
        "boundary": boundary,
        "classification": "synthetic-public-example",
        "created_at": CREATED_AT,
        "file_count": len(inventory),
        "files": inventory,
        "schema_version": 1,
        "total_size": sum(len(data) for data in files.values()),
    }


def _temporary_path(directory: Path, prefix: str = "synthetic-") -> Path:
    descriptor, name = tempfile.mkstemp(prefix=prefix, suffix=".tar", dir=directory)
    os.close(descriptor)
    return Path(name)


def _add_member(archive: tarfile.TarFile, spec: MemberSpec) -> None:
    member = tarfile.TarInfo(spec.name)
    member.mode = 0o640
    member.mtime = 0
    member.uid = 0
    member.gid = 0
    member.uname = ""
    member.gname = ""

    if spec.kind == "file":
        member.size = len(spec.data)
        archive.addfile(member, io.BytesIO(spec.data))
    elif spec.kind == "directory":
        member.type = tarfile.DIRTYPE
        member.mode = 0o750
        archive.addfile(member)
    elif spec.kind == "symlink":
        member.type = tarfile.SYMTYPE
        member.linkname = spec.linkname
        archive.addfile(member)
    elif spec.kind == "hardlink":
        member.type = tarfile.LNKTYPE
        member.linkname = spec.linkname
        archive.addfile(member)
    elif spec.kind == "fifo":
        member.type = tarfile.FIFOTYPE
        archive.addfile(member)
    elif spec.kind == "character":
        member.type = tarfile.CHRTYPE
        member.devmajor = 1
        member.devminor = 3
        archive.addfile(member)
    elif spec.kind == "block":
        member.type = tarfile.BLKTYPE
        member.devmajor = 7
        member.devminor = 0
        archive.addfile(member)
    elif spec.kind == "sparse":
        member.size = len(spec.data)
        member.pax_headers = {
            "GNU.sparse.map": f"0,{len(spec.data)}",
            "GNU.sparse.realsize": "4096",
            "GNU.sparse.size": "4096",
        }
        archive.addfile(member, io.BytesIO(spec.data))
    else:
        raise ValueError(f"unknown synthetic member kind: {spec.kind}")


def create_archive(
    directory: Path,
    *,
    boundary: str = "service-local-state",
    files: Mapping[str, bytes] | None = None,
    manifest: dict[str, object] | None = None,
    manifest_bytes: bytes | None = None,
    members: Sequence[MemberSpec] | None = None,
) -> ArchiveFixture:
    selected_files = dict(DEFAULT_FILES[boundary] if files is None else files)
    selected_manifest = (
        build_manifest(boundary, selected_files)
        if manifest is None
        else copy.deepcopy(manifest)
    )
    serialized_manifest = (
        json.dumps(selected_manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
        + b"\n"
        if manifest_bytes is None
        else manifest_bytes
    )
    selected_members = (
        [MemberSpec(path, data) for path, data in sorted(selected_files.items())]
        if members is None
        else list(members)
    )
    tar_format = (
        tarfile.PAX_FORMAT
        if any(member.kind == "sparse" for member in selected_members)
        else tarfile.USTAR_FORMAT
    )
    path = _temporary_path(directory)
    with tarfile.open(path, mode="w", format=tar_format) as archive:
        _add_member(archive, MemberSpec("manifest.json", serialized_manifest))
        for member in selected_members:
            _add_member(archive, member)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return ArchiveFixture(path, digest, selected_manifest, selected_files)


def create_raw_archive(directory: Path, data: bytes) -> ArchiveFixture:
    path = _temporary_path(directory, prefix="raw-")
    path.write_bytes(data)
    return ArchiveFixture(path, hashlib.sha256(data).hexdigest(), None, {})


def compress_archive(directory: Path, fixture: ArchiveFixture) -> ArchiveFixture:
    data = gzip.compress(fixture.path.read_bytes(), mtime=0)
    path = _temporary_path(directory, prefix="compressed-")
    path.write_bytes(data)
    return ArchiveFixture(path, hashlib.sha256(data).hexdigest(), fixture.manifest, fixture.files)


def corrupt_archive(directory: Path, fixture: ArchiveFixture) -> ArchiveFixture:
    data = bytearray(fixture.path.read_bytes())
    if not data:
        raise ValueError("cannot corrupt an empty fixture")
    data[len(data) // 2] ^= 0x01
    path = _temporary_path(directory, prefix="corrupted-")
    path.write_bytes(data)
    return ArchiveFixture(path, hashlib.sha256(data).hexdigest(), fixture.manifest, fixture.files)
