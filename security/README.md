# Security

[Home](../README.md) · [Apps and services](../apps/README.md) ·
[Monitoring](../monitoring/README.md)

The lab uses Trivy for image and repository scans, Falco for runtime activity,
CrowdSec for network defense, and ClamAV for malware scanning. Prometheus, Loki,
Grafana, and Alertmanager connect scan results and events to dashboards and
notifications.

## Trivy

Repeated scans can produce a lot of the same findings. I compare complete
results so alerts can focus on new findings, severity changes, and available
fixes. The [alerting notes](../docs/case-studies/actionable-vulnerability-management.md)
explain that choice and the notification rules.

The [scanner example](../automation/trivy/README.md) reads image references from
Compose files and scans images through the registry. It also checks repository
files for configuration issues and secrets. A failed scan keeps the last good
result and reports the failure separately.

[Scanner setup](../automation/trivy/README.md) ·
[Dashboard and notifications](../monitoring/README.md) ·
[Trivy documentation](https://trivy.dev/docs/latest/)

## Falco

Falco watches runtime activity using its modern eBPF engine. The public example
includes an Ansible role, two rule-tuning examples, and a Falcosidekick Compose
configuration.

Falcosidekick routes events to Loki for searching and Alertmanager for
notifications. Falco's process health and successful event delivery are separate
things to check; the [routing notes](../automation/falco/event-flow.md) explain
what happens if delivery fails.

[Falco setup and tuning](../automation/falco/README.md) ·
[Falco documentation](https://falco.org/docs/)

## CrowdSec and ClamAV

CrowdSec and ClamAV cover network defense and malware scanning. They sit alongside
the access controls described in the [networking notes](../networking/README.md)
and the host maintenance covered by [Ansible](../automation/ansible/README.md).

[CrowdSec documentation](https://docs.crowdsec.net/) ·
[ClamAV documentation](https://docs.clamav.net/)

## Repository checks

GitHub Actions checks publication rules and local Markdown links and scans Git
history for secrets. Changes to automation run the relevant component tests;
container and integration checks run manually. The
[workflow overview](../automation/README.md#checks-in-this-repository) links to
those jobs.

## Notes

- [Threats and assumptions](../docs/threat-model.md)
- [Making vulnerability alerts useful](../docs/case-studies/actionable-vulnerability-management.md)
- [Reporting a repository security issue](../SECURITY.md)
