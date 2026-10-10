# Setup guide checks

[Home](../../README.md) · [Setup guides](../../README.md#setup-guides)

Checked on 2026-10-10 using temporary directories and fresh Docker Compose
projects. The examples remove their test containers and volumes afterward.
The Debian package commands were also followed in a fresh Debian 13 container:
Docker Engine, its CLI, and the Compose plugin installed from the signed Docker
APT repository in the [VM guide](../../proxmox/debian-vm/README.md#install-docker).

| Setup | What was checked | Run it |
|---|---|---|
| Apps, Jellyfin, metrics, and Loki | Twelve service examples: startup and their documented API, storage, or query checks | `python3 scripts/check-service-examples.py --smoke all` |
| Media managers | Writable library roots, application startup, and Seerr-to-manager connectivity through a shared namespace | `python3 scripts/check-stack-examples.py --smoke media` |
| Caddy | DNS-enabled build, source restrictions, outpost routing, denied access, and identity outage | `python3 scripts/check-stack-examples.py --smoke access` |
| Authentik | Local-CA HTTPS, browser login and consent, group-based denial, and an unavailable identity server | `python3 networking/private-access/check_authentik.py` |
| Pi-hole and Unbound | Local record, recursive answers, and rejection of invalid DNSSEC signatures | `python3 networking/dns/check.py` |
| Host alerts | A failed scrape and its recovery reach a local Discord-compatible receiver | `python3 scripts/check-stack-examples.py --smoke alerts` |
| Alloy | Journal configuration accepted by Alloy | `python3 scripts/check-stack-examples.py --smoke alloy` |
| ClamAV | Clean, detection, and error exit codes with an inert custom signature; source files retained | `python3 security/clamav/check.py` |
| Terraform | Provider schema validation and three mock-provider plans | `bash proxmox/terraform/check.sh` |

Run commands from the repository root. Component guides list their dependencies.
The [integration workflow](../../.github/workflows/integration.yml) runs the
container checks on GitHub; [example checks](../../.github/workflows/examples.yml)
include the Terraform plans and existing automation tests.

The media test substitutes a namespace peer for the VPN. The Caddy routing test
uses a mock identity service. These runs do not create a Proxmox VM, enroll a
Tailscale device, or issue a public DNS certificate. The corresponding guides
include checks for those provider- and host-specific steps.

The separate Authentik browser test uses a real server, PostgreSQL database, and
embedded outpost. It caught an internal-hostname redirect in the walkthrough;
the guide now uses the reachable HTTPS identity URL and checks that connection
from the Authentik container too.

The repository's 159 Python unit tests, configuration checks, isolated restore
drill, Markdown links, and publication checks also passed. The local publication
audit included the private denylist. The retained Trivy screenshot is an
[approved crop of the September capture](../../screenshots/grafana-security-dashboard.review.md).
