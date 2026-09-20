# Claim-to-Evidence Matrix

## Status Definitions

- **Planned:** Public proof has not been prepared.
- **Drafted:** Public explanatory documentation exists, but executable or runtime
  proof is still pending.
- **Publicly evidenced:** Reviewed code, CI, validation records, or runtime
  evidence support the claim. This describes evidence strength; repository
  publication does not strengthen an unverified operational claim.
- **Executable evidence:** Reviewed code and tests support the implementation,
  but operated-environment evidence is still pending.

No claim should appear as a finalized resume bullet until its status is
`Publicly evidenced`.

| Claim | Required public proof | Status |
|---|---|---|
| Designed a three-node Proxmox private cloud with reviewed cluster-health evidence | [Architecture](../docs/architecture.md), [platform catalog](../docs/platform-catalog.md), and [reviewed cluster summary](screenshots/README.md#proxmox-cluster-health) showing three online nodes and quorum; point-in-time evidence, not sustained uptime or failover validation | Publicly evidenced |
| Segmented workloads by trust and function | [Threat model](../docs/threat-model.md), [network and identity design](../docs/network-and-identity.md), and [primary trust-boundary diagram](../README.md#architecture); zone-policy validation and operated evidence still required | Drafted |
| Centralized private application access and identity | [Architecture](../docs/architecture.md) and [identity-boundary design](../docs/network-and-identity.md#identity-boundaries); reviewed authentication evidence still required | Drafted |
| Centralized infrastructure and security telemetry | [Sanitized Grafana dashboard](../automation/monitoring/README.md), file provisioning, 11 structural and query-reference tests, six synthetic PromQL cases for the failed-repository counter, Grafana loading validation, and an [operated Trivy dashboard capture](screenshots/README.md#vulnerability-management); remaining query execution and central scrape/log validation are pending, and the capture does not validate the public example | Drafted |
| Automated host hardening and controlled patching | [Sanitized Ansible roles](../automation/ansible/README.md), example inventory, 18 static policy tests, and syntax/effective-inventory validation; live transaction evidence still required | Drafted |
| Built vulnerability scanning with delta-based alerting | [Scanner and delta engine](../automation/trivy/README.md), synthetic fixtures, 27 tests, validated alert rules, [operated finding presentation](screenshots/README.md#vulnerability-management), and [one delivered fix-aware alert](screenshots/README.md#actionable-security-alert); not a remediation or delivery-reliability claim | Publicly evidenced |
| Deployed runtime detection and event routing | [Sanitized Falco role](../automation/falco/README.md), 15 policy tests, validated rules and routing structure, and event-flow diagram; disposable-host transaction and operated alert still required | Drafted |
| Validated a dependency-update change with Forgejo Compose checks | [Reviewed workflow result](screenshots/README.md#forgejo-validation) showing successful checkout and Compose-validation steps; PR association inspected before redaction, not proof of required-check enforcement or deployment | Publicly evidenced |
| Enforced protected infrastructure changes across private repositories | [Sanitized validation and promotion workflows](../automation/ci/README.md), repository-control narrative, and [reviewed validation run](screenshots/forgejo-validation-run.review.md); private repository-setting and permission-boundary evidence still required | Drafted |
| Implemented exact-revision controlled deployment and rollback | [Restricted target helper](../automation/ci/target/restricted_deploy.py), [delivery case study and sequence](../docs/case-studies/fail-closed-infrastructure-delivery.md), 30 policy and transaction tests, effective SSH/sudo validation, and a [dated disposable-target recovery and rollback drill](drills/2026-08-24-fail-closed-delivery-rollback.md); operated promotion and rollback evidence still required | Publicly evidenced |
| Automated dependency-update workflows | Sanitized Renovate policy and redacted update pull request | Planned |
| Implemented layered VM and selected off-host backups | [Synthetic recovery-boundary model](../automation/recovery/recovery-model.json), [recovery case study](../docs/case-studies/recovery-and-storage-dependencies.md), backup architecture, and redacted job evidence; private job and operated evidence remain pending | Drafted |
| Validated delivery recovery and rollback on an isolated disposable target | [Dated sanitized drill report](drills/2026-08-24-fail-closed-delivery-rollback.md) with entry and exit criteria, expected and actual transitions, limitations, and cleanup confirmation | Publicly evidenced |
| Validated an isolated synthetic state restore and unsafe-input rejection | [Restore implementation](../automation/recovery/restore.py), 27 policy and transaction tests, and a [dated sanitized restore drill](drills/2026-08-24-isolated-synthetic-restore.md) | Publicly evidenced |
| Implemented a public storage-readiness startup policy | [Sanitized systemd service](../automation/recovery/systemd/example-storage-dependent.service), policy tests, and `systemd-analyze verify`; live mount and boot-failure evidence remain pending | Executable evidence |

## Evidence-Backed Resume Wording

The two bounded bullets and their clause-to-evidence mapping are maintained in
the [v1 release checklist](../docs/release-readiness.md#resume-wording). They cover
the evidenced platform design, Trivy implementation and observed notification,
disposable-target delivery validation, and isolated synthetic restore.

The repository and evidence links are public and work without authentication.
The profile entry is applied; the resume wording is copy-ready at the owner's
request. Segmentation, identity, private backup jobs,
Ansible/Falco operation, enforced repository protections, and Renovate automation
must not be added without the missing evidence above.
