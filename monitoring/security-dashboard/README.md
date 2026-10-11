# Trivy and Falco dashboard

[Home](../../README.md) · [Monitoring](../README.md)

Load Trivy scan results and Falco events into a Grafana dashboard. It combines
finding totals with scanner health, so a failed scan remains visible alongside
the last complete results.

## What it shows

Panels show scanner health, new findings, totals, and runtime events. Totals show
zero only if a successful scan has been recorded. Missing health data stays
“no data.”

## Setup

Requirements: Docker Compose, Bash, curl, Grafana with administrator access,
Prometheus collecting [Trivy metrics](../../automation/trivy/README.md#metrics-and-alerts), and Loki receiving
[Falcosidekick events](../../automation/falco/event-flow.md). Start with the
[host-metrics guide](../host-metrics/README.md) if Grafana is new.

In your Grafana working directory, download the dashboard and its provisioning
files. This uses the same `provisioning/` layout as the host-metrics guide:

```bash
(
  set -eu
  mkdir -p provisioning/dashboards provisioning/datasources security-dashboard
  for file in provisioning/dashboards/security.yml provisioning/datasources/security.yml; do
    curl --fail --location --output "$file" \
      "https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/monitoring/security-dashboard/grafana/$file"
  done
  curl --fail --location --output security-dashboard/security-control-overview.json \
    https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/monitoring/security-dashboard/grafana/dashboards/security-control-overview.json
)
```

In `provisioning/datasources/security.yml`, replace the
`example.com` URLs with addresses reachable from the Grafana container. Retain
the `security-prometheus` and `security-loki` UIDs used by the dashboard. If you
already have a default datasource, change this file's `isDefault` to `false`.

Keep the existing provisioning-directory mount and add the dashboard mount to
Grafana's `volumes` list. If starting from another Grafana configuration, merge
these files into its provisioning directory first. The resulting mounts are:

```yaml
      - ./provisioning:/etc/grafana/provisioning:ro
      - ./security-dashboard:/var/lib/grafana/dashboards/security:ro
```

Recreate Grafana with `docker compose up -d grafana`, retaining any `-f`
arguments used by your stack. Open **Dashboards → Security → Trivy and Falco**.
Check both datasources under **Connections → Data sources**, then
compare a finding total with its Prometheus query and a recent event with Loki
Explore. A fresh complete Trivy scan should supply the scanner-health panels.

The [provider](grafana/provisioning/dashboards/security.yml) polls files every
30 seconds and disables UI edits. Change the downloaded JSON to edit panels;
keep it and the provisioning files with your Grafana configuration backups.

Prometheus panels use the [Trivy metrics](../../automation/trivy/README.md#metrics-and-alerts)
for scan attempts, complete baselines, success, findings, and metadata changes.
Loki panels select `{source="syscall"}` and require Falcosidekick to preserve
`source`, `priority`, `hostname`, and `rule` stream labels.

| Symptom | First thing to check |
|---|---|
| Dashboard absent | Mount destinations, provider path, and Grafana startup logs |
| Datasource not found | UIDs in the datasource file still match the dashboard |
| Scan panels show no data | Trivy completed a scan and Prometheus scrapes both finding and health jobs |
| Event panels empty | Loki URL, Falcosidekick labels, and selected time range |

## Tests

From the repository root, with Docker and the dependencies in [requirements.txt](requirements.txt):

```bash
python3 -m unittest discover -s monitoring/security-dashboard/tests -p 'test_*.py' -v
python3 monitoring/security-dashboard/tests/validate_promql.py
python3 monitoring/security-dashboard/tests/validate_grafana.py
```

The Grafana check starts a pinned 12.4.1 container, loads the files read-only,
and checks the dashboard and folder through the API.

The PromQL check runs the dashboard's failed-repository query with pinned
`promtool`, covering healthy, failed, mixed, attempt-only, and missing-data cases.
It uses `count` because summing zero-valued failure samples would always report
zero. Testing the remaining queries is on the [roadmap](../../ROADMAP.md).
