# File backups with Restic

[Home](../../README.md) · [Storage](../README.md)

I use Restic for Vaultwarden backups on the Pi, with a copy on another host.
It keeps encrypted snapshots of files and lets me restore an older copy without
overwriting the working application.

- [Set up a repository](#set-up-a-repository)
- [Back up application files](#back-up-application-files)
- [Restore and check](#restore-and-check)
- [Keep a copy on another host](#keep-a-copy-on-another-host)
- [Retention and maintenance](#retention-and-maintenance)
- [Try it with disposable files](#try-it-with-disposable-files)

## Requirements

Install [Restic](https://restic.readthedocs.io/en/stable/020_installation.html)
and OpenSSL on the backup host; on Debian, use `sudo apt install restic openssl`.
The commands use Bash. The account running Restic needs read access to the source
files and write access to the backup destination.

## Set up a repository

Choose a new repository directory. This starts with a local copy; the off-host
step below adds protection against losing this machine.

```bash
umask 077
mkdir -p "$HOME/.config/restic" "$HOME/backups"
export RESTIC_REPOSITORY="$HOME/backups/app-data"
export RESTIC_PASSWORD_FILE="$HOME/.config/restic/app-data.password"
(
  set -euC
  openssl rand -hex 32 > "$RESTIC_PASSWORD_FILE"
)
restic init
```

Save the password in your password manager too. Losing it means losing access
to the repository. On subsequent shell sessions, set the same two environment
variables; initialize a repository only once.

## Back up application files

For Vaultwarden, first make a consistent copy using the
[application's backup steps](../../apps/utilities/README.md#vaultwarden). For
other apps, follow their own backup procedure: stop SQLite writers or use a
supported backup command, and dump PostgreSQL before copying its data.

Select the directory containing the completed archive, Compose file, and private
configuration. Keep that source directory stable between runs:

```bash
read -r -p 'Absolute directory containing the completed application backup: ' BACKUP_SOURCE
test -d "$BACKUP_SOURCE"
restic backup "$BACKUP_SOURCE" --tag app-data
restic snapshots --tag app-data
```

Check that `backup` exits successfully and inspect the new snapshot with
`restic ls SNAPSHOT_ID`. An unreadable source file can produce an incomplete
snapshot, so a listed snapshot alone is not enough. Keep the source separate
from the Restic repository to avoid backing up the backup itself.

For scheduled backups, run the application's consistent-copy step before Restic,
stop the job if either command fails, and retain a timestamp of the last complete
run. Restic's [automation notes](https://restic.readthedocs.io/en/stable/040_backup.html#environment-variables)
cover supplying credentials to an unattended job.

## Restore and check

Choose a specific snapshot from the list, then restore to a fresh directory:

```bash
read -r -p 'Snapshot ID to restore: ' SNAPSHOT_ID
RESTORE_DIR=$(mktemp -d "$HOME/restic-restore.XXXXXX")
restic restore "$SNAPSHOT_ID" --target "$RESTORE_DIR"
printf 'Restored files: %s\n' "$RESTORE_DIR"
restic check --read-data
```

Absolute source paths are recreated underneath `RESTORE_DIR`. Check the files
there, then use the app's restore steps on an isolated instance. For Vaultwarden,
check login, an older vault entry, attachments, and client sync. A repository
check verifies stored data; opening the restored application checks whether its
database and files work together.

## Keep a copy on another host

Prepare a destination account with SFTP access and a writable backup directory.
Verify its SSH host key and key-based login first. Replace the hostname, account,
and path below with your destination; the password file belongs to this second
Restic repository:

```bash
OFFHOST_REPOSITORY='sftp:backup@backup-01:/srv/backups/app-data'
OFFHOST_PASSWORD_FILE="$HOME/.config/restic/app-data-offhost.password"
(
  set -euC
  umask 077
  openssl rand -hex 32 > "$OFFHOST_PASSWORD_FILE"
)
restic -r "$OFFHOST_REPOSITORY" --password-file "$OFFHOST_PASSWORD_FILE" init
restic -r "$OFFHOST_REPOSITORY" --password-file "$OFFHOST_PASSWORD_FILE" copy \
  --from-repo "$RESTIC_REPOSITORY" --from-password-file "$RESTIC_PASSWORD_FILE"
restic -r "$OFFHOST_REPOSITORY" --password-file "$OFFHOST_PASSWORD_FILE" snapshots
restic -r "$OFFHOST_REPOSITORY" --password-file "$OFFHOST_PASSWORD_FILE" check --read-data
```

Save the second password separately too. On later runs, repeat `copy`, not
`init`; it skips snapshots already copied. Test a restore directly from this
repository using the same `-r` and `--password-file` arguments. My second copy
is on another lab host, so it covers losing the Pi rather than losing the site.

## Retention and maintenance

Choose retention for each repository independently. Preview a policy before
deleting anything:

```bash
restic forget --tag app-data --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --dry-run
```

Review the snapshot IDs to keep and remove. When satisfied, run it without
`--dry-run`, then run `restic prune` to reclaim space. The off-host repository has
its own retention; copying snapshots does not mirror local deletions. If archive
directories change each run, review Restic's default host/path grouping before
choosing a retention policy.

After upgrading Restic, check its version, run a backup and repository check, and
restore a small file. Monitor free space at both destinations.

| Symptom | First thing to check |
|---|---|
| Wrong password or no key found | Password file belongs to the selected repository |
| Backup exits with unreadable files | Source ownership and whether the application copy completed |
| SFTP connection fails | Host key, SSH identity, remote path, and write permission |
| Restored files seem absent | Original absolute path underneath the restore directory |
| Space stays occupied after forgetting snapshots | Prune has completed on that repository |

## Try it with disposable files

Use a fresh Bash shell for this exercise, with Restic, OpenSSL, and `diff`.
Everything goes into a new temporary directory. It demonstrates backup, an edit,
and recovery of the earlier file.

### Create a repository

```bash
umask 077
work=$(mktemp -d)
export RESTIC_REPOSITORY="$work/repository"
export RESTIC_PASSWORD_FILE="$work/password.txt"
openssl rand -hex 32 > "$RESTIC_PASSWORD_FILE"
mkdir "$work/files"
printf 'First version of a note.\n' > "$work/files/note.txt"
printf 'An example document.\n' > "$work/files/document.txt"
restic init
```

Restic should report that it created a repository. The password file and the
repository are separate: losing the password means losing access to the backup.
For this exercise they share one temporary directory; for real backups, keep
the password in your password manager as well.

### Back up the files

Run the backup from inside the source directory so the snapshot contains the
files at its root:

```bash
(cd "$work/files" && restic backup . --tag example)
restic snapshots --tag example
restic ls latest
```

The listing should contain `note.txt` and `document.txt`. Keep the snapshot ID
when choosing between several backups. This new repository has only one, so
`latest` selects it throughout the example.

### Change a file and restore

```bash
printf 'A later edit.\n' > "$work/files/note.txt"
restic restore latest --target "$work/restored"
cat "$work/restored/note.txt"
diff -u "$work/files/document.txt" "$work/restored/document.txt"
```

The restored note should contain `First version of a note.` The unchanged
document should compare without any output from `diff`. Your source note still
contains the later edit because the restore used a separate destination.

Check the repository's stored data too:

```bash
restic check --read-data
```

A repository check verifies the stored backup data. For an application, also
start an isolated restored instance and check that its database and files work
together.

### Cleanup

The exercise prints its directory so you can inspect it before deleting it:

```bash
printf 'Example files and repository: %s\n' "$work"
unset RESTIC_REPOSITORY RESTIC_PASSWORD_FILE
```

When finished, remove that temporary directory, including its generated password
file. It contains only the example files if you followed the commands above.

[Restic backup guide](https://restic.readthedocs.io/en/stable/040_backup.html) ·
[Restoring backups](https://restic.readthedocs.io/en/stable/050_restore.html) ·
[Copying snapshots](https://restic.readthedocs.io/en/stable/045_working_with_repos.html#copying-snapshots-between-repositories)
