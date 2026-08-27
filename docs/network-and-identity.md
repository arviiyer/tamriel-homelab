# Network and Identity Design

Status: **Drafted architecture evidence**. This document describes the
sanitized logical design. It does not prove current firewall rules, identity
configuration, DNS enforcement, or operation over time.

## Scope and Claim Boundary

The network and identity model limits what an endpoint, workload, or automation
identity can reach after it crosses a trust boundary. It complements the
[primary architecture diagram](../README.md#architecture) and
[threat model](threat-model.md) without publishing production topology.

This public model intentionally excludes addresses, interface names, VLAN IDs,
firewall aliases, raw rule order, DNS overrides, application groups, account
names, management routes, and emergency access procedures.

## Design Goals

- Do not treat local-network presence as authorization.
- Keep infrastructure management on a private administrative path.
- Give client and workload zones only the flows required for their role.
- Centralize application authentication where the application supports it.
- Keep administrative, user, automation, and workload identities distinct.
- Treat DNS and egress restrictions as network controls, not proof of identity.
- Make policy or identity failure visible rather than silently broadening access.

## Trust Zones

The zones represent different control assumptions, not exact production
segments. A flow absent from this model is denied by default and requires a
specific operational justification.

| Zone | Intended access | Default restriction |
|---|---|---|
| Management | Private administration of infrastructure and selected service control planes | No general client membership or public ingress |
| Infrastructure | Hypervisors, gateway, storage, identity, DNS, and core platform services | No broad client or workload reachability |
| Trusted clients | Private application access through approved ingress paths | No inherited infrastructure-management access |
| Managed work | Business use and required external services | No reachability to personal infrastructure or data |
| Untrusted devices | Constrained DNS and egress for devices with limited owner control | No private-zone access by default |
| Guest | Internet access for temporary devices | No private-zone reachability |
| Media | Explicit application, storage, DNS, and egress flows required by media workloads | No general management or unrelated application access |
| Sandbox | Dedicated control and explicitly approved egress for disposable analysis workers | No trusted-zone access and no unsolicited ingress |

## Access Paths

### Administration

Administrative access enters through a private overlay path represented publicly
by Tailscale. Management interfaces are not intentionally exposed as public
internet services. OpenSSH access uses role-specific key policy, and the public
[Ansible example](../automation/ansible/README.md) demonstrates static policy for
source-aware effective-configuration checks.

The overlay reduces exposure but is not treated as sufficient authorization.
Administrative endpoint security, key handling, service authorization, and
source restrictions remain separate controls.

### Private Applications

Trusted clients reach private web applications through a Caddy reverse-proxy
boundary. Applications that support centralized integration use Authentik with
OIDC or forward authentication and application-group authorization. Applications
that cannot use this path retain their own authentication boundary and must not
be described as centrally authenticated.

Central identity does not grant management-plane access. Application sessions,
administrative SSH identities, and infrastructure authorization remain separate
security contexts.

### Controlled Delivery

Forgejo validation and deployment identities have different authority. Pull
request content runs without deployment credentials. A separately authorized
promotion passes one validated full commit SHA through a forced-command target
boundary that owns the allowlist, health check, and rollback state.

This path is documented and validated separately in the
[fail-closed delivery case study](case-studies/fail-closed-infrastructure-delivery.md).

## Identity Boundaries

| Identity type | Authority boundary | Public claim |
|---|---|---|
| Application user | Authentik group or application-native authorization | Central integration is used where supported; operated authentication evidence is pending |
| Administrator | Private-path access plus service-specific SSH or management authorization | Static SSH policy is published; live network and identity enforcement is not |
| Source and CI identity | Forgejo repository and workflow permissions | Sanitized workflow structure is published; private repository settings remain unverified publicly |
| Deployment identity | Source-restricted key, forced command, and narrow target-side policy | The public target transaction is validated; operated runner and repository evidence is pending |
| Workload identity | Service-specific runtime credentials and network reachability | Credentials remain outside source control; complete private service policy is not published |

No single sign-on claim implies a single authorization plane. The identity
provider proves an application-facing identity only within the integration and
group policy that the application consumes.

## Logical Flow Policy

This table shows the intended policy shape. It is not a firewall export, an
ordered ruleset, or evidence that each flow is currently enforced.

| Source | Destination | Purpose | Policy baseline |
|---|---|---|---|
| Management | Infrastructure control planes | Administration and recovery | Explicit private path with service-specific authorization |
| Trusted clients | Private edge and approved applications | Normal application use | Constrained ingress with central authentication where supported |
| Application workloads | Identity and required platform services | Authentication, DNS, and service dependencies | Explicit service flows only |
| Workloads | Prometheus and Loki paths | Metrics and logs | Workload-to-observability flows only |
| Security automation | Observability and alerting | Findings, runtime events, and control health | Explicit telemetry destinations only |
| Delivery | Restricted target helper | Exact-revision promotion or rollback | Forced command and target-owned allowlist |
| Media | Shared bulk storage | Required data access | Constrained exports and workload-specific reachability |
| Managed work, untrusted, and guest | Private zones | None by default | Deny |
| Sandbox | Trusted and infrastructure zones | None | Deny |
| Client and workload zones | DNS and external services | Name resolution and approved egress | Zone-appropriate resolver and egress policy |

## DNS and Egress

Central DNS policy provides a consistent control point for private name
resolution, filtering, and zone-specific resolver behavior. It does not replace
network segmentation or application authentication, and DNS success does not
grant access to the resolved service.

Egress policy is proportional to the zone. Trusted clients require normal
private application access, while untrusted, media, and sandbox workloads use
narrower destinations or service paths. Exact resolver rules, allowlists, and
external destinations remain private because publishing them would reveal
operational topology and control gaps.

## Failure Expectations

- Loss of the private administration path must not create a public management
  fallback.
- Loss of centralized identity must not silently turn an authenticated ingress
  path into anonymous access; application-specific failure behavior still needs
  runtime validation.
- Loss of DNS or telemetry must be observable as a control-health problem rather
  than interpreted as proof that clients or workloads are healthy.
- A new inter-zone dependency requires an explicit flow review rather than a
  broad temporary allow rule.
- A promotion runner cannot gain a general target shell from the deployment
  credential.
- A sandbox or untrusted endpoint remains outside trusted zones even when it can
  reach approved DNS or egress services.

## Public Evidence and Gaps

Publicly inspectable support currently includes:

- the [primary trust-boundary diagram](../README.md#architecture);
- the [threat-to-control narrative](threat-model.md);
- the [capability-oriented platform catalog](platform-catalog.md);
- static [OpenSSH hardening policy](../automation/ansible/README.md); and
- validated [restricted delivery policy](../automation/ci/README.md).

Still required for stronger claims:

- a sanitized zone-policy case study or synthetic rule-validation example;
- reviewed authentication-flow evidence;
- reviewed DNS and ingress evidence;
- confirmation of private repository and runner permission boundaries; and
- operated evidence showing segmentation and identity controls over time.

Until that evidence exists, the network and centralized-identity rows in the
[claim-to-evidence matrix](../evidence/validation-matrix.md) remain `Drafted`.

## Limitations

- The design does not claim formal zero trust or enterprise compliance.
- Central identity coverage is incomplete where an application lacks a suitable
  integration.
- A private overlay narrows exposure but retains endpoint, identity-provider,
  and control-plane dependencies.
- Network controls do not protect against an already authorized administrator or
  a compromised service inside an allowed flow.
- No raw firewall, switching, DNS, identity-provider, or overlay configuration is
  public evidence.
