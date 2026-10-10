# Publication Policy

## Purpose

Rules for sharing files from the private homelab. Production configuration,
credentials, and repository histories stay outside this checkout.

## Allowed Material

- Purpose-written architecture and threat-model documentation
- Sanitized configuration examples using public aliases
- Reworked automation that runs against synthetic fixtures
- Public CI definitions that require no production credentials
- Reviewed screenshots, with redaction only where sensitive information appears
- Sanitized validation and recovery-drill records
- Generalized lessons learned and architecture decisions
- A public Git author name and GitHub no-reply commit identity
- Credential-free example environment files using public placeholders
- Ordinary infrastructure labels in screenshots and descriptions

## Prohibited Material

- Production Git histories, bundles, reflogs, or repository mirrors
- Raw firewall, router, hypervisor, identity-provider, or controller exports
- Plaintext or encrypted credentials, private keys, recovery codes, or tokens
- Secret-bearing environment files, Terraform state, vault files, or
  secret-bearing examples
- Passwords, API keys, session cookies, recovery codes, and URLs or QR codes that
  grant access, including authenticated share links
- Private personal information, such as personal email addresses, phone numbers,
  home addresses, precise personal locations, and private messages or documents
- Emergency access procedures
- Complete production detection suppressions or allowlists
- Malware, PCAPs, log exports, database dumps, or captured evidence
- Sensitive information in screenshots, browser tabs, notifications, or image
  metadata

The owner's public Git identity and deliberately published contact details may
remain. Information about other people needs the same care as personal files.

## What needs redaction

Redact based on what a value reveals or allows someone to access. An ordinary
hostname, private IP address, or VM ID is not a credential.

| Keep when no sensitive content is present | Remove when present |
|---|---|
| IP addresses, domains, hostnames, VM IDs, MAC addresses, public fingerprints | Passwords, tokens, private keys, session cookies, recovery codes |
| Generic account names, pool and dataset names, storage paths | Private personal names, contact details, identifying paths, private documents |
| Versions, resource usage, charts, capacities, task times and schedules | Personal routines or location details that are not intended for sharing |
| Browser chrome, app navigation, ordinary URLs | Access-granting URL parameters, private messages, sensitive tabs or notifications |

A hostname or path containing a person's private details still needs editing.
Keep useful context and apply small opaque masks to the sensitive parts. Crop
only when it improves the image or removes sensitive content. An image with
nothing sensitive needs no visible redaction.

## Source Import Process

1. Select one useful script, configuration example, or diagram.
2. Re-create it in this repository without copying private history.
3. Replace environment values with variables, public aliases, and synthetic
    fixtures.
4. Remove unnecessary operational details.
5. Add tests that run without private infrastructure and document how to use it.
6. Review the diff for identifiers and credentials.
7. Run `bash scripts/check-public-safety.sh` and the relevant component tests.

Bulk copying a directory and attempting to redact it afterward is not an
approved import method.

## Sensitive-Value Audit

Keep known secrets and private personal strings in a fixed-string denylist
outside this repository. Do not add every hostname, domain, or address simply
because it belongs to the lab. Review older denylists against this distinction.
The file contains one sensitive value per non-empty line and must never be copied
into the public workspace.

Run the local current-tree and retained-history audit with:

```bash
PUBLIC_SAFETY_DENYLIST_FILE=/path/outside/repository/private-identifiers.txt \
  bash scripts/check-public-safety.sh
```

The checker rejects a denylist stored inside the repository and does not print
matching sensitive values. Public CI runs generic current-tree and retained-history
checks without this private file and supplements them with a complete-history
secret scan. Run the local denylist check when there are known sensitive values
to check. The checker does not inspect image pixels or replace screenshot review.

## Public Aliases

Use role-based names in runnable examples and fixtures:

| Role | Public alias |
|---|---|
| Hypervisor nodes | `pve-01`, `pve-02`, `pve-03` |
| Edge gateway | `edge-01` |
| Identity workload | `identity-01` |
| Application workload | `apps-01` |
| Observability workload | `observability-01` |
| Security automation workload | `security-01` |
| Backup workload | `backup-01` |

Use RFC 5737 documentation addresses and `example.com` when an example requires
an address or domain. These conventions keep examples reusable; they do not
require replacing ordinary labels in screenshots or descriptions of the lab.

## Screenshot Review

Screenshots must be staged and edited outside this repository. Only the final
reviewed image may be force-added to `evidence/screenshots/`. Each image may be up
to 4 MiB; use lossless compression where practical to keep interface text clear.
The review limit for other files is 2 MiB.

Required review:

1. Inspect the full image, including URLs, tabs, notifications, and personal content.
2. Remove secrets and private personal information with small opaque masks or a
   crop. Do not blur or pixelate sensitive text. Keep harmless interface details.
3. Check embedded metadata and remove sensitive fields, if any.
4. Run OCR and inspect the extracted text, then check the image visually for
   content OCR may miss.
5. Have a second review compare the image with this policy.
6. Add a short caption and a linked review record containing capture month,
   any edits, reviewer, and context. "No redaction needed" is a valid result.

Metadata is information stored in the image file rather than its visible pixels.
It may include comments, author details, timestamps, or GPS coordinates. Check
for personal details and secrets; harmless color profiles and software labels
can stay. Removing metadata does not change the visible screenshot. A screenshot
does not normally inherit the camera or GPS metadata of photos displayed in it.

Earlier review records describe the stricter edits made at the time. They remain
historical records, not requirements to repeat those edits on new screenshots.
Do not replace real labels with fabricated aliases inside an image.

Original screenshots remain outside the public repository.

## Documentation

Describe the code and test results accurately. Link to the relevant implementation
or screenshot, and record unfinished work in `ROADMAP.md`. Test results from
generated fixtures describe those tests, not private infrastructure operation.

## Pre-Publication Review

Before the first push to a public remote:

- confirm there is no remote inherited from a private repository;
- inspect `git log --all --stat` and every tracked path;
- run a history-wide secret scan;
- inspect all images with metadata and OCR tools;
- verify public CI uses no repository secrets;
- confirm every link works while unauthenticated.
