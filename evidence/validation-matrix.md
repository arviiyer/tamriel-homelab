# Claim-to-Evidence Matrix

## Status Definitions

- **Planned:** Public proof has not been prepared.
- **Drafted:** Public explanatory documentation exists, but executable or runtime
  proof is still pending.
- **Publicly evidenced:** Reviewed code, CI, validation records, or runtime
  evidence support the claim.
- **Executable evidence:** Reviewed code and tests support the implementation,
  but operated-environment evidence is still pending.

No claim should appear as a finalized resume bullet until its status is
`Publicly evidenced`.

| Claim | Required public proof | Status |
|---|---|---|
| Designed and operate a three-node Proxmox private cloud | Sanitized architecture, platform catalog, redacted cluster evidence | Drafted |
| Segmented workloads by trust and function | Threat model, zone-policy case study, sanitized network diagram | Drafted |
| Centralized private application access and identity | Architecture document, identity flow, redacted authentication evidence | Drafted |
| Centralized infrastructure and security telemetry | [Sanitized Grafana dashboard](../automation/monitoring/README.md), file provisioning, 11 structural and query-reference tests, and Grafana loading validation; query execution, scrape configuration, and operated screenshot still required | Drafted |
| Automated host hardening and controlled patching | [Sanitized Ansible roles](../automation/ansible/README.md), example inventory, 18 static policy tests, and syntax/effective-inventory validation; live transaction evidence still required | Drafted |
| Built vulnerability scanning with delta-based alerting | [Scanner and delta engine](../automation/trivy/README.md), synthetic fixtures, 27 tests, validated alert rules; operated screenshot still required | Executable evidence |
| Deployed runtime detection and event routing | [Sanitized Falco role](../automation/falco/README.md), 15 policy tests, validated rules and routing structure, and event-flow diagram; disposable-host transaction and operated alert still required | Drafted |
| Enforced protected infrastructure changes across private repositories | [Sanitized validation and promotion workflows](../automation/ci/README.md) and repository-control narrative; redacted PR and private repository-setting evidence still required | Drafted |
| Implemented exact-revision controlled deployment and rollback | [Restricted target helper](../automation/ci/target/restricted_deploy.py), [delivery case study and sequence](../docs/case-studies/fail-closed-infrastructure-delivery.md), 30 policy and transaction tests, effective SSH/sudo validation, and a [dated disposable-target recovery and rollback drill](drills/2026-08-24-fail-closed-delivery-rollback.md); operated workflow evidence still required | Publicly evidenced |
| Automated dependency-update workflows | Sanitized Renovate policy and redacted update pull request | Planned |
| Implemented layered VM and selected off-host backups | [Synthetic recovery-boundary model](../automation/recovery/recovery-model.json), [recovery case study](../docs/case-studies/recovery-and-storage-dependencies.md), backup architecture, and redacted job evidence; private job and operated evidence remain pending | Drafted |
| Validated delivery recovery and rollback on an isolated disposable target | [Dated sanitized drill report](drills/2026-08-24-fail-closed-delivery-rollback.md) with entry and exit criteria, expected and actual transitions, limitations, and cleanup confirmation | Publicly evidenced |
| Validated an isolated synthetic state restore and unsafe-input rejection | [Restore implementation](../automation/recovery/restore.py), 27 policy and transaction tests, and a [dated sanitized restore drill](drills/2026-08-24-isolated-synthetic-restore.md) | Publicly evidenced |
| Implemented a public storage-readiness startup policy | [Sanitized systemd service](../automation/recovery/systemd/example-storage-dependent.service), policy tests, and `systemd-analyze verify`; live mount and boot-failure evidence remain pending | Executable evidence |

## Candidate Resume Bullets

These are drafts, not approved claims:

> Designed and operate a three-node Proxmox private cloud with segmented
> networks, centralized identity, private ingress, security observability, and
> automated VM backups.

> Implemented security and delivery automation across infrastructure
> repositories using Ansible, Trivy, Falco, Renovate, and protected self-hosted
> CI, including delta-based vulnerability alerts, exact-revision deployment,
> and rollback controls.

The final wording will be approved only when all clauses map to publicly
evidenced rows above.
