# Host metrics

[Home](../../README.md) · [Monitoring](../README.md)

I use Node Exporter on the hosts and VMs, Prometheus to collect their metrics,
and Grafana to view them. This guide starts with the monitoring host, then adds
other machines and Discord alerts.

- [Install](#install)
- [Add other hosts](#add-other-hosts)
- [Alerts and Discord](#alerts-and-discord)
- [Updates and backups](#updates-and-backups)
- [Try it locally](#try-it-locally)

## Install

Requirements: a Linux Docker Engine host, Docker Compose, Bash, curl, OpenSSL,
and free local ports 3000 and 9090 (plus 9093 for alerts). Node Exporter mounts
the host's root filesystem, procfs, and sysfs read-only. Docker Desktop reports
its Linux VM rather than the desktop OS.

Download the files on your monitoring host, preserving the provisioning paths:

```bash
mkdir -p "$HOME/homelab-examples"
mkdir "$HOME/homelab-examples/host-metrics"
cd "$HOME/homelab-examples/host-metrics"
(
  set -eu
  mkdir -p provisioning/datasources provisioning/dashboards
  for file in compose.yml prometheus.yml dashboard.json \
    provisioning/datasources/prometheus.yml provisioning/dashboards/hosts.yml; do
    curl --fail --location --output "$file" \
      "https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/monitoring/host-metrics/$file"
  done
)
```

### Configure Grafana login

The supplied file also supports a [local trial](#try-it-locally) without an
account. For this installation, replace these entries under Grafana's
`environment` before its first start:

```yaml
      GF_AUTH_ANONYMOUS_ENABLED: "false"
      GF_AUTH_DISABLE_LOGIN_FORM: "false"
      GF_SECURITY_DISABLE_INITIAL_ADMIN_CREATION: "false"
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_ADMIN_PASSWORD:?Set an initial admin password}
```

Create `.env` once and keep the generated password in your password manager:

```bash
(
  set -euC
  umask 077
  printf 'GRAFANA_ADMIN_PASSWORD=%s\n' "$(openssl rand -hex 24)" > .env
)
```

In `prometheus.yml`, change `host: example-host` to a stable name for this
machine, such as `observability-01`. In `compose.yml`, change
`--storage.tsdb.retention.time=1d` to the history you want to retain; I use `15d`
in the lab. Watch disk use as you add targets.

```bash
docker compose config --quiet
docker compose up -d
docker compose ps
```

On a remote VM, run this from your workstation:

```bash
ssh -N -L 3000:127.0.0.1:3000 -L 9090:127.0.0.1:9090 \
  -L 9093:127.0.0.1:9093 operator@observability-01
```

Open [Grafana](http://127.0.0.1:3000/d/host-metrics-example), sign in as `admin`
with the password in `.env`, and open [Prometheus targets](http://127.0.0.1:9090/targets).
Allow a few scrapes for the CPU rate. The included dashboard shows reachability,
available memory, root-filesystem space, and CPU use. Grafana loads it from
[dashboard.json](dashboard.json); edit that file to change these panels.

Use the [private HTTPS guide](../../networking/private-access/README.md#use-it-with-an-application)
for daily browser access. Existing Grafana accounts retain their saved password;
the initial-password setting only applies to a fresh database.

## Add other hosts

On each Debian host, install the exporter and allow TCP 9100 from the monitoring
host through its firewall:

```bash
sudo apt install prometheus-node-exporter
sudo systemctl enable --now prometheus-node-exporter
curl -fsS http://127.0.0.1:9100/metrics | head
```

Append another entry to `static_configs` under the existing `node` job in
`prometheus.yml`. Replace the documentation address with that host's address:

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

Check **Status → Target health**, then query `up{job="node"}`. Each target should
report `1`. The supplied dashboard uses the `host` labels. For the dashboard shown
on the [monitoring page](../README.md#grafana), use **Dashboards → New → Import**
and import [Node Exporter Full, 1860](https://grafana.com/grafana/dashboards/1860-node-exporter-full/),
selecting the provisioned Prometheus datasource. It supplies the wider network,
disk, and system panels for host-installed exporters. The bundled container
enables only CPU, memory, filesystem, and host-information collectors.

The [networking page](../../networking/README.md#caddy-and-authentik) describes
Grafana's Authentik integration in the lab. The separate
[security dashboard](../../automation/monitoring/README.md) needs Trivy metrics
and Falco logs, which this example does not generate.

## Alerts and Discord

The optional [override](alerts.override.yml) adds Alertmanager and
[host alerts](hosts.rules.yml). In the same working directory:

```bash
(
  set -eu
  for file in alerts.override.yml alerts.prometheus.yml hosts.rules.yml alertmanager.yml; do
    curl --fail --location --output "$file" \
      "https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/monitoring/host-metrics/$file"
  done
)
```

Carry your host labels and extra scrape targets into `alerts.prometheus.yml`;
the override selects that file instead of `prometheus.yml`.

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

Keep both `-f` arguments on later Compose commands.

## Updates and backups

Back up configuration, Grafana data, and Alertmanager data (including silences);
choose whether the metrics history also needs a backup. For consistent volume
copies, stop the relevant service first. Follow the
[volume backup steps](../../apps/utilities/README.md#cold-copies-updates-and-cleanup)
using both Compose files when alerts are enabled. Keep `.env` and the Discord
webhook file with the private backup.

To update, change the reviewed image digest, pull, and recreate the stack:

```bash
docker compose -f compose.yml -f alerts.override.yml pull
docker compose -f compose.yml -f alerts.override.yml up -d
```

Without the alerts extension, use `docker compose pull` and `docker compose up -d`.

Check scrape targets, dashboard queries, and a test notification afterward.
Restore Grafana into a separate project and port before replacing its working
data; keep notifications off in an Alertmanager test copy.

| Symptom | First thing to check |
|---|---|
| Target is down | Exporter listener, target address, and firewall from the monitoring host |
| Target is up but a panel is empty | Selected host, datasource, enabled collectors, and time range |
| An added host disappears after enabling alerts | Targets in `alerts.prometheus.yml` |
| Alert fires but Discord stays quiet | Receiver name, webhook mount/read permissions, and Alertmanager logs |

## Try it locally

To view just the included dashboard, run the unmodified files from the repository
root:

```bash
docker compose -p host-metrics-example -f monitoring/host-metrics/compose.yml up -d
```

This starts an anonymous, read-only Grafana viewer on localhost with no admin
account. Open <http://127.0.0.1:3000/d/host-metrics-example>. Its data stays in
separate project volumes; use the installation steps above for your own stack.

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

For the installed stack with alerts, run
`docker compose -f compose.yml -f alerts.override.yml down` in its working
directory instead. Add `--volumes` only to discard the selected stack's saved data.
