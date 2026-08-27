# ADR 0003: Separate Validation from Privileged Promotion

- Status: Accepted
- Public record: August 2026
- Scope: Sanitized delivery architecture

## Context

A passing CI job proves that selected checks ran against a revision; it does not
prove that the same revision will be deployed. Giving pull-request content a
general deployment credential also turns repository execution into a broad
production-access boundary.

## Decision

Run change validation without deployment credentials and bind it to one full
commit SHA. Require a separate manual promotion authorization. The promotion
path rechecks revision metadata without executing repository content and reaches
the target through a source-restricted, forced-command identity.

The target independently owns ancestry checks, allowed change shape, drift
detection, health checks, durable state, recovery, and rollback.

## Consequences

- Pull-request execution does not receive a general target identity.
- The validated and promoted source revision is explicit and immutable.
- Passing validation makes a revision eligible; it does not force deployment.
- Stateful or high-risk changes retain a human approval boundary.
- The target transaction is more complex because it must fail closed and retain
  recovery state.
- Private branch protection, runner labels, and operated workflow history still
  require separate evidence.

## Public Evidence

The [delivery case study](../case-studies/fail-closed-infrastructure-delivery.md),
[restricted target helper](../../automation/ci/target/restricted_deploy.py), and
[dated rollback drill](../../evidence/drills/2026-08-24-fail-closed-delivery-rollback.md)
support a `Publicly evidenced` validated-implementation claim. They do not prove
operation of the private workflow over time.
