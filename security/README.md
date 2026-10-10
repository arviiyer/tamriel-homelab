# Security

[Home](../README.md) · [Apps and services](../apps/README.md) ·
[Monitoring](../monitoring/README.md)

The lab uses Trivy for image and repository scans, Falco for runtime activity,
CrowdSec for network defense, and ClamAV for malware scanning. Prometheus, Loki,
Grafana, and Alertmanager connect scan results and events to dashboards and
notifications.

Setup guides: [Trivy](../automation/trivy/README.md) ·
[Falco](../automation/falco/README.md) · [CrowdSec](crowdsec/README.md) ·
[ClamAV](clamav/README.md)

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

Falco watches runtime activity on the service VMs using its modern eBPF engine.
I use Falcosidekick to send those events to Loki and Alertmanager. The
[setup guide](../automation/falco/README.md) includes an Ansible role and two
rule-tuning examples.

The [routing notes](../automation/falco/event-flow.md) explain which priorities
produce notifications and how to check event delivery.

[Falco setup and tuning](../automation/falco/README.md) ·
[Falco documentation](https://falco.org/docs/)

## CrowdSec and ClamAV

CrowdSec runs on OPNsense, using local detections and community decisions for
network blocking. Prometheus collects its metrics alongside the firewall's host
metrics.

ClamAV runs on the media VM and scans the downloads share. A host-side job waits
for the mount and daemon, invokes the container's scanner, and sends result and
freshness metrics to Pushgateway. Quarantined files stay separate from the media
library. The [Media page](../media/README.md) explains the storage layout.

These tools sit alongside the access controls in the
[networking notes](../networking/README.md) and host maintenance covered by
[Ansible](../automation/ansible/README.md).

[CrowdSec setup and metrics](crowdsec/README.md) ·
[ClamAV scans and scheduling](clamav/README.md)

## Tamriel Sandbox

The sandbox project has a FastAPI control plane, a React analyst interface, and
a C# agent in a disposable Windows VM. Proxmox snapshots provide a clean baseline
between runs. The UI brings together run state, telemetry, screenshots, and
console access.

Analysis is currently paused: the Windows worker and scheduler are stopped,
while the private API, UI, and database remain available. Broader reliability
and browser-telemetry work is unfinished.

The worker has separate network access from ordinary applications, and analysis
data has its own storage. The [project guide](../projects/sandbox/README.md)
explains the architecture and includes a generated lifecycle walkthrough.

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
