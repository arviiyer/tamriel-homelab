# Host metrics

[Home](../../README.md) · [Monitoring](../README.md)

A small Node Exporter, Prometheus, and Grafana stack for host CPU, memory, and
root-filesystem metrics. Grafana loads the datasource and dashboard from files.

## Run it

Requirements: a Linux Docker Engine host, Docker Compose, and free local ports
3000 and 9090. Node Exporter mounts the host's root filesystem, procfs, and sysfs
read-only. Docker Desktop reports its Linux VM rather than the desktop OS.

From the repository root:

```bash
docker compose -p host-metrics-example -f monitoring/host-metrics/compose.yml config --quiet
docker compose -p host-metrics-example -f monitoring/host-metrics/compose.yml up -d
```

Open [Grafana](http://127.0.0.1:3000/d/host-metrics-example) and
[Prometheus targets](http://127.0.0.1:9090/targets). Allow a few scrapes for the
CPU rate. The dashboard shows exporter reachability, available memory, available
root-filesystem space, and CPU use.

Grafana is an anonymous, read-only viewer for this loopback-bound example; initial
admin creation is disabled. Node Exporter has no host-published port and uses
only the internal metrics network. Prometheus and Grafana also join an access
network for their loopback-published interfaces.

## Files

- [Compose stack](compose.yml)
- [Prometheus scrape configuration](prometheus.yml)
- [Dashboard](dashboard.json)
- [Datasource](provisioning/datasources/prometheus.yml)
- [Dashboard provider](provisioning/dashboards/hosts.yml)

Only the CPU, memory, filesystem, and host-information collectors are enabled.
The lab runs Node Exporter as a host service and scrapes multiple machines; this
example keeps everything in one Compose project for a local trial.

## Adapting it

For more hosts, install Node Exporter on each and add explicit scrape targets.
Allow the monitoring host to reach those exporters. Keep Prometheus and Grafana
private, and configure authentication before extending access beyond localhost.

The [networking page](../../networking/README.md#caddy-and-authentik) describes
Grafana's Authentik integration in the lab. The separate
[security dashboard](../../automation/monitoring/README.md) needs Trivy metrics
and Falco logs, which this example does not generate.

## Checks and cleanup

With Python 3 and Docker Compose 2.24.4 or newer:

```bash
python3 scripts/check-service-examples.py --smoke host-metrics
```

The check uses a temporary project and random loopback ports. It checks every
dashboard query against collected metrics, reads the provisioned dashboard
through Grafana, and confirms Prometheus records a failed scrape after the
exporter stops. The temporary project's data is removed afterward.

Stop your interactive example while retaining its data:

```bash
docker compose -p host-metrics-example -f monitoring/host-metrics/compose.yml down
```

Add `--volumes` to discard that example's metrics and Grafana data. To update,
change the reviewed image digest, back up persistent data, recreate the stack,
and check targets and dashboard queries again.
