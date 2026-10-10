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
sudo apt install nfs-common
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

On a VM dedicated to these stacks, make Docker require its shared storage:

```bash
sudo systemctl edit docker.service
```

Enter:

```ini
[Unit]
RequiresMountsFor=/mnt/nas/downloads /mnt/nas/media
After=network-online.target
Wants=network-online.target
```

Save and run `sudo systemctl daemon-reload`. Apply this during a maintenance
window by stopping the Compose stacks, then restarting Docker and starting the
stacks again. Use only this VM's actual NAS paths in the drop-in.

Check `systemctl show docker -p RequiresMountsFor`, `findmnt`, and application
access after a reboot. If the NAS arrives after a mount timeout, restore NFS
connectivity, start the mount units, and then start Docker and the stacks.

My lab additionally waits for the NAS's NFS listener before trying the mounts.
For a service-specific check of the expected filesystem and a marker file,
see the [storage-check example](../../automation/recovery/README.md#storage-checks).

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
- Avoid starting an app against an empty local mount directory. The media Compose
  file rejects missing bind paths, but only the mount dependency establishes NFS.

[TrueNAS NFS guide](https://www.truenas.com/docs/scale/scaletutorials/shares/addingnfsshares/)
