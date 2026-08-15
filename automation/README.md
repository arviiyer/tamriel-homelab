# Automation Evidence

This directory will contain selected, sanitized automation that demonstrates a
specific engineering claim and runs without production access.

Planned components:

```text
ansible/       host hardening and controlled patching examples
ci/            exact-revision validation and restricted delivery examples
falco/         runtime-sensor deployment and narrow tuning examples
monitoring/    Prometheus rules and Grafana provisioning
trivy/         vulnerability scan and delta-processing pipeline
```

Available now:

- [Trivy actionable scan pipeline](trivy/README.md), including strict scan
  completion, finding deltas, health metrics, alert rules, synthetic fixtures,
  and integration tests.
- [Ansible host hardening and controlled patching](ansible/README.md), including
  rollback-protected key-only SSH with per-user effective validation, automatic
  security updates without unattended reboot, and serial fail-stop full
  upgrades.
- [Falco runtime detection](falco/README.md), including a modern eBPF deployment
  transaction, narrow synthetic tuning examples, structured event routing, and
  offline policy tests.
- [Security observability dashboard](monitoring/README.md), including
  file-owned Grafana provisioning, current Trivy and Falco query references,
  structural tests, and a container-backed loading check.

Artifacts are re-created here through the process in
[`docs/publication-policy.md`](../docs/publication-policy.md). Production
directories and Git histories are never copied wholesale.
