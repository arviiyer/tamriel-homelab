# TrueNAS shares and VM mounts

[Home](../../README.md) · [Storage](../README.md) · [Media](../../media/README.md)

TrueNAS holds the photos, synced files, downloads, and media. Application
databases stay on the VMs. My four NAS drives form two mirrored pairs.

## Create datasets and shares

Requirements: an installed TrueNAS SCALE system with a healthy pool, a Debian
client VM, and a routed connection between them. Pool creation erases the
selected disks; use the [TrueNAS storage guide](https://www.truenas.com/docs/scale/scaletutorials/storage/managepoolsscale/)
when preparing a new NAS.

In **Datasets**, create a separate dataset for each kind of data you want to
manage independently. A layout matching these guides is:

| Dataset | Client path | Use |
|---|---|---|
| `tank/photos` | `/mnt/nas/photos` | Immich library |
| `tank/sync` | `/mnt/nas/sync` | Syncthing folders |
| `tank/downloads` | `/mnt/nas/downloads` | Download clients |
| `tank/media` | `/mnt/nas/media` | Movies, TV, and music |
| `tank/backups` | `/mnt/pbs/backups` | PBS datastore on the backup VM |

Use the Generic dataset preset for ordinary Linux/NFS files. Create a NAS user
and group with the numeric UID/GID used by the writing containers, and grant
that identity the required dataset permissions. For the media example this is
the `PUID`/`PGID` in its `.env`. Ensure directory traversal is allowed on parent
datasets too.

Under **Shares → Unix Shares (NFS)**, add each dataset path and restrict it to the
specific client hosts that need it. Enable NFSv4 and the NFS service at boot.
The media VM needs only downloads and media. PBS needs only its datastore.

Ordinary application exports should retain root squashing. If using Maproot,
map client root to the intended unprivileged storage identity. PBS is different:
its dedicated export must allow datastore ownership to be initialized, as
described in the [PBS guide](../pbs/README.md).

## Mount from Debian

The addresses below are documentation examples. Replace `192.0.2.20` with your
NAS address and the dataset paths with your actual exports.

```bash
sudo apt install nfs-common curl
sudo mkdir -p /mnt/nas/downloads /mnt/nas/media
```

Add these entries to `/etc/fstab` on the media VM:

```fstab
192.0.2.20:/mnt/tank/downloads /mnt/nas/downloads nfs4 rw,hard,_netdev,nofail,x-systemd.automount,x-systemd.mount-timeout=90s 0 0
192.0.2.20:/mnt/tank/media /mnt/nas/media nfs4 rw,hard,_netdev,nofail,x-systemd.automount,x-systemd.mount-timeout=90s 0 0
```

`nofail` lets the OS boot without the NAS. Services that use the shares still
need the explicit dependency below. `hard` mounts retry interrupted NFS requests
rather than returning partial I/O to applications.

```bash
sudo systemctl daemon-reload
sudo systemctl start mnt-nas-downloads.automount mnt-nas-media.automount
ls /mnt/nas/downloads /mnt/nas/media
findmnt -t nfs,nfs4
```

As the user matching the container UID/GID, create, read, rename, and remove a
disposable file on each share. Do this without `sudo` to test the application's
permissions. Create the media guide's subdirectories using that same identity.

NFS permissions use numeric identities. A matching username on two machines is
not enough if its UID differs. Changing an export's Maproot also does not repair
the ownership of files already stored there.

## Wait for mounts

My app and media VMs sometimes start before the NAS. A small systemd service
waits for TCP 2049, then the shares mount and Docker starts:

`NAS listening → NFS mounts → Docker → containers`

Download the three files on the Docker VM:

```bash
mkdir -p "$HOME/homelab/nfs"
cd "$HOME/homelab/nfs"
(
  set -eu
  for file in nas-ready.service wait-for-nas.conf docker-mounts.conf; do
    curl -fLo "$file" \
      "https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/storage/nfs/$file"
  done
)
```

Set your NAS address in [nas-ready.service](nas-ready.service). It waits two
seconds between attempts, with no overall timeout. If the NAS is offline at boot,
the VM stays accessible and Docker waits.

The [mount drop-in](wait-for-nas.conf) makes each share wait for that service.
The [Docker drop-in](docker-mounts.conf) requires both mounts. Install them:

```bash
sudo install -m 644 nas-ready.service /etc/systemd/system/nas-ready.service
for share in downloads media; do
  sudo install -D -m 644 wait-for-nas.conf \
    "/etc/systemd/system/mnt-nas-${share}.mount.d/wait-for-nas.conf"
done
sudo install -D -m 644 docker-mounts.conf \
  /etc/systemd/system/docker.service.d/nfs-mounts.conf
sudo systemctl daemon-reload
```

For the app VM, use `photos` and `sync` in the loop and the matching paths in
`docker-mounts.conf`. For another path, get its unit name with
`systemd-escape --path --suffix=mount /mnt/nas/media`. The mount units start
`nas-ready.service` themselves, so it does not need `systemctl enable`.

Reboot the VM when ready to restart its services, then check:

```bash
systemctl status nas-ready.service docker.service
findmnt -t nfs,nfs4 -o SOURCE,TARGET,OPTIONS
docker ps
```

Keep an `/etc/fstab` entry for every path in the Docker drop-in. Without one,
Docker can use the local directory instead. It will also start with the wrong
export if that export mounts successfully. Check `SOURCE` against the intended
NAS and dataset before starting apps.

## If storage does not come up

```bash
systemctl list-jobs
sudo journalctl -b -u nas-ready.service -u mnt-nas-downloads.mount -u mnt-nas-media.mount
```

| What you see | What to check |
|---|---|
| `nas-ready` stays activating | NAS power, NFS service, and TCP 2049 between the VM and NAS |
| Mount fails after the listener is ready | Export path, allowed client address, and the mount journal |
| Files are missing or the source is wrong | Stop the apps and check the export in `/etc/fstab` |

After fixing a failed mount, retry it and start Docker:

```bash
sudo systemctl daemon-reload
sudo systemctl reset-failed mnt-nas-downloads.mount mnt-nas-media.mount docker.service
sudo systemctl start mnt-nas-downloads.mount mnt-nas-media.mount
findmnt -t nfs,nfs4 -o SOURCE,TARGET,OPTIONS
sudo systemctl start docker.service
```

If an incorrect share is already mounted, stop the stacks, then
`docker.service` and `docker.socket`. Stop the share's `.mount` and `.automount`
units, correct `/etc/fstab`, and use the retry commands above. Run
`docker compose up -d` in each stack directory if its containers were stopped
manually.

## Snapshots and file recovery

In TrueNAS **Data Protection → Periodic Snapshot Tasks**, select a dataset and
choose its schedule and retention. I keep daily snapshots for the file-sync and
photo datasets. Check the next run and snapshot list after creating a task.

To recover a file, select the snapshot and clone it into a new dataset. Share the
clone temporarily to the intended client, copy the required file back, and remove
the temporary share/clone after checking it. This avoids rolling back unrelated
changes to the whole live dataset.

Snapshots share the pool's failure boundary. Configure replication or another
off-host backup for files that need to survive losing the NAS. Keep pool scrubs
and disk-health checks enabled and review their results.

## Notes

- Separate datasets/exports prevent cross-share hardlinks, even if their paths
  are next to each other inside the container.
- A VM backup excludes guest-mounted NFS files. Back up the application database
  and shared library as complementary parts of the restore.

[TrueNAS NFS guide](https://www.truenas.com/docs/scale/scaletutorials/shares/addingnfsshares/)
