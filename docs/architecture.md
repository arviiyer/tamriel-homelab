# The setup

[Home](../README.md) · [Apps and services](../apps/README.md)

Most services run in Docker Compose on Debian VMs. Three Proxmox nodes host the
VMs, with separate machines for the router, NAS, and Raspberry Pi services.
The [hardware list](../README.md#hardware) and [VM table](../proxmox/README.md#virtual-machines)
show the machines and workloads.

## Opening an application

For an app such as FreshRSS, the path at home is:

1. Pi-hole resolves the app's name to the Raspberry Pi's LAN address.
2. Caddy on the Pi terminates HTTPS and forwards the request to the app VM.
3. FreshRSS sends the browser to Authentik for sign-in, then opens the reader.

Away from home, the same name resolves through public DNS to the Pi's Tailscale
address. The client joins the tailnet before opening it. Other apps use their
own login or Authentik's proxy outpost, as listed in the
[sign-in table](../networking/README.md#caddy-and-authentik).

The [private-access guide](../networking/private-access/README.md) walks through
DNS, certificates, and sign-in. The [network-zone notes](../networking/README.md#network-zones)
explain which clients and workloads can make those connections.

## Files and databases

I keep databases on VM-local disks and bulk files on TrueNAS. For Immich, that
means PostgreSQL is backed up with the application VM while the photo library
needs its own file backup. The [storage page](../storage/README.md) has the full
data and backup layout.

The app and media VMs wait for their NAS mounts before starting Docker. The
media VM sees only the download and media exports. Jellyfin reads the library;
Sonarr and Radarr write to it. The [media page](../media/README.md) follows that
path from request to playback.

## Shared dependencies

Grouping services into VMs makes them easier to maintain separately, but they
still share hardware and supporting services:

| Dependency | What relies on it |
|---|---|
| OPNsense, switch, and access point | Routing between zones and client connectivity |
| Raspberry Pi | DNS, private web proxy, Vaultwarden, search, and the cluster quorum device |
| Authentik VM | New sign-ins for integrated apps; behavior of existing sessions depends on the app |
| TrueNAS | Photos, synced files, downloads, media, and the PBS datastore |
| ROG Ally GPU | Hardware transcoding in the media VM |
| Monitoring VM | Metrics, logs, dashboards, and most centralized alerts |

The quorum device contributes a vote, not another copy of a VM disk. Likewise,
PBS on a NAS export can recover a VM disk but shares the NAS's failure boundary.
The [Proxmox notes](../proxmox/README.md#supporting-devices) and
[backup notes](../storage/README.md#backups) cover those tradeoffs.

## Keeping it running

- [Monitoring](../monitoring/README.md) connects host metrics, logs, application
  checks, and notifications.
- [Automation](../automation/README.md) follows a configuration change from a
  Forgejo pull request through backup, deployment, and checking the application.
- [Security](../security/README.md) covers image scans, runtime events, firewall
  blocking, and download scans.

The [roadmap](../ROADMAP.md) includes the management/server VLAN split, UPS
monitoring, and the remaining deployment and recovery exercises.
