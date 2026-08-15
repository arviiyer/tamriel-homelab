# Architecture

## Design Goal

Tamriel is a self-hosted private-cloud environment for operating personal
services and developing security engineering capabilities. Its architecture is
designed around explicit trust boundaries, observable failure, controlled
change, and recoverable state.

The public model uses role-based aliases and omits production addressing and
identifiers.

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

### Delivery

Private Forgejo repositories use protected branches and pull-request validation.
The delivery model separates validation from production promotion and uses
restricted target-side controls for the workloads that support automated
deployment.

### Recovery

VM-level snapshots protect service operating systems and local application
state. Selected high-value data also receives an off-host copy. Recovery is
designed around restoration into an isolated identity before any production
replacement decision.

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

## Public Evidence Plan

This document currently describes the sanitized logical architecture. The first
public release will add:

- a polished trust-boundary and data-flow diagram;
- public architecture decision records;
- links from each layer to reviewed implementation examples; and
- redacted runtime evidence for the operated platform.
