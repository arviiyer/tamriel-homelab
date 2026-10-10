# Uptime Kuma

[Home](../../README.md) · [Monitoring](../README.md)

Kuma checks the path to an application independently of Prometheus's host metrics.
I monitor hosts and HTTPS endpoints separately, with grouped notifications for
the media stack.

## Install

Requirements: Docker Engine, Compose, curl, and local persistent storage. In a
new directory outside this checkout, download [compose.yml](compose.yml):

```bash
curl -fLo compose.yml \
  https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/monitoring/uptime-kuma/compose.yml
docker compose config --quiet
docker compose up -d
```

Open `http://localhost:3002` and create the administrator. On a remote VM, use
`ssh -L 3002:127.0.0.1:3002 operator@observability-01`. The initial port is
local-only; add a [private HTTPS route](../../networking/private-access/README.md)
for daily use. The lab uses an Authentik proxy outpost for this UI.

## Add useful monitors

1. Add an HTTP(s) monitor for an application's regular HTTPS URL. Use the same
   hostname clients use, rather than a direct container address.
2. Select a reasonable interval, such as 60 seconds, and two retries to avoid
   notifying for a brief restart.
3. Set the accepted status codes deliberately. A login redirect can be a valid
   reachability result; a keyword on the sign-in page can make that more specific.
   It still does not test a complete authenticated session.
4. Add a separate host or TCP monitor where it helps distinguish a host outage
   from a failed application.
5. Create a Discord notification under **Settings → Notifications**, supply its
   private webhook, and use **Test** before attaching it to a monitor.

For a disposable test endpoint, stop its server, wait for a Down notification,
then start it and check the Up notification. Keep Kuma running during the test.

My standalone monitors notify directly. Display-only groups stay quiet. The
Servarr group sends one aggregate notification while its child monitors remain
visible without each sending another notification.

## Backups and updates

Keep `/app/data` on local storage. Stop Kuma before archiving its volume so its
SQLite database is consistent, then restart it. Retain the Compose file and
matching image reference with the private backup; the database contains saved
notification settings.

Restore to a separate project and port with outbound notifications blocked until
you have checked the monitors. For major-version upgrades, follow the upstream
migration instructions before changing the image. After recreating it, check
login, fresh heartbeat timestamps, and a test notification.

| Symptom | First thing to check |
|---|---|
| All private HTTPS checks fail, host metrics work | Tailscale enrollment, expiry, DNS, and proxy path |
| Login page reports healthy while app is broken | What the monitor actually requests and accepts |
| Many alerts for one media-host outage | Child/group notification assignments |
| No recovery notification | Fresh Up heartbeat and whether Kuma restarted during the incident |

[Uptime Kuma documentation](https://github.com/louislam/uptime-kuma/wiki)

To check the example's startup in a disposable project, run
`python3 scripts/check-service-examples.py --smoke uptime-kuma` from the repository
root with Python 3 and Compose 2.24.4 or newer. The monitor and notification checks
above need your chosen endpoints.
