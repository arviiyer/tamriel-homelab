# Architecture

## Design Goal

Tamriel is a self-hosted private-cloud environment for operating personal
services and developing security engineering capabilities. Its architecture is
designed around explicit trust boundaries, observable failure, controlled
change, and recoverable state.

The public model uses role-based aliases and omits production addressing and
identifiers.

## Trust-Boundary and Data-Flow Model

The primary [platform diagram](../README.md#architecture) presents the logical
trust boundaries that connect access, segmented network policy, role-separated
workloads, telemetry, controlled delivery, state ownership, and isolated
recovery. It is intentionally not a physical topology: placement details,
addresses, management routes, and production identities are omitted.

The model distinguishes three decisions that are easy to lose in a conventional
infrastructure diagram:

- untrusted and externally controlled endpoints do not inherit reachability to
  private zones;
- validation makes one exact revision eligible for a separately authorized,
  target-constrained promotion; and
- backup copies flow into an isolated restore identity and stop at a manual
  replacement decision rather than overwriting authoritative state.

## Logical Layers

### Edge and Access

Remote administrative access enters through a private overlay path. Web
applications use a reverse-proxy layer and centralized authentication where the
application supports it. Management interfaces are not intentionally exposed as
public internet services.

### Network Policy

A dedicated gateway separates infrastructure, trusted clients, managed work
devices, untrusted devices, guest clients, media workloads, and sandbox
workloads. Policy is based on required flows rather than broad inter-zone
reachability.

The [network and identity design](network-and-identity.md) documents the public
zone model, access paths, identity boundaries, generic flow policy, and evidence
gaps without reproducing private firewall or identity-provider configuration.

### Compute

Three Proxmox nodes provide the virtualization layer. Workloads are separated by
role so identity, observability, applications, security automation, delivery,
and backup responsibilities do not collapse onto one general-purpose system.

### Application Runtime

Most service workloads use Docker Compose inside role-specific virtual machines.
Configuration is version-controlled privately, while runtime credentials and
persistent application state stay outside source control.

### Data and Storage

Databases remain on VM-local storage to avoid coupling transactional state to
network filesystem availability. Shared storage is reserved for bulk data and
other workloads suited to network-attached storage.

### Telemetry and Detection

Host and application metrics flow to Prometheus. System and application logs
flow to Loki. Grafana provides shared analysis views, while Alertmanager routes
actionable infrastructure and security events. Security automation adds
vulnerability, runtime-detection, firewall, and malware-scanning signals.

The public evidence includes the
[Trivy scan and delta pipeline](../automation/trivy/README.md), the
[Falco runtime-event flow](../automation/falco/event-flow.md), and
[file-provisioned security dashboards](../automation/monitoring/README.md).

### Delivery

Private Forgejo repositories use protected branches and pull-request validation.
The delivery model separates validation from production promotion and uses
restricted target-side controls for the workloads that support automated
deployment. The public
[fail-closed delivery example](../automation/ci/README.md) binds validation and
promotion to one full commit SHA while keeping deployment credentials out of
repository-controlled validation.

### Recovery

VM-level snapshots protect service operating systems and local application
state. Selected high-value data also receives an off-host copy. Recovery is
designed around restoration into an isolated identity before any production
replacement decision.

The public
[recovery example](../automation/recovery/README.md) models VM-local and shared
bulk-data authority separately, validates a bounded isolated synthetic restore,
and provides a static storage-readiness policy. It does not prove private backup
jobs, retention execution, off-host transfer, or operated restore outcomes.

## Architecture Principles

### Private by Default

An application being web-based does not imply that it needs public internet
exposure. Private access remains the default, with exceptions requiring an
explicit purpose and a narrower trust boundary.

### State Has an Owner

Every persistent data set should have one authoritative location, a documented
backup boundary, and a recovery procedure. Databases and bulk data use different
storage strategies because their consistency and availability requirements
differ.

### Failure Must Be Visible

A missing scan, failed backup, stale metric, or stopped log pipeline is itself an
operational signal. Monitoring should detect silent control failure rather than
only report findings produced by healthy controls.

### Promotion Is Not Validation

A passing CI result makes a revision eligible for promotion; it does not make an
automatic production change mandatory. Stateful or high-risk services retain a
manual approval boundary.

### Recovery Precedes Destructive Change

Changes to keys, stateful platforms, and deployment mechanisms require a viable
rollback or isolated recovery path before production mutation.

These cross-cutting choices are recorded in the public
[architecture decision index](adr/README.md).

## Public Evidence Plan

The sanitized logical architecture, primary trust-boundary diagram, focused
network and identity design, and key architecture decisions are documented.
Redacted runtime evidence is still required before the operated platform claims
can advance beyond the boundaries in the
[claim-to-evidence matrix](../evidence/validation-matrix.md).
