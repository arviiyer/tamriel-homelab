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

For a persistent setup, copy this directory's example files into a directory such
as `/srv/host-metrics` on your monitoring VM. Keep its `provisioning/` directory
structure. Use that working directory for the commands below.

On each Debian host, install the exporter and allow TCP 9100 from the monitoring
host through its firewall:

```bash
sudo apt install prometheus-node-exporter
sudo systemctl enable --now prometheus-node-exporter
curl -fsS http://127.0.0.1:9100/metrics | head
```

Add a target under the `node` job in `prometheus.yml`, replacing the documentation
address with that host's address:

```yaml
      - targets: [192.0.2.83:9100]
        labels:
          host: apps-01
```

Give each host its own stable `host` label. Validate and recreate Prometheus:

```bash
docker compose run --rm --no-deps --entrypoint promtool prometheus \
  check config /etc/prometheus/prometheus.yml
docker compose up -d --force-recreate prometheus
```

Check **Status → Target health**, then query `up{job="node"}`. The supplied
dashboard uses the `host` labels. For a wider set of panels, enable Grafana login
as below and import [Node Exporter Full, 1860](https://grafana.com/grafana/dashboards/1860-node-exporter-full/),
selecting the Prometheus datasource.

Before extending Grafana access, edit its environment in `compose.yml`: set
`GF_AUTH_ANONYMOUS_ENABLED=false`, `GF_AUTH_DISABLE_LOGIN_FORM=false`, and
`GF_SECURITY_DISABLE_INITIAL_ADMIN_CREATION=false`. Add
`GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:?Set an initial admin password}`
and create a private `.env` with the generated password. On a fresh volume,
recreate Grafana, sign in as `admin`, and verify the dashboard. Existing Grafana
accounts retain their saved password. Configure the
[private HTTPS route](../../networking/private-access/README.md) before binding
the port to a private interface reachable by another proxy host.

The [networking page](../../networking/README.md#caddy-and-authentik) describes
Grafana's Authentik integration in the lab. The separate
[security dashboard](../../automation/monitoring/README.md) needs Trivy metrics
and Falco logs, which this example does not generate.

## Alerts and Discord

The optional [override](alerts.override.yml) adds Alertmanager and
[host alerts](hosts.rules.yml). Download it together with `alerts.prometheus.yml`,
`hosts.rules.yml`, and `alertmanager.yml` into the same working directory. Carry
your extra scrape targets into `alerts.prometheus.yml`; the override selects
that file instead of `prometheus.yml`.

```bash
docker compose -f compose.yml -f alerts.override.yml config --quiet
docker compose -f compose.yml -f alerts.override.yml up -d
```

Open <http://127.0.0.1:9093>. Initially, alerts remain visible locally with no
external notification receiver. To deliver them to Discord, create a webhook
in the intended channel and save its URL in a private file outside Git:

```bash
read -r -s -p 'Discord webhook URL: ' DISCORD_WEBHOOK
printf '\n'
umask 077
printf '%s\n' "$DISCORD_WEBHOOK" > discord-webhook
unset DISCORD_WEBHOOK
sudo chown 65534:65534 discord-webhook
sudo chmod 400 discord-webhook
```

Add this mount to Alertmanager in `alerts.override.yml`:

```yaml
      - ./discord-webhook:/run/discord-webhook:ro
```

Replace the receiver in `alertmanager.yml` and set the route's `receiver` to
`discord`:

```yaml
receivers:
  - name: discord
    discord_configs:
      - webhook_url_file: /run/discord-webhook
        send_resolved: true
```

Validate the two configurations, then recreate the stack:

```bash
docker compose -f compose.yml -f alerts.override.yml run --rm --no-deps \
  --entrypoint promtool prometheus check config /etc/prometheus/prometheus.yml
docker compose -f compose.yml -f alerts.override.yml run --rm --no-deps \
  --entrypoint amtool alertmanager check-config /etc/alertmanager/alertmanager.yml
docker compose -f compose.yml -f alerts.override.yml up -d --force-recreate
```

To test delivery without stopping a real host, temporarily add an unreachable
target `127.0.0.1:1` to the `node` job with `host: alert-test`. Recreate Prometheus,
wait for the two-minute alert delay and grouping interval, and check the firing
message. Change that test target to `node-exporter:9100`, recreate Prometheus,
and check the recovery message. Then remove the test target. This exercises
scraping, rule evaluation, routing, and external delivery together.

Keep both `-f` arguments on later Compose commands. Back up configuration,
Grafana data, and Alertmanager data (including silences); choose whether the
metrics history also needs a backup. For consistent volume copies, stop the
relevant service first. Review retention and free space before increasing the
one-day example retention in `compose.yml`.

## Checks and cleanup

From the repository root, with Python 3 and Docker Compose 2.24.4 or newer:

```bash
python3 scripts/check-service-examples.py --smoke host-metrics
python3 scripts/check-stack-examples.py --smoke alerts
```

The check uses a temporary project and random loopback ports. It checks every
dashboard query against collected metrics, reads the provisioned dashboard
through Grafana, and confirms Prometheus records a failed scrape after the
exporter stops. The temporary project's data is removed afterward.
The alert check also waits for a host-down rule and its recovery notification
to reach a local Discord-compatible receiver; it takes a few minutes.

Stop the initial local example while retaining its data:

```bash
docker compose -p host-metrics-example -f monitoring/host-metrics/compose.yml down
```

For the copied stack with alerts, run
`docker compose -f compose.yml -f alerts.override.yml down` in its working
directory instead. Add `--volumes` to discard the selected stack's saved data. To update,
change the reviewed image digest, back up persistent data, recreate the stack,
and check targets and dashboard queries again.
