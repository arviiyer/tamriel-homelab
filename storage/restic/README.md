# Try a backup and restore with Restic

[Home](../../README.md) · [Storage](../README.md)

I use Restic for Vaultwarden backups on the Pi, with a copy on another host.
This walkthrough uses a few disposable text files to show the same basic cycle:
back up, change a file, and restore the earlier copy into a new directory.

## Requirements

Install [Restic](https://restic.readthedocs.io/en/stable/020_installation.html).
The commands below use Bash, OpenSSL, and `diff`. Run them in one shell. All files
go into a new temporary directory outside this checkout.

## Create a repository

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

## Back up the files

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

## Change a file and restore

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

## Using this for an application

- For SQLite applications, use the supported database-backup command or stop the
  application while taking a consistent copy.
- For PostgreSQL, make a successful database dump before backing up its output.
  Do not treat a copy of a running database directory as a dump.
- Include attachments, configuration, and required encryption keys. Keep those
  backups and their credentials private.
- Send a copy to another host or storage destination. A local repository helps
  with a deleted file but is lost with the disk it lives on.
- Record the application version, restore into a new location, and check the
  application before replacing its working data.

The [storage page](../README.md#backups) lists what each lab application needs.
Restic's [repository-copy documentation](https://restic.readthedocs.io/en/stable/045_working_with_repos.html#copying-snapshots-between-repositories)
covers copying snapshots between repositories.

## Cleanup

The exercise prints its directory so you can inspect it before deleting it:

```bash
printf 'Example files and repository: %s\n' "$work"
unset RESTIC_REPOSITORY RESTIC_PASSWORD_FILE
```

When finished, remove that temporary directory, including its generated password
file. It contains only the example files if you followed the commands above.

[Restic backup guide](https://restic.readthedocs.io/en/stable/040_backup.html) ·
[Restoring backups](https://restic.readthedocs.io/en/stable/050_restore.html)
