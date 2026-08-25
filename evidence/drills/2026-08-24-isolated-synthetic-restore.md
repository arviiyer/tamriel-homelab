# Isolated Synthetic Restore Drill

**Date:** August 24, 2026
**Classification:** Validated isolated synthetic restore
**Claim boundary:** This is not a private-platform, VM-backup, PBS, Restic, or
operated-environment restore.

## Objective

Validate that the public recovery component can verify a bounded synthetic
backup, publish exact files only into a new isolated destination, reject corrupt
or unsafe input without creating a destination, and remove all temporary drill
state.

This record supports the isolated synthetic restore claim in the
[claim-to-evidence matrix](../validation-matrix.md). The separate systemd unit
has static syntax and policy evidence; it was not exercised as a live mount or
boot transaction in this drill.

## Entry Criteria

- The drill ran as an unprivileged user with Python 3.14.7.
- It required no network, Docker daemon, root access, credentials, private
  repository, production path, or writable repository checkout.
- Every tar archive, digest, restore destination, and synthetic identifier was
  generated under a new private temporary directory owned by the drill identity.
- The tracked recovery model contained only public synthetic authority
  boundaries and illustrative generation labels.
- No pre-existing restore destination or authoritative data was available to the
  exercise.

The reviewed command was:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 \
  automation/recovery/tests/run_isolated_restore_drill.py
```

## Scenarios

| Scenario | Expected result | Actual result | Status |
|---|---|---|---|
| Recovery model | Strict version, classification, and two authority boundaries are accepted | The tracked model passed validation | Pass |
| Archive preflight | External digest, manifest, member inventory, state boundary, sizes, and file digests agree | The synthetic service-state archive passed every preflight check | Pass |
| Isolated restore | Exact bytes are published only to a new destination with directories `0750` and files `0640` | Restored content and fixed modes matched the verified archive | Pass |
| Corruption | An altered archive paired with the original independent digest is rejected before staging | Digest validation rejected the archive and no destination appeared | Pass |
| Path traversal | A member attempting to escape its authority root is rejected | The unsafe path was rejected and no outside file appeared | Pass |
| Symbolic link | A link member cannot redirect a write | The member type was rejected and no destination appeared | Pass |
| Boundary confusion | Shared bulk data cannot be restored as service-local state | The manifest boundary mismatch was rejected | Pass |
| Failed-staging cleanup | A synthetic local write failure removes staging and publishes no destination | The injected write failure was rejected and staging was removed | Pass |
| Failed-transaction paths | Rejections leave no destination, outside path, or hidden staging directory | All asserted paths remained absent | Pass |
| Workspace cleanup | Generated archives, restore data, and identifiers are removed | The temporary drill root no longer existed after completion | Pass |

The drill emitted only sanitized PASS summaries. No archive, digest, generated
backup identifier, temporary path, restored data, or raw command output was
retained as publication evidence.

## Development Observations

Review before the recorded pass added explicit rejection of a symlinked
destination parent and changed the storage-readiness marker from an existence
check to an exact byte comparison. A later adversarial review added nonzero tar
trailer rejection, descriptor-relative staging and publication, explicit
post-publication durability reporting, exact restored-inventory checks, and an
injected staging-write failure. Final review added enforcement that the
destination parent is owned by the restore identity and is not group- or
world-writable. Regression tests cover those policies. The full restore drill
was rerun after the changes and passed.

## Exit Criteria

- The valid destination contained only the two expected synthetic files.
- Restored bytes and fixed file and directory modes matched expectations.
- Corrupt, traversal, link, and wrong-boundary destinations remained absent.
- No traversal target or hidden staging directory existed.
- The temporary workspace and all generated backup material were removed.
- No production or private artifact was read, written, or published.

## Limitations

- The purpose-written tar format is not compatible with PBS, Restic, VM images,
  or application-consistent database recovery.
- An external SHA-256 detects corruption only when its expected value comes from
  an independently trusted channel. The component does not authenticate, sign,
  or encrypt backups.
- The exercise does not prove backup creation, freshness, pruning, transfer,
  media durability, private recovery objectives, or operation over time.
- The isolated destination is a filesystem tree, not a security sandbox or a
  replacement for application-specific semantic validation.
- Root and other processes running as the restore identity remain trusted within
  the destination namespace.
- The atomic publication step requires Linux procfs and `renameat2`; power-loss
  behavior and non-Linux filesystems are outside this drill.
- The storage-readiness unit remains static executable evidence. Runtime mount
  loss, stale storage, marker creation, and actual service startup remain future
  exercises.
