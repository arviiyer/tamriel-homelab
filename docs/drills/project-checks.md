# Project example checks

[Projects](../../projects/README.md) · [Setup guide checks](setup-guide-checks.md)

Checked on October 10, 2026. The examples ran locally, in disposable containers,
or against disposable Proxmox VMs.
Generated files, models, and test data stayed outside the repository.

## Results

| Project | Checked |
|---|---|
| Printer Monitor | Three Python tests, installation into an empty home directory, JSON sample output, and the GTK sample window. The local CUPS queue was available while its printer was offline. |
| Reading brief | Eight Python tests and a live FreshRSS → Jev → local Qwen → JSON/RSS → Homarr check. Exact source comparisons, duplicate filtering, same-day reruns, failure preservation, and the FreshRSS article link passed. Details below. |
| Seerr approver | Eight Go tests with the race detector and `go vet`; Docker build. Fixture checks cover permission and interaction handling. The public client passed read-only integration checks against fresh Seerr. Reviewed screenshots show a real approval through the existing lab bot. |
| Forge | Five Go tests with the race detector and `go vet`; Terraform formatting, provider validation, and a two-VM mocked plan. Live browser checks created two VMs, preserved the first one's configuration, checked SSH login and protection, exercised power controls, and removed both VMs. |
| Sandbox | Four Python tests and all four generated browser scenarios: completed, stopped, missing evidence, and failed reset. Reviewed captures of a historical benign run in the private analyst UI. |

The project index and all five guides passed local Markdown link checks and
Chromium rendering at 1280-pixel and 390-pixel widths, including diagrams and
images. The Forge and Sandbox demo interfaces also fit the narrow viewport.

The model-container smoke test caught an unquoted YAML flow-list entry in the
temporary mount options. Quoting the complete mount fixed startup; the actual
model check then passed.

## Reading brief

A fresh FreshRSS reader imported seven controlled entries: two public Debian
advisories, a synthetic SQLite restore article and its paraphrase, a promotional
article, and URL/content duplicates. Jev selected one restore article and both
advisories. The paraphrase, exact duplicates, and promotional entry were omitted.
This used the existing API account with fresh worker state, not a new TypeSafe
account. The complete check used 16 ranking/comparison API attempts, including
an intentional authentication failure.

The first source comparison caught a text-cleaning bug: newlines used to wrap
HTML source became separate sentences. The fix collapses those spaces while
retaining paragraph, list, and line-break boundaries. A regression test and the
repeated live run passed; both advisory excerpts now include their complete
sentences. All published excerpts matched the cleaned source text.

A same-day rerun made no API calls and retained identical output. An actual API
authentication failure and an unavailable local model preserved the last good
publication. Featured-article history and JSON/RSS output also passed.

The documented widget rendered the public worker's JSON in a fresh Homarr 2.4.1
installation, with a 300-second refresh interval. Its article link opened the
correct entry after FreshRSS login. The board fit a 390-pixel viewport.
[Screenshot](../../screenshots/reading-live.webp) and
[review](../../screenshots/reading-live.review.md).

This checks the complete integration on known inputs. It is not a multi-day
assessment of reading quality across the normal subscription set.

## Seerr Discord Approver

The public client's local-account login, exact Manage Requests permission check,
pending-request listing, per-request lookup, and title lookup passed against a
fresh Seerr 3.4.1 installation. Four pending requests used Blender open films.
The disposable Jellyfin, Seerr, and Radarr containers were removed afterward.

The eight Go tests use fake Seerr/Discord transports to check permissions, CSRF,
webhook authentication, owner/location checks, signed actions, approval replay,
denial/cancellation, stale requests, and avoiding blind write retries.

The owner supplied screenshots of a *Big Buck Bunny* request and its approval
through the existing lab bot. They show the pending buttons, the bot's approval
confirmation, and Seerr's processing status. The screenshots demonstrate the
running lab version, which includes posters and richer details; the public
example uses compact text messages. The public example's Discord Gateway and
live decision checks remain on the [roadmap](../../ROADMAP.md#projects).

[Pending request](../../screenshots/seerr-approval-pending.webp) ·
[Approved request](../../screenshots/seerr-approved.webp) ·
[Screenshot reviews](../../screenshots/seerr-approved.review.md)

## Forge

The public portal ran in a new Terraform directory against Proxmox with verified
TLS. It cloned two Debian 13 VMs, using 1 CPU / 1 GiB and 2 CPUs / 1.5 GiB. The
complete first-VM configuration remained identical while the second was added.
Protection was reflected in Proxmox and disabled the portal's destroy action.

The first guest-login check found that Debian's existing `operator` system group
prevented cloud-init from creating the same-named user. Both Terraform examples
now use `labuser`. The repeated live check confirmed DHCP, the QEMU guest agent,
SSH public-key login, and completed cloud-init configuration.

An initial shutdown timed out during first-boot work. After that work finished,
the portal's graceful shutdown and start both reached the requested hypervisor
state. The corrected walkthrough waits for cloud-init before power checks.
Protection removal and both deletions passed; the original VM inventory was
unchanged and the test Terraform state was empty afterward.
[Screenshot](../../screenshots/forge-live.webp) and
[review](../../screenshots/forge-live.review.md).

## Sandbox

The private UI was opened through its normal analyst sign-in and filtered to a
completed September 29 benign execution-fixture run. The captures show its
overview, process timeline, and collected screenshots: 139 events and 20
artifacts. The worker remained quarantined, its Windows VM stayed powered off,
and the scheduler/worker container stayed stopped.

[Overview](../../screenshots/sandbox-overview.webp) ·
[Run detail](../../screenshots/sandbox-run.webp) ·
[Screenshot reviews](../../screenshots/sandbox-run.review.md)

## Scope of these results

- The public Discord example's live button delivery and decisions remain untested.
  The lab-bot screenshots and fresh-Seerr read checks cover the steps above.
- Sandbox's public viewer replays generated events. It does not validate a
  Windows agent, hypervisor reset, console relay, or network isolation. The private
  UI captures document an existing run, not a new execution qualification.

## Repeat the checks

From the repository root:

```bash
python3 -m unittest discover -s projects/printer-monitor/tests -v
python3 -m unittest discover -s projects/reading-brief/tests -v
python3 -m unittest discover -s projects/sandbox/tests -v
go -C projects/seerr-discord-approver test -race ./...
go -C projects/seerr-discord-approver vet ./...
go -C projects/forge test -race ./...
go -C projects/forge vet ./...
bash projects/forge/check-terraform.sh
docker build -t seerr-approver-check projects/seerr-discord-approver
python3 scripts/check-markdown-links.py
```

The [project workflow](../../.github/workflows/projects.yml) runs the unit,
configuration, and mocked Terraform checks. Follow each guide's first-task
section for the interactive checks and live integrations.
