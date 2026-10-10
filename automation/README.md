# Automation

[Home](../README.md) · [Apps and services](../apps/README.md) ·
[Security](../security/README.md)

Forgejo hosts the lab's configuration, Renovate opens dependency-update pull
requests, and Ansible handles host configuration. This page connects that
workflow to the scripts, roles, and examples in the repository.

## Git and updates

[![Compose validation in Forgejo](../evidence/screenshots/forgejo-validation-run.png)](../evidence/screenshots/README.md#forgejo-ci)

Compose checks passing on a dependency-update pull request. The lab's
configuration repositories live in private Forgejo, with credentials and
application data outside Git.

Renovate opens update pull requests for review. Compose and service-specific
checks run before merge. Merging records the configuration change; applying it
is a separate step.

The [deployment example](ci/README.md) separates validation from deployment.
A manual request selects one commit, validation checks that commit, and the
target checks it again before allowing an image change. Service health checks
decide whether to record success or restore the previous definition.

[How deployment and rollback work](../docs/case-studies/fail-closed-infrastructure-delivery.md) ·
[Recorded disposable-host exercise](../evidence/drills/2026-08-24-fail-closed-delivery-rollback.md)

## Runners and deployment

Forgejo Actions runs on a dedicated VM. General validation jobs use the CI runner;
image publication uses a separate release runner with the required Docker access.
Application databases, NAS mounts, and service credentials stay off the runner VM.

Stirling PDF and Tamriel Sandbox have manually triggered deployment workflows.
Other services use their documented manual apply steps after review and merge.
Stirling PDF deployment saves its persistent configuration before changing the
image. The sandbox also needs database-aware handling when migrations change.

The public deployment example exercises commit selection, image-only changes,
health checks, and rollback against a disposable service. Its
[test documentation](ci/README.md#tests) describes that scope.

## VM provisioning

The [Forge portal](../proxmox/README.md#provisioning) uses Terraform and cloud-init
for VMs. Ansible configures the hosts afterward. Provisioning a machine and
updating an application on it are separate workflows.

## Host maintenance

The [Ansible examples](ansible/README.md) configure SSH and security updates.
The SSH role checks a fresh connection after applying changes and arms a rollback
timer before changing access. Full upgrades run one host at a time and stop on
failure. The setup guide lists prerequisites and the checks still to exercise
on disposable hosts.

## Examples

Each component has setup instructions and test commands:

| Component | What it does |
|---|---|
| [Trivy](trivy/README.md) | Scan images and repositories, compare findings, alert on changes |
| [Deployment](ci/README.md) | Deploy the commit checked by CI; roll back unhealthy changes |
| [Recovery](recovery/README.md) | Check archives and restore into a new directory |
| [Ansible](ansible/README.md) | Configure SSH and updates; upgrade one host at a time |
| [Falco](falco/README.md) | Detect suspicious runtime activity and route events |
| [Grafana](monitoring/README.md) | Display scan results and Falco events |
| [Syncthing](../apps/syncthing/README.md) | Run file sync with a local management interface |
| [Caddy](../networking/caddy/README.md) | Route a hostname to an internal upstream |
| [Host metrics](../monitoring/host-metrics/README.md) | Scrape metrics and load a Grafana dashboard |

## Checks in this repository

| Workflow | When it runs | What it checks |
|---|---|---|
| [Repository checks](../.github/workflows/validate.yml) | Pull requests, pushes to `main`, or manual runs | Publication rules, Markdown links, validation scripts, and Git-history secrets |
| [Automation examples](../.github/workflows/examples.yml) | Relevant automation or service-example changes, or manual runs | Component tests and configuration validation |
| [Integration checks](../.github/workflows/integration.yml) | Manual runs | Service-example smoke tests, container checks, Grafana loading, PromQL, and the delivery drill image build |

The complete delivery drill has its own
[disposable-host requirements](ci/README.md#tests). The integration workflow
builds its image; the recorded drill describes the full SSH and Compose exercise.

## Notes

- [Forgejo documentation](https://forgejo.org/docs/latest/)
- [Renovate documentation](https://docs.renovatebot.com/)
- [Ansible documentation](https://docs.ansible.com/ansible/latest/)
