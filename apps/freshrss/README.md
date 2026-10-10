# FreshRSS

[Home](../../README.md) · [Apps](../README.md) · [Networking](../../networking/README.md)

FreshRSS is my browser-based feed reader. It holds security news and technical
articles and supplies the input for the [Morning SOC Briefing](../projects/README.md#morning-soc-briefing).

- [Install](#install)
- [Add feeds](#add-feeds)
- [Sign-in](#sign-in)
- [Article text and images](#article-text-and-images)
- [Backups and updates](#backups-and-updates)
- [Troubleshooting](#troubleshooting)

## The setup

FreshRSS runs in Docker on the application VM. SQLite and configuration stay on
local storage. Caddy supplies the HTTPS route, and Authentik provides sign-in
through the image's `mod_auth_openidc` integration.

Local DNS points the hostname at the proxy's LAN address. Remote access uses
Tailscale. Both paths retain the same HTTPS hostname and OIDC callback.

## Install

Requirements: Docker Engine, the Compose plugin, and curl. Download the
[Compose file](compose.yml) into a new directory outside this checkout:

```bash
mkdir -p "$HOME/homelab-examples"
mkdir "$HOME/homelab-examples/freshrss"
cd "$HOME/homelab-examples/freshrss"
curl --fail --location --output compose.yml \
  https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/apps/freshrss/compose.yml
```

The example uses SQLite, persistent Docker volumes, and a local-only web port.
It refreshes feeds every half hour; adjust `CRON_MIN` and `TZ` in `compose.yml`
for your own setup, then start it:

```bash
docker compose config --quiet
docker compose up -d
docker compose ps
```

Open <http://127.0.0.1:8080> and complete the wizard:

1. Check that the requirements pass and select SQLite.
2. Create your FreshRSS user with a password and choose form authentication.
3. Keep anonymous reading and registration disabled for a personal reader.

On a remote VM, use `ssh -L 8080:127.0.0.1:8080 operator@apps-01` to reach the
wizard from your browser. For regular access, configure a private HTTPS route
using the [networking notes](../../networking/README.md#caddy-and-authentik).
If Caddy runs on another host, bind the web port to the intended private
interface and allow that proxy through the firewall.

## Add feeds

Use **Subscription management** to add an RSS/Atom URL or import an OPML file
from another reader. Group feeds into categories, refresh them, and open a few
articles before importing the rest.

To refresh manually and check for errors:

```bash
docker compose exec --user www-data freshrss php ./app/actualize_script.php
docker compose logs --tail=50 freshrss
```

Export OPML from **Subscription management → Import / export** for a portable
copy of your subscriptions. It does not include saved articles or read/unread
state, which live in the database.

## Sign-in

The integration uses a confidential OAuth2/OIDC provider with `openid`, `email`,
and `profile` scopes. FreshRSS uses the authenticated username supplied by the web
server. Use the default Debian image on an architecture supported by its
[OIDC module](https://freshrss.github.io/FreshRSS/en/admins/16_OpenID-Connect.html).

Register exact callback URLs. In this setup, both the ordinary callback and its
explicit `:443` form were needed. For a documentation hostname, those would be
`https://rss.example.com/i/oidc/` and `https://rss.example.com:443/i/oidc/`.

Add `env_file: .env` under the `freshrss` service. Create that private file with
`chmod 600 .env` after saving the settings below:

| Variable | Value |
|---|---|
| `OIDC_ENABLED` | `1` |
| `OIDC_PROVIDER_METADATA_URL` | Discovery URL from the Authentik provider |
| `OIDC_CLIENT_ID` | Client ID from Authentik |
| `OIDC_CLIENT_SECRET` | Client secret from Authentik |
| `OIDC_CLIENT_CRYPTO_KEY` | Separate random value from `openssl rand -hex 32` |
| `OIDC_REMOTE_USER_CLAIM` | `preferred_username` |
| `OIDC_SCOPES` | `openid email profile` |
| `OIDC_X_FORWARDED_HEADERS` | `X-Forwarded-Host X-Forwarded-Proto X-Forwarded-Port` |

Have Caddy supply those forwarded headers with the original host, HTTPS scheme,
and port. Keep direct access to the backend restricted to the proxy.

The FreshRSS username must exactly match the chosen claim. For an existing
installation, confirm that match before changing **Administration → Authentication**
to **HTTP (for advanced users with HTTPS)** and recreating the container with
`docker compose up -d`. For a new OIDC installation, configure OIDC before the
wizard, then use the displayed `REMOTE_USER` as the initial username and select
HTTP authentication there.

Check logout and a fresh login through Caddy, then verify that anonymous requests
cannot read articles or cached images. Homarr links to the reader, but keeps its
own local login.

## Article text and images

Some feeds only provide summaries. I enable FreshRSS's full-content extraction
for selected feeds instead of applying it to every subscription. Selectors need
to match the publisher's page structure and occasionally need updating.

The custom Local Media Cache extension downloads article images during ingestion
and serves them behind the reader's authentication. Its cache has a size limit.
It uses FreshRSS's protected fetch path so private destinations and unsafe
redirects stay blocked. That extension is part of my private setup; the example
above runs standard FreshRSS. Leave `INTERNAL_HOST_ALLOWLIST` empty when fetching
public feeds.

## Backups and updates

Keep the SQLite database, application configuration, and custom extensions. Use
a consistent SQLite backup or stop the application while copying its database.
The article-image cache is disposable and separate from the reader's saved data.
Record the Authentik provider settings and keep its credentials outside Git.

For the Compose example above, this Bash block stops FreshRSS, archives both
volumes, and starts it again after a successful copy. Run it from the directory
containing `compose.yml`; it needs `tar` in the container, supplied by the image.

```bash
(
  set -eu
  umask 077
  backup=$(mktemp -d "$HOME/freshrss-backup.XXXXXX")
  docker compose stop freshrss
  docker compose run --rm -T --no-deps --entrypoint tar freshrss \
    -C /var/www/FreshRSS -czf - data extensions > "$backup/data.tar.gz"
  cp compose.yml "$backup/"
  if [ -f .env ]; then cp .env "$backup/"; fi
  docker compose start freshrss
  printf 'Backup saved to %s\n' "$backup"
)
```

If the copy fails, fix the error before starting FreshRSS again. Move the backup
off this host with your backup tool. The [Restic walkthrough](../../storage/restic/README.md)
shows the backup-and-restore cycle using disposable files.

To check a backup, copy the saved Compose file into a new directory. Use a new
Compose project and a different loopback port, keep OIDC disabled for the local
test, and restore into its empty volumes before startup:

```bash
read -r -p 'Path to the saved data.tar.gz: ' ARCHIVE
docker compose -p freshrss-restore run --rm -T --no-deps --entrypoint tar freshrss \
  -C /var/www/FreshRSS -xzf - < "$ARCHIVE"
docker compose -p freshrss-restore up -d
```

For a backup configured with HTTP authentication, use a separate test identity
provider or follow the upstream access-control instructions for the isolated
copy. Check subscriptions, saved articles, and read/unread state. Exported OPML
alone cannot verify those last two.

Before updating, make the backup, read the release notes, and change the image
tag and digest together. Then run:

```bash
docker compose pull
docker compose up -d
docker compose logs --tail=50 freshrss
```

Check login, feed refresh, article text, and images. `docker compose down` stops
the reader while keeping its volumes; adding `--volumes` deletes its saved data.

## Troubleshooting

| Symptom | First thing to check |
|---|---|
| Feeds only update manually | `CRON_MIN` is set and the container has been recreated after changes |
| Login succeeds but the user is unknown | FreshRSS username matches the OIDC identity claim |
| Redirect URI mismatch | Exact callback URL, `:443` variant, and forwarded headers |
| Full articles are empty | The publisher changed its page structure or blocks automated requests |
| Images disappear in the custom cache | Fetch failures, cache limits, and extension logs |

## Notes

With Python 3 and Compose 2.24.4 or newer, run this from the repository root to
check startup, create a test user, and restore a backup into a separate instance:

```bash
python3 scripts/check-service-examples.py --smoke freshrss
```

- [FreshRSS documentation](https://freshrss.github.io/FreshRSS/)
- [Official container setup](https://github.com/FreshRSS/FreshRSS/tree/edge/Docker)
- [Authentik integration](https://integrations.goauthentik.io/services/freshrss/)
- [Try a local reverse proxy](../../networking/caddy/README.md)
