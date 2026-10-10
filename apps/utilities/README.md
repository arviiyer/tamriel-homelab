# Other apps

[Home](../../README.md) · [Apps](../README.md)

These smaller services each have a separate Compose file. Vaultwarden, SearXNG,
and OpenSpeedTest run on my Raspberry Pi. Stirling PDF runs on the application VM.

## Install an example

Requirements: Docker Engine, Compose, curl, and OpenSSL. Create a new directory
outside this checkout for the service, download its linked YAML file as
`compose.yml`, and run the commands in its section. For example:

```bash
mkdir -p "$HOME/homelab-examples"
mkdir "$HOME/homelab-examples/vaultwarden"
cd "$HOME/homelab-examples/vaultwarden"
curl -fLo compose.yml \
  https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/apps/utilities/vaultwarden.yml
```

The initial browser ports are local-only. On a remote machine, use an SSH tunnel
such as `ssh -L 8081:127.0.0.1:8081 operator@proxy-01`. Follow the
[private HTTPS guide](../../networking/private-access/README.md) for regular access;
an off-host proxy needs a reachable private binding and the matching firewall rule.

## Vaultwarden

I use Bitwarden clients with Vaultwarden. Its SQLite database and attachments
stay on the Pi, with Restic copies locally and on another host.

Download [vaultwarden.yml](vaultwarden.yml) as above. For the initial local setup,
create `.env` with `VAULT_SIGNUPS_ALLOWED=true`, restrict it with `chmod 600 .env`,
and start:

```bash
docker compose config --quiet
docker compose up -d
curl -f http://127.0.0.1:8081/alive
```

Open `http://localhost:8081`, register your account, and set
`VAULT_SIGNUPS_ALLOWED=false` in `.env`. Recreate the container with
`docker compose up -d` and check that a second registration is refused.

Configure an HTTPS route to Vaultwarden with its own login, then set
`VAULT_DOMAIN=https://vault.example.com` to your real hostname and recreate it.
In each Bitwarden client, choose **Self-hosted** and enter that URL. Test saving
a disposable entry in one client and syncing it to another. The browser vault
needs HTTPS or a localhost secure context. Keep browser-only forward-auth
redirects off the native-client API path.

For a simple consistent backup, stop Vaultwarden and archive its `/data` volume
using the cold-copy steps below. Keep the database, attachments, sends, and key
files together. An encrypted vault export alone is not a complete server backup.
Use [Restic](../../storage/restic/README.md) to copy the archive off the Pi.

When restoring to a separate instance, check login, an old item, attachments,
and client synchronization. Bitwarden client and server versions must be
compatible; a successful HTTP login can still leave a newer client stuck loading.

