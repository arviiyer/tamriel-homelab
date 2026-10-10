# Proxmox Backup Server

[Home](../../README.md) · [Storage](../README.md) · [Proxmox](../../proxmox/README.md)

PBS backs up my service VMs. It runs in a separate VM and stores backups on a
dedicated TrueNAS export. That covers a lost VM disk; the NAS remains a shared
dependency for both bulk files and these backups.

## Prepare the backup server

Requirements: a PBS installation, a persistent datastore with enough capacity,
and connectivity from the Proxmox nodes to PBS on TCP 8007. Use the
[PBS installer and requirements](https://pbs.proxmox.com/docs/installation.html)
for a fresh system. Give it a stable address and configure its supported package
repository, timezone, and updates.

For a NAS-backed datastore:

1. Create a dedicated backup dataset and NFS export using the
   [storage guide](../nfs/README.md).
2. Restrict that export to the backup VM. PBS must be able to set its datastore
   ownership. My dedicated export maps client root to root; ordinary application
   exports use unprivileged mappings.
3. Install `nfs-common`, create `/mnt/pbs/backups`, and add an NFS mount for that
   path to `/etc/fstab`. Mount it before creating the datastore.
4. Check `findmnt -T /mnt/pbs/backups` and write access. In the PBS UI, open
   **Datastore → Add Datastore**, name it `vm-backups`, and use that directory.

PBS initializes the datastore's directory structure. Keep it dedicated to PBS
and let PBS manage its contents. NFS metadata performance affects verification
and garbage collection, so watch those task durations as the datastore grows.

Add the mount dependency to `proxmox-backup-proxy.service` with
`sudo systemctl edit proxmox-backup-proxy.service`:

```ini
[Unit]
RequiresMountsFor=/mnt/pbs/backups
```

Run `sudo systemctl daemon-reload` and restart the proxy during a quiet period.
Confirm the mount and datastore before the next backup job. Schedule maintenance
tasks after the NAS is available too.

## Connect Proxmox VE

1. In PBS **Configuration → Access Control**, create a dedicated user such as
   `pve-backup@pbs`, then a privilege-separated API token named `pve`.
2. On `/datastore/vm-backups`, grant both the user and its token the
   `DatastoreBackup` role with propagation. Token privileges cannot exceed the
   parent user's privileges.
3. Copy the PBS certificate fingerprint from its dashboard. Store the token's
   one-time secret in your password manager.
4. In Proxmox VE **Datacenter → Storage → Add → Proxmox Backup Server**, set the
   PBS address, datastore `vm-backups`, username `pve-backup@pbs!pve`, token secret,
   and the fingerprint verified from PBS. Select the nodes allowed to use it.

Open the new storage entry. The datastore should list successfully. A 403 usually
means one of the two ACLs is missing; a TLS error calls for checking the server
address and fingerprint.

## Make the first backup

On a small VM, choose **Backup → Backup now**, select PBS storage and snapshot
mode, and run the task. Check the task output and the resulting backup in PBS.
The guest agent can freeze supported filesystems during the snapshot. Applications
with additional consistency requirements should also use their database backups.

In **Datacenter → Backup**, add scheduled jobs for the intended VMs. Review every
disk's **Backup** option. My service-VM jobs generally run daily, with less frequent
jobs for supporting machines. I stagger them rather than starting everything
at the same time.

In PBS, configure datastore pruning, garbage collection, and verification jobs:

- **Pruning** removes backup snapshots beyond the selected retention. A starting
  policy is seven daily and four weekly recovery points.
- **Garbage collection** reclaims unreferenced chunks later. Pruning does not
  immediately return that space.
- **Verification** checks stored chunks. Review failed tasks and notifications.

Keep datastore retention on PBS when using the restricted backup token above.
If configuring pruning from Proxmox VE instead, review the additional permissions
required by that operation.

## Try a restore

In Proxmox, open the VM's **Backup** tab and select the PBS storage. Check the
latest task result and the disks included in the backup, then:

1. Select a completed backup and choose **Restore**.
2. Choose a new, unused VM ID and storage with enough free space. Leave automatic
   startup disabled.
3. Before the first boot, disconnect its network interfaces or attach them to an
   isolated test network. The restored guest contains the original hostname,
   network settings, service credentials, and scheduled jobs.
4. Boot from the console. Check the OS, local disks, and application data. For
   services that need NAS files, supply a copied test dataset on the isolated
   network before starting them.
5. Check the application itself: sign in, open older data, and try a small write.
   Keep the original VM running separately while evaluating the restored copy.

For one file, use Proxmox's **File Restore** action instead of restoring the whole
VM. An extracted database directory still needs the application's consistency
and restore checks.

## What to keep elsewhere

Guest-mounted NFS files are outside VM disk backups. PBS configuration, credentials,
and any client-side encryption key also need a separate private backup. A backup
of the PBS VM is useful for rebuilding the server, but does not include its
guest-mounted datastore.

My datastore shares the NAS with the library files. A second PBS server or an
off-host copy is needed for a separate storage failure boundary. Check your
oldest and newest retained backups after changing retention or upgrading PBS.

[PBS storage documentation](https://pbs.proxmox.com/docs/storage.html) ·
[Proxmox VE backup documentation](https://pve.proxmox.com/pve-docs/chapter-vzdump.html)
