# Content Plan

## Reader Journey

### First 30 Seconds

The repository must show:

- one sentence explaining what was built;
- one trust-boundary and data-flow diagram;
- five capability statements organized by engineering outcome; and
- direct links to code, runtime evidence, and case studies.

### First 90 Seconds

A technical reviewer should be able to follow one of these paths:

- vulnerability scan to delta calculation to alert;
- pull request to exact-revision validation to controlled deployment;
- network threat to segmentation control to validation; or
- backup policy to isolated restore exercise.

### Deeper Review

Detailed documents should cover constraints, alternatives, implementation,
validation, limitations, and lessons learned. A service catalog is supporting
material, not the primary story.

## Flagship README Order

1. Outcome statement
2. Architecture diagram
3. Verified capabilities
4. Claim-to-evidence links
5. Engineering case studies
6. Selected runtime evidence
7. Technology summary
8. Scope and privacy statement
9. Limitations and current work

## Engineering Pillars

### Platform and Storage

Focus on clustered virtualization, workload separation, local database storage,
shared bulk storage, GPU-backed workloads, and resource-aware operation.

### Network and Identity

Focus on trust zones, default-deny policy, private ingress, identity-aware
access, centralized DNS controls, and restricted management paths.

### Detection and Observability

Focus on metrics and logs as a unified operational signal, vulnerability deltas,
runtime detection, alert quality, malware scanning, and stale-control detection.

### Automation and Delivery

Focus on idempotent hardening, dependency updates, protected changes,
exact-revision validation, manual promotion, deployment allowlists, and rollback.

### Reliability and Recovery

Focus on snapshot policy, off-host copies, isolated restores, state boundaries,
health checks, storage readiness, and documented failure handling.

## Initial Case Studies

### Actionable Vulnerability Management

**Question answered:** How were recurring scan results converted into alerts an
operator can act on?

**Evidence target:** scanner, delta engine, synthetic fixtures, unit tests,
Prometheus rules, dashboard, and redacted alert.

### [Fail-Closed Infrastructure Delivery](case-studies/fail-closed-infrastructure-delivery.md)

**Question answered:** How can a self-hosted CI system promote reviewed changes
without giving a general runner unrestricted production access?

**Evidence target:** sequence diagram, sanitized workflow, restricted command
boundary, validation checks, and rollback drill.

### Network Change Blast Radius

**Question answered:** How did a failed high-risk migration change the design of
future network changes?

**Evidence target:** threat-to-control table, generic zone policy, failure
analysis, staged rollout, and rollback gates.

### [Recovery and Storage Dependencies](case-studies/recovery-and-storage-dependencies.md)

**Question answered:** How are stateful services protected and prevented from
starting against unavailable storage?

**Evidence target:** retention model, isolated restore procedure, systemd
dependency examples, and dated exercise result.

## Resume Alignment

Use the two [evidence-backed resume bullets](release-readiness.md#resume-wording)
and matching GitHub presentation in the v1 release checklist. Each clause maps
to a `Publicly evidenced` row in the [claim-to-evidence matrix](../evidence/validation-matrix.md).
The wording deliberately excludes stronger operational claims that remain
drafted or planned. Public repository access and signed-out links are verified,
and the profile entry is applied. The resume wording is supplied for the owner
to paste into the resume document.

## Explicit Exclusions

- Do not lead with a count of hosted applications.
- Do not publish a logo collage as the architecture diagram.
- Do not present the media stack as a primary engineering accomplishment.
- Do not combine the malware-analysis platform into this repository.
- Do not use private commit activity as the only proof of implementation.
- Do not treat screenshots as a substitute for code or validation.
