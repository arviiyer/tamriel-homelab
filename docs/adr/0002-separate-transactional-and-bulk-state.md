# ADR 0002: Separate Transactional State from Shared Bulk Storage

- Status: Accepted
- Public record: August 2026
- Scope: Sanitized logical architecture

## Context

Databases and bulk files have different consistency, availability, and recovery
requirements. Coupling transactional state to network filesystem availability
can make an application depend on storage behavior it cannot validate. An absent
mount can also leave an ordinary local directory at the expected path, allowing
a service to create divergent state that appears healthy.

## Decision

Keep transactional application state on VM-local storage. Use shared storage for
bulk data and workloads suited to network-attached semantics. Give each data set
one authoritative boundary, a corresponding backup boundary, and a distinct
restore decision.

Storage-dependent services must verify the expected mounted boundary before
startup rather than relying on path existence or timing alone.

## Consequences

- Database availability is not directly coupled to shared-storage reachability.
- Bulk data can use shared capacity without making it the authority for every
  application state transition.
- VM-local and shared data require different backup and recovery coverage.
- Capacity planning and recovery coordination become more explicit.
- The design does not provide automatic database high availability.
- Services using shared data need mount and boundary assertions.

## Public Evidence

The [recovery case study](../case-studies/recovery-and-storage-dependencies.md)
documents the authority model. The public
[storage-readiness policy](../../automation/recovery/README.md) is executable
static evidence, while private storage operation and backup jobs remain
`Drafted`.
