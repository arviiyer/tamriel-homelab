# ADR 0004: Restore Before Authoritative Replacement

- Status: Accepted
- Public record: August 2026
- Scope: Sanitized recovery architecture

## Context

A successful backup job does not prove that its data is complete, safe to parse,
or usable by an application. Restoring directly over authoritative state can
turn corruption, boundary confusion, or operator error into an irreversible
incident.

## Decision

Restore a selected backup into a new isolated identity after validating its
external digest, declared authority boundary, exact inventory, paths, types,
sizes, and per-file digests. Publish only a complete new destination and stop at
an explicit application review and manual replacement decision.

The restore transaction does not overwrite or automatically replace
authoritative data.

## Consequences

- Unsafe or incomplete input fails before destination publication.
- Existing state is not mutated by the restore transaction.
- Recovery requires temporary capacity and an application-specific validation
  step.
- Replacement remains a deliberate operational action rather than a side effect
  of extraction.
- The public synthetic format does not prove private VM, database, PBS, or
  Restic recovery.

## Public Evidence

The [recovery case study](../case-studies/recovery-and-storage-dependencies.md),
[restore implementation](../../automation/recovery/restore.py), and
[dated isolated drill](../../evidence/drills/2026-08-24-isolated-synthetic-restore.md)
support a `Publicly evidenced` claim for the synthetic restore boundary. Private
backup and operated recovery evidence remain pending.
