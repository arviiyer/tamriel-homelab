# Pi-hole and Unbound

[Home](../../README.md) · [Networking](../README.md) · [Private HTTPS](../private-access/README.md)

The Raspberry Pi runs Pi-hole for client DNS and Unbound for recursive lookups.
Local application records point at Caddy's LAN address. OPNsense supplies clients
with the Pi's DNS address through DHCP.

## Install

Use a Debian-based host with a stable LAN address. Install Pi-hole using its
[official installation steps](https://docs.pi-hole.net/main/basic-install/), then
set its administrator password with `sudo pihole setpassword`.

When Caddy shares this host, move Pi-hole v6's web interface to port 8080:

```bash
sudo pihole-FTL --config webserver.port '8080'
sudo systemctl restart pihole-FTL
sudo apt install unbound dns-root-data dnsutils
```

Create `/etc/unbound/unbound.conf.d/pi-hole.conf`:

```yaml
server:
    interface: 127.0.0.1
    port: 5335
    do-ip4: yes
    do-ip6: no
    do-udp: yes
    do-tcp: yes
    harden-glue: yes
    harden-dnssec-stripped: yes
    use-caps-for-id: no
    edns-buffer-size: 1232
    prefetch: yes
    hide-identity: yes
    hide-version: yes
```

Debian's `dns-root-data` supplies the root hints and its Unbound package supplies
the trust-anchor configuration. The example uses IPv4 upstream transport; enable
IPv6 transport if your network supports it. IPv6 DNS records can still be resolved.

```bash
sudo unbound-checkconf
sudo systemctl enable --now unbound
sudo systemctl restart unbound
dig @127.0.0.1 -p 5335 example.com
dig @127.0.0.1 -p 5335 fail01.dnssec.works
```

The ordinary query should succeed; the deliberately invalid DNSSEC domain should
return `SERVFAIL`. If the package enabled `unbound-resolvconf.service`, follow
Pi-hole's [Debian resolver-loop instructions](https://docs.pi-hole.net/guides/dns/unbound/)
before changing the host's resolver.

In Pi-hole **Settings → DNS**, deselect the other upstream resolvers and use
`127.0.0.1#5335` as the custom upstream. Check a client query in Pi-hole's query
log and confirm that it is forwarded to Unbound.

## Give clients the DNS server

Set the Pi's address as the DNS server in each intended OPNsense DHCP scope, then
renew a test client's lease. Allow those client networks to reach the Pi on
both UDP and TCP 53. Routed VLAN clients may require Pi-hole's listening mode
to accept non-local requests; limit those sources with the firewall.

Permit the Pi's recursive DNS traffic to the internet on UDP/TCP 53. If redirecting
client DNS at the gateway, exclude the resolver itself to avoid a loop. A public
DNS server advertised as a second client resolver can bypass Pi-hole and its
local records.

## Local application names

Under Pi-hole **Settings → Local DNS Records**, add your application hostnames
with the proxy's LAN address. For example, `photos.example.com` and
`rss.example.com` both point at Caddy, while Caddy chooses the upstream service.

```bash
dig @192.0.2.5 photos.example.com
dig photos.example.com
```

Replace the example address and name. Both queries should return the proxy LAN
address from a home client. If only the first works, check the client's DNS
settings, browser secure DNS, and stale cache. The
[private-access guide](../private-access/README.md) adds remote DNS and TLS.

## Backups and updates

Export Pi-hole's Teleporter backup from its settings before changing versions.
Keep the Unbound configuration with it. Update Pi-hole with `pihole -up` and
Unbound through the OS packages, then repeat the resolver and client tests.
When restoring to a new host, check its address and listening mode before
advertising it through DHCP.

[Pi-hole documentation](https://docs.pi-hole.net/) ·
[Unbound integration guide](https://docs.pi-hole.net/guides/dns/unbound/)

## Checks

From the repository root, run `python3 networking/dns/check.py` with Docker,
Compose, and outbound UDP/TCP 53 available. It starts a fresh Pi-hole container
and a Debian Unbound container using the configuration above. It checks a local
record, recursive lookups, and DNSSEC rejection, including a successful lookup
of the invalid domain when validation is explicitly disabled for that query.
The temporary containers and data are removed afterward.
