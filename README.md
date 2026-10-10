# Tamriel Homelab

Tamriel is my three-node Proxmox homelab. I use it to run personal services and
work on security projects. This repo has notes on the setup, scripts, and
configuration examples from building it.

## The setup

Most services run with Docker Compose inside Debian VMs, grouped by role.
Databases live on the VMs' own disks; shared storage holds bulk files.
Administration goes through Tailscale, and web applications use Caddy with
Authentik for sign-in where supported.

```mermaid
flowchart LR
    admin[Admin access] --> tailscale[Tailscale] --> management[Proxmox management]
    clients[Trusted clients] --> caddy[Caddy · Authentik] --> apps

    subgraph cluster[Three-node Proxmox cluster]
        management
        apps[Docker Compose in VMs] --> databases[Local databases]
    end

    apps --> storage[TrueNAS · ZFS<br/>Shared files]
    apps --> monitoring[Prometheus · Loki · Grafana]
```

[More about the setup](docs/architecture.md) ·
[Networking](docs/network-and-identity.md)

## Hardware

| Hardware | Specs | Use |
|---|---|---|
| GMKtec NucBox K10 | Core i9-13900HK, 32 GB DDR5, 1 TB NVMe | Proxmox node |
| ACEMAGIC K1 | Intel N95, 16 GB DDR4, 1 TB SATA SSD | Proxmox node |
| ASUS ROG Ally | Ryzen Z1 Extreme, 16 GB LPDDR5, 512 GB NVMe | Proxmox node with GPU passthrough for media |
| Raspberry Pi 5 | 16 GB RAM, 128 GB microSD | DNS, reverse proxy, and cluster quorum device |
| UGREEN DXP4800 Plus | Pentium Gold 8505, 8 GB RAM, 128 GB NVMe, 4 × 4 TB Seagate ST4000VN006 HDDs | TrueNAS SCALE storage |
| Lenovo ThinkCentre M720q | Core i5-8500T, 8 GB RAM, 256 GB SSD, Intel i350-T4 NIC | OPNsense router/firewall |
| Ubiquiti USW-Lite-16-PoE | 16-port managed PoE switch | Wired networking |
| Ubiquiti U6-Plus | Wi-Fi 6 access point | Wireless networking |
| CyberPower CP1500PFCLCD | 1500 VA / 1000 W | UPS power protection |

The NAS hard drives are arranged as two mirrored pairs.

## What's running

The lab hosts file sync, photos, documents, a password vault, search, media, and
development services. Supporting those:

| Job | Tools |
|---|---|
| Networking and access | OPNsense, Tailscale, Caddy, Authentik |
| Storage and backups | TrueNAS, ZFS, Proxmox Backup Server, Restic |
| Git and updates | Forgejo, Renovate, Ansible |
| Metrics, logs, and alerts | Prometheus, Loki, Grafana, Alertmanager |
| Security | Trivy, Falco, CrowdSec, ClamAV |

## Automation

Each folder has its own setup and test commands:

- [Trivy](automation/trivy/): scan images and repositories; alert on new vulnerabilities and available fixes.
- [Ansible](automation/ansible/): configure SSH and updates; upgrade one host at a time.
- [Deployment](automation/ci/): deploy the commit that passed CI and roll back if health checks fail.
- [Falco](automation/falco/): detect suspicious runtime activity and send events to Loki and Alertmanager.
- [Grafana](automation/monitoring/): a dashboard for scan results and Falco events.
- [Recovery](automation/recovery/): test restores with generated archives and check storage before starting services.

GitHub Actions checks links, publication rules, and secrets on each push. Changes
to automation also run the relevant tests. Container builds and integration
checks run manually from [Actions](https://github.com/arviiyer/tamriel-homelab/actions/workflows/integration.yml).

## Screenshots

[![Trivy dashboard in Grafana](evidence/screenshots/grafana-security-dashboard.png)](evidence/screenshots/README.md#trivy-dashboard)

The lab's Trivy dashboard. The secret panel reports file scans; Git history is
checked separately. [More screenshots](evidence/screenshots/README.md).

## Notes

- [Making vulnerability alerts useful](docs/case-studies/actionable-vulnerability-management.md)
- [Deploying the commit that passed CI](docs/case-studies/fail-closed-infrastructure-delivery.md)
- [Restoring without overwriting live data](docs/case-studies/recovery-and-storage-dependencies.md)
- [Next steps](ROADMAP.md)
