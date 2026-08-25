# Synthetic Recovery Evidence

Status: **Publicly evidenced synthetic restore and executable storage policy**.
This purpose-written component validates and restores bounded synthetic archives
in an isolated local directory. It does not claim that PBS, Restic, VM backup, or
any other private backup operation has been implemented, validated, or operated.

The evidence demonstrates two decisions: recovery inputs should fail closed
before writing data, and a storage-dependent service should not start merely
because its expected path exists. Everything here uses synthetic content and
public placeholder paths.

## Recovery Model

[`recovery-model.json`](recovery-model.json) is a strict schema-version `1`
example with exactly two authority boundaries:

| Boundary | Authority represented by the example | Included archive roots | Deliberately separate |
|---|---|---|---|
| `service-local-state` | Application-owned local state | `config/`, `state/` | Shared content, credentials, and runtime cache |
| `shared-bulk-data` | Shared content storage | `catalog/`, `objects/` | Service-local state, credentials, and temporary data |

Each boundary defines its authority, included and excluded roots, copy format,
illustrative generation labels, isolated restore target, and manual replacement
gate. The generation labels are examples, not a schedule or an operated
retention policy. The boundaries prevent a valid archive for one authority from
being accepted as a restore for the other.

## Archive Format

The input is an uncompressed tar file. `manifest.json` and every payload member
must be regular files; the archive contains no directory entries. Payload paths
begin with the selected boundary's exact `archive_root`, followed by one of that
boundary's included roots. The archive root is removed when files are installed
under the requested destination.

The manifest has exactly these top-level fields:

```text
schema_version, classification, backup_id, created_at, boundary,
files, file_count, total_size
```

Each `files` entry has exactly `path`, `size`, and `sha256`. The inventory is
sorted, unique, complete, and must exactly equal the tar member set other than
`manifest.json`. Nonzero data after the final member is rejected. `created_at`
uses `YYYY-MM-DDTHH:MM:SSZ`, and `backup_id` uses a matching
`synthetic-YYYYMMDDTHHMMSSZ-label` form. The fixed classification is
`synthetic-public-example`.

An expected SHA-256 for the complete tar file is mandatory and is supplied
outside the archive. Internal file digests do not replace that external
integrity check.

Resource limits are part of the input policy:

| Input | Limit |
|---|---:|
| Recovery model | 64 KiB |
| Complete archive | 8 MiB |
| Manifest | 64 KiB |
| Payload files | 128 |
| One payload file | 1 MiB |
| All payload bytes | 4 MiB |

## CLI

Run from the repository root. Model validation requires no archive:

```bash
python3 automation/recovery/restore.py validate-model \
  --model automation/recovery/recovery-model.json
```

For a separately reviewed synthetic tar file, calculate its digest outside the
archive and verify it without writing a destination:

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

Restore that synthetic archive only to a new destination:

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

Successful commands emit one deterministic JSON object. Usage failures emit one
`recovery: ERROR:` line and exit `2`; rejected policy or input emits the same
single-line prefix and exits `1`. Expected failures do not produce tracebacks.

## Safety Behavior

The verifier reads the archive through a no-follow file open where the platform
provides it, bounds the complete byte snapshot in memory, and checks the external
digest before parsing tar metadata. It uses no `extract` or `extractall` call.
All member bytes and digests are validated before a staging path is created, so
path replacement after validation cannot change the bytes being restored.

The policy rejects malformed or duplicate-key JSON, schema extensions, a wrong
boundary or root, noncanonical timestamps, unsafe relative paths, backslashes,
control characters, traversal, duplicate or unlisted members, missing members,
parent-file collisions, and declared or observed size and digest mismatches. It
also rejects directories, symbolic links, hard links, sparse files, devices,
and FIFOs.

Restore creates a random hidden sibling staging directory with mode `0700` while
it writes. Final directories are fixed to `0750`, files to `0640`, and every file
is synchronized before publication. Only after complete validation and staging
does a Linux no-replace atomic rename publish the destination. An existing or
concurrently created destination is never overwritten. Failed transactions
remove their staging directory.

