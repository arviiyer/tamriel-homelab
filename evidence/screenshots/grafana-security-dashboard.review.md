# Screenshot Review: Trivy Dashboard

- Capture month: 2026-09
- Review status: Approved for inclusion
- Claim demonstrated: Vulnerability totals and delta-based finding presentation
- Source: Real operated environment
- Cropped to minimum evidence: Yes; Summary section only
- Opaque redactions applied: Not needed in the retained crop
- Browser URL removed: Not present
- Hostnames and addresses removed: Surrounding detail tables excluded
- Usernames, emails, and IDs removed: Not present in retained crop
- Hashes, tokens, and fingerprints removed: Surrounding image references excluded
- Owner-approved retained values: Original Last Scan timestamp; owner approved this past scan-result timestamp, not disclosure of a recurring schedule
- Metadata stripped: Yes; RGB PNG with only IHDR, IDAT, and IEND chunks, without alpha or embedded metadata
- OCR output reviewed: Yes; retained text also inspected visually because OCR misreads one count
- Pixel integrity checked: Yes; retained crop is pixel-identical to the original
- First review: OpenCode; visual, pixel, metadata, and OCR checks
- Second reviewer: arviiyer (repository owner); image and caption approved

## Caption

Trivy dashboard showing vulnerability totals and new critical and fixable HIGH findings.

## Evidence Boundary

This is the operated Trivy dashboard, not the purpose-written public Grafana
provisioning example. It supports observed finding presentation, not validation
of that example's queries, Falco activity, or the latest scan's completeness.

The displayed secret-scan result is not an independent complete-history audit or
a guarantee that no credentials exist. The public scanner's
[current-tree secret-scanning boundary](../../automation/trivy/README.md#secret-scanning-boundary)
is unchanged. Counts are not a claim of remediation, and this capture has not been
correlated to the separate Discord notification as the same scan.

Original captures and OCR output remain outside the repository.
