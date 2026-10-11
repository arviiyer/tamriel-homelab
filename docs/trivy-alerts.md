# Making vulnerability alerts useful

[Home](../README.md) · [Security](../security/README.md) ·
[Trivy setup](../automation/trivy/README.md)

Repeated scans kept reporting the same vulnerabilities. A failed scan could also
produce incomplete output that looked like things had been fixed.

## Comparing scans

I added a saved JSON result to compare complete Trivy scans. The scanner reads
image references from Compose files and scans through the registry, so it needs
no access to the hosts' Docker sockets. It also checks repository files for
configuration issues and secrets.

If any required scan fails, the previous result stays in place. Separate health
metrics report the failure without replacing the last known findings.

## What triggers an alert

| Finding | When to alert |
|---|---|
| New critical vulnerability | Always |
| New high vulnerability | When a fix exists |
| Existing vulnerability becomes critical | Alert on the severity change |
| Fix becomes available for a high/critical vulnerability | Alert on the new fix |
| Secret in checked-out files | Every complete scan |
| New critical misconfiguration | Always |

Separate alerts cover failed, missing, and stale scans. Findings without fixes
remain visible in Grafana.

## Reading the findings

Alerts focus on changes and available fixes. A JSON report lists the affected
CVEs, packages, images, and files.

The screenshots show the [dashboard](../screenshots/README.md#trivy-dashboard)
and a [Discord alert](../screenshots/README.md#discord-alert) for eight
new high-severity findings with fixes available.

[Setup, comparison rules, and limitations](../automation/trivy/README.md)
