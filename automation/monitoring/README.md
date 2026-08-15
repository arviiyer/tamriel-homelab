# Security Observability Dashboard

This public evidence slice provisions a purpose-written Grafana dashboard for
the Trivy and Falco contracts published in this repository. It demonstrates how
scanner health, actionable finding deltas, and runtime events are separated for
operator review.

Status: **Drafted static evidence**. Grafana accepts the dashboard and
provisioning files, but no operated-environment screenshot is included yet.

## Review Path

The dashboard answers four questions in order:

1. Did the security scanner run and preserve a recent complete baseline?
2. Which new findings or security-relevant transitions require action?
3. Which current high-impact findings remain assigned to a workload?
4. What runtime events are Falco sensors forwarding for investigation?

This ordering prevents an empty finding panel from being mistaken for a healthy
control. Finding statistics display zero only when the successful-baseline
timestamp exists; missing health telemetry remains visible as no data.

## Layout

```text
automation/monitoring/
|-- grafana/
|   |-- dashboards/
|   |   `-- security-control-overview.json
|   `-- provisioning/
|       |-- dashboards/security.yml
|       `-- datasources/security.yml
|-- tests/test_dashboard.py
`-- requirements.txt
```

## Data Contracts

Prometheus panels consume only metrics emitted by the public Trivy slice:

- attempt and complete-baseline timestamps;
- overall and per-repository scan success;
- current, new, fixed, and transitioned vulnerability findings;
- current and new misconfiguration findings; and
- current-tree secret findings.

Loki panels use the public Falcosidekick stream contract:

```logql
{source="syscall"}
```

The dashboard does not embed a production datasource UID. The provisioning
example creates `security-prometheus` and `security-loki` against `example.com`
URLs. Adapt those URLs in a private deployment without changing panel identity.

## File Ownership

The dashboard provider disables UI updates and deletion. Reviewed files remain
the source of truth, and Grafana polls the directory every 30 seconds. This
avoids configuration drift from unreviewed UI edits.

## Validate

Run structural and query-reference tests:

```bash
python3 -m unittest discover \
  -s automation/monitoring/tests \
  -p 'test_*.py' \
  -v
```

Public CI also starts Grafana 12.4.1 from an immutable image digest, mounts the
provisioning files read-only, and requires the dashboard API to return the
expected UID. This catches errors that JSON parsing alone cannot detect.

## Production Differences

The operated environment uses private datasource locations, additional
infrastructure dashboards, and environment-specific labels. Those identifiers,
raw exports, screenshots, and unrelated panels are deliberately excluded.

## Limitations

- Dashboard loading does not prove that production datasources are reachable or
  that every query parses or returns the expected data.
- Falco panels depend on Falcosidekick preserving `source`, `priority`,
  `hostname`, and `rule` as Loki stream labels.
- The dashboard shows detection and scanner telemetry, not complete SIEM
  coverage.
- A reviewed runtime screenshot and query walkthrough are still required before
  this becomes operated evidence.
