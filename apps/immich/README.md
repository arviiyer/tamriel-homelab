# Immich

[Home](../../README.md) · [Apps](../README.md) · [Storage](../../storage/README.md)

Immich is the photo library. It runs on the application VM with Authentik sign-in
and stores the library on TrueNAS.

## The setup

| Component | Role |
|---|---|
| Immich server | Web interface, uploads, and background jobs |
| Machine-learning service | Photo search and recognition jobs |
| PostgreSQL with Immich's extensions | Library metadata |
| Redis | Application cache and job coordination |
| NAS library | Photo and video files |

The database stays on a local VM disk. The NAS mount must be ready before the
containers start. See [storage dependencies](../../storage/README.md#waiting-for-shared-storage).

## Setup notes

Start with the [Compose files for the selected Immich release](https://docs.immich.app/install/docker-compose/).
Keep the server, machine-learning service, and supported database image aligned
with that release. Immich's database image includes extensions; a stock PostgreSQL
image is not an interchangeable replacement.

Set the library location to the mounted photo share and the database location to
local storage. Keep the database connection settings consistent between the
server and database containers. The lab uses a connection URL with an explicit
database hostname.

For sign-in, configure an Authentik OAuth2/OIDC provider and the callbacks listed
in [Immich's OAuth guide](https://docs.immich.app/administration/oauth/), including
the mobile-client callback when using the phone app. Check a complete login and
photo upload through the intended Caddy hostname.

## Backups and updates

The library files and database are a pair. A VM backup covers local application
data, while the externally mounted library needs its own protection. NAS snapshots
help recover files; they remain on the same storage system.

Before an update, read the release's migration notes, back up the database and
library, and retain the previous image references. If an update changes the
database schema, rolling back just the image is insufficient. Follow the
[Immich backup and restore instructions](https://docs.immich.app/administration/backup-and-restore/)
for the matching release.

After an update, check sign-in, uploads, thumbnails, job queues, and access to
existing photos. The lab also collects Immich's application metrics in
[Grafana](../../monitoring/README.md#grafana).
