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

Copy the role and playbook into your own Ansible project, supply an inventory,
and run from its Falco directory:

```bash
ansible-playbook -i /path/to/private/inventory.yml playbooks/falco.yml
```

With Docker Compose installed, check the Falcosidekick configuration from the
repository root:

```bash
docker compose \
  --env-file automation/falco/falcosidekick/environment.example \
  -f automation/falco/falcosidekick/compose.yml config
```

Falcosidekick 2.34.1 is digest-pinned, non-root, and read-only, with capabilities
dropped and `no-new-privileges`. See the [event routing](event-flow.md) for Loki
and Alertmanager settings.

The example receiver uses plain HTTP on a documentation address. An adapted
deployment needs a private address and port 2801 restricted to approved sensors;
use an authenticated TLS proxy if the network cannot provide that protection.
Host firewall configuration is environment-specific and is not included here.

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
