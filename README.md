# Tamriel Homelab

Tamriel is my three-node Proxmox homelab. I use it to run personal services and
work on security projects. Most services run in Docker on Debian VMs, with
TrueNAS for shared files and OPNsense handling the network. This repo has notes
on the setup, screenshots, scripts, and configuration examples from building it.

## Table of Contents

- [Apps](apps/) - Apps and services running in the lab.
- [Projects](projects/) - Tools I've built, with setup guides and runnable examples.
- [Media](media/) - Jellyfin, Seerr, the *arr stack, and GPU transcoding.
- [Proxmox](proxmox/) - Proxmox cluster and virtual machine setup.
- [Networking](networking/) - Firewall, DNS, remote access, and sign-in.
- [Storage](storage/) - Current storage and backup setup.
- [Monitoring](monitoring/) - Grafana dashboards, metrics, logs, and alerts.
- [Security](security/) - Trivy, Falco, CrowdSec, and ClamAV.
- [Automation](automation/) - Forgejo, Renovate, Ansible, and deployment scripts.

## The setup

I group Docker Compose services into Debian VMs by role. The ROG Ally passes
its GPU to the media VM, while the Raspberry Pi runs DNS and the reverse proxy.
Databases live on the VMs' own disks; TrueNAS holds photos, synced files, and media.
I reach the lab through Tailscale when away from home.

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
[The Proxmox cluster](proxmox/README.md)

## Hardware

### Compute

| Hardware | Specs | Use |
|---|---|---|
| GMKtec NucBox K10 | Core i9-13900HK, 32 GB DDR5, 1 TB NVMe | Proxmox node |
| ACEMAGIC K1 | Intel N95, 16 GB DDR4, 1 TB SATA SSD | Proxmox node |
| ASUS ROG Ally | Ryzen Z1 Extreme, 16 GB LPDDR5, 512 GB NVMe | Proxmox node with GPU passthrough for media |

[How I group the workloads](proxmox/README.md#virtual-machines)

### Storage

| Hardware | Specs | Use |
|---|---|---|
| UGREEN DXP4800 Plus | Pentium Gold 8505, 8 GB RAM, 128 GB NVMe, 4 × 4 TB Seagate ST4000VN006 HDDs | TrueNAS SCALE storage |

The NAS hard drives are arranged as two mirrored pairs.
[Storage and backup notes](storage/README.md)

### Networking

| Hardware | Specs | Use |
|---|---|---|
| Lenovo ThinkCentre M720q | Core i5-8500T, 8 GB RAM, 256 GB SSD, Intel i350-T4 NIC | OPNsense router/firewall |
| Ubiquiti USW-Lite-16-PoE | 16-port managed PoE switch | Wired networking |
| Ubiquiti U6-Plus | Wi-Fi 6 access point | Wireless networking |

### Supporting devices

| Hardware | Specs | Use |
|---|---|---|
| Raspberry Pi 5 | 16 GB RAM, 128 GB microSD | DNS, reverse proxy, and cluster quorum device |
| CyberPower CP1500PFCLCD | 1500 VA / 1000 W | UPS power protection |

## What's running

I use Syncthing for documents and notes, Immich for photos, FreshRSS for reading,
and Jellyfin for media. Homarr brings the service links and reading brief together.

[![Homarr service cards and reading brief](screenshots/homarr-home.webp)](apps/homarr/README.md)

| Job | Tools |
|---|---|
| Files, photos, and documents | [Syncthing, Immich, Stirling PDF](apps/README.md#files-photos-and-documents) |
| Reading and utilities | [FreshRSS, Homarr, Vaultwarden, SearXNG](apps/README.md#reading-and-utilities) |
| Media | [Jellyfin, Seerr, Servarr, Gluetun](media/README.md) |
| Networking and access | [OPNsense, Tailscale, Caddy, Authentik](apps/README.md#networking-and-sign-in) |
| Storage and backups | [TrueNAS, ZFS, Proxmox Backup Server, Restic](apps/README.md#storage-and-backups) |
| Git and updates | [Forgejo, Renovate, Ansible](apps/README.md#git-and-updates) |
| Metrics, logs, and alerts | [Prometheus, Loki, Grafana, Alertmanager](apps/README.md#dashboards-and-monitoring) |
| Security | [Trivy, Falco, CrowdSec, ClamAV](apps/README.md#security) |

The [Projects](projects/README.md) section covers Forge VM provisioning, Discord
request approvals, the reading brief, Printer Monitor, and Tamriel Sandbox.

## Setup guides

Start with one app or follow the VM, storage, and access guides to build out a
host. Each guide lists its requirements and configuration files. Work in your
own service directory; if you already cloned this repo, copy the linked files
there instead of downloading them again. Replace example addresses, domains,
and hostnames with your own.

| Start with | Guide |
|---|---|
| A VM for your containers | [Debian on Proxmox](proxmox/debian-vm/README.md), [Terraform clone](proxmox/terraform/README.md) |
| Shared storage and backups | [TrueNAS and NFS](storage/nfs/README.md), [PBS](storage/pbs/README.md), [Restic](storage/restic/README.md) |
| Private application access | [Pi-hole and Unbound](networking/dns/README.md), [Caddy, Tailscale, and Authentik](networking/private-access/README.md) |
| Files, photos, reading, and a homepage | [Syncthing](apps/syncthing/README.md), [Immich](apps/immich/README.md), [FreshRSS](apps/freshrss/README.md), [Homarr](apps/homarr/README.md) |
| Media requests and playback | [Download stack](media/servarr/README.md), [Jellyfin and GPU transcoding](media/jellyfin/README.md) |
| Passwords, search, and utilities | [Vaultwarden, SearXNG, Stirling PDF, OpenSpeedTest](apps/utilities/README.md) |
| Dashboards and notifications | [Host metrics and alerts](monitoring/host-metrics/README.md), [Loki and Alloy](monitoring/logs/README.md), [Uptime Kuma](monitoring/uptime-kuma/README.md) |
| Security tools | [CrowdSec](security/crowdsec/README.md), [ClamAV](security/clamav/README.md), [Trivy](automation/trivy/README.md), [Falco](automation/falco/README.md) |

## Automation

I review Renovate's image updates in Forgejo, back up the affected application,
and apply the checked change. Ansible handles host configuration and OS updates.
The [automation page](automation/README.md) explains that routine and links to
the scripts and playbooks.

[Set up Renovate](automation/renovate/README.md) ·
[Host maintenance](automation/ansible/README.md)

## Screenshots

[![Landscape album in Immich](screenshots/immich-album.webp)](apps/immich/README.md)

A landscape album in Immich. More captures are beside the app descriptions and
in the [screenshot gallery](screenshots/README.md), including FreshRSS,
Jellyfin, Seerr, Grafana, TrueNAS, and PBS.

## Notes

- [What went wrong with the first network migration](docs/network-migration.md)
- [Making vulnerability alerts useful](docs/case-studies/actionable-vulnerability-management.md)
- [Deploying the commit that passed CI](docs/case-studies/fail-closed-infrastructure-delivery.md)
- [Restoring without overwriting live data](docs/case-studies/recovery-and-storage-dependencies.md)
- [Next steps](ROADMAP.md)
