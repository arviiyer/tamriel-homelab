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

The [deployment example](ci/README.md) separates validation from deployment.
A manual request selects one commit, validation checks that commit, and the
target checks it again before allowing an image change. Service health checks
decide whether to record success or restore the previous definition.

[How deployment and rollback work](../docs/case-studies/fail-closed-infrastructure-delivery.md) ·
[Recorded disposable-host exercise](../evidence/drills/2026-08-24-fail-closed-delivery-rollback.md)

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

## Checks in this repository

| Workflow | When it runs | What it checks |
|---|---|---|
| [Repository checks](../.github/workflows/validate.yml) | Pull requests, pushes to `main`, or manual runs | Publication rules, Markdown links, validation scripts, and Git-history secrets |
| [Automation examples](../.github/workflows/examples.yml) | Relevant automation changes or manual runs | Component tests and configuration validation |
| [Integration checks](../.github/workflows/integration.yml) | Manual runs | Container-backed configuration checks, Grafana loading, PromQL, and the delivery drill image build |

The complete delivery drill has its own
[disposable-host requirements](ci/README.md#tests). The integration workflow
builds its image; the recorded drill describes the full SSH and Compose exercise.

## Notes

- [Forgejo documentation](https://forgejo.org/docs/latest/)
- [Renovate documentation](https://docs.renovatebot.com/)
- [Ansible documentation](https://docs.ansible.com/ansible/latest/)
