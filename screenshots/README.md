# Screenshots

[Home](../README.md) · [Apps and services](../apps/README.md)

Captures from the lab. Click an image to open it at full resolution.

## Homarr

[![Homarr service cards and reading brief](homarr-home.webp)](homarr-home.webp)

Service links, Pi-hole statistics, and the Morning SOC Briefing.

[Homarr notes](../apps/README.md#homarr) · [Review details](homarr-home.review.md)

## Immich

[![Landscape album in Immich](immich-album.webp)](immich-album.webp)

Landscape photos and videos in an album.

[Immich setup](../apps/immich/README.md) · [Review details](immich-album.review.md)

## FreshRSS

[![FreshRSS feed categories and articles](freshrss-reader.webp)](freshrss-reader.webp)

Security feeds grouped by topic.

[Feed-view review](freshrss-reader.review.md)

[![An article open in FreshRSS](freshrss-article.webp)](freshrss-article.webp)

An expanded article with its text and image.

[FreshRSS setup](../apps/freshrss/README.md) · [Article-view review](freshrss-article.review.md)

## Jellyfin

[![Jellyfin library and Continue Watching](jellyfin-library.webp)](jellyfin-library.webp)

Media categories and the Continue Watching row.

[Jellyfin setup](../media/jellyfin/README.md) · [Review details](jellyfin-library.review.md)

## Seerr

[![Trending and popular titles in Seerr](seerr-discover.webp)](seerr-discover.webp)

Browsing trending and popular titles in Seerr.

[Media setup](../media/README.md) · [Review details](seerr-discover.review.md)

## Host monitoring

[![CPU, memory, network, and disk panels in Grafana](grafana-host-metrics.webp)](grafana-host-metrics.webp)

The Node Exporter dashboard in Grafana.

[Monitoring setup](../monitoring/README.md) · [Review details](grafana-host-metrics.review.md)

## TrueNAS storage

[![TrueNAS storage layout and health](truenas-storage.webp)](truenas-storage.webp)

Two mirrored data VDEVs, storage usage, and disk health.

[Storage setup](../storage/README.md) · [Review details](truenas-storage.review.md)

## TrueNAS snapshots

[![Periodic snapshot tasks in TrueNAS](truenas-snapshots.webp)](truenas-snapshots.webp)

Enabled snapshot tasks with finished status.

[Backup notes](../storage/README.md#backups) · [Review details](truenas-snapshots.review.md)

## PBS backup

[![PBS backup task completed successfully](pbs-backup.webp)](pbs-backup.webp)

A VM backup completed with status OK in 4 minutes 38 seconds.

[PBS restore notes](../storage/README.md#a-vm-from-pbs) · [Review details](pbs-backup.review.md)

## Trivy dashboard

[![Trivy vulnerability summary](grafana-security-dashboard.png)](grafana-security-dashboard.png)

*Vulnerability totals, new critical findings, and new high-severity findings with fixes.*

[Monitoring setup](../monitoring/README.md)

[Redaction and review details](grafana-security-dashboard.review.md)

## Forgejo CI

[![Successful Forgejo Compose validation](forgejo-validation-run.png)](forgejo-validation-run.png)

*Compose checks passing on a dependency-update pull request.*

[Git and update workflow](../automation/README.md#git-and-updates)

[Redaction and review details](forgejo-validation-run.review.md)

## Discord alert

[![Trivy alert delivered to Discord](security-scan-alert.png)](security-scan-alert.png)

*Trivy alert delivered to Discord for eight new high-severity findings with available fixes.*

[Alerting notes](../docs/case-studies/actionable-vulnerability-management.md)

[Redaction and review details](security-scan-alert.review.md)

## Proxmox cluster

[![Proxmox cluster showing three online nodes and quorum](proxmox-cluster-summary.png)](proxmox-cluster-summary.png)

*Proxmox cluster health showing three nodes online and quorum established.*

[Cluster setup](../proxmox/README.md)

[Redaction and review details](proxmox-cluster-summary.review.md)

<details>
<summary>Adding screenshots</summary>

For app captures, check photos, album names, feed titles, avatars, and device
labels for private personal details. Ordinary infrastructure labels, statistics,
and browser bars can stay. Originals and working copies stay outside this repo.

### Adding an image

This directory accepts only final, reviewed screenshots. Original captures and
working redaction files stay outside the repository. Follow the
[screenshot checklist](../docs/publication-policy.md#screenshot-review).

The deny-by-default `.gitignore` requires each image and its same-name `.review.md`
record to be force-added after review. For example:

```text
grafana-security-dashboard.png
grafana-security-dashboard.review.md
```

### Review record template

```markdown
# Screenshot Review: <title>

- Capture month: YYYY-MM
- What it shows: <feature or result>
- Source: Real operated environment / synthetic fixture
- Edits: None needed / <specific crops or opaque masks and why>
- Secrets and private personal information: Not present / <what was removed>
- Browser chrome and URLs checked: Yes
- Metadata checked: No sensitive fields / <what was removed>
- OCR output reviewed: Yes
- Reviewer: <name or handle>
- Second reviewer: <name or handle>
- Notes: <useful context, if needed>
```

### What to capture

Keep enough of the interface to show the feature clearly. Browser chrome,
navigation, sidebars, and surrounding panels can remain when they contain no
secrets or private personal information. Crop for composition when useful.

| Filename | What to show | What to crop or redact |
|---|---|---|
| `grafana-security-dashboard.png` | Severity totals and new critical/fixable HIGH findings | Tokens in URLs, private account details, or sensitive log excerpts |
| `forgejo-validation-run.png` | Workflow and job names, successful checkout and Compose-validation steps | Credentials in output and private actor details |
| `security-scan-alert.png` | A delivered notification with severity, finding counts, and an update instruction | Webhook tokens, private messages, or personal account details |
| `proxmox-cluster-summary.png` | Cluster health, node inventory, quorum, and resource usage | Credentials or private personal information in labels and account details |

Ordinary technical values do not need redaction: hostnames, IP addresses, VM IDs,
pool names, versions, timestamps, schedules, resource totals, public CVEs, commit
hashes, and image digests can stay. Check the content, not just the field name.
When a value really is sensitive, fully cover it with an opaque mask; do not
replace it with a fabricated label.

</details>
