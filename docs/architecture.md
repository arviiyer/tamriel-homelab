# The setup

Three Proxmox nodes host Debian VMs for applications, identity, monitoring,
security tools, Git/CI, and backups. Most applications run with Docker Compose.
Terraform and cloud-init handle VM provisioning and templates; Ansible handles
host configuration.

[Overview diagram](../README.md#the-setup)

## Access and networking

Tailscale provides private admin access. Hypervisor, gateway, and storage
management stay off the public internet, and each service still requires its
own login. This reduces exposure but makes admin access depend on Tailscale and
trusted devices; recovery needs a separate access method.

Trusted clients reach web applications through Caddy, with Authentik sign-in
where supported. OPNsense and managed switches separate infrastructure, personal
devices, work devices, guests, media, and sandbox workloads. The
[networking notes](network-and-identity.md) cover which connections are allowed.

## Storage

Databases stay on the VMs' own disks so a shared-storage outage does not also
take away their database files. TrueNAS and ZFS hold bulk files and provide
snapshots and integrity checks. Local and shared data need separate backups;
this setup does not provide automatic database failover.

A missing network mount can leave an ordinary directory in its place. The
[systemd example](../automation/recovery/README.md#storage-checks) checks the mount
and a dataset marker before starting a service, preventing writes to that empty
local directory.

## Monitoring and security

Prometheus collects metrics, Loki collects logs, Grafana displays both, and
Alertmanager sends notifications. Trivy scans for vulnerabilities, configuration
issues, and secrets. Falco watches runtime activity; CrowdSec and ClamAV handle
network defense and malware scanning.

The [Trivy example](../automation/trivy/README.md) tracks scanner health separately
from findings so a failed scan cannot look like a clean result. See also the
[Falco routing](../automation/falco/event-flow.md),
[Grafana configuration](../automation/monitoring/README.md), and
[security notes](threat-model.md).

## Changes and deployment

Configuration lives in private Forgejo repositories, with Renovate opening
dependency-update pull requests. Credentials and application data stay outside
Git. The [Ansible examples](../automation/ansible/README.md) configure SSH,
security updates, and one-host-at-a-time upgrades.

In the [deployment example](../automation/ci/README.md), CI checks one exact
commit without deployment credentials. Deployment requires a separate manual
request. The target checks that commit again, allows only an image change, and
checks service health before recording success. These extra checks add
complexity, but limit what a compromised CI runner can change. Database migrations
need their own recovery plan.

## Recovery

The backup tools are Proxmox Backup Server and Restic, with VM snapshots and
off-host copies for selected data.

The [restore example](../automation/recovery/README.md) checks an archive's
checksum and contents before writing to a new directory. It never overwrites an
existing destination. This needs spare disk space and application-specific checks
before replacing live data. The included drill runs offline with generated files.
