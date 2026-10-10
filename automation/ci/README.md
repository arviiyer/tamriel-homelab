# Deployment and rollback

[Home](../../README.md) · [Automation](../README.md)

A Forgejo workflow and SSH helper that deploy the commit checked by CI, test
service health, and roll back failures.

[Design notes](../../docs/case-studies/fail-closed-infrastructure-delivery.md) ·
[Rollback drill](../../docs/drills/2026-08-24-fail-closed-delivery-rollback.md)

## Setup

[`forgejo/promote.yml`](forgejo/promote.yml) accepts deploy or rollback plus a full
SHA from protected `main`. Validation checks out that exact commit without a
deployment key. Its read-only repository token exists only during fetch, before
repository-controlled Compose processing.

The separate deployment job compares the checked SHA with the request and
verifies that it belongs to `main`, without running repository code. The
`promotion` label must select a dedicated, short-lived runner; only the final
request step receives the SSH key.

The example uses `/var/lib/example-deploy`, `/srv/example-api`,
`apps-01.example.com`, and source address `192.0.2.40`. An adapted deployment
needs root-controlled paths, verified host keys, a Git remote and credentials,
and application credentials outside this checkout.

The account-wide SSH policy and
[`authorized_keys` restrictions](target/authorized_keys.example) force requests
through [`restricted_deploy.py`](target/restricted_deploy.py). The per-key source
restriction and narrow sudo rule further limit access. The helper ignores
command-line arguments and reads this exact shape from `SSH_ORIGINAL_COMMAND`:

```text
deploy|rollback example-api <40-character-main-commit>
```

Only a digest-pinned image from `registry.example.com/example-api` may change.
Mounts, devices, capabilities, commands, environment, and extra services cannot
be changed by the request.

## Tests

Run from the repository root with Python dependencies from [requirements.txt](requirements.txt).
The SSH/sudo check needs OpenSSH and `visudo`; building the drill image needs Docker:

```bash
python3 -m unittest discover -s automation/ci/tests -p 'test_*.py' -v
bash automation/ci/tests/validate_target.sh
bash automation/ci/tests/run_disposable_host_drill.sh --build-only
```

The Python tests run offline and cover credentials, rejected commands, Git
ancestry, live configuration changes, deployment, rollback, and interrupted
writes. The SSH/sudo check generates and removes its own host key and tests both
allowed and disallowed source addresses.

The full drill requires privileged nested Docker. Run it only on a dedicated
disposable Docker host or isolated daemon after reviewing the harness:

```bash
bash automation/ci/tests/run_disposable_host_drill.sh
```

The launcher builds a temporary target without a default network route. Generated
Git history, a loopback TLS registry, and an SSH endpoint let the drill test real
deployments, rejected requests, failed health checks, rollback, and cleanup.

The full drill takes about a minute for the intentional health failure. The manual
[integration workflow](../../.github/workflows/integration.yml) builds the image.
Its pinned packages allow dependencies from the base image to upgrade within the
same Alpine release. Privileged containers do not isolate the host securely;
the full drill must not run on a production, shared, or credential-bearing host.

## How deployment works

The target stores its own credentials, Compose file, commit history, lock, and
health endpoint. For deployment, it:

1. Takes a nonblocking lock and fetches protected `main` into a root-controlled
   bare repository.
2. Checks that current/requested commits are reachable and the requested commit
   descends from the recorded current revision.
3. Rejects unrecorded edits to the live Compose file and changes beyond the image
   digest.
4. Pulls the image, records a pending transaction, and applies the exact tracked
   Compose definition.
5. Checks the fixed local health endpoint, then saves current/previous revisions.
   Apply or health failure restores the recorded current revision.

File updates use atomic rename and sync the parent directory. If saving the
revision fails before replacement, the helper restores the current definition.
If replacement happened but syncing failed, it keeps the pending record and
reports failure so the next invocation can recover.

For rollback, the request SHA is the expected current revision, not a destination.
The target selects its recorded previous revision. Pending metadata lets a later
invocation restore recorded state after interruption before attempting a change.

## Limits

- Rollback covers one Compose definition and image digest. Database migrations,
  application data, and multi-service orchestration need separate recovery.
- Use a fresh runner for each deployment; cleanup scripts cannot reliably clear
  credentials after a host crash. Repository permissions and secret access also
  need to be configured separately.
