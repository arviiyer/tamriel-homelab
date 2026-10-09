# Publication Policy

## Purpose

Rules for sharing files from the private homelab. Production configuration,
credentials, and repository histories stay outside this checkout.

## Allowed Material

- Purpose-written architecture and threat-model documentation
- Sanitized configuration examples using public aliases
- Reworked automation that runs against synthetic fixtures
- Public CI definitions that require no production credentials
- Redacted runtime screenshots that pass the review checklist
- Sanitized validation and recovery-drill records
- Generalized lessons learned and architecture decisions
- A public Git author name and GitHub no-reply commit identity
- Credential-free example environment files using public placeholders

## Prohibited Material

- Production Git histories, bundles, reflogs, or repository mirrors
- Raw firewall, router, hypervisor, identity-provider, or controller exports
- Plaintext or encrypted credentials, private keys, recovery codes, or tokens
- Secret-bearing environment files, Terraform state, vault files, or
  secret-bearing examples
- Real IP addresses, domains, MAC addresses, VM IDs, host keys, fingerprints,
  production usernames, local paths, or emergency access procedures
- Complete production detection suppressions or allowlists
- Malware, PCAPs, log exports, database dumps, or captured evidence
- Screenshots that retain browser URLs, user identities, unique IDs, or hidden
  metadata

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

## Known-Identifier Audit

Known production domains, hostnames, account names, and other environment
identifiers must be maintained in a fixed-string denylist outside this
repository. The file contains one identifier per non-empty line and must never
be copied into the public workspace.

Run the local current-tree and retained-history audit with:

```bash
PUBLIC_SAFETY_DENYLIST_FILE=/path/outside/repository/private-identifiers.txt \
  bash scripts/check-public-safety.sh
```

The checker rejects a denylist stored inside the repository and does not print
matching private values. Public CI runs generic current-tree and retained-history
checks without this private file and supplements them with a complete-history
secret scan. A private denylist audit remains a required local publication check
because CI must not receive the private identifier set.

## Public Aliases

Use role-based names rather than production names:

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
an address or domain.

## Screenshot Review

Screenshots must be staged and edited outside this repository. Only the final
reviewed image may be force-added to `evidence/screenshots/`.

Required review:

1. Crop to the area being shown.
2. Apply opaque redaction rather than blur or pixelation.
3. Remove browser chrome when it contains a production URL.
4. Remove hostnames, addresses, usernames, emails, IDs, hashes, and schedules.
5. Strip EXIF and ancillary metadata.
6. Run OCR and inspect the extracted text.
7. Have a second review compare the image with this policy.
8. Add a short caption and a linked review record containing capture month,
   redactions, reviewer, and context. Capture dates need not appear in
   the visible gallery caption.

The initial reviewed set has two specific owner-approved retained values: the
[past scan-result timestamp](../evidence/screenshots/grafana-security-dashboard.review.md)
and the [cluster display name matching the public project](../evidence/screenshots/proxmox-cluster-summary.review.md).
These approvals do not extend to recurring schedules, node names, account details,
or other identifying values. Do not replace real labels with fabricated aliases
inside an image.

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
