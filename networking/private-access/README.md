# Private HTTPS and sign-in

[Home](../../README.md) · [Networking](../README.md) · [Apps](../../apps/README.md)

Caddy runs on my Raspberry Pi and forwards requests to the application VMs.
Pi-hole resolves app names to the Pi's LAN address at home; public DNS returns
its Tailscale address for use away from home. Authentik runs on a separate VM.

This guide follows that layout. I run Caddy as a host service in the lab; the
Compose file here builds the same Cloudflare DNS module and uses host networking.

## The setup

Replace these addresses and `example.com` with your own:

| Host | Address | Services |
|---|---|---|
| `proxy-01` | `192.0.2.5` plus its Tailscale address | Caddy, Tailscale, local DNS |
| `identity-01` | `192.0.2.81` | Authentik on TCP 9000 |
| `observability-01` | `192.0.2.82` | Uptime Kuma on TCP 3001 |
| `media-01` | `192.0.2.84` | Jellyfin on TCP 8096, Seerr on TCP 5055 |

Use Linux hosts with Docker Engine, Compose, curl, and OpenSSL. Allow at least
2 cores and 2 GB RAM for Authentik. Caddy needs ports 80 and 443 available.
You also need a Cloudflare-managed domain, a tailnet, and
[local DNS](../dns/README.md).

Configure the router and host firewalls for these connections:

| Source | Destination | TCP ports |
|---|---|---|
| Trusted LAN and tailnet clients | Pi proxy | 443, optionally 80 for redirects |
| Pi proxy | Identity VM | 9000 |
| Pi proxy | Monitoring VM | 3001 |
| Pi proxy | Media VM | 8096, 5055 |
| Identity VM | Pi proxy | 443, for the embedded outpost |
| Seerr's Docker network on the media VM | Media VM | 8096 |

