# Small projects

[Home](../../README.md) · [Apps](../README.md)

A few tools built around the services in the lab.

## Morning SOC Briefing

The reading brief selects articles from FreshRSS and displays them in Homarr.
TypeSafe Jev ranks relevance and usefulness; a local Qwen model running through
llama.cpp selects source excerpts for the final brief. The ranking step uses an
external API, while excerpt selection runs locally on the app VM's CPU.

I switched to source excerpts after the small model added unsupported details
when writing free-form summaries. It now returns sentence IDs, and the code
copies those sentences from the article. The published brief retains links to
the original sources.

SQLite records completed briefs, model responses, and already-featured articles.
A separate read-only server supplies JSON and RSS to the dashboard. Generation
starts the local model when needed, and a failed generation keeps the previous
published brief. This is still a reading pilot.

[FreshRSS notes](../freshrss/README.md) ·
[Homarr widget setup](../homarr/README.md#morning-soc-briefing) ·
[llama.cpp](https://github.com/ggml-org/llama.cpp)

## Forge VM provisioner

Forge is a small Go web interface for creating Proxmox VMs from templates. It
uses Terraform and cloud-init for provisioning, with direct Proxmox API calls
for power controls. It is separate from Forgejo, which hosts Git repositories.

The portal merges new VM requests with the existing Terraform state before
applying them. That keeps launching another VM from removing one already managed
by the same state. The portal also has protected-VM controls.

[VM provisioning notes](../../proxmox/README.md#provisioning)

## Seerr Discord Approver

Seerr sends request events to a private webhook, and this service adds approve
and deny actions in Discord. It uses a dedicated Seerr account with request
management permission and checks that actions come from the configured owner.

Discord interactions arrive over an outbound Gateway connection. The webhook
stays inside Docker networking. Before changing a request, the service reads
its current state from Seerr so an old message cannot act on stale information.

[Media requests](../../media/README.md#requests-and-downloads)

## Printer Monitor

A small GTK 4 desktop app shows the USB printer's status, estimated ink levels,
loaded paper, and CUPS jobs. It reads CUPS and IPP-over-USB and offers shortcuts
to the print queue and scanner.

The printer is attached to a laptop, so the monitor runs there too. A local app
is useful whenever the printer is connected without needing another server-side
exporter or dashboard.

## Tamriel Sandbox

The separate [sandbox project](../../security/README.md#tamriel-sandbox) combines
an analyst UI, a control-plane API, and a disposable Windows worker. Analysis is
currently paused.
