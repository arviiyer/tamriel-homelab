# Restore testing

A restore example that checks an archive and writes it to a new directory.
Includes generated test archives and a systemd unit that checks storage before
starting a service.

[Design notes](../../docs/case-studies/recovery-and-storage-dependencies.md) ·
[Restore drill](../../evidence/drills/2026-08-24-isolated-synthetic-restore.md)

## Try it

On Linux with Python 3, procfs, and `renameat2` support, run from the repository root:

```bash
python3 automation/recovery/tests/run_isolated_restore_drill.py
```

The drill generates archives, restores them, rejects corrupt or unsafe input,
and cleans up its temporary files.

## Verify and restore an archive

Using the same requirements, check the dataset definitions first:

```bash
python3 automation/recovery/restore.py validate-model \
  --model automation/recovery/recovery-model.json
```

For a test tar file you have already reviewed, calculate its checksum and verify it:

```bash
MODEL=automation/recovery/recovery-model.json
ARCHIVE=/tmp/reviewed-synthetic-recovery.tar
DIGEST=$(sha256sum "$ARCHIVE" | cut -d ' ' -f 1)
python3 automation/recovery/restore.py verify \
  --model "$MODEL" \
  --boundary service-local-state \
  --archive "$ARCHIVE" \
  --sha256 "$DIGEST"
```

For archives received from elsewhere, obtain the expected digest through an
independently trusted channel.

Restore to a new destination under a private parent directory:

```bash
RESTORE_ROOT=$(mktemp -d /tmp/reviewed-synthetic-recovery.XXXXXX)
chmod 0700 "$RESTORE_ROOT"
DESTINATION=$RESTORE_ROOT/restored-state
python3 automation/recovery/restore.py restore \
  --model "$MODEL" \
  --boundary service-local-state \
  --archive "$ARCHIVE" \
  --sha256 "$DIGEST" \
  --destination "$DESTINATION"
```

Success emits one JSON object. Usage errors exit `2`; rejected policy/input exits
`1`. Both emit a single `recovery: ERROR:` line without an expected-error traceback.

## Tests

Run the unit tests and check the service file with `systemd-analyze`:

```bash
python3 -m unittest discover -s automation/recovery/tests -p 'test_*.py' -v
systemd-analyze verify --recursive-errors=no \
  automation/recovery/systemd/example-storage-dependent.service
```

Tests cover dataset definitions, archive checks, restores, command-line errors,
cleanup, and systemd configuration.

## Model and archive format

[`recovery-model.json`](recovery-model.json) uses schema version `1` and separates
two datasets:

| Dataset (`--boundary`) | Archive roots | Excluded |
|---|---|---|
| `service-local-state` | `config/`, `state/` | Shared content, credentials, cache |
| `shared-bulk-data` | `catalog/`, `objects/` | Service-local state, credentials, temporary data |

Input is uncompressed tar containing regular files only, including
`manifest.json`. Payload paths start with the selected boundary's `archive_root`
and an included root. The outer archive root is stripped during restore.

The manifest has exactly these fields:

```text
schema_version, classification, backup_id, created_at, boundary,
files, file_count, total_size
```

Each sorted, unique `files` entry has `path`, `size`, and `sha256`; the inventory
must exactly match the payload. Classification is `synthetic-public-example`.
`created_at` uses `YYYY-MM-DDTHH:MM:SSZ`; `backup_id` uses the matching
`synthetic-YYYYMMDDTHHMMSSZ-label`. Nonzero data after the final tar member is
rejected. A whole-archive SHA-256 supplied outside the archive is mandatory.

| Input | Limit |
|---|---:|
| Model / manifest | 64 KiB each |
| Archive | 8 MiB |
| Payload files | 128 |
| One file | 1 MiB |
| Total payload | 4 MiB |

## Restore behavior

The verifier reads the archive into memory within the size limit and checks the
supplied digest before parsing. It avoids following links where supported and
checks all file contents before writing. It never calls tar `extract` or
`extractall`; replacing the source path cannot change the bytes already checked.

It rejects duplicate-key/malformed JSON, schema extensions, incorrect timestamps,
wrong datasets/roots, unsafe paths, backslashes, control characters, traversal,
missing/extra/duplicate members, parent-file collisions, and size/digest mismatch.
Directories, links, sparse files, devices, and FIFOs are also rejected.

The parent directory must belong to the user running the restore and cannot be
group- or world-writable. Writes use an open parent-directory descriptor so
replacing its path cannot redirect them. Staging starts at `0700`; final
directories use `0750` and files `0640`. Files are synced before an atomic
no-replace rename. Existing or concurrently created destinations are never
overwritten.

Failed staging is removed. If the rename succeeds but syncing the parent fails,
the command reports uncertain durability and keeps the destination for inspection.

## Storage checks

The [systemd unit](systemd/example-storage-dependent.service) orders startup after
`network-online.target`, requires mounts for `/srv/example-data`, and asserts that
the path is a read-write mount. Its `.storage-boundary` must exactly match the
[`shared-bulk-data` marker](systemd/shared-bulk-data.marker), installed separately
as `/usr/local/share/example-storage-boundary`.

It uses a temporary service user, restricted capabilities/filesystem/syscalls,
and a no-op `ExecStart` to replace with the workload command. The mount manager
handles mounting; the service checks storage at startup.

The archive stores regular files with fixed permissions. Pausing application
writes, restoring ownership/ACLs, and replacing live data are separate steps.
Encryption and signing belong in the backup/transfer tools. Root and processes
running as the restore user can access the destination.
