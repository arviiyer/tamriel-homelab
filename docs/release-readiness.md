# v1 Release Readiness

## Decision

**Review date:** September 19, 2026

**Disposition:** Local candidate checks passed; approved for private staging.
Public release remains pending.

**Release date:** Not selected; requires owner approval after the safety gates pass.

The repository remains private. The previously authorized release-readiness
commit and branch-only staging push are complete. The September 19 review covers
status reconciliation, reader navigation, and renewed candidate validation.
The owner authorized one commit and branch-only push of the five-file
documentation candidate after checks. Public visibility, profile edits, and
release tags remain separate owner decisions.

## Verified Staging Baseline

- Revision: `f66028e74001db2025bd134ae5f369d268f90135`
- Commit: `portfolio: prepare v1 release review`
- Branch: local `main` and `origin/main` matched at the start of this review.
- [GitHub Actions run](https://github.com/arviiyer/tamriel-homelab/actions/runs/35025863015):
  completed successfully on September 15; rechecked on September 19.
- Both jobs passed: **Publication safety** and **Secret scan**.

This closes the previous staging commit/push/CI task. The run requires repository
access while staging is private and covers the named commit, not the September 19
working-tree edits. Any new candidate commit needs its own CI result.

The [September 19 local review](handoff.md#september-19-candidate-review) passed
the complete validation set, private-identifier audit, and local rendering/link
checks. Its five-file documentation candidate is approved for private staging.
For later candidate revisions, verify the exact commit in the
[validation workflow runs](https://github.com/arviiyer/tamriel-homelab/actions/workflows/validate.yml?query=branch%3Amain)
rather than treating the historical baseline run as coverage.

## Resume Wording

Project title: [Tamriel Homelab: Security-Engineered Self-Hosted Infrastructure](https://github.com/arviiyer/tamriel-homelab)

- Designed a three-node Proxmox private cloud and built Trivy vulnerability
  scanning with delta-based, fix-aware alerts, backed by 27 synthetic tests and
  reviewed cluster-health and notification evidence.
- Implemented exact-revision Docker Compose delivery with restricted SSH,
  health-gated promotion, and guarded rollback; validated recovery on a
  disposable target and unsafe-input rejection in an isolated synthetic restore.

| Wording | Evidence and boundary |
|---|---|
| Three-node platform design | [Architecture](architecture.md) and [cluster capture](../evidence/screenshots/README.md#proxmox-cluster-health); no sustained-availability or failover claim |
| Delta-based, fix-aware alerts | [Trivy implementation and 27 tests](../automation/trivy/README.md), [finding presentation](../evidence/screenshots/README.md#vulnerability-management), and [one delivered notification](../evidence/screenshots/README.md#actionable-security-alert); no remediation or delivery-reliability claim |
| Exact-revision delivery and recovery | [Restricted delivery implementation](../automation/ci/README.md) and [disposable-target drill](../evidence/drills/2026-08-24-fail-closed-delivery-rollback.md); not operated production promotion, rollback, or enforced repository protection |
| Isolated restore and unsafe-input rejection | [Synthetic restore implementation](../automation/recovery/README.md) and [dated drill](../evidence/drills/2026-08-24-isolated-synthetic-restore.md); not VM, database, PBS, or Restic recovery |

These replace the broader drafts. Apply them to the actual resume only after the
project link is publicly accessible. Do not add unevidenced operational clauses
from the [matrix](../evidence/validation-matrix.md).

## GitHub Presentation

Prepared description:

> Security-engineered homelab portfolio: Proxmox architecture, Trivy alerts,
> restricted delivery, and isolated recovery with tests and reviewed evidence.

Prepared topics: `homelab`, `security-engineering`, `devsecops`, `proxmox`,
`trivy`, `ansible`, `docker-compose`, `prometheus`, `grafana`, `infrastructure-as-code`.

Prepared profile entry:

```markdown
### [Tamriel Homelab](https://github.com/arviiyer/tamriel-homelab)
Security-engineered self-hosted infrastructure, presented through reviewed
architecture, executable examples, and bounded runtime evidence.

- [Vulnerability deltas and fix-aware alerts](https://github.com/arviiyer/tamriel-homelab/blob/main/docs/case-studies/actionable-vulnerability-management.md)
- [Restricted delivery and disposable-target rollback](https://github.com/arviiyer/tamriel-homelab/blob/main/docs/case-studies/fail-closed-infrastructure-delivery.md)
- [Isolated synthetic restore and storage boundaries](https://github.com/arviiyer/tamriel-homelab/blob/main/docs/case-studies/recovery-and-storage-dependencies.md)
```

After publication, apply the description and topics, replace the profile badge
wall with the concise project entry, and pin this as the first portfolio project.
No external profile or repository settings have been changed in this review.

## Private Identifier Audit

The existing denylist in the external evidence workspace's audit directory was
used in place on September 15 and again on September 19. The checker passed for
the current files, staged index, ref-reachable history, and checked metadata and
paths. Its contents were neither displayed nor copied into this repository.
Repeat this audit against the final publication snapshot.

This result covers identifiers in the existing list, not a guarantee that every
possible private identifier is represented. Generic secret scans and manual
review remain separate controls.

## Commit Metadata Review

The September 19 recheck confirmed that all 15 ref-reachable commits use no-reply
author and committer emails, including the staging commit added after the
September 15 audit. The effective identity for new commits matches the reviewed
public identity. Two superseded commits retain non-no-reply committer metadata
only in local reflog history; neither is reachable from any current ref, and their
trees match the sanitized replacements.

September 15 authenticated GitHub commit-object requests returned not found.
Remote branch/tag and pull-request inventories were rechecked on September 19:
only `main` and no pull requests were listed. These checks did not demonstrate
remote exposure, but do not certify server-cache removal or prove that the old
objects were never uploaded.

An ordinary branch-only `main` push transfers the selected reachable history,
not local reflogs or the whole object database. No rewrite, reflog expiration, or
object pruning was needed for the completed private-staging push. Do not restore
the superseded commits or distribute the local `.git` directory. The remaining
remote-retention uncertainty belongs in the owner's separate public-release
decision, not a claim that the current branch contains private identity metadata.

## Remaining Gates

1. Verify the selected release candidate's commit identity and ancestry, and
   require successful private-staging CI for that exact revision. The owner
   approved the September 19 documentation commit and branch-only push without
   force or tags; the preceding `f66028e` run is the verified historical baseline.
2. Approve the public release date and final snapshot, including the bounded
   metadata review above. Repeat required checks and the
   file/history/private-identifier review immediately before changing visibility.
3. With explicit owner approval, change visibility and confirm public CI. Confirm
   GitHub private vulnerability reporting is enabled as promised by
   [SECURITY.md](../SECURITY.md); its availability was not established by the
   private-stage API check.
4. Test every README, evidence, and profile link while signed out. Apply the
   prepared resume/profile/repository presentation only after access works.
5. Tag `v1.0.0` only after the public page and all release gates are verified and
   the owner authorizes tagging.

## Follow-Up Scope

The network-migration case study, standalone dependency-update PR, remaining
Prometheus/Loki query execution, live Ansible/Falco transactions, operated
promotion/rollback, and real backup/storage-failure exercises remain separate
evidence tasks. They are not additional minimum-v1 requirements; stronger claims
in those areas remain blocked until their evidence exists.

Fresh validation results and review scope are recorded in the
[handoff](handoff.md#september-19-candidate-review).
