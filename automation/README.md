# Automation

[Home](../README.md) · [Apps and services](../apps/README.md) ·
[Security](../security/README.md)

I keep configuration in Forgejo, review image updates from Renovate, and use
Ansible for host settings and OS updates. Merging a change and applying it are
separate steps.

## Git and updates

[![Compose validation in Forgejo](../screenshots/forgejo-validation-run.png)](../screenshots/README.md#forgejo-ci)

Compose checks passing on a dependency-update pull request. The lab's
configuration repositories live in private Forgejo, with credentials and
application data outside Git.

For a typical application update:

1. Review Renovate's image change and the upstream release notes.
2. Wait for Compose and service checks, then merge the pull request.
3. Back up the app's data and configuration, keeping the old image reference.
4. Apply the checked commit on its host and recreate the affected containers.
5. Check sign-in and an ordinary task in the app, then record the result.

The [Forgejo guide](forgejo/README.md) covers installation, private access,
Authentik sign-in, and backups. The [Renovate guide](renovate/README.md) covers
the bot account, Docker configuration, daily timer, and the steps from an update
PR to deployment.

## Runners and deployment

Forgejo Actions runs on a dedicated VM. General validation jobs use the CI runner;
image publication uses a separate release runner with the required Docker access.
Application databases, NAS mounts, and service credentials stay off the runner VM.

Stirling PDF and Tamriel Sandbox have manually triggered deployment workflows.
Other services use their documented manual apply steps after review and merge.
Stirling PDF deployment saves its persistent configuration before changing the
image. The sandbox also needs database-aware handling when migrations change.

The [deployment guide](ci/README.md) includes the exact-commit request and
rollback helper for a small API service, with the checks on the runner and target.

## VM provisioning

The [Forge portal](../projects/forge/README.md) uses Terraform and cloud-init
for VMs. Ansible configures the hosts afterward. Provisioning a machine and
updating an application on it are separate workflows.

## Host maintenance

The [Ansible examples](ansible/README.md) configure SSH and security updates.
The SSH role checks a fresh connection after applying changes and arms a rollback
timer before changing access. Full upgrades run one host at a time and stop on
failure. The setup guide covers prerequisites, configuration, and a first run.

## Scripts and playbooks

Each component has setup instructions and test commands:

| Component | What it does |
|---|---|
| [Forgejo](forgejo/README.md) | Host Git repositories, pull requests, and Actions workflows |
| [Trivy](trivy/README.md) | Scan images and repositories, compare findings, alert on changes |
| [Deployment](ci/README.md) | Deploy the commit checked by CI; roll back unhealthy changes |
| [Renovate](renovate/README.md) | Open Docker image update PRs in Forgejo on a daily schedule |
| [Ansible](ansible/README.md) | Configure SSH and updates; upgrade one host at a time |
| [Falco](falco/README.md) | Detect suspicious runtime activity and route events |
| [ClamAV](../security/clamav/README.md) | Scan downloads and distinguish findings from scan errors |
| [Terraform](../proxmox/terraform/README.md) | Clone one Debian VM with cloud-init and an SSH public key |
| [Grafana](../monitoring/security-dashboard/README.md) | Display scan results and Falco events |

Application configuration lives beside its [setup guide](../README.md#setup-guides).

## Checks in this repository

| Workflow | When it runs | What it checks |
|---|---|---|
| [Repository checks](../.github/workflows/validate.yml) | Pull requests, pushes to `main`, or manual runs | File checks, Markdown links, validation scripts, and Git-history secrets |
| [Automation examples](../.github/workflows/examples.yml) | Relevant automation or service-example changes, or manual runs | Component tests, Terraform plans, and configuration validation |
| [Project examples](../.github/workflows/projects.yml) | Relevant project changes, or manual runs | Python and Go tests, race checks, sample runs, and mocked multi-VM Terraform plans |
| [Integration checks](../.github/workflows/integration.yml) | Manual runs | App stacks, DNS, browser sign-in, alerts, Grafana, PromQL, and the delivery drill image build |

Each component lists its test commands. The [deployment drill](ci/README.md#tests)
also exercises SSH and Compose on a disposable host.

## Notes

- [Forgejo documentation](https://forgejo.org/docs/latest/)
- [Renovate documentation](https://docs.renovatebot.com/)
- [Ansible documentation](https://docs.ansible.com/ansible/latest/)
