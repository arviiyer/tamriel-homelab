# Threat Model

## Scope

This threat model covers the homelab's infrastructure, management plane,
self-hosted applications, software-delivery path, and stored personal data. It
is intentionally proportional to a privately operated environment rather than
modeled as an internet-facing enterprise service.

## Assets

- Hypervisor and network-management control planes
- Identity-provider configuration and sessions
- Source repositories and deployment artifacts
- Application databases and personal data
- Backup repositories and recovery credentials
- Security telemetry and operational logs
- Administrative workstations and SSH identities

## Trust Zones

| Zone | Trust assumption | Primary controls |
|---|---|---|
| Management | Restricted administrative devices and identities | Private access, strong authentication, source restrictions, key-based administration |
| Infrastructure | Hypervisors, storage, gateway, and core services | Restricted east-west policy, host hardening, monitoring, backups |
| Trusted clients | Personal devices permitted to use private services | Authenticated access and limited infrastructure reachability |
| Managed work | Employer-managed or externally controlled endpoints | Isolated from personal infrastructure and data |
| Untrusted devices | Devices with limited patching or vendor control | Default-deny access to private zones and constrained DNS/egress policy |
| Guest | Temporary user devices | Internet access without private-zone reachability |
| Media | Workloads with specialized egress and storage requirements | Isolated ingress, constrained mounts, malware scanning, workload hardening |
| Sandbox | Disposable analysis workers | No trusted-zone access, dedicated control path, rollback and quarantine |

## Priority Threats

### Vulnerable or Stale Software

Long-lived containers and hosts can accumulate known vulnerabilities even when
the surrounding network is private.

**Controls:** scheduled image and configuration scanning, dependency-update pull
requests, host patch automation, fix-aware alerting, and stale-scan detection.

### Credential Leakage

Source history, configuration exports, logs, screenshots, and deployment systems
can unintentionally retain credentials.

**Controls:** runtime secret separation, protected source workflow, secret
scanning, restricted deployment identities, screenshot review, and an explicit
public/private publication boundary.

### Compromised or Untrusted Client

A device on the local network should not automatically receive access to
infrastructure management or unrelated application data.

**Controls:** network segmentation, default-deny inter-zone policy, private
administrative paths, centralized identity, and restricted service ingress.

### Malicious or Compromised Workload

A container or guest may execute unexpected processes, access sensitive paths,
or attempt lateral movement.

**Controls:** workload separation, minimal mounts, container hardening, runtime
detection, centralized logs, restricted networks, and host-level monitoring.

### Unsafe Software Delivery

A compromised CI job or malformed deployment request could turn repository
write access into broad production access.

**Controls:** protected branches, exact-revision validation, separate runner
roles, manual promotion, forced-command deployment identities, target-side
allowlists, drift checks, health checks, and rollback.

### Data Loss or Corruption

Hardware failure, operator error, failed upgrades, and inaccessible network
storage can damage or hide important state.

**Controls:** local transactional storage, VM snapshots, tiered retention,
off-host copies for selected data, integrity checks, isolated restores, and
dependency-aware service startup.

The public [recovery case study](case-studies/recovery-and-storage-dependencies.md)
validates a synthetic restore and static startup policy. It does not establish
that private backup jobs or restore outcomes are publicly evidenced.

### Monitoring Blindness

A failed scanner, log shipper, or scrape target can create false confidence.

**Controls:** target-health monitoring, stale-result alerts, explicit scan
timestamps, centralized service logs, and routine operational review.

## Assumptions

- Physical security is appropriate for a residential environment.
- Administrative identities and endpoints remain high-trust and require
  separate hardening outside this repository.
- Private access substantially reduces exposure but does not replace patching,
  authentication, or segmentation.
- Open-source components may fail or change behavior across upgrades and require
  operational validation.

## Out of Scope

- Enterprise regulatory compliance claims
- High-availability guarantees for every personal service
- Protection against an adversary with persistent physical access
- Public malware-analysis services or untrusted third-party sample submission
- Claims of formal zero-trust architecture

## Residual Risk

The platform remains a single-operator environment with finite hardware,
maintenance time, and failure domains. Some services are intentionally manually
promoted, not every data set has equivalent off-host protection, and detection
coverage is constrained by available telemetry. Case studies will state these
limitations rather than presenting the homelab as risk-free.
