# Syncthing

[Home](../../README.md) · [Apps](../README.md) · [Storage](../../storage/README.md)

Syncthing syncs my documents, pictures, and Obsidian notes. The lab copy lives on
TrueNAS, with configuration on the application VM. It replaced Nextcloud for
file synchronization.

## Try it locally

This example uses a Docker volume and binds the management and TCP sync ports to
localhost. Use explicit device addresses for this local trial. Syncthing's normal
outbound discovery and relay behavior is available on the project network; those
options can be disabled in Settings when using only direct connections.

Requirements: Docker Engine and Docker Compose. From the repository root:

```bash
docker compose -p syncthing-example -f apps/syncthing/compose.yml config --quiet
docker compose -p syncthing-example -f apps/syncthing/compose.yml up -d
curl --fail http://127.0.0.1:8384/rest/noauth/health
```

Open <http://127.0.0.1:8384>. Set a GUI username and password in Settings before
adapting access for other devices. The Docker image prepares the volume and then
runs Syncthing as UID/GID 1000.

To pair with Syncthing running directly on the same computer:

1. Exchange device IDs and approve the device on each side.
2. In the host-side app, set this container's address to `tcp://127.0.0.1:22000`.
3. Leave the host-side app initiating the connection to the container. Its own
   GUI and listener must use different ports if they conflict with the example.
4. Create a test folder in the container under `/var/syncthing/example-files`,
   share it with the host-side device, and accept it into a new empty host folder.
5. Add a disposable text file and check that both sides become Up to Date.

For LAN or Tailscale use, choose the intended host interface for the sync port,
allow it through the firewall, and configure a reachable device address. Keep
GUI access private. The lab's Caddy route is for the GUI, not the sync protocol.

## Storage and backups

The example keeps configuration, device keys, and files in its named volume.
The lab instead mounts the NAS file share separately and makes Docker wait for
that mount. See [storage startup ordering](../../storage/README.md#waiting-for-shared-storage).

Sync propagates deletions too. Keep snapshots or backups independently of the
sync relationship, and back up configuration and device keys privately. When
restoring, avoid running two instances with the same device identity.

## Updates and cleanup

The image is pinned by digest and in-app upgrades are disabled. To update,
review the release notes, back up the volume, change the image reference, and
recreate the service. Check device connections and folder status afterward.

Stop the example while keeping its volume:

```bash
docker compose -p syncthing-example -f apps/syncthing/compose.yml down
```

Add `--volumes` only when discarding the example's files and identity.

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
