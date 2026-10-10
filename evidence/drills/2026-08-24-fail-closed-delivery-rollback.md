# Deployment and Rollback Test

**Date:** August 24, 2026
**Environment:** Disposable container with generated Git history and images

Testing the [deployment helper](../../automation/ci/README.md) over SSH and sudo,
including failed health checks and rollback.

## Setup

- The target ran as a privileged, short-lived container with no default network
  route.
- The launcher built from five reviewed files, with no repository or host
  deployment mounts. Helper paths were root-owned inside the container.
- Nested Docker and a loopback TLS registry supplied test images offline.
- Git history, keys, certificates, and deployment state were generated for the run.

The target base image and direct package versions are pinned in
[`automation/ci/tests/disposable-host/Dockerfile`](../../automation/ci/tests/disposable-host/Dockerfile).
The launcher and exercise are implemented in
[`run_disposable_host_drill.sh`](../../automation/ci/tests/run_disposable_host_drill.sh)
and
[`disposable_host_drill.sh`](../../automation/ci/tests/disposable_host_drill.sh).
The passing target used the `x86_64` build of Docker Engine 29.1.3.

## Results

All scenarios passed. A, B, C, and D stand for generated full commit hashes.

| Test | Observed result |
|---|---|
| Starting conditions | No default route or pre-existing deployment path |
| Shell request | Rejected after SSH/sudo, before any deployment change |
| Deploy A → B | B passed health/version checks; state recorded B/A; pending record removed |
| Add an environment value (D) | Rejected; B stayed live and healthy |
| Deploy unhealthy C | C and its pending record were observed, then B was restored and checked; state stayed B/A; pending record removed |
| Roll back from B | Target selected A, passed health checks, and recorded A/B |
| Cleanup | Nested service/network removed; launcher confirmed target destruction |

## Harness fixes

Early runs needed a bounded startup wait, a pinned HTTP test binary because
BusyBox lacked its HTTP applet, and corrected Alpine OpenSSH options and paths.
The harness then switched from a working-tree mount to a five-file build context,
used Docker's returned container ID for cleanup, checked removal of the exact
container/network, and used a unique temporary image tag. The deployment helper
was unchanged. A fresh run passed; generated files and raw logs were not retained.

## Running it again

The full test needs privileged nested Docker on a dedicated disposable host or
isolated daemon. Automation changes run the unit tests; the manual
[integration workflow](../../.github/workflows/integration.yml) builds the target image.

See the [test commands](../../automation/ci/README.md#tests).
