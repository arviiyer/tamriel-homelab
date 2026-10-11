# Screenshots

[Home](../README.md) · [Apps and services](../apps/README.md)

Screenshots from the lab and project examples. Click an image to open it at
full resolution.

## Homarr

[![Homarr service cards and reading brief](homarr-home.webp)](homarr-home.webp)

Service links, Pi-hole statistics, and the daily reading brief in Homarr v1.

[Homarr setup](../apps/homarr/README.md)

## Immich

[![Landscape album in Immich](immich-album.webp)](immich-album.webp)

Landscape photos and videos in an album.

[Immich setup](../apps/immich/README.md)

## FreshRSS

[![FreshRSS feed categories and articles](freshrss-reader.webp)](freshrss-reader.webp)

Security feeds grouped by topic.

[![An article open in FreshRSS](freshrss-article.webp)](freshrss-article.webp)

An expanded article with its text and image.

[FreshRSS setup](../apps/freshrss/README.md)

## Jellyfin

[![Jellyfin library and Continue Watching](jellyfin-library.webp)](jellyfin-library.webp)

Media categories and the Continue Watching row.

[Jellyfin setup](../media/jellyfin/README.md)

## Seerr

[![Trending and popular titles in Seerr](seerr-discover.webp)](seerr-discover.webp)

Browsing trending and popular titles in Seerr.

[Media setup](../media/README.md)

## Host monitoring

[![CPU, memory, network, and disk panels in Grafana](grafana-host-metrics.webp)](grafana-host-metrics.webp)

The Node Exporter dashboard in Grafana.

[Monitoring setup](../monitoring/README.md)

## TrueNAS storage

[![TrueNAS storage layout and health](truenas-storage.webp)](truenas-storage.webp)

Two mirrored data VDEVs, storage usage, and disk health.

[Storage setup](../storage/README.md)

## TrueNAS snapshots

[![Periodic snapshot tasks in TrueNAS](truenas-snapshots.webp)](truenas-snapshots.webp)

Enabled snapshot tasks with finished status.

[Backup notes](../storage/README.md#backups)

## PBS backup

[![PBS backup task completed successfully](pbs-backup.webp)](pbs-backup.webp)

A VM backup completed with status OK in 4 minutes 38 seconds.

[PBS setup and restores](../storage/pbs/README.md)

## Trivy dashboard

[![Trivy findings by image and repository](grafana-security-dashboard.png)](grafana-security-dashboard.png)

Critical and high findings grouped by image and repository.

[Monitoring setup](../monitoring/README.md)

## Forgejo CI

[![Successful Forgejo Compose validation](forgejo-validation-run.png)](forgejo-validation-run.png)

Compose checks passing on a dependency-update pull request.

[Git and update workflow](../automation/README.md#git-and-updates)

## Discord alert

[![Trivy alert delivered to Discord](security-scan-alert.png)](security-scan-alert.png)

A Trivy alert for eight new high-severity findings with fixes available.

[Alerting notes](../docs/trivy-alerts.md)

## Proxmox cluster

[![Proxmox cluster showing three online nodes and quorum](proxmox-cluster-summary.png)](proxmox-cluster-summary.png)

The September cluster view, with three nodes online and the VM inventory.

[Cluster setup](../proxmox/README.md)

## Project examples

[![Reading brief in Homarr](reading-live.webp)](reading-live.webp)

The reading worker's output in Homarr v2, using two Debian advisories and a
sample restore article. [Reading brief setup](../projects/reading-brief/README.md).

[![Forge managing two test VMs](forge-live.webp)](forge-live.webp)

Two test VMs with different CPU and memory settings. [Forge setup](../projects/forge/README.md).

[![Pending Discord approval request](seerr-approval-pending.webp)](seerr-approval-pending.webp)

A pending *Big Buck Bunny* request in the lab's Discord bot.

[![Discord approval confirmation](seerr-approved.webp)](seerr-approved.webp)

After approval, Seerr reports the request as processing. The
[bot example](../projects/seerr-discord-approver/README.md) uses text messages
rather than the posters shown here.

[![Printer Monitor sample window](printer-demo.webp)](printer-demo.webp)

The GTK window using sample data. [Printer Monitor setup](../projects/printer-monitor/README.md).

[![Sandbox analyst overview](sandbox-overview.webp)](sandbox-overview.webp)

The lab's Sandbox UI showing a completed benign test run.

[![Sandbox benign run detail](sandbox-run.webp)](sandbox-run.webp)

Process events and collected screenshots from the same run.
[Sandbox notes](../projects/sandbox/README.md).

The Forge guide also has an optional [sample portal](../projects/forge/README.md#try-it-locally).

## Adding screenshots

- Check the full image, including URLs, tabs, notifications, and personal content.
- Remove secrets and private personal information with a crop or small opaque mask.
- Inspect metadata and OCR output, then check the image visually too.
- Keep useful interface context. Ordinary hostnames, addresses, and metrics can stay.
- Add a short caption and identify sample data or a different app version if relevant.

Keep originals and editing files outside this repository. Force-add only the
final reviewed image, up to 4 MiB. Detailed review notes stay local.
