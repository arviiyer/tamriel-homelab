# Host logs in Loki

[Home](../../README.md) · [Monitoring](../README.md)

Host journals help explain what happened around a failed scrape or application
restart. Loki stores the entries and Grafana searches them by host and unit.

The lab's active hosts still use Promtail. It reached end of life in March 2026,
so this new-install walkthrough uses Grafana Alloy. Migrating the existing hosts
is on the [roadmap](../../ROADMAP.md).

## Start Loki

Requirements: a Linux Docker host with Compose, curl, and local storage. Download
[compose.yml](compose.yml) and [loki.yml](loki.yml) into a new directory outside
this checkout:

```bash
mkdir -p "$HOME/homelab-examples"
mkdir "$HOME/homelab-examples/logs"
cd "$HOME/homelab-examples/logs"
curl -fLO https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/monitoring/logs/compose.yml
curl -fLO https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/monitoring/logs/loki.yml
docker compose config --quiet
docker compose run --rm --no-deps loki -config.file=/etc/loki/config.yml -verify-config=true
docker compose up -d
curl -f http://127.0.0.1:3100/ready
```

Allow a short startup period before `/ready` returns `ready`. Logs stay in the
`loki-data` volume, with seven-day retention and background deletion. Loki has
no authentication in this example and initially listens only on localhost.

## Send the host journal

Install Alloy from Grafana's
[Linux package instructions](https://grafana.com/docs/alloy/latest/set-up/install/linux/).
Download [config.alloy](config.alloy) and install it as `/etc/alloy/config.alloy`:

```bash
curl -fLO https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/monitoring/logs/config.alloy
sudo install -m 0644 config.alloy /etc/alloy/config.alloy
sudo usermod -aG systemd-journal alloy
sudo alloy validate /etc/alloy/config.alloy
sudo systemctl enable --now alloy
sudo systemctl restart alloy
logger -t homelab-check 'Example journal entry for Loki'
journalctl -u alloy -n 30 --no-pager
```

The configuration reads the local journal, retaining `host`, `job`, and `unit`
labels. It writes to Loki on this same host. For other hosts, change the write
URL to the monitoring server's private address, bind Loki's port to that private
interface, and restrict container ingress to the log senders and Grafana. Across
untrusted networks, use an authenticated TLS proxy. Avoid publishing raw Loki
ports to the internet.

## Search in Grafana

With Grafana login enabled as described in the
[metrics guide](../host-metrics/README.md#configure-grafana-login), add a **Loki** datasource.
Use a URL reachable from Grafana's container. A host service's `127.0.0.1` is not
the container's localhost: use the monitoring host's allowed private address,
or join the two containers to a dedicated network and use `http://loki:3100`.

Use **Save & test**, open **Explore**, select Loki, and search:

```logql
{job="journal"} |= "Example journal entry for Loki"
```

Narrow by `host`, then by `unit`, when investigating a particular service:

```logql
{job="journal", host="apps-01", unit="docker.service"}
```

This collects service journal entries. Application stdout using Docker's
`json-file` driver needs its own collection source; it does not automatically
appear in the Docker daemon's journal. Falco events have their own
[Falcosidekick path](../../automation/falco/event-flow.md).

## Maintenance

Keep the Alloy configuration and state directory, Loki configuration, and any
logs you need within your private backup policy. To copy Loki's filesystem store,
stop Loki first. Update the selected image/version, validate configuration, and
repeat the generated journal-entry check after restarting.

| Symptom | First thing to check |
|---|---|
| Journal readable as root but absent in Loki | Alloy's `systemd-journal` group and service restart |
| Loki returns connection refused | Binding, container state, and sender's route |
| Grafana datasource fails | Address reachable from the Grafana container, not your browser |
| Old entries missing | Journal age, Alloy's `max_age`, Grafana time range, and Loki retention |
| Wrong host after cloning a VM | Hostname and Alloy state from the template |

[Alloy journal source](https://grafana.com/docs/alloy/latest/reference/components/loki/loki.source.journal/) ·
[Promtail migration](https://grafana.com/docs/loki/latest/setup/migrate/migrate-to-alloy/)

## Checks

From the repository root, with Python 3, Docker, and Compose 2.24.4 or newer:

```bash
python3 scripts/check-service-examples.py --smoke logs
python3 scripts/check-stack-examples.py --smoke alloy
```

These check Loki ingestion, queries, persistence across a restart, and Alloy's
configuration syntax. Use the `logger` step above to check the host journal path.
