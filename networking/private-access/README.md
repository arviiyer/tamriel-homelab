# Private HTTPS and sign-in

[Home](../../README.md) · [Networking](../README.md) · [Apps](../../apps/README.md)

I use the same application hostname at home and away. Selected apps have Pi-hole
records pointing at Caddy's LAN address; public DNS returns its Tailscale address.
Caddy terminates HTTPS, then the application uses its own login or Authentik.
This guide gives both the application and identity hostname a local DNS record.

This walkthrough puts a small web page behind Authentik forward authentication.
It includes the proxy configuration and the DNS, certificate, and provider steps.
The lab's native OIDC integrations are linked at the end.

## Before starting

You need a Linux host with Docker Engine, Compose, curl, OpenSSL, Python 3, and
free ports 80, 443, 2019, 8088, 9000, and 9443. Allow at least 2 cores and 2 GB RAM for
Authentik. Use a dedicated test host if you already run a proxy on these ports.

You also need a domain with DNS hosted by Cloudflare, a tailnet, and a local DNS
server. Follow the [Pi-hole and Unbound guide](../dns/README.md) for local DNS.
Replace `example.com` and the documentation addresses with your own values.

The walkthrough puts Caddy, Authentik, and the sample page on the same host.
My lab has Caddy on the Pi and Authentik on its own VM; in that arrangement,
replace the loopback upstream with the identity VM's private address and allow
the proxy to reach it.

## Tailscale and DNS

