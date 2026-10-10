# Falco runtime detection

[Home](../../README.md) · [Security](../../security/README.md) ·
[Automation](../README.md)

An Ansible role for Falco's modern eBPF engine, two rule-tuning examples,
and Falcosidekick event routing.

## Setup

Requirements: Python dependencies from [requirements.txt](requirements.txt) (including
`ansible-core` 2.21.3), a Debian-family guest, kernel 5.8+ with BPF JIT enabled,
verified SSH host keys, and a reachable Falcosidekick endpoint restricted to your
sensors. The example inventory targets only `falco_sensors` and uses documentation
addresses.

On the control machine, copy the example into a private working directory.
Debian controllers also need `python3-venv`. From the repository root:

```bash
mkdir -p "$HOME/homelab-examples"
mkdir "$HOME/homelab-examples/falco"
cp -R automation/falco/roles automation/falco/playbooks \
  automation/falco/ansible.cfg automation/falco/inventory.example.yml \
  automation/falco/requirements.txt "$HOME/homelab-examples/falco/"
cd "$HOME/homelab-examples/falco"
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
cp inventory.example.yml inventory.yml
```

Set your sensor addresses and `falco_sidekick_url` in `inventory.yml`. Start with
one disposable Debian VM, with working SSH and sudo. The
[Ansible guide](../ansible/README.md#run) covers those connection checks.

## Start the event receiver

On the receiver's Docker host, put the linked
[Compose file](falcosidekick/compose.yml) and
[environment template](falcosidekick/environment.example) in a new working
directory. Copy the template to `.env` and set the host's private bind address,
Loki URL, and Alertmanager URL. These must be reachable from the container.

```bash
docker compose config --quiet
docker compose up -d
docker compose logs --tail=30 falcosidekick
```

Falcosidekick 2.34.1 is digest-pinned, non-root, and read-only, with capabilities
dropped and `no-new-privileges`. See the [event routing](event-flow.md) for Loki
and Alertmanager settings.

The example receiver uses plain HTTP on a documentation address. An adapted
deployment needs a private address and port 2801 restricted to approved sensors;
use an authenticated TLS proxy if the network cannot provide that protection.
Host firewall configuration is environment-specific and is not included here.

Send the [warning fixture](tests/fixtures/falco-event.json) to the receiver,
replacing the URL with your private endpoint. Download the fixture as
`falco-event.json` first. Set its timestamp to now so Loki accepts it:

```bash
python3 - <<'PY' | curl --fail --json @- http://security-01.example.com:2801/
import datetime
import json
from pathlib import Path
event = json.loads(Path("falco-event.json").read_text())
event["time"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
print(json.dumps(event))
PY
```

Confirm its rule name appears in Loki and Alertmanager, then repeat with the
[notice fixture](tests/fixtures/falco-notice-event.json). Notice should reach
Loki without creating a warning notification. This tests receiver routing with
generated events.

## Deploy a sensor

From the copied Falco directory on your control machine:

```bash
ansible-playbook -i inventory.yml playbooks/falco.yml --limit apps-01 -K
```

`-K` prompts for sudo; omit it if that account has passwordless sudo. On the
sensor, check `systemctl status falco-modern-bpf`,
`curl --fail http://127.0.0.1:8765/healthz`, and
`journalctl -u falco-modern-bpf -n 30 --no-pager`.

For an end-to-end check on that disposable host, open a shell in a test container
with a TTY, such as `docker run --rm -it debian:stable-slim sh`, then exit. The
upstream **Terminal shell in container** rule should appear in local syslog and
Loki. Its notice priority does not reach the warning-only Alertmanager output.
Check the rule's priority and exceptions if it is absent, then check receiver
reachability before adding more sensors.

Keep the inventory, managed configuration, and local rule choices in your private
configuration repository. Before a package update, keep a VM backup and repeat
the health and event checks on one host. Configuration rollback below does not
downgrade the Falco package.

## Tests

From the repository root:

```bash
python3 -m unittest discover -s automation/falco/tests -p 'test_*.py' -v
(cd automation/falco && ansible-playbook --syntax-check playbooks/falco.yml)
```

With Docker, check the rendered configuration and rules using CI's pinned image:

```bash
output="$(mktemp)"
python3 automation/falco/tests/render_config.py "$output"
docker run --rm \
  -v "$output:/tmp/falco.yaml:ro" \
  -v "$PWD/automation/falco/roles/falco/files/falco_rules.local.yaml:/etc/falco/falco_rules.local.yaml:ro" \
  --entrypoint falco \
  falcosecurity/falco@sha256:d0cfe422d6ac0e0f20857798f46c7d7273210e1b064b22821e4e6e7f843cde6b \
  --dry-run -c /tmp/falco.yaml \
  -r /etc/falco/falco_rules.yaml \
  -r /etc/falco/falco_rules.local.yaml
rm -f "$output"
```

## Deployment and rollback

The role checks kernel/BPF prerequisites and installs an exact Falco package
version with a checksum-pinned signing key. It disables the unused kernel-module
service and automatic Falcoctl rule updates.

For each host, it:

1. Saves local rules under a filename based on their SHA-256; existing rule files
   are never edited.
2. Renders a candidate configuration and validates it with both rulesets using
   `falco --dry-run`.
3. Saves the active managed configuration, installs the candidate, and starts or
   restarts `falco-modern-bpf.service`.
4. Checks the local health endpoint repeatedly; if startup fails, restores the
   previous managed configuration and restarts Falco.

The rollout changes one host at a time and stops at the first failure. Rollback
covers the managed configuration, not the package, bundled rules, or engine/service
selection. Failed upgrades or engine changes need manual review.

## Tuning and event delivery

Each [local exception](roles/falco/files/falco_rules.local.yaml) extends one
upstream rule and matches an exact process and workload. Tests reject wildcards,
broad exceptions, and disabled upstream rules. The examples contain only two
exceptions; the lab's full set stays private.

The health endpoint checks that Falco is running. Check event arrival in Loki
separately. [Disposable-host deployment tests](../../ROADMAP.md) are still planned.
