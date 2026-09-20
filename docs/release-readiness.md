# v1 Release Record

## Decision

**Review date:** September 19, 2026

**Disposition:** Public repository published and signed-out access verified.

**Publication date:** September 19, 2026

**Release version:** `v1.0.0`; the [GitHub release record](https://github.com/arviiyer/tamriel-homelab/releases)
records the published tag and its exact target.

The owner approved publication after the final review, including the bounded
metadata finding below. Visibility is public, the repository description and
topics are applied, and private vulnerability reporting is enabled. The owner
also authorized reviewed release-status commits and the annotated `v1.0.0` tag
and GitHub release after final public CI and signed-out verification pass.

## Verified Publication Baseline

- Revision made public: `c351f9c074d1141e4835708a34e514020230b82b`
- Commit: `docs: reconcile v1 readiness and review results`
- Branch: local `main` and remote `main` matched at publication.
- [GitHub Actions run](https://github.com/arviiyer/tamriel-homelab/actions/runs/35485194349):
  completed successfully on September 19 and is publicly accessible.
- Both jobs passed: **Publication safety** and **Secret scan**.

The final publication checks repeated the full local validation set, current-tree
and retained-history secret scans, the external private-identifier audit, and
screenshot metadata/OCR checks. All three retained Actions logs also passed secret
and private-identifier scans before visibility changed. Review scope and evidence
boundaries are recorded in the [handoff](handoff.md#september-19-publication-review).

Release-status documentation follows this baseline. Verify the exact tagged or
default-branch commit in the
[validation workflow runs](https://github.com/arviiyer/tamriel-homelab/actions/workflows/validate.yml?query=branch%3Amain)
rather than treating a historical run as coverage for later changes.

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

These replace the broader drafts. The project and evidence links are publicly
accessible. The owner requested copy-ready wording rather than an edit to the
resume document. Do not add unevidenced operational clauses from the
[matrix](../evidence/validation-matrix.md).

## GitHub Presentation

Applied repository description:

> Security-engineered homelab portfolio: Proxmox architecture, Trivy alerts,
> restricted delivery, and isolated recovery with tests and reviewed evidence.

Applied topics: `homelab`, `security-engineering`, `devsecops`, `proxmox`,
`trivy`, `ansible`, `docker-compose`, `prometheus`, `grafana`, `infrastructure-as-code`.

Applied profile entry:

```markdown
### [Tamriel Homelab](https://github.com/arviiyer/tamriel-homelab)
Security-engineered self-hosted infrastructure, presented through reviewed
architecture, executable examples, and bounded runtime evidence.

- [Vulnerability deltas and fix-aware alerts](https://github.com/arviiyer/tamriel-homelab/blob/main/docs/case-studies/actionable-vulnerability-management.md)
- [Restricted delivery and disposable-target rollback](https://github.com/arviiyer/tamriel-homelab/blob/main/docs/case-studies/fail-closed-infrastructure-delivery.md)
- [Isolated synthetic restore and storage boundaries](https://github.com/arviiyer/tamriel-homelab/blob/main/docs/case-studies/recovery-and-storage-dependencies.md)
```

The [profile update](https://github.com/arviiyer/arviiyer/commit/b8e4543ce1ab56a558c41c41c6608d649ba3218d)
places Tamriel first, replaces the Tools badge wall with a concise skills line,
and preserves the other projects and certifications. The rendered profile and
new evidence links were verified without authentication. First-position pinning
remains a separate GitHub UI task; it is not inferred from README ordering.

## Private Identifier Audit

The existing denylist in the external evidence workspace's audit directory was
used in place on September 15 and again on September 19. The checker passed for
the current files, staged index, ref-reachable history, and checked metadata and
paths. Its contents were neither displayed nor copied into this repository.
The audit was repeated against the exact `c351f9c` publication snapshot before
visibility changed; later release-documentation changes require the same checks.

This result covers identifiers in the existing list, not a guarantee that every
possible private identifier is represented. Generic secret scans and manual
review remain separate controls.

## Commit Metadata Review

The final September 19 review confirmed that all 16 commits reachable from the
publication snapshot use no-reply author and committer emails. The effective
identity for new commits matches the reviewed public identity. Two superseded
commits retain non-no-reply committer metadata
only in local reflog history; neither is reachable from any current ref, and their
trees match the sanitized replacements.

Authenticated GitHub commit-object requests again returned not found during the
final September 19 review. Remote branch/tag and pull-request inventories showed
only `main` and no pull requests before publication. These checks did not
demonstrate remote exposure, but do not certify server-cache removal or prove
that the old objects were never uploaded. The owner accepted this bounded
limitation before authorizing the visibility change.

An ordinary branch-only `main` push transfers the selected reachable history,
not local reflogs or the whole object database. No rewrite, reflog expiration, or
object pruning was needed for the completed private-staging push. Do not restore
the superseded commits or distribute the local `.git` directory.

## Release Verification

| Check | Publication result |
|---|---|
| Exact-revision checks | Local checks and both CI jobs passed for the publication baseline; release-documentation commits require their own CI result |
| Visibility and security reporting | Public repository; private vulnerability reporting confirmed enabled |
| Anonymous links | All 59 unique publication links passed without authentication at publication; new release links are checked as they are added |
| GitHub rendering | Five Mermaid diagrams and four gallery images loaded in signed-out Chromium |
| Repository and profile presentation | Description, ten topics, and the reviewed profile entry applied and publicly verified |
| Resume | Copy-ready title/link and two bounded bullets supplied at the owner's request |
| Versioned artifact | Owner-authorized annotated `v1.0.0` tag and release, gated on final public CI; verify the target in [GitHub Releases](https://github.com/arviiyer/tamriel-homelab/releases) |

For follow-up changes, keep review and CI tied to the exact candidate revision.
Do not broaden operational claims solely because the repository is now public.

## Follow-Up Scope

The network-migration case study, standalone dependency-update PR, remaining
Prometheus/Loki query execution, live Ansible/Falco transactions, operated
promotion/rollback, and real backup/storage-failure exercises remain separate
evidence tasks. They are not additional minimum-v1 requirements; stronger claims
in those areas remain blocked until their evidence exists.

Fresh validation results and review scope are recorded in the
[handoff](handoff.md#september-19-publication-review).
