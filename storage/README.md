# Storage and backups

[Home](../README.md) · [Apps and services](../apps/README.md) ·
[Proxmox](../proxmox/README.md)

TrueNAS SCALE provides shared storage on the UGREEN NAS. Its four 4 TB hard
drives are arranged as two mirrored pairs. PBS and Restic are the backup tools.

[![TrueNAS storage layout and health](../evidence/screenshots/truenas-storage.webp)](../evidence/screenshots/README.md#truenas-storage)

## Where data lives

| Data | Location |
|---|---|
| Immich PostgreSQL, Forgejo PostgreSQL, Authentik PostgreSQL | Local VM disks |
| FreshRSS SQLite, Homarr appdata, reading-brief SQLite | Local application VM disk |
| Jellyfin and Servarr configuration/databases | Local media VM disk |
| Immich photo library | NAS share |
| Syncthing documents, pictures, and notes | NAS share |
| Media library and downloads | Separate NAS shares |
| PBS datastore | Dedicated NAS share mounted by the backup VM |
| Vaultwarden data | Local Pi storage, with Restic copies |

I keep databases on VM-local disks so a shared-storage outage does not also
take away their database files. Services can still depend on shared files,
and local and shared data need separate backups. This arrangement does not
provide automatic database failover.

ZFS supplies snapshots and integrity checks for the shared files. See the
[hardware list](../README.md#storage) for the NAS specifications.

## Backups

The lab uses Proxmox Backup Server and Restic, with VM snapshots and off-host
copies for selected data. These tools address different layers:

- **PBS:** VM backup and restore.
- **Restic:** File backup and restore.
- **Snapshots:** Recovery points on the storage that holds the data.

PBS backs up the service VMs' disks, including their local databases and
configuration. Guest-mounted NFS files are outside those VM disk backups. The
datastore is itself on the NAS, so a PBS backup there shares the NAS's failure
boundary. It is not an off-site copy.

[![A completed PBS backup task](../evidence/screenshots/pbs-backup.webp)](../evidence/screenshots/README.md#pbs-backup)

ZFS snapshots cover selected file and photo datasets. Vaultwarden has a local
Restic repository and a copy on another host, with repository checks. Keeping
another copy on the same device would not cover losing that device.

[![Finished periodic snapshot tasks in TrueNAS](../evidence/screenshots/truenas-snapshots.webp)](../evidence/screenshots/README.md#truenas-snapshots)

| Application | What needs to be recoverable together |
|---|---|
| Immich | Database, library files, configuration, and matching application version |
| Syncthing | Synced files plus configuration and device identity; sync alone is not a backup |
| Forgejo | Database, repositories, application data, and encryption/signing keys |
| Authentik | Database, configuration, and existing secret key |
| FreshRSS | Consistent SQLite backup, configuration, and custom extensions |
| Homarr | Appdata and the existing encryption key |
| Jellyfin and Servarr | Configuration/databases, matching images, and the separately stored library |
| Vaultwarden | Consistent database, attachments and other vault data, configuration, and backup credentials |

Keep credentials and encryption keys in the private backup process. An image
rollback after a schema migration may also need the matching database backup.

For an application, identify both its database and its files before choosing a
restore procedure. A restored archive needs application-level checks before
replacing live data. The
[recovery notes](../docs/case-studies/recovery-and-storage-dependencies.md)
walk through the public example's archive checks and separate restore destination.

## Try a restore

### Restic files

The [Restic walkthrough](restic/README.md) creates a repository, backs up example
files, changes a note, and restores the earlier version into a new directory.
It is a small way to try the tool before choosing real backup sources.

### A VM from PBS

In Proxmox, open the VM's **Backup** tab and select the PBS storage. Check the
latest task result and the disks included in that backup. Guest-mounted NAS
files still need their separate backup.

To rehearse a restore:

1. Select a completed backup and choose **Restore**.
2. Choose a new, unused VM ID and storage with enough free space. Leave automatic
   startup disabled.
3. Before the first boot, disconnect its network interfaces or attach them to an
   isolated test network. The restored guest contains the original hostname,
   network settings, service credentials, and scheduled jobs.
4. Boot from the console. Check the OS, local disks, and application data. For
   services that need shared files, supply a copied test dataset on the isolated
   network before starting them.
5. Check the application itself: sign in, open saved data, and try a small write.
   Keep the original VM running separately while evaluating the restored copy.

For a single file, use Proxmox's **File Restore** action on the backup instead of
restoring the whole VM. A database directory extracted this way still needs the
application's consistency and restore checks.

### Archive checks

The included drill generates an archive, restores it to a new directory, checks
the contents, and exercises corrupt and unsafe input. It cleans up its temporary
files afterward.

On Linux with Python 3, procfs, and `renameat2` support, run from the repository
root:

```bash
python3 automation/recovery/tests/run_isolated_restore_drill.py
```

[Restore tool and archive format](../automation/recovery/README.md) ·
[Recorded synthetic restore exercise](../evidence/drills/2026-08-24-isolated-synthetic-restore.md)

## Waiting for shared storage

The application and media hosts wait for NFS availability before mounting their
shares. Docker then requires the relevant mounts before starting. That ordering
addresses the race where a VM boots before the NAS is ready.

A missing network mount can leave an ordinary local directory where the share
should be. The [systemd example](../automation/recovery/README.md#storage-checks)
checks for the expected read-write mount and dataset marker before starting its
placeholder workload. Testing it with missing or incorrect mounts is on the
[roadmap](../ROADMAP.md#lab-and-automation).

## Notes

- [TrueNAS documentation](https://www.truenas.com/docs/scale/)
- [PBS administration guide](https://pbs.proxmox.com/docs/)
- [Restic documentation](https://restic.readthedocs.io/en/stable/)
