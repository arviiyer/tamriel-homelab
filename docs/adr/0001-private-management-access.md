# ADR 0001: Keep Management Access Private by Default

- Status: Accepted
- Public record: August 2026
- Scope: Sanitized logical architecture

## Context

Hypervisor, gateway, storage, identity, and automation control planes have a
larger blast radius than normal application interfaces. Local-network presence
is not sufficient evidence that an endpoint or user should administer them.
Publishing management services directly also expands the credential and patching
boundary.

## Decision

Management interfaces are not intentionally exposed as public internet
services. Administrative access enters through a private overlay path and still
requires service-specific authorization such as restricted SSH keys. Client
application ingress remains a separate path and does not imply management
reachability.

The public architecture omits exact routes and emergency procedures.

## Consequences

- Public exposure and unauthenticated scanning of management services are
  reduced.
- Compromise of an ordinary client zone does not automatically grant a path to
  infrastructure control planes.
- Administration depends on the private access control plane and trusted
  endpoints.
- Recovery from an overlay or identity failure requires a separately governed
  private procedure that cannot be published here.
- Private access does not replace endpoint hardening, strong authentication,
  patching, or source restrictions.

## Public Evidence

The [network and identity design](../network-and-identity.md) and
[threat model](../threat-model.md) document the boundary. The public
[Ansible SSH policy](../../automation/ansible/README.md) provides static host
policy evidence. Operated network and access evidence remains pending.
