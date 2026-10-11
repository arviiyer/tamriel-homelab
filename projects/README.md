# Projects

[Home](../README.md) · [Apps](../apps/README.md)

Tools I've built around the lab: a morning reading list, VM provisioning, media
request approvals, printer status, and an analysis sandbox.

| Project | What I use it for |
|---|---|
| [Daily reading brief](reading-brief/) | Picking articles from FreshRSS to read in Homarr |
| [Forge](forge/) | Creating Proxmox VMs from templates and managing their power |
| [Seerr Discord Approver](seerr-discord-approver/) | Approving media requests from Discord |
| [Printer Monitor](printer-monitor/) | Checking CUPS jobs, ink levels, and printer status on my laptop |
| [Tamriel Sandbox](sandbox/) | Bringing analysis runs, telemetry, and worker recovery into one UI |

## How they fit together

The [reading brief](reading-brief/) uses [FreshRSS](../apps/freshrss/) and
[Homarr](../apps/homarr/). The [Discord approver](seerr-discord-approver/) sits
beside the [media stack](../media/). [Forge](forge/) provisions VMs on
[Proxmox](../proxmox/), while [Sandbox](sandbox/) has a separate control plane
and disposable Windows worker. [Printer Monitor](printer-monitor/) runs on the
laptop connected to the USB printer.
