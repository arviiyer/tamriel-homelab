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

## Approved Initial Targets

- Grafana security dashboard
- Successful Forgejo pull-request validation
- Security scan or alert result
- Proxmox cluster summary
- Dependency-update pull request
- Backup or recovery result

The initial release will select four screenshots from this list.
