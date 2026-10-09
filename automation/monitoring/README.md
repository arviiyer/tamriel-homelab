# Grafana dashboard

A Grafana dashboard loaded from files, showing Trivy scan results and Falco events.

## What it shows

Panels show scanner health, new findings, totals, and runtime events. Totals show
zero only if a successful scan has been recorded. Missing health data stays
“no data.”

## Setup

- [Dashboard JSON](grafana/dashboards/security-control-overview.json)
- [Dashboard provider](grafana/provisioning/dashboards/security.yml)
- [Datasource definitions](grafana/provisioning/datasources/security.yml)

Datasources use `security-prometheus` and `security-loki` UIDs with `example.com`
URLs. In an adapted deployment, change the URLs while retaining those UIDs.
The provider disables UI updates and deletion and polls the files every 30 seconds.

Prometheus panels use the [Trivy metrics](../trivy/README.md#metrics-and-alerts)
for scan attempts, complete baselines, success, findings, and metadata changes.
Loki panels select `{source="syscall"}` and require Falcosidekick to preserve
`source`, `priority`, `hostname`, and `rule` stream labels.

## Tests

From the repository root, with Docker and the dependencies in [requirements.txt](requirements.txt):

```bash
python3 -m unittest discover -s automation/monitoring/tests -p 'test_*.py' -v
python3 automation/monitoring/tests/validate_promql.py
python3 automation/monitoring/tests/validate_grafana.py
```

The Grafana check starts a pinned 12.4.1 container, loads the files read-only,
and checks the dashboard and folder through the API.

The PromQL check runs the dashboard's failed-repository query with pinned
`promtool`, covering healthy, failed, mixed, attempt-only, and missing-data cases.
It uses `count` because summing zero-valued failure samples would always report
zero. Testing the remaining queries is on the [roadmap](../../ROADMAP.md).
