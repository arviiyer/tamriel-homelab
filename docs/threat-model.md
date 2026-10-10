# Security notes

[Home](../README.md) · [Security](../security/README.md)

The lab holds personal data, application databases, source code, credentials,
backups, and security logs. Protecting the hypervisors, network controls, identity
provider, and administrative devices is especially important because compromise
there can affect many services.

## Main threats

| Threat | Response |
|---|---|
| Vulnerable or outdated software | Scan images/configuration, patch hosts, open update PRs, and alert on available fixes or stale scans |
| Leaked credentials | Keep runtime secrets outside Git, scan for secrets, restrict deployment keys, and review files before sharing |
| Compromised client | Separate [network zones](network-and-identity.md), block connections by default, keep admin access private, and require application logins |
| Compromised workload | Separate workloads, limit mounts and network access, harden containers, and collect runtime events/logs |
| Compromised CI job | Run checks without deployment keys; deploy on request with commit, allowed-change, and health checks on the target |
| Data loss or bad upgrade | VM-local databases, snapshots, selected off-host copies, isolated restore, and rollback |
| Missing network storage | Check the expected read-write mount and dataset before service startup |
| Silent monitoring failure | Track attempts, complete-scan timestamps, and target health separately from findings |

The [delivery](case-studies/fail-closed-infrastructure-delivery.md) and
[recovery](case-studies/recovery-and-storage-dependencies.md) notes show
how failures are handled in the deployment and restore examples.

## Assumptions and remaining risk

- Admin devices and accounts are trusted and need their own protection.
- Physical security is residential; persistent physical access is outside scope.
- Private access reduces exposure but still requires patching and authentication.
- Allowed network flows can be abused by a compromised service.
- Hardware, operator time, and detection coverage are limited. Some changes are
  manual, and only selected data has off-host protection.

Public malware-analysis services and third-party sample submission are outside
this repository's scope.
