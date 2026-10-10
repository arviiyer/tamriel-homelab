# CrowdSec on OPNsense

[Home](../../README.md) · [Security](../README.md) · [Networking](../../networking/README.md)

CrowdSec reads the firewall's logs and combines local detections with community
decisions. Its pf bouncer applies IP blocks at OPNsense. Prometheus scrapes its
metrics alongside the firewall's Node Exporter metrics.

## Install the plugin

Requirements: an updated OPNsense installation, access to its plugin repository,
and an existing private administration path. Save an OPNsense configuration
backup before changing plugins.

1. Open **System → Firmware → Plugins**, enable **Show community plugins**, and
   install `os-crowdsec`.
2. Refresh the page and open **Services → CrowdSec → Overview**. The plugin
   installs the engine, local API, firewall bouncer, and OPNsense log collection.
3. Check that the engine and bouncer are running through the plugin's controls.
   Let the plugin manage service startup and configuration.
4. Inspect the installed collections and acquisition metrics. The OPNsense
   collection should receive firewall logs. A running process alone does not
   establish that logs are being parsed.

From the OPNsense shell, these are read-only checks:

```bash
cscli collections list
cscli metrics
cscli bouncers list
cscli decisions list
pfctl -t crowdsec_blocklists -T show | wc -l
```

The bouncer should have recent API pulls, and the pf table should reflect active
ban decisions. My installed plugin uses `crowdsec_blocklists` with underscores.
Use the plugin documentation to confirm the table name if your version differs.

Console enrollment is optional. If using it, create an enrollment command in the
CrowdSec console, run it on this firewall, and accept the engine there. Keep the
enrollment token and generated API credentials private.

## Add metrics

CrowdSec initially listens for metrics on localhost. The
[local override](config.yaml.local) enables port 6060 on a chosen private
address. Replace `192.0.2.1` with the firewall's intended monitoring address and
merge it into `/usr/local/etc/crowdsec/config.yaml.local`. Preserve any other
local settings already in that file.

Validate with `crowdsec -c /usr/local/etc/crowdsec/config.yaml -t`, then restart
the engine using the plugin UI. Add a firewall rule allowing only the monitoring
host to reach that address on TCP 6060. From the monitoring host:

```bash
curl --fail http://192.0.2.1:6060/metrics
```

Replace the documentation address. Add the job from
[prometheus.yml](prometheus.yml) to your existing `scrape_configs`, rather than
creating a second top-level key. Validate Prometheus and restart/reload it using
the [metrics guide](../../monitoring/host-metrics/README.md#add-other-hosts).

Query `up{job="crowdsec"}` and `sum(cs_active_decisions{job="crowdsec",action="ban"})`.
CrowdSec 1.7+ uses the `cs_` metric prefix. An empty decisions series can mean
there are no matching decisions; use `up` to check scrape health independently.

## Check a decision reaches pf

On a test firewall, add a short-lived decision for a documentation address:

```bash
cscli decisions add --ip 192.0.2.123 --duration 2m --reason example-check
pfctl -t crowdsec_blocklists -T test 192.0.2.123
cscli decisions delete --ip 192.0.2.123
```

Wait for the bouncer's next pull before the pf check, then check again after
deletion. This tests decision delivery to the firewall table. Test actual packet
blocking from a separate disposable client whose address you can safely block;
keep the administration client separate from that test. Local detection also
depends on the correct log acquisition and installed scenarios.

## Maintenance

Update the plugin through OPNsense's firmware workflow. Retain the private
configuration backup and local override, then repeat the engine, bouncer, log,
and scrape checks after updating. OPNsense XML backups and CrowdSec credential
files stay outside this repository.

| Symptom | Check |
|---|---|
| Engine up but no parsed events | Acquisition metrics and the plugin's OPNsense collection |
| Decisions exist but pf table is empty | Bouncer status, credentials, and recent API pulls |
| Prometheus cannot scrape | Metrics bind address, local override, and firewall source rule |
| No community decisions | Central API connectivity and blocklist/enrollment settings |

[OPNsense installation](https://docs.crowdsec.net/u/getting_started/installation/opnsense/) ·
[Local overrides](https://docs.crowdsec.net/docs/configuration/crowdsec_configuration/#overriding-values)
