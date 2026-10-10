# The setup

[Home](../README.md) · [Apps and services](../apps/README.md)

Three Proxmox nodes host Debian VMs for applications, identity, monitoring,
security tools, Git/CI, and backups. Most applications run with Docker Compose;
TrueNAS provides shared bulk storage. The [Proxmox page](../proxmox/README.md)
covers VM roles, provisioning tools, and supporting devices.

The [app catalogue](../apps/README.md) lists the personal services: Syncthing,
Immich, FreshRSS, Stirling PDF, Homarr, Vaultwarden, and SearXNG. The
[media VM](../media/README.md) runs Jellyfin, Seerr, and the download stack with
GPU passthrough. CI has a separate VM from Forgejo's application data.

[Overview diagram](../README.md#the-setup) · [Hardware](../README.md#hardware)

## Access and networking

OPNsense separates network zones. Tailscale provides private admin access, while
trusted clients reach web applications through Caddy with Authentik sign-in
where supported. See the [networking page](../networking/README.md) for the access
diagram and [network-zone notes](network-and-identity.md) for allowed connections.

## Storage

Databases stay on the VMs' own disks; TrueNAS and ZFS hold shared files. The
[storage page](../storage/README.md) explains that choice, the backup layers, and
the example startup check for services that depend on a mount.

## Monitoring and security

Prometheus, Loki, Grafana, and Alertmanager handle metrics, logs, dashboards,
and notifications. The [monitoring page](../monitoring/README.md) shows the
dashboard and alert screenshots and how scan results and events flow between tools.

The [security page](../security/README.md) introduces Trivy, Falco, CrowdSec, and
ClamAV. The [security notes](threat-model.md) cover threats and assumptions.

## Changes and deployment

Forgejo holds private configuration repositories, Renovate opens update pull
requests, and Ansible configures hosts. The
[automation page](../automation/README.md) links the Git workflow, host maintenance,
and deployment example to their implementation and test commands.

## Recovery

The backup tools are PBS and Restic. See the [backup notes](../storage/README.md#backups)
and the [restore example](../automation/recovery/README.md), which checks generated
archives and restores them to a new directory. Application-specific recovery
needs its own checks before replacing live data.
