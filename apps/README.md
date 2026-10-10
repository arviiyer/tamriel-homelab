# Apps and services

[Home](../README.md) · [The setup](../docs/architecture.md)

These are the tools I use to host services, manage changes, and keep an eye on
Tamriel. Each section links to the relevant setup notes and the project's own
documentation.

- [Dashboards and monitoring](#dashboards-and-monitoring)
- [Git and updates](#git-and-updates)
- [Networking and sign-in](#networking-and-sign-in)
- [Storage and backups](#storage-and-backups)
- [Hosts and containers](#hosts-and-containers)
- [Security](#security)

## Dashboards and monitoring

### Grafana

[![Trivy summary in Grafana](../evidence/screenshots/grafana-security-dashboard.png)](../evidence/screenshots/README.md#trivy-dashboard)

I use Grafana to view metrics and logs. The Trivy dashboard above shows finding
totals and new findings with available fixes. Its secret panel reports file
scans; Git-history scanning runs separately. The public dashboard example also
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

## Git and updates

### Forgejo

[![Forgejo checking a dependency-update pull request](../evidence/screenshots/forgejo-validation-run.png)](../evidence/screenshots/README.md#forgejo-ci)

Forgejo hosts my private configuration repositories. The screenshot shows
Compose checks passing on a dependency-update pull request. The
[deployment example](../automation/ci/README.md) shows how a separate request can
deploy the commit that passed validation and roll back an unhealthy change.

[Git and update workflow](../automation/README.md#git-and-updates) ·
[Forgejo documentation](https://forgejo.org/docs/latest/)

### Renovate

Renovate opens dependency-update pull requests in the configuration repositories.
Those changes go through the Git workflow described on the automation page.

[Update notes](../automation/README.md#git-and-updates) ·
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

## Storage and backups

### TrueNAS and ZFS

TrueNAS SCALE runs on the UGREEN NAS and holds shared bulk files. The four hard
drives form two mirrored pairs. Application databases stay on the VMs' own disks;
the [storage notes](../storage/README.md#where-data-lives) explain that choice.

[Storage setup](../storage/README.md) ·
[TrueNAS documentation](https://www.truenas.com/docs/scale/)

### Proxmox Backup Server and Restic

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
