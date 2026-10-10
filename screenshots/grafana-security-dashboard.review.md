# Screenshot Review: Trivy Dashboard

- Capture month: 2026-09
- Review status: Approved for inclusion
- What it shows: Vulnerability totals and changes between scans
- Source: Real operated environment
- Crop: Four vulnerability summary panels, narrowed in October 2026 from the September capture
- Opaque redactions applied: Not needed in the retained crop
- Browser URL removed: Not present
- Hostnames and addresses removed: Surrounding detail tables excluded
- Usernames, emails, and IDs removed: Not present in retained crop
- Hashes, tokens, and fingerprints removed: Surrounding image references excluded
- Owner-approved retained values: Vulnerability totals and scan deltas
- Metadata stripped: Yes; RGB PNG with only IHDR, IDAT, and IEND chunks, without alpha or embedded metadata
- OCR output reviewed: Yes; retained text also inspected visually because OCR misreads one count
- Pixel integrity checked: Yes; retained crop is pixel-identical to the original
- First review: OpenCode; visual, pixel, metadata, and OCR checks
- Second reviewer: arviiyer (repository owner); narrower crop approved on 2026-10-10

## Caption

Trivy dashboard showing vulnerability totals and new critical and fixable HIGH findings.

## What this shows

This is the operated Trivy dashboard, not the purpose-written public Grafana
provisioning example. It supports observed finding presentation, not validation
of that example's queries, Falco activity, or the latest scan's completeness.

The October edit removes the old secret-status panel with its inaccurate label
and the scan-time panel. It is a crop of the earlier image, not a new scan or a
change to the displayed values. Counts do not show remediation, and this capture
has not been correlated to the Discord notification as the same scan.

Original captures and OCR output remain outside the repository.
