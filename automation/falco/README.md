# Falco Runtime Detection

This public evidence slice demonstrates host-level runtime detection for
container workloads using Falco's modern eBPF engine and Falcosidekick event
routing. It is a purpose-written example, not the production role, inventory,
or complete tuning set.

Status: **Drafted static evidence**. Configuration, rules, deployment policy,
and routing structure are validated from a clean checkout. A disposable-host
transaction and reviewed operated-environment evidence are still pending.

## Security Question

How can unexpected workload behavior be detected across service VMs without
turning normal container activity into an unreviewable stream of alerts?

## Design

- Install an exact Falco package version from a checksum-pinned signing key.
- Use the CO-RE modern eBPF engine without kernel-module compilation.
- Enrich syscall events with container identity.
- Require JSON output before forwarding events to Falcosidekick.
- Preserve syslog locally while routing structured events centrally.
- Send `notice` and above to Loki, but only `warning` and above to
  Alertmanager.
- Validate candidate configuration and rules together before activation.
- Activate an immutable rules release through one managed configuration file.
- Restore the previous managed configuration if Falco does not remain healthy.
- Change one host at a time and stop the rollout on the first failure.
- Reject broad tuning examples through offline policy tests.

See the [runtime event flow](event-flow.md) for trust boundaries and failure
behavior.

## Layout

```text
automation/falco/
|-- ansible.cfg
|-- inventory.example.yml
|-- playbooks/falco.yml
|-- roles/falco/
|   |-- defaults/main.yml
|   |-- files/falco_rules.local.yaml
|   |-- tasks/main.yml
|   `-- templates/falco.yaml.j2
|-- falcosidekick/
|   |-- compose.yml
|   `-- environment.example
|-- tests/
|   |-- fixtures/falco-event.json
|   |-- fixtures/falco-notice-event.json
|   |-- render_config.py
|   `-- test_policy.py
`-- event-flow.md
```

## Deployment Transaction

The Ansible role checks the target's kernel and BPF JIT state before installing
Falco. It disables the unused kernel-module service and the automatic Falcoctl
artifact follower so rules cannot change outside the reviewed deployment path.

The role then:

1. Stores the proposed local rules under a SHA-256-derived immutable filename.
2. Renders a candidate configuration that references that rules release.
3. Runs `falco --dry-run` against the packaged upstream rules, candidate
   configuration, and immutable local rules.
4. Preserves the active managed configuration.
5. Installs the validated configuration and starts or restarts
   `falco-modern-bpf.service`.
6. Requires the loopback process-health endpoint to remain reachable across a
   stability interval.
7. Restores the previous managed configuration and restarts Falco if activation
   fails.

The health gate proves process and webserver liveness. It does not prove that
the modern eBPF inspector is processing kernel events; that requires the pending
disposable-host exercise.

The package version, packaged upstream rules, and service selection are outside
the managed-file rollback boundary. A failed package upgrade or engine migration
therefore stops the play for operator review rather than claiming full rollback.

The example inventory targets only `falco_sensors`. Hypervisors, edge systems,
and other roles require a separate compatibility and threat-model decision.

## Tuning Standard

The local rules file contains synthetic examples only. Every exception:

- appends to a specific upstream rule;
- combines process and workload context;
- uses exact comparisons;
- contains no wildcard; and
- retains the upstream rule condition and enabled state.

The complete production-derived suppression set is intentionally not public.
A new exception should begin with a reviewed event, be narrowed against fields
that remain stable for the workload, pass Falco validation, and then be observed
for unintended coverage.

## Falcosidekick

The Compose example uses Falcosidekick 2.34.1 at an immutable multi-architecture
digest. It runs as the image's non-root user with a read-only root filesystem,
all Linux capabilities dropped, and `no-new-privileges` enabled.

Render the synthetic configuration:

```bash
docker compose \
  --env-file automation/falco/falcosidekick/environment.example \
  -f automation/falco/falcosidekick/compose.yml \
  config
```

The example exposes the receiver on an RFC 5737 documentation address. A real
deployment must bind a private address and restrict port 2801 to approved Falco
sensors. Falcosidekick's native receiver is plain HTTP in this example; use a
protected network or a TLS-authenticated proxy when that trust assumption does
not hold.

## Run

Requirements:

- `ansible-core` 2.21.3;
- a Debian-family Linux guest;
- kernel 5.8 or newer with the BPF JIT enabled;
- a reachable, network-restricted Falcosidekick endpoint; and
- verified SSH host keys and a private inventory outside this repository.

The documentation-only inventory is intentionally unreachable. After replacing
it with a private inventory, run from `automation/falco/`:

```bash
ansible-playbook playbooks/falco.yml
```

## Validate

Run offline policy and rendering tests:

```bash
python3 -m unittest discover \
  -s automation/falco/tests \
  -p 'test_*.py' \
  -v
```

Check Ansible syntax:

```bash
cd automation/falco
ansible-playbook --syntax-check playbooks/falco.yml
```

Validate the rendered configuration and both rulesets with the same immutable
Falco image used by CI:

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

## Production Differences

The private environment has a different inventory, internal addresses,
notification destinations, deployment history, and a larger tuning set based
on observed workloads. None of those values or raw events are included here.

## Limitations

- Offline validation proves schema, rule compatibility, and policy invariants;
  it does not prove that a target kernel permits the modern eBPF probe.
- The managed-file rollback and service-health path require a disposable-host
  failure exercise before this can be described as executable or operated
  evidence.
- Package downgrade and restoration of a prior Falco engine are intentionally
  outside the automated rollback boundary.
- The public example does not include the host firewall rule that restricts the
  Falcosidekick receiver because network policy is environment-specific.
- Falcosidekick does not provide durable queuing. Downstream delivery health
  needs separate monitoring.
- No reviewed runtime alert or dashboard screenshot has been published yet.
