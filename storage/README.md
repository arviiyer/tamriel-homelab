# Storage and backups

[Home](../README.md) · [Apps and services](../apps/README.md) ·
[Proxmox](../proxmox/README.md)

TrueNAS SCALE provides shared storage on the UGREEN NAS. Its four 4 TB hard
drives are arranged as two mirrored pairs. PBS and Restic are the backup tools.

## Where data lives

| Data | Location |
|---|---|
| Application databases | The VMs' own disks |
| Shared bulk files | TrueNAS and ZFS |

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

For an application, identify both its database and its files before choosing a
restore procedure. A restored archive needs application-level checks before
replacing live data. The
[recovery notes](../docs/case-studies/recovery-and-storage-dependencies.md)
walk through the public example's archive checks and separate restore destination.

## Try a restore

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

A missing network mount can leave an ordinary local directory where the share
should be. The [systemd example](../automation/recovery/README.md#storage-checks)
checks for the expected read-write mount and dataset marker before starting its
placeholder workload. Testing it with missing or incorrect mounts is on the
[roadmap](../ROADMAP.md#lab-and-automation).

## Notes

- [TrueNAS documentation](https://www.truenas.com/docs/scale/)
- [PBS administration guide](https://pbs.proxmox.com/docs/)
- [Restic documentation](https://restic.readthedocs.io/en/stable/)
