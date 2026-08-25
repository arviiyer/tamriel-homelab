# Platform Catalog

This catalog describes capabilities rather than production placement, addresses,
or exact versions. Application count is not used as a measure of engineering
quality.

## Foundation

| Capability | Technology | Engineering focus |
|---|---|---|
| Virtualization | Proxmox VE | Three-node compute, workload separation, snapshots, guest lifecycle |
| Network policy | OPNsense and managed switching | Trust zones, default-deny policy, DNS controls, management restrictions |
| Shared storage | TrueNAS and ZFS | Bulk-data storage, snapshots, integrity tasks, constrained exports |
| Workload runtime | Debian and Docker Compose | Role-specific VMs, reproducible service definitions, local state boundaries |
| Private access | Tailscale and Caddy | Private administrative path, reverse proxy, constrained ingress |

## Identity and Access

| Capability | Technology | Engineering focus |
|---|---|---|
| Central identity | Authentik | OIDC, forward authentication, application-group enforcement |
| Source control | Forgejo | Private repositories, protected branches, OIDC access, audit history |
| Administrative access | OpenSSH | Key-based access, role restrictions, source restrictions, forced commands |

## Observability and Detection

| Capability | Technology | Engineering focus |
|---|---|---|
| Metrics | Prometheus and exporters | Host, application, firewall, scan, and control-health metrics |
| Logs | Loki and log shippers | Central journal, application, proxy, and firewall log analysis |
| Visualization | Grafana | Provisioned infrastructure and security dashboards |
| Alert routing | Alertmanager | Source- and severity-aware notification routing |
| Vulnerability management | Trivy | Image, configuration, and secret scanning with delta tracking |
| Runtime detection | Falco and Falcosidekick | eBPF-based events, structured forwarding, narrow noise tuning |
| Network defense | CrowdSec | Shared detection decisions and firewall enforcement |
| Malware scanning | ClamAV | Scheduled scanning, quarantine workflow, and scan-health metrics |

## Automation and Delivery

| Capability | Technology | Engineering focus |
|---|---|---|
| Host configuration | Ansible | SSH hardening, patch policy, serial upgrades, runtime-sensor deployment |
| Dependency updates | Renovate | Reviewed update pull requests, rate limiting, digest maintenance |
| Continuous integration | Forgejo Actions | Syntax, configuration, test, migration, and artifact validation |
| Controlled delivery | Restricted deployment helpers | Exact revisions, target allowlists, snapshots, health checks, rollback |
| Infrastructure provisioning | Terraform and cloud-init | Repeatable virtual-machine provisioning and constrained templates |

## Reliability and Recovery

| Capability | Technology | Engineering focus |
|---|---|---|
| VM backups | Proxmox Backup Server | Snapshot consistency, tiered retention, isolated restore procedure |
| Selected off-host copies | Restic | Encrypted copies, retention, and repository integrity checks |
| Storage readiness | systemd dependencies | Mount assertions, boundary identity, and startup gating with a [static public example](../automation/recovery/README.md) |
| Service health | Prometheus and application checks | Detecting unhealthy services and stale controls |

The public recovery implementation validates generic authority boundaries,
isolated restore behavior, and the storage-readiness policy. It does not evidence
the private PBS or Restic jobs, schedules, retention execution, or operation over
time.

## Application Workloads

The platform also operates private identity, file synchronization, photo,
document, dashboard, credential-vault, search, media, and development services.
They are included in this portfolio only when they demonstrate a transferable
engineering decision such as state isolation, identity integration, container
hardening, storage orchestration, or recovery.

The separate malware-analysis platform is intentionally excluded from this
repository and may become its own sanitized case study later.
