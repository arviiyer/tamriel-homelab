# Disposable Delivery Recovery and Rollback Drill

**Date:** August 24, 2026
**Classification:** Validated on an isolated disposable synthetic target
**Claim boundary:** This is not production or operated-environment evidence.

## Objective

Validate that the public exact-revision delivery implementation can cross a real
forced-command SSH and sudo boundary, apply a digest-pinned Compose revision,
recover automatically from failed health validation, and roll back only to the
target's recorded previous revision.

This record supports the exact-revision delivery claim in the
[claim-to-evidence matrix](../validation-matrix.md). It does not validate private
Forgejo settings, application-data recovery, or operation over time.

## Entry Criteria

- The target ran as a privileged, short-lived container with no default network
  route.
- The launcher copied only five reviewed public artifacts into a temporary build
  context. No repository, credential, runtime state, or host deployment path was
  mounted into the target.
- Fixed root-owned helper paths existed only inside the disposable target.
- A nested Docker daemon and loopback-only TLS registry supplied synthetic
  images without external network access during the exercise.
- Git history, SSH keys, host keys, certificates, image digests, and deployment
  state were generated inside the target for this run only.

The target base image and direct package versions are pinned in
[`automation/ci/tests/disposable-host/Dockerfile`](../../automation/ci/tests/disposable-host/Dockerfile).
The launcher and exercise are implemented in
[`run_disposable_host_drill.sh`](../../automation/ci/tests/run_disposable_host_drill.sh)
and
[`disposable_host_drill.sh`](../../automation/ci/tests/disposable_host_drill.sh).
The passing target used the `x86_64` build of Docker Engine 29.1.3.

## Scenarios

| Scenario | Expected result | Actual result | Status |
|---|---|---|---|
| Entry isolation | No default route or pre-existing deployment path is available | Network and path preconditions passed before mutation | Pass |
| Forced-command boundary | A shell command is rejected by the restricted parser | The request crossed SSH and sudo but was rejected before target mutation | Pass |
| Exact-revision promotion | Healthy revision B replaces A and records state as B/A | Compose pulled and applied B; fixed health and version checks passed; pending state was removed | Pass |
| Candidate policy | Revision D, which adds an environment value, is rejected | Canonical Compose comparison rejected the non-image change; B remained live and healthy | Pass |
| Failed-health recovery | Unhealthy revision C becomes active with B-to-C pending metadata, then B is restored | C and its pending transaction were observed; the helper failed the request, restored B, rechecked health, preserved B/A state, and removed pending metadata | Pass |
| Guarded rollback | A rollback guarded by current revision B selects recorded previous revision A | The target selected A, applied it, passed health validation, and recorded A/B state | Pass |
| Cleanup | Service resources and the disposable target are removed | Nested containers and network were removed; the outer launcher confirmed target destruction | Pass |

All state and live-definition comparisons used the generated full synthetic Git
revisions. This record uses revision labels instead of retaining ephemeral
commit hashes, image digests, keys, fingerprints, container IDs, or raw output.

## Development Observations

Pre-record dry runs found fixture-only defects: an immediate bootstrap readiness
check, a minimal BusyBox build without the HTTP applet, and two Alpine OpenSSH
invocation differences. The harness was corrected to use a bounded readiness
check, a pinned HTTP fixture binary, supported daemon options, and an absolute
daemon path. A subsequent safety review replaced the working-tree mount with a
five-file build context, changed cleanup to use the container ID returned by
Docker, added exact container and network cleanup assertions, and made the image
tag unique and temporary. The restricted deployment helper was not changed. The
complete exercise was then rerun from a new target and passed.

## Exit Criteria

- Revision A was live and healthy after explicit rollback.
- State recorded A as current and B as previous.
- No pending transaction remained.
- The nested Compose service and network were removed by exact project name.
- The launcher confirmed that the disposable target no longer existed.
- No generated key, certificate, state file, Git repository, image, or raw log
  was copied into this repository.

## Limitations

- This is one repeatable synthetic exercise, not evidence of operation over
  time.
- The target was a privileged nested-Docker container, not a disposable virtual
  machine with a production-equivalent filesystem or init system. Privileged
  container execution is not a security boundary against the Docker host, so
  the harness must be reviewed and run only on a dedicated disposable host or
  isolated daemon.
- The synthetic Git origin and loopback registry do not validate Forgejo branch
  protection, repository authentication, registry authentication, or runner
  labels and permissions.
- The health contract is a fixed HTTP success check; it does not prove deeper
  application correctness.
- Rollback covers one Compose definition and image digest. Database migrations,
  persistent application data, backup restore, and power-loss durability remain
  separate evidence tasks.
- Public CI execution and reviewed operated-workflow screenshots remain pending.