Limit backend access to those sources. For Docker-published ports, use the
[Docker host firewall rules](https://docs.docker.com/engine/network/packet-filtering-firewalls/),
including `DOCKER-USER` with the iptables backend; an ordinary UFW input rule
does not filter forwarded container traffic. The lab's media rule filters
traffic arriving on the VM's LAN interface while allowing local container
connections. There are no WAN port forwards for these applications.

## Tailscale and DNS

On the Pi, [install Tailscale](https://tailscale.com/download/linux), then run:

```bash
sudo tailscale up --accept-dns=false
tailscale ip -4
```

Permit your client identities to reach this device on TCP 443 in the tailnet
policy. Enroll your phone or laptop too.

Create **DNS-only** public A records for `auth.example.com` and
`status.example.com`, pointing at the Pi's Tailscale address. In Pi-hole, point
the same names at `192.0.2.5`. Remove conflicting AAAA or CNAME records. Authentik
must also resolve its own HTTPS name to a reachable proxy address.

## Install Authentik

On **identity-01**, obtain the [official Compose file](https://docs.goauthentik.io/install-config/install/docker-compose/):

```bash
mkdir -p "$HOME/homelab/authentik"
cd "$HOME/homelab/authentik"
curl -fLo compose.yml https://docs.goauthentik.io/compose.yml
(
  set -euC
  umask 077
  printf 'PG_PASS=%s\nAUTHENTIK_SECRET_KEY=%s\nCOMPOSE_PORT_HTTP=192.0.2.81:9000\nCOMPOSE_PORT_HTTPS=127.0.0.1:9443\n' \
    "$(openssl rand -hex 24)" "$(openssl rand -hex 48)" > .env
)
```

Set the HTTP binding to your identity VM's address. Remove the worker's
`/var/run/docker.sock` mount: the embedded outpost does not need it. Keep the
database on the VM's local disk.

```bash
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps
```

From your workstation, run `ssh -N -L 9000:192.0.2.81:9000 operator@identity-01`.
Open `http://localhost:9000/if/flow/initial-setup/` and create the administrator.
Create a normal user, a `homelab-users` group, and add the user to that group.

## Start the application

On **observability-01**, follow the [Uptime Kuma guide](../../monitoring/uptime-kuma/README.md)
and create its administrator through the initial SSH tunnel. Then change the
published port to `192.0.2.82:3001:3001` and run `docker compose up -d`.

From the Pi, check both upstreams:

```bash
curl -I http://192.0.2.81:9000/if/flow/default-authentication-flow/
curl -I http://192.0.2.82:3001/
```

Both should return an HTTP response. Resolve connectivity problems here before
configuring HTTPS.

## Build Caddy with DNS certificates

Create a Cloudflare API token with **Zone → DNS → Edit** and **Zone → Zone → Read**,
limited to your zone. DNS validation obtains certificates without an inbound WAN
connection. On **proxy-01**:

```bash
mkdir -p "$HOME/homelab/private-access"
cd "$HOME/homelab/private-access"
(
  set -eu
  for file in compose.yml Dockerfile .dockerignore Caddyfile environment.example; do
    curl -fLo "$file" \
      "https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/networking/private-access/$file"
  done
)
cp environment.example .env
chmod 600 .env
```

Edit `.env`:

| Setting | Value |
|---|---|
| `AUTH_DOMAIN`, `APP_DOMAIN` | `auth.example.com`, `status.example.com` |
| `AUTH_UPSTREAM`, `APP_UPSTREAM` | `192.0.2.81:9000`, `192.0.2.82:3001` |
| `PROXY_LISTEN_ADDRESSES` | Space-separated LAN and Tailscale addresses of the Pi |
| `TRUSTED_CIDRS` | Allowed client CIDRs, client Tailscale addresses with `/32`, and the identity VM's address with `/32` |
| `CLOUDFLARE_API_TOKEN` | Your zone-scoped token |

The identity VM needs access because its embedded outpost connects back to the
HTTPS identity URL. Use the source address Caddy sees, usually the VM address
after Docker masquerading.

```bash
docker compose build
docker compose config --quiet
docker compose up -d
docker compose logs --tail=50 caddy
```

Open `https://auth.example.com` and sign in. For certificate errors, check DNS
and token permissions in the logs.

## Add forward authentication

In Authentik:

1. Under **Applications → Applications → Create with provider**, name the app
   `Uptime Kuma`, slug `uptime-kuma`, and select **Proxy Provider**.
2. Choose **Forward auth (single application)** and external host
   `https://status.example.com`. Select the default explicit-consent authorization
   and invalidation flows offered by your release.
3. Bind `homelab-users` on the application's **Policy / Group / User Bindings** tab.
4. Under **Applications → Outposts**, add the app to the embedded outpost. Set
   `authentik_host` to `https://auth.example.com/`.
5. Open the status URL in a private browser window and sign in as the normal user.

The [Caddyfile](Caddyfile) routes outpost requests first, checks the session, then
proxies Kuma. Keep that ordering inside `route`. Kuma retains its own login.

From the Authentik directory, check the outpost's return path:

```bash
docker compose exec -T server python -c \
  'import urllib.request; print(urllib.request.urlopen("https://auth.example.com/if/flow/default-authentication-flow/").status)'
```

Expect `200`. A `403` usually means the identity VM is missing from `TRUSTED_CIDRS`.

## Use it with an application

For another forward-auth application, copy the app block and configure its
hostname, upstream, and Authentik provider. For native OIDC or the app's own
login, omit the outpost and `forward_auth` directives:

```caddyfile
rss.example.com {
	import private_site
	route {
		import private_clients
		reverse_proxy 192.0.2.83:8080
	}
}
```

Publish FreshRSS on `192.0.2.83:8080:80` and allow the proxy to reach it.
The [FreshRSS](../../apps/freshrss/README.md#sign-in),
[Immich](../../apps/immich/README.md#authentik-sign-in), and
[Jellyfin](../../media/jellyfin/README.md#access-and-sign-in) guides cover their
OIDC setup. Native phone and TV clients generally need the application's login,
without an extra forward-auth browser redirect.

## Media routes

The [media stack](../../media/README.md) uses the same Pi proxy. Download
[media.caddy](media.caddy), replace its names and media VM address, and append
its two blocks to your Caddyfile. They use the app's own login:

```bash
curl -fLo media.caddy \
  https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/networking/private-access/media.caddy
# Edit media.caddy first, then add it once:
cat media.caddy >> Caddyfile
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

Add `media.example.com` and `requests.example.com` to public and local DNS using
the same addresses as the other apps. Check Jellyfin playback and a Seerr login
through HTTPS. In Seerr, the internal Jellyfin URL is `http://192.0.2.84:8096`;
its browser-facing URL is `https://media.example.com`.

## Check each path

| Check | Expected result |
|---|---|
| Home client resolves an app name | Pi's LAN address |
| Remote client resolves it | Pi's Tailscale address |
| Remote client connected to Tailscale | HTTPS and application login |
| Remote client disconnected | Application unreachable |
| User outside `homelab-users` opens Kuma | Authentik denies access |
| Fresh private window after logout | Sign-in required |

Use `dig status.example.com` for DNS and `curl -I https://status.example.com`
for the unauthenticated redirect. To test the Pi directly while retaining TLS
verification: `curl --resolve status.example.com:443:192.0.2.5 -I https://status.example.com`.

## Changes and backups

Reload Caddy after editing its file. Recreate it with
`docker compose up -d --force-recreate caddy` after changing `.env`.
For host-installed Caddy, use `sudo systemctl reload caddy`.

Back up the proxy configuration, environment, and certificate volume. Authentik
needs its PostgreSQL backup, original secret key, uploads, and custom templates.
Follow the [upgrade notes](https://docs.goauthentik.io/install-config/upgrade/)
and check a fresh login afterward.

| Symptom | Check |
|---|---|
| HTTPS times out | Tailnet policy, firewall, listen addresses, and conflicting AAAA records |
| Caddy responds 403 | Client source address against `TRUSTED_CIDRS` |
| Redirect points at an internal address | Outpost's `authentik_host` |
| Application not found | Provider external host and outpost assignment |
| HTTP 502 | Backend process, binding, and reachability from the Pi |

## Checks

From the repository root with Python 3, Docker, and Compose 2.24.4+:

```bash
python3 scripts/check-stack-examples.py --smoke access
```

This tests routing, denied access, and identity outages with a mock provider.
For real Authentik browser login, use a virtual environment with
[requirements-test.txt](requirements-test.txt), run
`python3 -m playwright install --with-deps chromium`, then
`python3 networking/private-access/check_authentik.py`. The temporary stack
needs about 4 GiB of free memory and removes its containers afterward.

[Authentik's Caddy reference](https://docs.goauthentik.io/add-secure-apps/providers/proxy/server_caddy/)
