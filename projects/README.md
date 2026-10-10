# Projects

[Home](../README.md) · [Apps](../apps/README.md)

Tools I've built around the lab: a morning reading list, VM provisioning, media
request approvals, printer status, and an analysis sandbox. Each guide explains
how I use it and includes a runnable example.

| Project | What it does | Start here |
|---|---|---|
| [Morning SOC Briefing](reading-brief/) | Ranks FreshRSS articles and publishes source excerpts to Homarr | Run with two sample articles |
| [Forge](forge/) | Creates Proxmox VMs from templates and manages their power | Open the sample portal |
| [Seerr Discord Approver](seerr-discord-approver/) | Adds owner-only approval buttons to media requests | Connect a bot and dedicated Seerr user |
| [Printer Monitor](printer-monitor/) | Shows CUPS jobs, IPP supplies, and printer status | Open the sample GTK window |
| [Tamriel Sandbox](sandbox/) | Brings analysis runs, telemetry, and worker recovery into one UI | Replay a generated worker lifecycle |

## How they fit together

The [reading brief](reading-brief/) uses [FreshRSS](../apps/freshrss/) and
[Homarr](../apps/homarr/). The [Discord approver](seerr-discord-approver/) sits
beside the [media stack](../media/). [Forge](forge/) provisions VMs on
[Proxmox](../proxmox/), while [Sandbox](sandbox/) has a separate control plane
and disposable Windows worker. [Printer Monitor](printer-monitor/) runs on the
laptop connected to the USB printer.

Start with a project's local example, then follow its configuration and first
task. Keep your installation and its data in a separate working directory.

[Test results](../docs/drills/project-checks.md)