The destination parent must be owned by the restore identity and cannot be
group- or world-writable. The restore holds an open descriptor for that trusted
parent and creates, checks, and publishes staging entries relative to the
descriptor. Replacement of the parent pathname cannot redirect writes. If
publication succeeds but synchronizing the parent directory fails, the command
reports ambiguous durability and retains the visible destination for review.

## Storage Dependency Policy

[`systemd/example-storage-dependent.service`](systemd/example-storage-dependent.service)
is a static synthetic unit. It:

- wants and starts after `network-online.target`;
- uses `RequiresMountsFor=/srv/example-data`;
- asserts that `/srv/example-data` is a mount point and is read-write;
- requires `/srv/example-data/.storage-boundary` to exactly match the public
  [`shared-bulk-data` marker](systemd/shared-bulk-data.marker);
- uses an absolute no-op placeholder `ExecStart`; and
- applies a constrained dynamic identity, empty capabilities, filesystem and
  kernel protection, syscall filtering, and a restrictive umask.

The pre-start check neither mounts storage nor runs a shell, network command, or
sleep-based readiness loop. The mount manager and storage platform remain
outside this static example. A deployment must install the tracked marker as
`/usr/local/share/example-storage-boundary`; this repository does not perform
that installation.

## Threat And Failure Model

The component treats an archive and its manifest as untrusted input. It is
designed to fail closed for corruption, a stale or incorrect external digest,
schema ambiguity, boundary confusion, unsafe tar metadata, unexpected
inventory, resource-exhaustion attempts within the documented limits,
destination collisions, shared-writable destination parents, and local write
failures. Before publication, rejection must leave the requested destination and
any traversal target absent. Post-publication synchronization failure follows
the explicit retained-destination behavior described above.

The external digest detects accidental corruption and replacement only when the
expected value arrives through a trusted independent channel. An attacker who
can replace both the archive and expected digest remains outside this control.
The manual replacement gate keeps restored content isolated for application-
specific review before any authoritative data is changed.

## Verification

Run all component checks from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s automation/recovery/tests \
  -p 'test_*.py' \
  -v
PYTHONDONTWRITEBYTECODE=1 python3 \
  automation/recovery/tests/run_isolated_restore_drill.py
python3 -m py_compile \
  automation/recovery/restore.py \
  automation/recovery/tests/archive_factory.py \
  automation/recovery/tests/test_restore.py \
  automation/recovery/tests/test_systemd_policy.py \
  automation/recovery/tests/run_isolated_restore_drill.py
systemd-analyze verify --recursive-errors=no \
  automation/recovery/systemd/example-storage-dependent.service
```

The unit tests build every tar fixture dynamically under temporary paths. The
unprivileged, offline drill validates the model; verifies and restores exact
synthetic bytes and modes; rejects corruption using the original external
digest; rejects traversal, symlink, and wrong-boundary archives; checks failed
staging cleanup, exact restored inventory, failed destinations, and the outside
path; and confirms temporary workspace cleanup.

## Limitations

- The archive and manifest provide no authentication, signing, or encryption.
- The format has no PBS or Restic compatibility and does not restore VMs or
  application-consistent snapshots.
- The example proves no pruning, freshness monitoring, schedules, off-host
  transfer, media durability, or restore-time objective.
- The illustrative retention generations are policy-shape examples only; they
  are not evidence that copies exist.
- The external digest must be distributed through an independently trusted
  channel that this component does not implement.
- Stable staging and no-replace publication require Linux procfs and `renameat2`
  support.
- A malicious process running as root or as the same restore identity is outside
  the local namespace trust boundary.
- The destination is an isolated filesystem tree. Application-specific
  quiescing, database recovery, semantic validation, ownership changes, and the
  manual replacement of authoritative state are outside the transaction.
- This is not evidence of private platform, PBS, Restic, VM backup, or homelab
  recovery operation.
- The systemd evidence is static policy only. It does not prove a mount,
  marker-management workflow, service start, or storage readiness in an
  operated environment.
