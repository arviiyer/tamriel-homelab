# Syncthing

[Home](../../README.md) · [Apps](../README.md) · [Storage](../../storage/README.md)

Syncthing syncs my documents, pictures, and Obsidian notes. The lab copy lives on
TrueNAS, with configuration on the application VM. It replaced Nextcloud for
file synchronization.

## Install

Requirements: Docker Engine, Docker Compose, curl, and a second device running
[Syncthing](https://syncthing.net/downloads/). Prepare the Docker host with the
[Debian VM guide](../../proxmox/debian-vm/README.md) if needed.

Download [compose.yml](compose.yml) into a new working directory:

```bash
mkdir -p "$HOME/homelab-examples"
mkdir "$HOME/homelab-examples/syncthing"
cd "$HOME/homelab-examples/syncthing"
curl -fLO https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/apps/syncthing/compose.yml
```

The configuration and device identity stay in a Docker volume on this host.
For a NAS-backed file library, follow the [NFS guide](../../storage/nfs/README.md)
first, including the Docker mount dependency. Add this entry to Syncthing's
existing `volumes` list, keeping the configuration volume:

```yaml
      - type: bind
        source: /mnt/nas/sync
        target: /data/sync
        bind:
          create_host_path: false
```

Replace the source with your mounted share. For local storage, create a directory
on the VM and use its absolute path instead. The container runs as UID/GID 1000;
set `PUID` and `PGID` to the identity that owns your files if it differs.

Under `ports`, change the sync binding from `127.0.0.1:22000:22000/tcp` to your
server's LAN address, for example `192.0.2.83:22000:22000/tcp`. Allow the intended
devices to reach TCP 22000. For direct remote syncing, use a Tailscale binding
and a corresponding tailnet rule, or Syncthing's discovery and relay facilities.

Keep the management port on localhost for initial setup:

```bash
docker compose config --quiet
docker compose up -d
docker compose ps
curl --fail http://127.0.0.1:8384/rest/noauth/health
```

Open <http://127.0.0.1:8384>. On a remote VM, first run
`ssh -L 8384:127.0.0.1:8384 operator@apps-01` from your workstation. Set a GUI
username and password in **Actions → Settings → GUI**.

For a regular browser URL, add a [private Caddy route](../../networking/private-access/README.md#use-it-with-an-application).
Caddy reaches the GUI only; device synchronization uses its own connection.

## Connect devices and folders

1. Exchange device IDs using **Actions → Show ID**, then add and approve each
   device on the other side.
2. For a direct connection, set the server's address on the other device to
   `tcp://192.0.2.83:22000`, replacing the address. Use the Tailscale address
   instead when connecting through that interface.
3. Add a folder on the server at `/data/sync/test`. Share it with the other device
   and accept it into a new empty folder there.
4. Add a text file, check both sides become **Up to Date**, then edit it on the
   other device and confirm the change returns.
5. Add the folders you want to keep, such as `documents`, `pictures`, and
   `obsidian`, choosing the folder type and versioning settings for each.

Existing folders need their data moved and paths changed deliberately; adding a
Docker mount does not migrate them. Discovery and relays are enabled by default.
If you want direct-only connections, disable them in **Settings → Connections**
after checking the explicit device addresses work.

## Storage and backups

Sync propagates deletions too. Keep snapshots or backups independently of the
sync relationship, and back up configuration and device keys privately. When
restoring, avoid running two instances with the same device identity.

Use the [cold-copy steps](../utilities/README.md#cold-copies-updates-and-cleanup)
with service name `syncthing` for its configuration volume. Back up the shared
files separately with [Restic](../../storage/restic/README.md) or your NAS backup
tool. After restoring, check the device ID, folder paths, and a test file before
resuming synchronization.

## Troubleshooting

| Symptom | First thing to check |
|---|---|
| Devices stay disconnected | Approved device IDs, explicit TCP address, and the published sync port |
| Folder reports permission denied | Configured PUID/PGID write access on the mounted share |
| GUI works but files do not sync | Caddy reaches the GUI only; TCP 22000 needs its own connection path |
| Deletion appears on every device | Sync propagated it; recover from folder versioning or a separate snapshot |

## Updates

The image is pinned by digest and in-app upgrades are disabled. To update,
review the release notes, back up the volume, change the image reference, and
recreate the service:

```bash
docker compose pull
docker compose up -d
docker compose logs --tail=50 syncthing
```

Check device connections and folder status afterward. `docker compose down`
keeps the configuration volume; adding `--volumes` deletes its device identity.

## Try it on one computer

For a local trial, use the unmodified Compose file. It keeps files in the named
volume and binds both ports to localhost. Pair a host-installed Syncthing with
the container at `tcp://127.0.0.1:22000`, and use `/var/syncthing/example-files`
as the container's folder. Give the host-side app different GUI/listener ports
if they conflict, and let it initiate the connection. Exchange a disposable file
before setting up shared storage or remote access.

## Checks

With Python 3 and Compose 2.24.4 or newer, the
[service smoke test](../../scripts/check-service-examples.py) starts two temporary
peers, pairs them, transfers a text file, and verifies that the device identity
survives a restart. It cleans up its temporary project's containers and volumes.

```bash
python3 scripts/check-service-examples.py --smoke syncthing
```

[Syncthing documentation](https://docs.syncthing.net/) ·
[Firewall setup](https://docs.syncthing.net/users/firewall.html)
