# Fail-Closed Delivery Evidence

Status: **Publicly evidenced as a validated implementation**. The public workflow
and target transaction are covered by offline tests and a
[dated disposable-target drill](../../evidence/drills/2026-08-24-fail-closed-delivery-rollback.md).
A reviewed [Forgejo validation capture](../../evidence/screenshots/README.md#forgejo-validation)
adds evidence of a successful Compose job. Operated promotion/rollback and
evidence over time remain pending before this can support an `Operated` claim.

This directory demonstrates how a reviewed source revision crosses from
deployment-secret-free validation into a narrowly privileged deployment
request. The read-only repository token is scoped to fetch steps and removed
before repository-controlled Compose processing. This is a purpose-written
public example, not a deployment checkout or a sanitized copy of the private
implementation.

## Trust Boundary

The example separates four responsibilities:

| Responsibility | Trust and credential boundary |
|---|---|
| Pull-request validation | Executes repository content without deployment credentials |
| Exact-revision validation | Checks out and validates the operator-supplied full SHA without deployment credentials |
| Promotion request | Starts in a fresh job that requires the `promotion` label to map to a dedicated ephemeral runner, executes no repository content, and exposes the forced-command SSH key only to the request step |
| Target transaction | Revalidates protected-main ancestry, policy, drift, health, and rollback using root-controlled local state |

Passing CI does not deploy automatically. The operator manually chooses deploy
or rollback and supplies a full protected-main SHA to
[`forgejo/promote.yml`](forgejo/promote.yml). The
`validate-revision` job checks that exact commit and exports the SHA only after
validation passes. The separate `promote` job requires that output, compares it
with the original input, rechecks protected-main ancestry without checking out
or executing repository code, and sends one restricted request.

The deployment credential cannot open a shell. The account-wide SSH policy and
per-key [`authorized_keys` restrictions](target/authorized_keys.example) both
force requests through
[`target/restricted_deploy.py`](target/restricted_deploy.py). The key also has an
RFC 5737 source-address restriction, and the sudo policy permits only that
helper. The helper ignores command-line arguments and accepts this exact request
shape through `SSH_ORIGINAL_COMMAND`:

```text
deploy|rollback example-api <40-character-main-commit>
```

## Target Transaction

The target owns its Git remote credential, runtime Compose file, deployment
state, lock, and health endpoint. None are supplied by the validation runner.
For a deployment, the helper:

1. serializes transactions with a nonblocking lock;
2. fetches the protected `main` ref into a root-controlled bare repository;
3. verifies current and requested revisions are reachable from that ref;
4. requires a deployment target to descend from recorded current state;
5. rejects drift between the live Compose file and the recorded revision;
6. renders both Compose models and permits only the allowlisted image digest to
   change;
7. pulls the candidate before recording a pending transaction;
8. applies the exact Compose file extracted from the requested commit;
9. promotes state only after the fixed local health check passes; and
10. restores the recorded current revision if apply or health verification
    fails.

State, pending metadata, and live-definition replacements are atomically renamed
and synchronized with their parent directories. If the state commit reports an
error, the helper rereads the visible state. A clearly uncommitted change is
restored immediately. A post-replacement synchronization failure remains
ambiguous even when the new state is readable, so pending metadata is retained
and the request fails; a later invocation can reconcile whichever state survived
durable storage.

For rollback, the supplied SHA is the expected current revision. The target uses
it only as a guard against stale operator state. The
target selects its recorded previous revision rather than accepting an arbitrary
rollback destination. Pending metadata lets the next request restore recorded
state after interruption before attempting another change.

## Synthetic Paths

The helper intentionally uses generic paths under `/var/lib/example-deploy` and
`/srv/example-api`, the public alias `apps-01.example.com`, and the RFC 5737
source address `192.0.2.40`. Adopters must provision their own root-controlled
paths, host-key material, repository remote, and runtime credentials outside
source control.

The sample allows only a digest-pinned image from
`registry.example.com/example-api`. It does not permit a revision to add mounts,
devices, capabilities, extra services, commands, or environment changes. This
narrow policy is what makes the forced request safer than granting a runner
general target access.

## Verification

The Forgejo capture shows successful `Checkout workflow revision` and
`Validate Compose files` steps. The
[review record](../../evidence/screenshots/forgejo-validation-run.review.md)
associates the run with a dependency-update pull request; this is narrower
evidence than the synthetic exact-revision deployment and rollback drill.

Run the offline policy and transaction tests from the repository root:

```bash
python3 -m unittest discover -s automation/ci/tests -p 'test_*.py' -v
bash automation/ci/tests/validate_target.sh
```

The tests execute successful deployment, failed-health recovery, explicit
rollback, interrupted-transaction recovery, command rejection, ancestry, drift,
candidate-policy, and workflow credential-boundary cases without a network,
Docker daemon, SSH key, or production host.

The target-policy check generates a temporary host key, validates the effective
OpenSSH forced command for both the allowed source and a nonmatching source,
checks the narrow sudo rule with `visudo`, and confirms the separate per-key
source restriction. It removes the generated key on exit.

Run the opt-in integration drill only on a dedicated disposable Docker host or
isolated daemon where a reviewed harness may receive privileged container
access:

```bash
bash automation/ci/tests/run_disposable_host_drill.sh
```

The launcher stages only the helper, policy examples, drill script, and
Dockerfile into a temporary build context. It builds a target from a
digest-pinned base and pinned direct package versions without mounting the
repository, then removes the target's default network route. Inside that target,
the drill creates a synthetic Git history, nested Docker daemon, loopback TLS
registry, root-owned deployment state, and isolated OpenSSH endpoint. It
validates a healthy promotion, shell rejection, non-image policy rejection,
failed-health recovery, guarded rollback, and cleanup using the unmodified
target helper. Normal CI builds the target image but does not run the full drill,
which requires privileged nested Docker and about one minute for the intentional
health failure.

`--privileged` is not a host security boundary. Review the harness before use and
do not run the full drill on a production, shared, or credential-bearing Docker
host.

## Limitations

- The example proves public policy and state-transition behavior, not that a
  private repository has branch protection enabled.
- The Forgejo capture does not prove trigger type, branch protections,
  required-check enforcement, reviewed-SHA semantics, promotion, or rollback.
- The target transaction changes only a Compose image digest. Database schemas,
  destructive migrations, and multi-service orchestration are outside its
  rollback boundary.
- The example restores the tracked runtime definition after failure; application
  data recovery remains a separate backup and restore concern.
- Root ownership, the forced-command request path, real Compose behavior, the
  health endpoint, automatic recovery, and explicit rollback have been validated
  on an isolated disposable synthetic target. A production-equivalent
  disposable VM exercise remains stronger future evidence.
- The disposable drill uses a synthetic local Git origin and registry. It does
  not validate target Git authentication, private Forgejo settings, registry
  authentication, or operation over time.
- The promotion label must select a dedicated ephemeral runner. Traps and unique
  temporary directories limit normal cleanup risk, but cannot make a persistent
  runner safe after abrupt host loss.
- Forgejo repository permissions and secret access must be reviewed separately;
  a forced command limits target capability but does not make an untrusted
  repository safe.
