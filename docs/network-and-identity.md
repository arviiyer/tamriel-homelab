# Networking and sign-in

[Home](../README.md) · [Networking](../networking/README.md)

The network separates client and workload zones. The existing infrastructure LAN
still holds management services and most application VMs; management and server
VLANs have not yet been split.

## Network zones

The table describes access roles. Management is an access role within the
infrastructure LAN, rather than a separate deployed VLAN. Connections between
the routed zones are blocked unless explicitly allowed.

| Zone | Allowed use | Main restriction |
|---|---|---|
| Management | Infrastructure administration | Private access and a login for each service |
| Infrastructure | Hypervisors, gateway, storage, identity, and DNS | No broad access from clients or workloads |
| Trusted clients | Private applications through the reverse proxy | No automatic admin access |
| Managed work | Business use and external services | No personal infrastructure or data |
| Untrusted devices | Restricted DNS and internet access | No private-zone access by default |
| Guest | Internet access | No private-zone access |
| Media | Required application, storage, DNS, and external services | No unrelated applications or management |
| Sandbox | Separate administration and limited outbound connections | No access to trusted zones or unsolicited inbound connections |

## Access paths

Admin access goes through Tailscale, followed by a login to the relevant service.
The [Ansible example](../automation/ansible/README.md) checks SSH settings for
specific users and source addresses.

Trusted clients reach web applications through Caddy. Authentik provides OIDC or
forward authentication where supported. Other applications retain their own
authentication. Signing into an application does not grant admin access to the lab.

Each application applies its own permissions and uses its own credentials for
dependencies. CI and deployment also use separate credentials; see the
[deployment notes](case-studies/fail-closed-infrastructure-delivery.md).

## Allowed connections

Administrators can reach management interfaces; trusted clients can reach the
application proxy. Services can reach their required identity, DNS, and other
dependencies. Monitoring receives metrics, logs, and security events. Deployment
can reach only the SSH helper. Media services can use selected storage shares.

Managed-work, untrusted, and guest zones are denied access to private zones;
sandbox workloads cannot reach trusted or infrastructure zones. DNS and egress
rules depend on the source zone. Resolving a name does not grant access to a service.

## When something fails

- Losing Tailscale access must not expose management interfaces publicly.
- An Authentik failure must not bypass sign-in.
- Missing DNS or monitoring signals should be visible as failures.
- New dependencies need specific connections allowed, not blanket access.

Allowed connections can still carry malicious traffic, and administrators have
broad access. See the [security notes](threat-model.md). The
[DNS](../networking/dns/README.md#checks) and
[browser sign-in](../networking/private-access/README.md#checks) guides include
isolated checks; routed VLAN and tailnet client tests are on the
[roadmap](../ROADMAP.md).
