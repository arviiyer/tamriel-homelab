# Immich

[Home](../../README.md) · [Apps](../README.md) · [Storage](../../storage/README.md)

I use Immich for my photo library. The photos live on TrueNAS, while the database
and the rest of the application run on the application VM. Sign-in uses Authentik.

- [Install](#install)
- [Phone backups](#phone-backups)
- [Authentik sign-in](#authentik-sign-in)
- [Backups and restores](#backups-and-restores)
- [Updates](#updates)
- [Troubleshooting](#troubleshooting)

## The setup

| Component | Role |
|---|---|
| Immich server | Web interface, uploads, and background jobs |
| Machine-learning service | Photo search and recognition jobs |
| PostgreSQL with Immich's extensions | Library metadata |
| Redis | Application cache and job coordination |
| NAS library | Photo and video files |

The database stays on a local VM disk. The NAS mount must be ready before the
containers start. See [storage dependencies](../../storage/README.md#waiting-for-shared-storage).

## Install

Requirements: a Linux host with Docker Engine, the Compose plugin, Bash, curl,
and enough memory and disk for the [Immich requirements](https://docs.immich.app/install/requirements/).
Use a new directory outside this checkout. For a NAS-backed library, mount the
share before starting the containers.

Choose a release from [Immich releases](https://github.com/immich-app/immich/releases).
Download both files from that same release:

```bash
mkdir -p "$HOME/homelab-examples"
mkdir "$HOME/homelab-examples/immich"
cd "$HOME/homelab-examples/immich"
read -r -p 'Immich release tag (vX.Y.Z): ' IMMICH_RELEASE
curl --fail --location --output docker-compose.yml \
  "https://github.com/immich-app/immich/releases/download/${IMMICH_RELEASE}/docker-compose.yml"
curl --fail --location --output .env \
  "https://github.com/immich-app/immich/releases/download/${IMMICH_RELEASE}/example.env"
chmod 600 .env
```

Edit `.env` before starting:

| Setting | What to use |
|---|---|
| `IMMICH_VERSION` | The exact release tag used above |
| `UPLOAD_LOCATION` | `./library` for a local trial, or the mounted photo directory |
| `DB_DATA_LOCATION` | `./postgres` on a local disk, never the NAS share |
| `DB_PASSWORD` | A generated password, for example from `openssl rand -hex 24` |
| `TZ` | Your timezone |

Keep the supplied server, machine-learning, and database image definitions
together. The database image includes extensions that stock PostgreSQL lacks.
The upstream environment variables work with the upstream Compose file; the
lab's custom database connection URL is not needed for this installation.

For the local trial, change the server's published port in `docker-compose.yml`
to `"127.0.0.1:2283:2283"`. Then run:

```bash
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps
curl --fail http://127.0.0.1:2283/api/server/ping
```

Startup can take a few minutes. The ping endpoint should return a `pong` response.
Open <http://127.0.0.1:2283>, create the administrator account, and upload a test
photo. Check that its thumbnail loads and that you can download the original.
On a remote VM, an SSH tunnel lets you use the same local URL:

```bash
ssh -L 2283:127.0.0.1:2283 operator@apps-01
```

For access from other devices, configure the private HTTPS hostname before
setting up phone backups. A host-installed Caddy on the same machine can reach
the loopback port. A proxy on another machine needs a port bound to the intended
private interface and a firewall rule allowing that proxy. See
[networking](../../networking/README.md#caddy-and-authentik) and Immich's
[reverse-proxy requirements](https://docs.immich.app/administration/reverse-proxy/).

## Phone backups

1. Install the [Immich mobile app](https://immich.app/download) with a version
   compatible with your server.
2. Connect to your HTTPS hostname, for example `https://photos.example.com`.
3. Sign in and select a small test album in the backup settings.
4. Run a backup and check the uploaded photos in the web interface. Open an
   original, not just its thumbnail.
5. Choose the albums and background-upload behavior you want for regular use.

The lab's photo service is private. At home, DNS points at Caddy; away from home,
the phone needs Tailscale connected before it can reach the same hostname.
Background uploads also depend on the phone's battery and background-app settings.

## Authentik sign-in

Create an OAuth2/OIDC application and provider in Authentik. Use the provider's
discovery URL and client credentials in Immich's OAuth settings, with the scopes
and claims from the [Immich OAuth guide](https://docs.immich.app/administration/oauth/).

Register the web callback URLs for your HTTPS hostname and the mobile callback
listed in that guide. The phone app hands the result back from its browser, so a
working desktop login alone does not check the mobile flow.

Test a fresh browser login, a phone login, and a photo upload through Caddy.
When connecting an existing Immich account, follow the account-linking steps
before enabling automatic account creation.

## Backups and restores

Keep the database and library files together. A VM backup includes local data,
but the guest's NAS mount is outside that backup. See the
[backup layout](../../storage/README.md#backups).

For an application-level backup:

1. Stop uploads and background changes with `docker compose stop immich-server`.
   Leave the database running.
2. Make a database dump using the commands for your release in the
   [Immich backup guide](https://docs.immich.app/administration/backup-and-restore/).
3. Back up the successful dump, all of `UPLOAD_LOCATION`, any external libraries,
   and the Compose and environment files. Keep the environment file private.
4. After those copies finish, run `docker compose start immich-server` and check
   the ping endpoint again.

Copying a running PostgreSQL data directory is not a substitute for the dump.
Immich's automatic database dumps also need copying off the server, and contain
no photos or videos.

Try a restore on a separate instance with its own database and library copy.
Start with the backed-up release, preserve the container paths for external
libraries, and use that release's restore procedure. Check users, albums, older
photos, videos, and downloads before considering the restore complete.

## Updates

Read the release notes for every version you cross, especially database and
mobile-app changes. Take the backup above and retain the old Compose file and
image references. Review the new release's Compose file alongside the old one,
then update `IMMICH_VERSION` and any required service definitions.

```bash
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps
docker compose logs --tail=50 immich-server
```

Check sign-in, uploads, thumbnails, job queues, and existing photos. A database
migration can require restoring the matching backup as well as the old image.
The lab also collects Immich's application metrics in
[Grafana](../../monitoring/README.md#grafana).

## Troubleshooting

| Symptom | First thing to check |
|---|---|
| Database connection errors | Database health, matching credentials, and the supported database image |
| Missing library or failed writes | NAS mount availability and directory permissions before container startup |
| Upload works locally but fails through Caddy | Proxy upload/time-out settings and the server logs |
| Phone cannot connect away from home | Tailscale, hostname resolution, and the mobile OAuth callback |
| Machine-learning jobs fail | Available RAM and the machine-learning container logs |

[Immich installation](https://docs.immich.app/install/docker-compose/) ·
[Mobile backup](https://docs.immich.app/features/mobile-backup/)
