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
| Implemented exact-revision controlled deployment and rollback | [Restricted target helper](../automation/ci/target/restricted_deploy.py), [delivery case study and sequence](../docs/case-studies/fail-closed-infrastructure-delivery.md), 30 policy and transaction tests, and effective SSH/sudo validation; dated operated rollback exercise still required | Executable evidence |
| Automated dependency-update workflows | Sanitized Renovate policy and redacted update pull request | Planned |
| Implemented layered VM and selected off-host backups | Sanitized retention model, backup architecture, redacted job evidence | Planned |
| Validated recoverability through an isolated restore or rollback | Dated sanitized drill report with entry and exit criteria | Planned |
| Prevented storage-dependent workload boot races | Sanitized systemd dependency examples and validation record | Planned |

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
