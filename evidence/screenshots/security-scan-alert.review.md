# Screenshot Review: Discord-Delivered Trivy Alert

- Capture month: 2026-09
- Review status: Approved for inclusion
- Claim demonstrated: One delivered notification for new fixable HIGH vulnerability findings
- Source: Real operated environment; Discord notification
- Cropped to minimum evidence: Yes; alert card only
- Opaque redactions applied: Yes; repository labels, image reference/version, and wrapped digest
- Browser URL removed: Not present
- Hostnames and addresses removed: Repository/image details masked; no destination URL visible
- Usernames, emails, and IDs removed: Sender header excluded; identifying repository details masked
- Hashes, tokens, and fingerprints removed: Image digest masked; no credentials observed
- Owner-approved retained values: None
- Metadata stripped: Yes; RGB PNG with only IHDR, IDAT, and IEND chunks, without alpha or embedded metadata
- OCR output reviewed: Yes; retained severity, count, status, and action also inspected visually
- Pixel integrity checked: Yes; solid-black masks and no differences outside the intended masks/crop
- First review: OpenCode; visual, pixel, metadata, and OCR checks
- Second reviewer: arviiyer (repository owner); image and caption approved

## Caption

Trivy alert delivered to Discord for eight new high-severity findings with available fixes.

## Evidence Boundary

The original alert name, firing status, warning alert priority, HIGH vulnerability
severity, count of eight findings, and update recommendation are unchanged.
Alert priority and vulnerability severity are separate fields. The generic
Alertmanager link label is visible, but no URL is present in the flattened image.

This records one observed notification delivery, not successful remediation,
continued delivery reliability, or latest-scan completeness. The notification has
not been correlated to the separate dashboard capture as the same scan. The
operated alert name need not match the sanitized public rule name.

Original captures and OCR output remain outside the repository.
