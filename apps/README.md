# Apps

[Home](../README.md) · [The setup](../docs/architecture.md)

These are the apps and services in Tamriel, from photos and file sync to the
tools that keep the lab running.

- [Files, photos, and documents](#files-photos-and-documents)
- [Reading and utilities](#reading-and-utilities)
- [Media and games](#media-and-games)
- [Small projects](#small-projects)
- [Dashboards and monitoring](#dashboards-and-monitoring)
- [Git and updates](#git-and-updates)
- [Networking and sign-in](#networking-and-sign-in)
- [Storage and backups](#storage-and-backups)
- [Hosts and containers](#hosts-and-containers)
- [Security](#security)

## Files, photos, and documents

### Syncthing

Syncthing syncs my documents, pictures, and Obsidian notes between devices. The
lab copy lives on the NAS. It replaced Nextcloud for this job.

[Setup and Compose example](syncthing/README.md) ·
[Syncthing documentation](https://docs.syncthing.net/)

### Immich

[![Landscape album in Immich](../screenshots/immich-album.webp)](immich/README.md)

I keep my photo library in Immich, with the photos on TrueNAS and the database
on the application VM. It uses Authentik for sign-in. Backing it up means keeping
both the library and database, since neither is useful as a complete restore
on its own.

[Setup, phone backups, and updates](immich/README.md) ·
[Immich documentation](https://docs.immich.app/)

### Stirling PDF

I use Stirling PDF for browser-based jobs such as rotating pages and merging
documents. It has its own login. Updates go through a manually triggered Forgejo
workflow that saves its configuration before changing the image.

[Deployment workflow](../automation/README.md#git-and-updates) ·
[Stirling PDF documentation](https://docs.stirlingpdf.com/)

## Reading and utilities

### FreshRSS

[![FreshRSS feed categories and articles](../screenshots/freshrss-reader.webp)](freshrss/README.md)

FreshRSS is my browser-based feed reader, with security news and technical
articles. Selected feeds fetch full article text. A custom extension caches
article images so the reading view can load them locally behind sign-in.

[Setup notes](freshrss/README.md) ·
[FreshRSS documentation](https://freshrss.github.io/FreshRSS/)

### Homarr

[![Homarr service cards and reading brief](../screenshots/homarr-home.webp)](../screenshots/README.md#homarr)

Homarr brings my service links and widgets together. I also use it to read the
[Morning SOC Briefing](projects/README.md#morning-soc-briefing), with source
excerpts and links back to FreshRSS. It uses a Custom API widget because the RSS
widget cuts the text short. Homarr has its own local login.

[Setup, Compose, and reading widget](homarr/README.md) ·
[Homarr documentation](https://homarr.dev/docs/)

### Vaultwarden

Vaultwarden holds my passwords, with Bitwarden clients connecting to it. It runs
on the Raspberry Pi behind Caddy. I keep Restic backups locally and on another
host, so the vault's only copy is not on the Pi.

[Backup notes](../storage/README.md#backups) ·
[Vaultwarden documentation](https://github.com/dani-garcia/vaultwarden/wiki)

### SearXNG

SearXNG is my private search page on the Raspberry Pi. The same hostname works
through local DNS at home and Tailscale when away.

[DNS and access](../networking/README.md#dns) ·
[SearXNG documentation](https://docs.searxng.org/)

### Local chat and Speedtest

The llama.cpp web interface runs on my laptop when needed, reached through Caddy
over Tailscale. It is separate from the reading brief's CPU model on the app VM.
The Pi also hosts a Speedtest web service; its exact application and setup still
need documenting.

[llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)

## Media and games

I use Jellyfin for playback and Seerr for requests. The Servarr applications
organize downloads and media. This runs on the ROG Ally, whose GPU is passed
through to the media VM for transcoding. The [Media page](../media/README.md)
shows how the pieces connect, and the [Jellyfin guide](../media/jellyfin/README.md)
covers setup and GPU checks.

[![Jellyfin library and Continue Watching](../screenshots/jellyfin-library.webp)](../media/jellyfin/README.md)

[![Seerr discovery view](../screenshots/seerr-discover.webp)](../media/README.md#requests-and-downloads)

| Service | Use | Project |
|---|---|---|
| Jellyfin | Media playback and hardware transcoding | [Setup](../media/jellyfin/README.md) · [Docs](https://jellyfin.org/docs/) |
| Seerr | Media requests | [Docs](https://docs.seerr.dev/) |
| Sonarr | TV library management | [Docs](https://wiki.servarr.com/sonarr) |
| Radarr | Movie library management | [Docs](https://wiki.servarr.com/radarr) |
| Lidarr | Music library management | [Docs](https://wiki.servarr.com/lidarr) |
| Readarr | Book library management | [Project](https://github.com/Readarr/Readarr) |
| Prowlarr | Indexer management | [Docs](https://wiki.servarr.com/prowlarr) |
| qBittorrent | Torrent downloads | [Project](https://www.qbittorrent.org/) |
| NZBGet | Usenet downloads | [Docs](https://nzbget.com/documentation/) |
| Gluetun | VPN connection for the download stack | [Docs](https://github.com/qdm12/gluetun-wiki) |
| FlareSolverr | Browser helper for indexer requests | [Project](https://github.com/FlareSolverr/FlareSolverr) |
| deunhealth | Restart selected unhealthy containers | [Project](https://github.com/qdm12/deunhealth) |
| Seerr Discord Approver | Approve or deny requests from Discord | [Notes](projects/README.md#seerr-discord-approver) |
| Minecraft | Game server in its own VM | [Project](https://www.minecraft.net/) |

## Small projects

The [project notes](projects/README.md) cover the Morning SOC Briefing, Forge VM
provisioner, Seerr Discord Approver, and desktop Printer Monitor. The
[sandbox notes](../security/README.md#tamriel-sandbox) describe the paused analysis
project.

## Dashboards and monitoring

### Grafana

[![CPU, memory, network, and disk panels in Grafana](../screenshots/grafana-host-metrics.webp)](../monitoring/README.md)

I use Grafana to view metrics and logs. The Node Exporter dashboard above shows
host CPU, memory, network traffic, and disk usage. A separate
[Trivy dashboard](../screenshots/README.md#trivy-dashboard) shows finding
totals and new findings with available fixes. The public dashboard example also
includes Falco events.

[Monitoring](../monitoring/README.md) ·
[Dashboard configuration](../automation/monitoring/README.md) ·
[Grafana documentation](https://grafana.com/docs/grafana/latest/)

### Prometheus, Loki, and Alertmanager

Prometheus collects metrics, Loki collects logs, and Alertmanager handles
notifications. Grafana brings the metrics and logs together. The
[monitoring notes](../monitoring/README.md#metrics-logs-and-alerts) show how scan
results and runtime events reach the dashboard and notifications.

[Prometheus](https://prometheus.io/docs/introduction/overview/) ·
[Loki](https://grafana.com/docs/loki/latest/) ·
[Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/)

### Uptime Kuma, Node Exporter, Promtail, and Pushgateway

Uptime Kuma checks whether services are reachable. Node Exporter supplies host
metrics, Promtail ships host logs to Loki, and Pushgateway holds batch-job metrics
from Trivy and ClamAV. The [monitoring page](../monitoring/README.md) covers both
host health and application checks.

[Uptime Kuma](https://github.com/louislam/uptime-kuma) ·
[Node Exporter](https://github.com/prometheus/node_exporter) ·
[Promtail](https://grafana.com/docs/loki/latest/send-data/promtail/) ·
[Pushgateway](https://github.com/prometheus/pushgateway)

## Git and updates

### Forgejo

[![Forgejo checking a dependency-update pull request](../screenshots/forgejo-validation-run.png)](../screenshots/README.md#forgejo-ci)

Forgejo hosts my private configuration repositories. The screenshot shows
Compose checks passing on a dependency-update pull request. The
[deployment example](../automation/ci/README.md) shows how a separate request can
deploy the commit that passed validation and roll back an unhealthy change.

[Git and update workflow](../automation/README.md#git-and-updates) ·
[Forgejo documentation](https://forgejo.org/docs/latest/)

Forgejo Actions uses separate general CI and image-release runners on a dedicated
VM. The [runner notes](../automation/README.md#runners-and-deployment) explain
which jobs run on each.

### Renovate

Renovate opens dependency-update pull requests in the configuration repositories.
Those changes go through the Git workflow described on the automation page.

[Setup and update walkthrough](../automation/renovate/README.md) ·
[Renovate documentation](https://docs.renovatebot.com/)

### Ansible

I use Ansible for host configuration. The public examples cover key-only SSH,
automatic security updates, and full upgrades one host at a time.

[Host maintenance](../automation/README.md#host-maintenance) ·
[Playbooks and requirements](../automation/ansible/README.md) ·
[Ansible documentation](https://docs.ansible.com/ansible/latest/)

## Networking and sign-in

### OPNsense

OPNsense runs on the ThinkCentre router/firewall. Together with the managed
switches, it separates administration, applications, and client devices into
network zones.

[Network layout](../networking/README.md#opnsense-and-the-network) ·
[OPNsense documentation](https://docs.opnsense.org/)

### Tailscale

I use Tailscale for private administrative access to the lab. Management services
still require their own logins.

[Admin access](../networking/README.md#tailscale) ·
[Tailscale documentation](https://tailscale.com/kb)

### Caddy and Authentik

Caddy routes requests to web applications. Authentik provides sign-in through
OIDC or forward authentication where the application supports it.

[Web access and sign-in](../networking/README.md#caddy-and-authentik) ·
[Caddy documentation](https://caddyserver.com/docs/) ·
[Authentik documentation](https://docs.goauthentik.io/)

### Pi-hole, Unbound, UniFi Network, and Cloudflare

Pi-hole and Unbound handle client DNS. UniFi Network manages the switch and Wi-Fi
access point. Cloudflare provides public DNS and a separate Tunnel for Minecraft;
the ordinary web apps use private Caddy routes.

[Networking notes](../networking/README.md) ·
[Pi-hole](https://docs.pi-hole.net/) ·
[Unbound](https://unbound.docs.nlnetlabs.nl/) ·
[UniFi Network](https://help.ui.com/hc/en-us/categories/6583256751383-UniFi-Network) ·
[Cloudflare DNS](https://developers.cloudflare.com/dns/)

## Storage and backups

### TrueNAS and ZFS

[![TrueNAS storage layout and health](../screenshots/truenas-storage.webp)](../storage/README.md)

TrueNAS SCALE runs on the UGREEN NAS and holds shared bulk files. The four hard
drives form two mirrored pairs. Application databases stay on the VMs' own disks;
the [storage notes](../storage/README.md#where-data-lives) explain that choice.

[Storage setup](../storage/README.md) ·
[TrueNAS documentation](https://www.truenas.com/docs/scale/)

### Proxmox Backup Server and Restic

[![PBS backup task completed successfully](../screenshots/pbs-backup.webp)](../storage/README.md#backups)

PBS and Restic are the lab's backup tools, alongside VM snapshots and off-host
copies for selected data. The storage page introduces the different backup
layers and links to a restore exercise using generated files.

[Backups and restore testing](../storage/README.md#backups) ·
[PBS documentation](https://pbs.proxmox.com/docs/) ·
[Restic documentation](https://restic.readthedocs.io/en/stable/)

## Hosts and containers

### Proxmox VE

Three Proxmox nodes host Debian VMs grouped by role. The hardware includes a
GMKtec mini PC, an ACEMAGIC mini PC, and an ROG Ally with GPU passthrough for media.

[Cluster and VM roles](../proxmox/README.md) ·
[Proxmox documentation](https://pve.proxmox.com/pve-docs/)

### Docker Compose

Most services run with Docker Compose inside the VMs. Compose definitions also
feed the [image scanner](../automation/trivy/README.md), which reads image
references and scans through the registry.

[How services fit together](../docs/architecture.md) ·
[Docker Compose documentation](https://docs.docker.com/compose/)

Terraform and cloud-init support provisioning through the
[Forge portal](../proxmox/README.md#provisioning). The Raspberry Pi also supplies
the cluster's quorum-device vote. PostgreSQL, Redis, and SQLite are dependencies
of the relevant applications; their data placement is covered under
[Storage](../storage/README.md#where-data-lives).

## Security

### Trivy

Trivy scans images and repository files for vulnerabilities, configuration
issues, and secrets. I compare complete scans so alerts can focus on new
findings and available fixes.

[Security setup](../security/README.md#trivy) ·
[Scanner example](../automation/trivy/README.md) ·
[Trivy documentation](https://trivy.dev/docs/latest/)

### Falco

Falco watches runtime activity. Falcosidekick routes events to Loki and
Alertmanager, connecting detection to the monitoring tools.

[Runtime detection](../security/README.md#falco) ·
[Deployment example](../automation/falco/README.md) ·
[Falco documentation](https://falco.org/docs/)

### CrowdSec and ClamAV

CrowdSec and ClamAV cover network defense and malware scanning. The
[security notes](../docs/threat-model.md) describe the threats considered across
the lab.

[Security overview](../security/README.md) ·
[CrowdSec documentation](https://docs.crowdsec.net/) ·
[ClamAV documentation](https://docs.clamav.net/)