Install Tailscale using its [Linux instructions](https://tailscale.com/download/linux),
then enroll the proxy host:

```bash
sudo tailscale up --accept-dns=false
tailscale ip -4
```

In the tailnet policy, permit your intended client identities to reach this
device on TCP 443. Check that no broader default grant defeats that restriction.
The server retains local DNS; enroll your phone or laptop as a client too.

Create two **DNS-only** public A records, `auth.example.com` and `app.example.com`,
pointing at the proxy's Tailscale IPv4 address. In Pi-hole's local DNS records,
point those same two names at its LAN address. Remove conflicting AAAA or CNAME
records. The public A records provide discovery, while reaching their address
requires Tailscale.

In the router and host firewall, allow trusted LAN clients to the proxy on TCP
443 (and optionally TCP 80 for redirects). Allow HTTPS through Tailscale and
allow Authentik's container network to reach the proxy on TCP 443. Keep
WAN port forwards absent. The example also checks client source addresses in
Caddy. UDP 443 is optional for HTTP/3; HTTPS works over TCP without it.

## Install Authentik

Create a fresh directory outside the checkout and obtain the official Compose
file. It pins a release when downloaded:

```bash
mkdir -p "$HOME/homelab-examples"
mkdir "$HOME/homelab-examples/authentik"
cd "$HOME/homelab-examples/authentik"
curl -fLo compose.yml https://docs.goauthentik.io/compose.yml
(
  set -euC
  umask 077
  printf 'PG_PASS=%s\nAUTHENTIK_SECRET_KEY=%s\nCOMPOSE_PORT_HTTP=127.0.0.1:9000\nCOMPOSE_PORT_HTTPS=127.0.0.1:9443\n' \
    "$(openssl rand -hex 24)" "$(openssl rand -hex 48)" > .env
)
```

Remove the worker's `/var/run/docker.sock` mount from `compose.yml`. This guide
uses the embedded outpost and does not need automatic Docker outpost deployment.
Keep the database volume on local storage.

```bash
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps
```

Use `ssh -L 9000:127.0.0.1:9000 operator@proxy-01` from your workstation, then
open `http://localhost:9000/if/flow/initial-setup/` and create the administrator.
Create a normal user for the application and a group called `homelab-users`.
Add that user to the group. Keep the original secret key with the database backup.

[Official Authentik installation](https://docs.goauthentik.io/install-config/install/docker-compose/)

## Build Caddy with DNS certificates

Cloudflare DNS validation lets Caddy obtain a publicly trusted certificate
without opening an inbound WAN port. Create a Cloudflare API token with
**Zone → DNS → Edit** and **Zone → Zone → Read**, limited to the selected zone.

```bash
mkdir "$HOME/homelab-examples/private-access"
cd "$HOME/homelab-examples/private-access"
for file in compose.yml Dockerfile .dockerignore Caddyfile environment.example; do
  curl --fail --location --output "$file" \
    "https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/networking/private-access/$file" || break
done
cp environment.example .env
chmod 600 .env
```

Edit `.env`:

| Setting | Value |
|---|---|
| `AUTH_DOMAIN`, `APP_DOMAIN` | Your two real DNS names |
| `AUTH_UPSTREAM` | `127.0.0.1:9000` for this walkthrough |
| `APP_UPSTREAM` | `127.0.0.1:8088` for the sample page |
| `PROXY_LISTEN_ADDRESSES` | Space-separated LAN and Tailscale addresses of this host |
| `TRUSTED_CIDRS` | Space-separated allowed LAN client CIDRs and client Tailscale addresses with `/32` |
| `CLOUDFLARE_API_TOKEN` | The zone-scoped token |

Use the source addresses the proxy actually sees. Keep tailnet access policy in
place even when allowing a broader Tailscale address range in Caddy.
Authentik's embedded outpost also connects to its HTTPS hostname. Include the
source address or dedicated Docker-network subnet used by those requests in
`TRUSTED_CIDRS`. Use `docker network inspect` on Authentik's Compose network to
find its subnet; the container's localhost is not the host's localhost.

```bash
docker compose build
docker compose config --quiet
docker compose up -d
docker compose logs --tail=50 caddy
```

Open your Authentik HTTPS hostname and sign in. If certificate issuance fails,
check token permissions and DNS propagation in the Caddy logs. Certificates and
ACME account data persist in `caddy-data`.

## Protect the sample application

On the proxy host, in another terminal:

```bash
mkdir -p "$HOME/homelab-examples/sample-page"
printf 'Private application reached through Caddy\n' > "$HOME/homelab-examples/sample-page/index.html"
python3 -m http.server 8088 --bind 127.0.0.1 \
  --directory "$HOME/homelab-examples/sample-page"
```

In Authentik's administration interface:

1. Use **Applications → Applications → Create with provider**. Name the app
   `Example app`, slug `example-app`, and choose a **Proxy Provider**.
2. Choose **Forward auth (single application)**. Set the external host to your
   exact `https://app.example.com` URL. Select the default explicit-consent
   authorization flow and default invalidation flow offered by your release.
3. On the application's **Policy / Group / User Bindings** tab, bind
   `homelab-users`. This limits access to the intended users.
4. Under **Applications → Outposts**, edit the embedded outpost and add this
   application. Set its `authentik_host` to your `https://auth.example.com/`
    hostname. This address must be reachable from both the browser and Authentik.
    For this embedded-outpost setup, keep the HTTPS hostname in `authentik_host`.
5. Save, then open the app in a private browser window. Sign in with the normal
   group member. The page should display the sample text.

The [Caddyfile](Caddyfile) sends outpost paths to Authentik first, checks the
session, and only then proxies the page. Keep that ordering inside `route`.
The upstream is bound to loopback, so clients cannot bypass the proxy.

From the Authentik working directory, check that the server can reach its own
HTTPS identity URL, replacing the hostname:

```bash
docker compose exec -T server python -c \
  'import urllib.request; print(urllib.request.urlopen("https://auth.example.com/if/flow/default-authentication-flow/").status)'
```

Expect `200`. A `403` points to the proxy's source-address restriction; connection
or certificate errors need fixing before an outpost login can complete.

## Check each path

| Check | Expected result |
|---|---|
| Home client resolves both names | Proxy's LAN address |
| Remote client resolves both names | Proxy's Tailscale address |
| Remote client with Tailscale connected | Valid HTTPS and Authentik login |
| Remote client with Tailscale disconnected | Application unreachable |
| Allowed user signs in | Sample page loads |
| User outside `homelab-users` signs in | Access denied |
| App opened after logging out, in a fresh private window | Sign-in required |

`dig app.example.com` checks DNS. `curl -I https://app.example.com` should show
the unauthenticated redirect. To isolate LAN DNS from routing, use
`curl --resolve app.example.com:443:192.0.2.5 -I https://app.example.com`, replacing
the address and hostname while retaining TLS verification.

On the test host, stop Authentik's server and retry an uncached app request.
The request must fail rather than return the page. Start Authentik again and
repeat a fresh login. Stop the sample Python server when finished.

## Use it with an application

Set `APP_UPSTREAM` to the service's reachable private address. Keep direct client
access to that backend blocked. With Caddy on another host, account for Docker's
forwarding rules as well as the ordinary host firewall when limiting access.

For an application with its own login or native OIDC, replace the app block with
this route. It retains the private-client check and leaves sign-in to the app:

```caddyfile
{$APP_DOMAIN} {
	import private_site
	route {
		import private_clients
		reverse_proxy {$APP_UPSTREAM}
	}
}
```

For OIDC, configure the provider using the app-specific guide:

- [FreshRSS](../../apps/freshrss/README.md#sign-in)
- [Immich](../../apps/immich/README.md#authentik-sign-in)
- [Jellyfin SSO plugin](../../media/jellyfin/README.md#access-and-sign-in)

Avoid putting a second forward-auth browser redirect in front of a native app
API that phone or TV clients must use. Homarr and Stirling PDF use their own
logins in my setup. The [sign-in table](../README.md#caddy-and-authentik) covers
the remaining services.

## Changes and backups

After editing only the Caddyfile, reload with
`docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile`.
After changing `.env`, recreate Caddy with `docker compose up -d --force-recreate`.
On the lab's host-installed Caddy, I use `sudo systemctl reload caddy`.

Back up the proxy configuration, private environment, and certificate volume.
For Authentik, retain a consistent PostgreSQL backup, its original secret key,
uploaded data, custom templates, and Compose definition. Follow its
[upgrade instructions](https://docs.goauthentik.io/install-config/upgrade/)
for release-specific migrations, then check both an existing session and a fresh
login. Rebuild the proxy image when updating Caddy or the DNS module.

| Symptom | First thing to check |
|---|---|
| DNS works but HTTPS times out | Tailscale policy, firewall, listening address, and conflicting AAAA record |
| Caddy responds 403 | Actual client source address against `TRUSTED_CIDRS` |
| Redirect points to an internal address | Embedded outpost's `authentik_host` URL |
| Authentik reports application not found | Provider external host and outpost application assignment |
| Login loops | Exact HTTPS host, cookies, clock, and outpost configuration |
| HTTP 502 after successful login | Backend address, process, and reachability from the proxy |

[Authentik's Caddy reference](https://docs.goauthentik.io/add-secure-apps/providers/proxy/server_caddy/)

## Checks

From the repository root, with Python 3, Docker, and Compose 2.24.4 or newer:

```bash
python3 scripts/check-stack-examples.py --smoke access
```

This builds the DNS-enabled proxy and tests its routing with a mock identity
provider, including denied access and an unavailable provider.

For a fresh Authentik instance and a real browser login, install the additional
test dependencies in a virtual environment. Playwright's `--with-deps` option
installs browser OS dependencies and may prompt for sudo:

```bash
python3 -m venv "$HOME/.venvs/tamriel-browser-check"
. "$HOME/.venvs/tamriel-browser-check/bin/activate"
python3 -m pip install -r networking/private-access/requirements-test.txt
python3 -m playwright install --with-deps chromium
python3 networking/private-access/check_authentik.py
```

The test creates temporary users, a group-bound application, and an embedded
outpost. It checks local-CA HTTPS, allowed and denied logins, and an identity
outage, then removes its containers and data. Allow about 4 GiB of free memory
for the temporary stack and browser. Public certificate issuance and tailnet
enrollment use your provider configuration and the walkthrough's client checks.
