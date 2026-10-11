# Requests and downloads

[Home](../../README.md) · [Media](../README.md) · [Jellyfin](../jellyfin/README.md)

Seerr sends requests to Sonarr and Radarr. Prowlarr supplies their indexers, and
qBittorrent or NZBGet downloads the files. The managers import completed files
into the library Jellyfin reads.

I run the download clients and managers through Gluetun with Mullvad WireGuard.
Seerr and Jellyfin use the ordinary application network. Mullvad has no port
forwarding, so this setup has no incoming torrent-port mapping.

- [Prepare storage](#prepare-storage)
- [Start the stack](#start-the-stack)
- [Connect the applications](#connect-the-applications)
- [Check the whole path](#check-the-whole-path)
- [Updates and backups](#updates-and-backups)
- [Troubleshooting](#troubleshooting)

## Prepare storage

Requirements: a Linux Docker Engine host, Compose v2, Bash, curl, a working
`/dev/net/tun`, and a Mullvad WireGuard configuration. Start with a Debian VM
using the [VM guide](../../proxmox/debian-vm/README.md). For shared storage, follow
the [NFS guide](../../storage/nfs/README.md) first.

Download the two files into a new directory on a local VM disk:

```bash
mkdir -p "$HOME/homelab-examples"
mkdir "$HOME/homelab-examples/servarr"
cd "$HOME/homelab-examples/servarr"
curl -fLO https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/media/servarr/compose.yml
curl -fLO https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/media/servarr/environment.example
cp environment.example .env
chmod 600 .env
id
```

Set `PUID` and `PGID` to the account that owns the download and media directories.
Set `DOWNLOADS_PATH=/mnt/nas/downloads` and `MEDIA_PATH=/mnt/nas/media` to match
the [NFS guide](../../storage/nfs/README.md). Set `MEDIA_BIND_IP` to the media VM's
private address, shown as `192.0.2.84` throughout these guides. Jellyfin uses the
same address and library. For a local trial, use local directories and
`MEDIA_BIND_IP=127.0.0.1`.

The directory layout inside the containers is:

```text
/data/downloads/
  torrents/incomplete/
  torrents/complete/
  usenet/intermediate/
  usenet/complete/
/data/media/
  movies/
  tv/
  music/
```

Create those subdirectories on the selected storage as the owning user. Keep
`config/` on the VM, since the applications store SQLite databases there.

```bash
mkdir -p config/{qbittorrent,sonarr,radarr,prowlarr,lidarr,nzbget,seerr}
sudo chown 1000:1000 config/seerr
```

Seerr's official image uses UID/GID 1000 independently of the LinuxServer images'
`PUID` setting. Check permissions from inside an application after startup.

My downloads and library are separate NFS exports. Imports copy files across
them, and a seeding torrent keeps its download copy. The example preserves that
layout. If you want hardlinks, use a single filesystem and a single `/data`
mount in the managers and download clients; see the
[Servarr storage guide](https://wiki.servarr.com/docker-guide).

## Start the stack

In Mullvad, generate a WireGuard configuration. Copy its private key and
interface address into `.env`, and set `SERVER_COUNTRIES` to the country you
selected. The address belongs to the generated key; it is not the VM address.
For another provider, change the Gluetun environment according to its
[provider guide](https://github.com/qdm12/gluetun-wiki/tree/main/setup/providers).

```bash
test -c /dev/net/tun
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps
docker compose logs --tail=50 gluetun
```

Gluetun must become healthy before its dependents start. Its built-in firewall
blocks their ordinary internet route when the tunnel is unavailable. Keep that
firewall enabled.

The ports bind to `MEDIA_BIND_IP`. Permit the Pi proxy to the web ports you use;
restrict other network clients at the router and Docker host, as described in
the [access guide](../../networking/private-access/README.md#the-setup).
For initial setup, open an SSH tunnel from your workstation:

```bash
ssh -N -L 8180:192.0.2.84:8180 -L 8989:192.0.2.84:8989 \
  -L 7878:192.0.2.84:7878 -L 9696:192.0.2.84:9696 \
  -L 5055:192.0.2.84:5055 operator@media-01
```

| Application | Browser address | Address for another container |
|---|---|---|
| qBittorrent | `http://localhost:8180` | `http://gluetun:8080` |
| Sonarr | `http://localhost:8989` | `http://gluetun:8989` |
| Radarr | `http://localhost:7878` | `http://gluetun:7878` |
| Prowlarr | `http://localhost:9696` | `http://gluetun:9696` |
| Seerr | `http://localhost:5055` | `http://seerr:5055` |

The VPN applications share one network namespace. Between them, use
`localhost` with the application's internal port. Seerr uses `gluetun` instead.
Host port 8180 maps to qBittorrent's internal port 8080.

For daily use, add the [media HTTPS routes](../../networking/private-access/README.md#media-routes)
to Caddy on the Pi.

## Connect the applications

### qBittorrent

1. Read the temporary password with `docker compose logs qbittorrent`. Sign in
   as `admin` and immediately set your own username and password.
2. In **Settings → Downloads**, set the save path to
   `/data/downloads/torrents/complete` and incomplete path to
   `/data/downloads/torrents/incomplete`.
3. In **Advanced**, select the VPN interface shown by
   `docker compose exec gluetun ip link` (normally `tun0`). Leave the optional
   address binding at all addresses on that interface.
4. Keep WebUI authentication enabled, including for localhost clients. The
   managers will receive their own saved client credentials.

### Sonarr and Radarr

1. Configure authentication during first setup.
2. Add `/data/media/tv` as Sonarr's root folder and `/data/media/movies` as Radarr's.
3. Under **Download Clients**, add qBittorrent at `localhost`, port `8080`, with
   its credentials. Use separate categories, such as `tv` and `movies`.
4. Use **Test**, then **Save**. Keep completed-download handling enabled.

Both managers see the same download paths returned by qBittorrent. No remote
path mapping is needed for this layout.

### Prowlarr

Add your indexers and test each one. Under **Settings → Apps**, add Sonarr and
Radarr using `http://localhost:8989` and `http://localhost:7878`. Set Prowlarr's
server URL to `http://localhost:9696`. Copy each manager's API key from
**Settings → General** into the corresponding application entry.

Use **Test** and **Sync App Indexers**, then check the indexer list in each manager.
Keep API keys in the applications' private configuration.

### Jellyfin and Seerr

First complete the [Jellyfin guide](../jellyfin/README.md), mapping this library
into its read-only `/media` mount. Create Movies and TV libraries.

In Seerr's wizard, select Jellyfin and enter `http://192.0.2.84:8096`.
`localhost` inside Seerr points back to Seerr itself. Set the external Jellyfin
URL to `https://media.example.com`, sign in, and sync the libraries. Both
Compose projects run on the media VM. From the Servarr directory, check:

```bash
docker compose exec seerr wget -qO- http://192.0.2.84:8096/health
```

Add Radarr at `http://gluetun:7878` and Sonarr at `http://gluetun:8989`, using their
API keys. Fetch their profiles and root folders, choose a profile and root for
each, and mark the intended default servers. Start with requests requiring
approval while checking the integration.

### Music, Usenet, and indexer helpers

These optional services are included as Compose profiles:

```bash
docker compose --profile music --profile usenet --profile indexer-helper up -d
```

- **Lidarr:** port 8686, root `/data/media/music`. Connect Prowlarr and qBittorrent
  as above, with a `music` category.
- **NZBGet:** port 6789. Change its initial credentials, add your Usenet provider,
  and set `MainDir=/data/downloads/usenet`, `DestDir=${MainDir}/complete`, and
  `InterDir=${MainDir}/intermediate` in its UI. Add it to the managers at
  `localhost:6789`, with separate categories. Downloads and imports need the
  same NAS readiness checks as torrents.
- **FlareSolverr:** add an indexer proxy in Prowlarr at `http://localhost:8191`,
  tag it, and apply that tag only to indexers that need it. It has no published
  host port. Core dumps are disabled and logs are bounded: browser dumps once
  consumed several gigabytes on my media VM.

Include the selected `--profile` arguments on later update and shutdown commands.
Readarr remains in the lab inventory, but its upstream project is
[retired](https://github.com/Readarr/Readarr#announcement-retirement-of-readarr).

## Check the whole path

1. From a VPN application, check the outbound IP:
   `docker compose exec qbittorrent curl -fsS https://am.i.mullvad.net/ip`.
   Compare it with the VM's non-VPN route and the selected provider exit.
2. In qBittorrent, add an official Linux-distribution torrent. Confirm the
   download progresses and the completed file appears at the expected path.
3. Test each manager's download client and Prowlarr application connection.
4. Import a media file you own through a manager's manual import. Check the
   destination, ownership, and Jellyfin library scan and playback.
5. Make and approve a Seerr request.
   Confirm it appears in the intended manager with the selected profile/root.

Gluetun's health check tests the VPN. Application HTTP checks test the individual
apps. Keeping those separate avoids a shared VPN/DNS problem causing a restart
storm across every service.

## Updates and backups

Stop the stack and back up `config/`, `compose.yml`, and the private `.env`
together. Downloads and the library have their own storage backup policy.
Keep the old image references with the matching databases before an upgrade.

Review release notes and replace the selected image digests, then run:

```bash
docker compose config --quiet
docker compose pull
docker compose up -d
docker compose ps
```

When Gluetun is replaced, recreate its dependents in the same operation so they
join the new namespace. For a small stack, `docker compose down` followed by
`docker compose up -d` is a straightforward maintenance window; bind-mounted
configuration survives. Repeat the connection checks afterward.

Restore a backup into a separate directory and use different browser ports.
Disconnect download clients and indexers in the restored copy before enabling
normal automation. Verify saved settings, request history, and library paths.

## Troubleshooting

| Symptom | First thing to check |
|---|---|
| Gluetun unhealthy | Matching WireGuard key/address, country, provider availability, and `/dev/net/tun` |
| Seerr cannot reach Radarr | Use `gluetun:7878`, not Seerr's localhost; check `FIREWALL_INPUT_PORTS` |
| Manager cannot import | Identical `/data/downloads` paths, mounted storage, and numeric ownership |
| Imports consume double the space | Separate exports require copies; torrents retain their seeding copy |
| Apps fail after a VPN update | Recreate the containers sharing Gluetun's old namespace |
| Mount disappears after reboot | [NFS readiness and Docker ordering](../../storage/nfs/README.md#wait-for-mounts) |

[Compose file](compose.yml) · [Environment template](environment.example) ·
[Gluetun documentation](https://github.com/qdm12/gluetun-wiki) ·
[Servarr documentation](https://wiki.servarr.com/)

## Checks

From the repository root, with Python 3 and Compose 2.24.4 or newer:

```bash
python3 scripts/check-stack-examples.py --validate
python3 scripts/check-stack-examples.py --smoke media
```

The smoke test checks startup, library permissions, and Seerr's connections to
the managers and a separate Jellyfin project. It substitutes a local namespace
for the VPN; check the real tunnel using your provider configuration above.
