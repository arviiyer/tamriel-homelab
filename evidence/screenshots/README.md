# Screenshot Evidence

This directory accepts only final, reviewed screenshots. Original captures and
working redaction files stay outside the repository.

The deny-by-default `.gitignore` requires each image to be force-added after
review. Every image must also have a same-name `.review.md` record. For example:

```text
grafana-security-dashboard.png
grafana-security-dashboard.review.md
```

## Review Record Template

```markdown
# Screenshot Review: <title>

- Capture month: YYYY-MM
- Claim demonstrated: <validation-matrix claim>
- Source: Real operated environment / synthetic fixture
- Cropped to minimum evidence: Yes
- Opaque redactions applied: Yes
- Browser URL removed: Yes / Not present
- Hostnames and addresses removed: Yes
- Usernames, emails, and IDs removed: Yes
- Hashes, tokens, and fingerprints removed: Yes
- Metadata stripped: Yes
- OCR output reviewed: Yes
- Second reviewer: <name or handle>
- Notes: <what remains visible and why it is safe>
```

## Initial V1 Capture Briefs

Capture only the minimum region described below. Browser chrome, navigation,
sidebars, notifications, and unrelated rows should remain outside the capture
rather than being redacted afterward.

| Filename | Evidence to retain | Content to remove or redact |
|---|---|---|
| `grafana-security-dashboard.png` | Dashboard title and the smallest set of panels showing scan health, actionable findings, and runtime-detection activity | URL, exact time range, datasource or host names, repository names, user identity, and notification details |
| `forgejo-validation-run.png` | Pull-request validation heading, required check names, and their successful conclusions | Repository and organization names, actor identity, commit hash, pull-request number, branch names, runner labels, URL, and exact timestamps |
| `security-scan-alert.png` | One reviewed scan or alert showing severity, actionable transition, and healthy scan context | Repository, image, host, destination, rule-instance IDs, hashes, URLs, notification recipient, and exact timestamps |
| `proxmox-cluster-summary.png` | Cluster health or quorum state and three visible node rows | Cluster and node names, addresses, VM or storage IDs, guest names, subscription keys, task history, exact versions, and exact resource totals |

Public CVE identifiers and generic product labels may remain visible. Opaque
redaction must fully cover each private value; do not replace real labels with
fabricated labels inside the image.

Dependency-update and backup or recovery screenshots remain approved later
targets, but they are not part of the initial four-image v1 set.