[Vaultwarden documentation](https://github.com/dani-garcia/vaultwarden/wiki)

## SearXNG

My private search page aggregates results from selected engines. Its hostname
works through local DNS at home and Tailscale away from home.

Download [searxng.yml](searxng.yml) as `compose.yml` into its own directory. Generate
the session secret once:

```bash
(umask 077; set -C; printf 'SEARXNG_SECRET=%s\n' "$(openssl rand -hex 32)" > .env)
docker compose config --quiet
docker compose up -d
```

Open `http://localhost:8082`, try a query, and select engines under Preferences.
For persistent instance settings, edit `/etc/searxng/settings.yml` in its
configuration volume. Keep `use_default_settings: true` and override only the
settings you need. I keep the Bing web engine inactive because it sometimes
ignored terms in multi-word queries; Google CSE is my main general engine.

Set `SEARCH_URL` in `.env` to the final HTTPS URL and recreate the service after
adding the private proxy route. This is a private instance with no built-in
user login. Limit access through the proxy/network, or add forward authentication
as shown in the networking guide.

Back up `/etc/searxng` and `.env`. The cache is disposable. After updating the
image, check a query and the engine-error panel: an upstream engine can reject
requests even when the SearXNG process is healthy.

[SearXNG container documentation](https://docs.searxng.org/admin/installation-docker.html)

## Stirling PDF

I use Stirling PDF to rotate pages and merge documents in a browser. It has its
own login. Its lab updates go through the
[manual deployment workflow](../../automation/README.md#runners-and-deployment).

Download [stirling-pdf.yml](stirling-pdf.yml) as `compose.yml` into a new directory:

```bash
(umask 077; set -C; printf 'PDF_INITIAL_PASSWORD=%s\n' "$(openssl rand -hex 24)" > .env)
docker compose config --quiet
docker compose up -d
docker compose logs --tail=50 stirling-pdf
```

Open `http://localhost:8087` after startup. Sign in as `operator` using the initial
password saved in `.env`, and complete any password-change prompt. The initial
password setting applies to a new database, not an existing account.

Try rotating a disposable PDF and merging two small files. Download the result
and check its page count and text. Add a private HTTPS route while retaining
Stirling PDF's own login. Version 3 distinguishes interactive use from some
automation/API features; check its current feature/licensing documentation for
the job you want to automate.

Back up `/configs` while stopped, including its database and encryption key.
After an update, verify login and a document operation. Keep the old image and
configuration backup together if the new release migrates the saved settings.

[Stirling PDF documentation](https://docs.stirlingpdf.com/)

## OpenSpeedTest

The Pi's Speedtest service is OpenSpeedTest. It measures browser-to-server
throughput, so a test over home Wi-Fi measures that local path. A test over
Tailscale includes the remote network and VPN path.

Download [openspeedtest.yml](openspeedtest.yml) as `compose.yml`:

```bash
docker compose up -d
```

Open `http://localhost:3010` for a basic page check. To measure a LAN client,
bind port 3010 to the server's LAN address and allow that client, then open the
LAN URL directly. An SSH tunnel or reverse proxy adds another component to the
measurement. The example is stateless; keep its Compose definition for recovery.

[OpenSpeedTest project](https://github.com/openspeedtest/Speed-Test)

## Cold copies, updates, and cleanup

For the stateful examples, stop the application before copying its volume. This
Bash block works on a local, rootful Linux Docker Engine host. Run it in the
service's working directory and enter its Compose service name (`vaultwarden`,
`searxng`, or `stirling-pdf`):

```bash
(
  set -eu
  umask 077
  read -r -p 'Compose service to back up: ' service
  container=$(docker compose ps -q "$service")
  test -n "$container"
  backup=$(mktemp -d "$HOME/app-backup.XXXXXX")
  volumes=$(docker inspect --format '{{range .Mounts}}{{if eq .Type "volume"}}{{println .Name}}{{end}}{{end}}' "$container")
  test -n "$volumes"
  docker compose stop "$service"
  for volume in $volumes; do
    mount=$(docker volume inspect --format '{{.Mountpoint}}' "$volume")
    sudo tar -C "$mount" -czf - . > "$backup/$volume.tar.gz"
  done
  cp compose.yml "$backup/"
  if [ -f .env ]; then cp .env "$backup/"; fi
  docker compose start "$service"
  printf 'Backup saved to %s\n' "$backup"
)
```

If copying fails, fix the error before starting the service again. For Docker
Desktop or a remote daemon, use a backup container with the volume mounted
instead of the daemon host's `Mountpoint`.

To test restoration, use a new Compose project and empty volume, stop its service,
extract the archive into that volume preserving numeric ownership, and start it
on a different loopback port. Check the application-specific data above.

For updates, read release notes, take the backup, change the pinned image
reference, and run `docker compose pull` followed by `docker compose up -d`.
`docker compose down` keeps named volumes; `down --volumes` deletes them.

From the repository root, `python3 scripts/check-service-examples.py --smoke
vaultwarden` checks the web interface and disabled registration in a disposable
instance. The same command accepts `searxng`, `stirling-pdf`, and `openspeedtest`;
it requires Python 3 and Compose 2.24.4 or newer.
