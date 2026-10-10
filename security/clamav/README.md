# Scan downloads with ClamAV

[Home](../../README.md) · [Security](../README.md) · [Media](../../media/README.md)

ClamAV runs on my media VM. A nightly host-side job waits for the NAS and scanner,
then scans the download share. The lab moves findings to local quarantine and
exports scan results to Pushgateway. This smaller example scans a read-only
directory and reports findings in the journal.

## Start the scanner

Requirements: a Linux Docker host, Compose, and about 3 GiB of available memory
for the scanner and signature updates. The official image loads its database into
memory; this is a significant part of the media VM's memory use.

Download [compose.yml](compose.yml) and [environment.example](environment.example)
into a new directory outside the checkout. Copy the template to `.env` and set
`SCAN_PATH` to an existing absolute path. For a local trial, use a new folder
containing ordinary disposable files. For the NAS, prepare the
[NFS mount and Docker dependency](../../storage/nfs/README.md) first.

```bash
docker compose config --quiet
docker compose up -d
docker compose logs --tail=40 clamav
docker compose exec -T clamav clamdscan --ping 30:2
```

The initial signature download and database load can take several minutes.
`clamdscan --ping` should finish successfully. No scanner port is published.
Check `docker compose exec clamav id clamav` and grant that account read and
directory-traversal permissions on the selected files, using NAS ACLs if needed.

## Run a scan

```bash
docker compose exec -T clamav clamdscan --infected /scan
printf 'Scanner exit status: %s\n' "$?"
```

| Exit | Meaning |
|---|---|
| `0` | Scan completed without a detection |
| `1` | At least one detection; review the reported files |
| `2` | Scan error, such as unreadable files or an unavailable daemon |

The source is read-only. Review detections before deciding how to handle the
files. A clean result covers the files and limits the engine could scan, not
every possible threat. Encrypted archives and oversized files need separate
handling according to your scanner settings.

## Schedule it

For the NAS-backed setup, keep the working files at `/srv/clamav` and install
[clamav-scan.service](clamav-scan.service) and [clamav-scan.timer](clamav-scan.timer)
under `/etc/systemd/system/`. Edit `RequiresMountsFor` and the `findmnt` path if
your download mount differs. These units expect NFS; a local-only trial can use
the manual command above.

```bash
sudo systemd-analyze verify /etc/systemd/system/clamav-scan.service /etc/systemd/system/clamav-scan.timer
sudo systemctl daemon-reload
sudo systemctl start clamav-scan.service
sudo journalctl -u clamav-scan.service -n 40 --no-pager
sudo systemctl show clamav-scan.service -p Result -p ExecMainStatus
sudo systemctl enable --now clamav-scan.timer
sudo systemctl list-timers clamav-scan.timer
```

The example treats exit `1` as a completed scan with findings, while exit `2`
fails the service. Check both the journal and `ExecMainStatus`; a green service
state alone does not establish that it found nothing. My lab additionally
monitors completed-scan freshness and finding counts through Pushgateway.

## Updates and checks

FreshClam updates the persisted signature volume while the daemon runs. Review
its update messages separately from scan results. Before changing the image,
back up the Compose definition and `.env`, replace the digest after checking
release notes, then run `docker compose pull` and `docker compose up -d`.
Repeat the ping and a small scan. The signature database can be downloaded again;
the files being scanned need their own backup.

From the repository root, run `python3 security/clamav/check.py`. The disposable
test creates an inert text file and a matching local signature, then verifies
clean, detected, and error results using the real ClamAV engine. It does not
download malware or depend on the public signature database.

| Symptom | Check |
|---|---|
| Daemon never becomes ready | Memory limit and initial FreshClam download logs |
| Permission denied | Numeric scanner identity and NAS file/parent-directory ACLs |
| Scan sees an empty directory | Actual NFS filesystem and mount dependency |
| FreshClam rate-limited | Reuse the signature volume and follow the reported retry time |

[ClamAV Docker documentation](https://docs.clamav.net/manual/Installing/Docker.html)
