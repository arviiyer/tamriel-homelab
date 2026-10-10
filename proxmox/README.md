# Proxmox

[Home](../README.md) · [Apps and services](../apps/README.md) ·
[Storage](../storage/README.md)

Tamriel runs on three Proxmox nodes. Debian VMs hold most services, with Docker
Compose inside the VMs and a separate TrueNAS system for shared bulk files.

## The cluster

[![Three online Proxmox nodes with quorum](../evidence/screenshots/proxmox-cluster-summary.png)](../evidence/screenshots/README.md#proxmox-cluster)

The cluster health view shows three nodes online with quorum established.

| Machine | Role |
|---|---|
| GMKtec NucBox K10 | Proxmox node |
| ACEMAGIC K1 | Proxmox node |
| ASUS ROG Ally | Proxmox node with GPU passthrough for media |

[Full hardware specifications](../README.md#hardware)

## Virtual machines

I group the VMs by role:

| Role | What runs there |
|---|---|
| Applications | Personal services, mostly managed with Docker Compose |
| Identity | Application sign-in |
| Monitoring | Metrics, logs, dashboards, and alerts |
| Security | Scanning and security tools |
| Git and CI | Configuration repositories and automation |
| Backups | Backup services |

Terraform and cloud-init handle VM provisioning and templates; Ansible handles
host configuration. The published [Ansible examples](../automation/ansible/README.md)
cover SSH and updates. The [automation page](../automation/README.md) connects
those examples to the Git workflow.

## Supporting devices

The Raspberry Pi 5 provides DNS, reverse proxy, and cluster quorum-device roles.
OPNsense runs on a separate ThinkCentre, and TrueNAS SCALE runs on the UGREEN NAS.
The [hardware list](../README.md#supporting-devices) also includes UPS power
protection.

Administration goes through [Tailscale](../networking/README.md#tailscale).
For application data and VM backups, see the
[storage and backup notes](../storage/README.md).

## Notes

- [Lab overview](../docs/architecture.md)
- [Proxmox administration guide](https://pve.proxmox.com/pve-docs/pve-admin-guide.html)
- [Proxmox PCI passthrough reference](https://pve.proxmox.com/wiki/PCI_Passthrough)
- [Next documentation work](../ROADMAP.md#documentation)
