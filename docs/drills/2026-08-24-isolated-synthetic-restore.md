# Isolated Restore Test

**Date:** August 24, 2026
**Environment:** Local temporary directory with generated archives

Testing the [restore tool](../../automation/recovery/README.md) with valid,
corrupt, and unsafe archives, including cleanup after failures.

## Setup

- The drill ran as an unprivileged user with Python 3.14.7.
- Everything was generated in a private temporary directory, using the two test
  datasets from the tracked recovery model.
- No network, Docker, root access, credentials, or existing data were needed.

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  automation/recovery/tests/run_isolated_restore_drill.py
```

## Results

All scenarios passed.

| Test | Observed result |
|---|---|
| Recovery model | Version, classification, and both dataset definitions accepted |
| Archive checks | External checksum, manifest, file list, dataset, sizes, and file checksums matched |
| Restore | Exact bytes restored to a new directory; directories `0750`, files `0640` |
| Corrupt archive | Checksum mismatch rejected before writing |
| Path traversal | Unsafe path rejected; no file created outside the destination |
| Symbolic link | Rejected; no destination created |
| Wrong dataset | Shared files rejected when service-local data was requested |
| Injected write failure | Staging removed; no destination created |
| Failure cleanup | No destination, outside path, or hidden staging directory left behind |
| Final cleanup | Temporary directory and all generated files removed |

Only sanitized PASS summaries were emitted. Generated files and raw output were
not retained.

## Fixes during testing

Before the recorded pass, checks were added for symlinked parents, exact storage
markers, and nonzero data after the final tar member. Writes switched to an open
parent-directory descriptor. Tests also covered uncertain durability after the
final rename, exact restored file lists, injected write failures, and parent
ownership/permissions. The full drill was rerun after those changes and passed.

## Running it again

The test uses Linux procfs and `renameat2`, with generated tar archives and
independently supplied digests. See the
[drill command](../../automation/recovery/README.md#try-it).
