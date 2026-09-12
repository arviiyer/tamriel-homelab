# Screenshot Review: Proxmox Cluster Health

- Capture month: 2026-09
- Review status: Approved for inclusion
- Claim demonstrated: Point-in-time health and quorum of a three-node Proxmox cluster
- Source: Real operated environment; Proxmox Datacenter Summary
- Cropped to minimum evidence: Yes; Health panel only
- Opaque redactions applied: Not needed in the retained crop
- Browser URL removed: Not present
- Hostnames and addresses removed: Node tree excluded; project-aligned cluster display name retained with owner approval
- Usernames, emails, and IDs removed: Account header, guest inventory, VM IDs, and storage details excluded
- Hashes, tokens, and fingerprints removed: Not present in retained crop
- Owner-approved retained values: Original cluster display name matching the public project name; this does not approve disclosure of node names or inventory
- Metadata stripped: Yes; RGB PNG with only IHDR, IDAT, and IEND chunks, without alpha or embedded metadata
- OCR output reviewed: Yes; full-panel and enlarged node-count passes inspected
- Pixel integrity checked: Yes; retained crop is pixel-identical to the original
- First review: OpenCode; visual, pixel, metadata, and OCR checks
- Second reviewer: arviiyer (repository owner); image and caption approved

## Caption

Proxmox cluster health showing three nodes online and quorum established.

## Evidence Boundary

Online 3, Offline 0, Quorate: Yes, and the green status indicator are unchanged.
Aggregate node counts are retained instead of publishing individual node rows.
Product context was inspected in the original; no title or public node aliases
were fabricated inside the crop. Exact product versions and resource totals are
excluded with the surrounding interface.

This is a point-in-time cluster-health observation. It does not demonstrate
automatic failover, workload health, backup recovery, segmentation, or sustained
uptime.

Original captures and OCR output remain outside the repository.
