# Trivy scans

[Home](../../README.md) · [Security](../../security/README.md) ·
[Automation](../README.md)

Scans repository files and images listed in Compose files, compares results with
the last complete scan, and exports Prometheus metrics.

[How the alerting works](../../docs/case-studies/actionable-vulnerability-management.md)

## Setup

Requirements: Bash 5+, Git, Python 3.11+, PyYAML 6.0.3, Trivy, curl, `flock`,
and `sha256sum`. Install Trivy using its
[package instructions](https://trivy.dev/docs/latest/getting-started/installation/).
The repository's CLI compatibility checks use Trivy 0.73.

On Debian, install `python3-venv` for the virtual environment. From the repository
root, copy the scanner into a private working directory:

```bash
mkdir -p "$HOME/homelab-examples"
mkdir "$HOME/homelab-examples/trivy"
cp automation/trivy/{scan.sh,delta.py,extract_images.py,requirements.txt,repositories.example.tsv,prometheus-rules.yml} \
  "$HOME/homelab-examples/trivy/"
cd "$HOME/homelab-examples/trivy"
chmod 700 .
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
cp repositories.example.tsv repositories.tsv
```

Edit `repositories.tsv` to select your repositories and revisions. The private
working directory also holds the scan baseline and any finding metadata.

Each non-comment line contains three tab-separated fields:

```text
alias    clone URL    revision
```

Aliases use lowercase letters, digits, underscores, or hyphens. Remote URLs must
use HTTPS without userinfo, query strings, or fragments. Use an external Git
credential helper for authentication. Absolute local paths work for offline use.

| Variable | Purpose | Default |
|---|---|---|
| `REPOSITORIES_FILE` | Repository configuration | `repositories.tsv` beside the script |
| `BASELINE_DIR` | Last complete JSON baseline | `var/baseline` beside the script |
| `PUSHGATEWAY_URL` | Optional Pushgateway URL | Metrics are not pushed |
| `TMPDIR` | Temporary scan storage | `/tmp` |
| `INITIALIZE_BASELINE` | Set to `1` for the first complete scan only | `0` |

## Run

In the copied directory with its virtual environment active, save the first
complete scan as a baseline:

```bash
INITIALIZE_BASELINE=1 bash scan.sh
```

Then run subsequent scans:

```bash
bash scan.sh
```

Use initialization only once. Later runs check that the saved baseline matches
the configured repositories. The first scan records existing vulnerabilities and
configuration issues without alerting on all of them.

Each baseline includes `_delta-report.json` with new/absent vulnerabilities,
metadata changes, new misconfigurations, and the current secret count. Store
baseline files privately: they contain paths and secret-finding metadata.

Check for `scan complete; baseline promoted` and inspect
`var/baseline/_delta-report.json`. The manifest in `_baseline.json` should list
the configured repositories. A nonzero exit leaves the earlier baseline in
place; read the named repository's error before trying again.

## Send metrics and run weekly

Use an existing private [Pushgateway](https://github.com/prometheus/pushgateway),
or install one on the monitoring host using its upstream instructions. Set
`PUSHGATEWAY_URL` to an address reachable from the scanning host and run another
scan. Prometheus needs a scrape job like this, using your actual address:

```yaml
  - job_name: pushgateway
    honor_labels: true
    static_configs:
      - targets: [observability-01.example.com:9091]
```

Copy `prometheus-rules.yml` into Prometheus's mounted configuration directory and
include that container path under `rule_files`. Validate with `promtool check
config`, reload Prometheus, and query `trivy_scan_success` and
`trivy_scan_last_success_timestamp_seconds`. Both the finding and health jobs
must be present. Connect notifications using the
[Alertmanager guide](../../monitoring/host-metrics/README.md#alerts-and-discord).

For a weekly scan, save this as `~/.config/systemd/user/trivy-scan.service`,
creating the directory first. Replace the Pushgateway URL, or omit that line
when keeping results locally:

```ini
[Unit]
Description=Scan homelab repositories and images

[Service]
Type=oneshot
WorkingDirectory=%h/homelab-examples/trivy
Environment=PATH=%h/homelab-examples/trivy/.venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=PUSHGATEWAY_URL=http://observability-01.example.com:9091
UMask=0077
ExecStart=/bin/bash %h/homelab-examples/trivy/scan.sh
```

Save the matching `trivy-scan.timer` beside it:

```ini
[Unit]
Description=Weekly homelab scan

[Timer]
OnCalendar=weekly
Persistent=true
RandomizedDelaySec=30m

[Install]
WantedBy=timers.target
```

Run `systemctl --user daemon-reload`, then `systemctl --user start trivy-scan`.
Read `journalctl --user -u trivy-scan` and confirm a fresh metric before enabling
the timer with `systemctl --user enable --now trivy-scan.timer`. On an unattended
host, `sudo loginctl enable-linger "$USER"` keeps the user manager running after
logout. Check the next run with `systemctl --user list-timers trivy-scan.timer`.
The service uses the same user's Git credential helper; no interactive password
prompt is available to a scheduled scan.

Back up the repository list and complete baseline together between scans. When
updating the scanner or Trivy, stop the timer, keep that backup, run one scan by
hand, and check the report and metrics before restarting the timer.

## Tests

Run from the repository root. Python tests need Git and the dependencies in
[requirements.txt](requirements.txt); they use a fake Trivy binary and temporary repositories.
The remaining checks need ShellCheck and `promtool`:

```bash
python3 -m unittest discover -s automation/trivy/tests -p 'test_*.py' -v
bash -n automation/trivy/scan.sh
shellcheck automation/trivy/scan.sh
promtool check rules automation/trivy/prometheus-rules.yml
```

## How it works

```mermaid
flowchart TB
    scan[Check out commits<br/>Read Compose files and scan]
    scan --> validate{Complete valid results?}
    validate -- No --> health[Publish failure metrics<br/>Keep previous baseline]
    validate -- Yes --> delta[Compare with previous baseline]
    delta --> commit[Save new baseline and send metrics]
    commit -- Success --> baseline[Keep new baseline]
    commit -- Failure --> rollback[Restore previous baseline]
```

Malformed Compose files, unresolved image variables, and failed clones or scans
block the new baseline. Trivy uses `--exit-code 0` so findings alone do not count
as scanner failures. JSON output must pass schema and metadata checks; Trivy 0.73
can omit `Results` when no supported target produces a result.

A lock prevents overlapping runs. The baseline manifest records the repository
set, schema, and file list. Findings and health use separate Pushgateway jobs.
The script keeps the old baseline directory until replacement and metrics
publication succeed, restoring it if either fails.

## Comparing results

| Type | Identity fields |
|---|---|
| Vulnerability | Repository, image reference, target, package, package path, vulnerability ID |
| Misconfiguration | Repository, file path, check ID, resource |
| Secret | Repository, file path, rule ID, start line |

The comparison ignores installed version, severity, and fixed version when
matching findings. Severity increases and newly available fixes are reported
separately. Changing the image tag/digest, target, or package path can produce an
absent/new pair even if the vulnerability remains.
Moving lines in a configuration file does not create a new finding. Secrets are
reported on every complete scan.

## Secret scans

Trivy scans the checked-out tree. Gitleaks handles full Git-history scanning in CI.

## Metrics and alerts

Finding metrics:

```text
trivy_vulnerabilities                 trivy_new_vulnerabilities
trivy_fixed_vulnerabilities           trivy_vulnerability_changes
trivy_misconfigurations               trivy_new_misconfigurations
trivy_secrets                         trivy_scan_last_success_timestamp_seconds
```

Health metrics:

```text
trivy_scan_success                   trivy_scan_attempt_timestamp_seconds
trivy_scan_duration_seconds          trivy_scan_repository_success
```

[Alert rules](prometheus-rules.yml) implement the
[alert policy](../../docs/case-studies/actionable-vulnerability-management.md#what-triggers-an-alert)
and flag failed or stale scans. The example freshness window is eight days.

## Limitations

- Changing the repository set requires archiving the baseline and starting a new
  series. Locally built images without an `image` reference are not scanned.
- Image tags can point to different content between scans. Pin digests to scan
  the same image content.
- Pushgateway and local disk cannot update atomically. The new baseline is saved
  before metrics are sent; a failed send restores the old one. A crash between
  these steps may leave them out of sync and need manual repair.
- Failures before health metrics can be published, such as missing tools or
  storage, rely on stale/missing-health alerts.
