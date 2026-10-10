# Documentation plan

I want this repository to be a personal tour of Tamriel: what runs on it, how I
use it, and how the services fit together. The reference is
[TechHut's homelab](https://github.com/TechHutTV/homelab), especially its app
catalogue, category guides, screenshots, and configuration examples.

This plan records the comparison and work order. The
[roadmap](../ROADMAP.md#documentation) tracks the work. The
[homepage](../README.md), [app catalogue](../apps/README.md), and category guides
now include the personal services and link to the existing screenshots and
examples. New app, general-monitoring, and storage captures remain to be added.

## Comparison

The comparison used TechHut's
[snapshot `2745f3d`](https://github.com/TechHutTV/homelab/tree/2745f3d3470244a0198e39bc118630f9b9e974af)
and Tamriel at commit `3f8273626543db0a095f423cb4f363929737cde0`, before these
documentation changes. It covers published files and documentation.

| Area | TechHut | Tamriel at the comparison point | Planned improvement |
|---|---|---|---|
| Homepage | Short introduction, category navigation, hardware grouped by purpose | Introduction, setup diagram, hardware table, tools, automation links | Add prominent routes into applications and category guides |
| Organization | Apps, media, cloud, storage, monitoring, proxy, and other lab categories | Most substantive content under `automation/` and `docs/` | Add reader-facing folders named after areas of the lab |
| Applications | Named apps with screenshots, personal descriptions, and project links | Personal services described as files, photos, documents, passwords, search, media, and development | Build a catalogue of confirmed applications |
| Writing | Explains usage, choices, changes, and troubleshooting | Mostly explains system behavior and implementation | Add actual usage and the reasoning behind choices |
| Hardware | Separate compute, networking, cameras, and other-device sections | Nine devices with specifications and roles | Group the table and link devices to relevant setup notes |
| Virtualization | Proxmox instructions throughout service guides | Three-node cluster and Debian VM model summarized | Explain workload grouping, GPU passthrough, and supporting Pi roles |
| Screenshots | App interfaces in the catalogue and setup illustrations in guides | Four operational screenshots, mainly in a gallery | Put application and infrastructure images beside their descriptions |
| Configuration | Eight standalone Compose files across service categories | One standalone Compose file for Falcosidekick, plus other automation | Add small examples for representative everyday services |
| Networking | Proxy, DNS, remote-access, and identity walkthroughs | Network zones, access paths, and sign-in behavior | Add practical Caddy, Authentik, DNS, and Tailscale notes and examples |
| Monitoring | Host/container monitoring setup and dashboard recommendations | Security dashboard provisioning and validation | Explain lab metrics, logs, dashboards, and notifications together |
| Storage and backups | Storage setup, client access, troubleshooting, and application backup guidance | Storage decisions, backup-tool names, and a synthetic restore example | Explain TrueNAS, PBS, and Restic responsibilities for actual services |
| Security | Mostly covered within service and access guides | Detailed Trivy and Falco examples | Connect the tools to everyday use through a category overview |
| Updates and deployment | Mostly per-service commands | Forgejo workflows, deployment restrictions, rollback, Ansible, and tests | Introduce the Git and update workflow before linking to implementation details |
| Validation | No test files or GitHub Actions workflows found in the inspected tree | Three GitHub workflows, eleven Python test modules, validators, and drills | Cover configuration added outside `automation/` |
| Maintenance | Some duplicated material and older instructions | Short documentation and a central roadmap | Give each explanation one main home and use relative links |

At those revisions, TechHut had 19 Markdown files and 46 image files, including
screenshots and thumbnails. Tamriel had 26 Markdown files and four screenshots;
90 of its 120 tracked files were under `automation/`. These counts describe the
content mix. The main gap is application coverage, practical service guides,
and visuals.

TechHut's homepage is relatively simple. Most of the visual tour is in its
[app catalogue](https://github.com/TechHutTV/homelab/blob/2745f3d3470244a0198e39bc118630f9b9e974af/apps/README.md).
Its [Immich guide](https://github.com/TechHutTV/homelab/blob/2745f3d3470244a0198e39bc118630f9b9e974af/cloud/immich/README.md)
is a useful reference for requirements, setup, everyday use, storage, backups,
updates, and troubleshooting. The
[monitoring guide](https://github.com/TechHutTV/homelab/blob/2745f3d3470244a0198e39bc118630f9b9e974af/monitoring/README.md)
still points to an older repository in its clone command, illustrating why
instructions and examples need to be maintained together.

## Source review

The inventory was reviewed against the private architecture reference, individual
service READMEs, and tracked Compose definitions. The catalogue now covers file
sync, photos, documents, reading, passwords, search, media, games, custom tools,
and supporting infrastructure. Databases, caches, and workers are described with
their parent applications.

The source review also clarified changes that older notes did not reflect:

- Syncthing replaced Nextcloud for documents, pictures, and notes.
- Jellyfin and Seerr returned to private access; the public media edge is retired.
- Homarr uses local credentials.
- Sandbox analysis is paused while its private API and UI remain available.
- The reading brief is a pilot using source excerpts, with external ranking and
  local excerpt selection.
- The laptop chat service starts on demand.

The review describes recorded configuration and operational notes. It did not
run a live-service audit. No tracked application screenshots were found in the
reviewed app, media, proxy, monitoring, provisioning, or Discord-approver repos.

## Details to collect

The remaining inputs are reviewed screenshots and the exact application behind
the Speedtest service. For future catalogue additions, confirm:

- The application name and purpose.
- Its placement by role, such as a Docker service in `apps-01` or a dedicated VM.
- Authentication, storage, and other service dependencies.
- A real reason for choosing it, customization, or troubleshooting discovery.
- Available screenshots, reviewed configuration examples, and existing notes.

Immich, FreshRSS, and Jellyfin now have setup notes. The category guides cover the
ROG Ally's GPU role, the Pi's services, VM provisioning, sign-in methods, and the
backup responsibilities of PBS, Restic, and NAS snapshots. Further code examples
for CrowdSec, ClamAV, Terraform, and Renovate can build on those descriptions.

Use public role names and follow the [publication policy](publication-policy.md)
when collecting material for this repository.

## Proposed layout

The category folders are in place, including Media. Service subfolders hold
focused guides and runnable examples:

```text
README.md
apps/
  README.md
  syncthing/
    compose.yml
    README.md
  immich/
    README.md
  freshrss/
    README.md
  projects/
    README.md
media/
  README.md
proxmox/
  README.md
networking/
  README.md
  caddy/
    README.md
    compose.yml
    Caddyfile
storage/
  README.md
monitoring/
  README.md
  host-metrics/
    README.md
    compose.yml
    prometheus.yml
    dashboard.json
    provisioning/
security/
  README.md
automation/
  README.md
  ansible/
  ci/
  falco/
  monitoring/
  recovery/
  trivy/
docs/
  architecture.md
  case-studies/
  ...
evidence/
  screenshots/
  drills/
```

Create a service subfolder when there is a useful guide or example to publish.
An app can appear in the catalogue with a description and upstream links.
Category pages will link directly to the relevant automation and design notes.
The architecture page will provide the cross-lab overview and point to category
pages for topic-specific details.

## Work order

### 1. Confirm the inventory

The private reference and service checkouts supply the app list. Use that source
for future additions too, preferring newer dated records when older notes differ.
Confirm personal usage and setup details before writing them in first person.

### 2. Update the homepage and navigation

Use this order in `README.md`:

1. A short introduction to Tamriel and what I use it for.
2. A "Table of Contents" linking to each category with a short description.
3. The setup diagram and a short explanation.
4. Hardware grouped into compute, storage, networking, and supporting devices.
5. A compact list of named applications and infrastructure.
6. A few representative screenshots.
7. Selected notes and the roadmap.

Add compact navigation to category pages and a table of contents to longer
guides. Publish navigation links alongside their target pages.

### 3. Build the app catalogue

Create `apps/README.md`, grouped by purpose: files/photos/documents,
passwords/utilities, media, development, dashboards, and infrastructure.

Each entry should contain:

- The application name and a screenshot where available.
- What I use it for and how it fits into the setup.
- One useful choice, customization, or limitation, when there is one to share.
- Links to its guide, configuration example, and official documentation.

Link to service pages for detailed instructions. This catalogue will be the
main visual tour of the lab.

### 4. Write the category guides

| Planned page | What to explain | Starting material |
|---|---|---|
| `proxmox/README.md` | Cluster layout, VM roles, Debian/Compose setup, ROG Ally GPU use, Pi roles | [Hardware](../README.md#hardware), [architecture](architecture.md), [cluster screenshot](../evidence/screenshots/README.md#proxmox-cluster) |
| `media/README.md` | Jellyfin, Seerr, downloads, VPN health, GPU checks, and NAS layout | [App catalogue](../apps/README.md#media-and-games), reviewed service definitions and dated private notes |
| `networking/README.md` | OPNsense, DNS, Tailscale, Caddy, Authentik, and an access-flow diagram | [Networking and sign-in](network-and-identity.md) |
| `storage/README.md` | Mirrored ZFS storage, local databases, shared files, PBS/Restic responsibilities, application backup contents | [Storage choices](architecture.md#storage), [restore notes](case-studies/recovery-and-storage-dependencies.md) |
| `monitoring/README.md` | Metrics collection, log collection, dashboards, and notifications | [Grafana configuration](../automation/monitoring/README.md), [Falco routing](../automation/falco/event-flow.md) |
| `security/README.md` | How Trivy, Falco, CrowdSec, and ClamAV are used | [Security notes](threat-model.md), [Trivy](../automation/trivy/README.md), [Falco](../automation/falco/README.md) |
| `automation/README.md` | Configuration changes, Renovate PRs, Forgejo checks/deployment, and host maintenance | [Deployment](../automation/ci/README.md), [Ansible](../automation/ansible/README.md), [deployment notes](case-studies/fail-closed-infrastructure-delivery.md) |

Explain the setup and its choices once, then link to deeper implementation
details. Update existing references as material is reorganized. Describe the
synthetic restore example and recorded drills according to what they actually
exercise; application-specific backup and restore guidance needs its own detail.

### 5. Add the first service examples

The first three examples are:

1. [Syncthing](../apps/syncthing/README.md), with persistent file and device data.
2. [Caddy](../networking/caddy/README.md), routing a local hostname to an internal
   upstream and returning an error when the upstream is unavailable.
3. [Host metrics](../monitoring/host-metrics/README.md), connecting Node Exporter,
   Prometheus, and a provisioned Grafana dashboard.

These examples run locally without lab credentials. Their
[shared check script](../scripts/check-service-examples.py) validates Compose and
uses temporary projects for startup, file transfer, routing, dashboard queries,
and failure checks. The existing security dashboard retains its separate Trivy
and Falco dependencies.

Each example should include requirements beside commands, purpose-written
configuration, an `environment.example` where needed, setup/startup steps,
verification, storage and backup notes, updates, troubleshooting, and upstream
links. Adapt individual reviewed artifacts using public aliases, documentation
addresses, and synthetic fixtures, following the
[source import process](publication-policy.md#source-import-process).

### 6. Add screenshots alongside the writing

Capture a service dashboard if one is used, two or three frequently used apps,
a broader monitoring view, and a useful storage or backup view. A physical setup
photo can be added if wanted and reviewed for publication.

Place images beside the relevant descriptions and reference the existing
Proxmox, Grafana, Forgejo, and alert images from their category pages. Store
reviewed images in `evidence/screenshots/` using the
[existing process](../evidence/screenshots/README.md#adding-an-image).

A future Grafana capture with accurate file-scan panel wording would simplify
the current caption's explanation of the Git-history label. Capture the corrected
interface rather than changing labels inside the image.

### 7. Update checks as content lands

These changes belong with the pages and examples that need them:

- Add selected top-level folders to [`.gitignore`](../.gitignore), which ignores
  new root paths by default. The category folders above are now allowed.
- Use `environment.example`. The
  [publication checker](../scripts/check-public-safety.sh) rejects `.env.example`
  along with other `.env` paths.
- Keep reviewed images at the location expected by the screenshot checks.
- Extend [example validation](../.github/workflows/examples.yml) to cover
  configuration added outside `automation/`. The service-example job now checks
  `apps/`, `networking/`, and `monitoring/`; their startup and behavior checks run
  in the manual [integration workflow](../.github/workflows/integration.yml).
- The [Markdown checker](../scripts/check-markdown-links.py) now validates local
  image targets and heading anchors, including linked images and repeated
  headings. [Focused tests](../tests/test_markdown_links.py) cover those behaviors.
- Update links and the [diagram index](../diagrams/README.md) when targets change.
- Run link, publication-safety, whitespace, and relevant artifact checks while
  editing, then complete the repository's required checks before each commit.

## Writing approach

Lead with what runs in the lab and how it is used. Use short introductions,
actual tool names, screenshots, and useful commands. Explain purpose before
configuration and put requirements beside the commands that need them.

Use first person for confirmed choices and experiences. Give each explanation
one main home, link to upstream documentation for general installation details,
and keep commands close to their configuration. Track unfinished work in the
roadmap. Examples and screenshots should support claims about working features.

## First milestone

The first milestone is a homepage, app catalogue, and category navigation with
relevant screenshots. It is ready when:

- The catalogue names the confirmed personal applications and explains their use.
- Every category linked from the homepage has useful introductory content.
- Readers can find a service, its purpose, and available setup/configuration links.
- Available reviewed screenshots appear beside the relevant descriptions.
- The homepage explains the hardware and how the major parts fit together.
- Links and publication checks pass, and remaining work is on the roadmap.

The category guides and first three service examples are now included. Screenshot
collection can proceed alongside further writing; new configuration should receive
validation coverage as it is introduced.
