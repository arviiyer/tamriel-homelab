# Project Handoff

**Updated:** September 19, 2026

## Current Objective

Maintain the published, evidence-backed portfolio for the actively operated
Tamriel homelab without publishing production secrets, topology, exports, or
private repository history.

The public repository is a purpose-built case study and executable evidence
collection. It is not a deployment source or mirror of the private Forgejo
repositories.

## Repository State

- Workspace: separate local public-portfolio checkout
- Branch: `main`
- Git history: purpose-built public commits reviewed before publication
- Remotes: `origin` points to the public GitHub portfolio repository
- GitHub repository: public as of September 19, 2026
- Release version: `v1.0.0`; verify the annotated tag and target in
  [GitHub Releases](https://github.com/arviiyer/tamriel-homelab/releases)

## September 19 Publication Review

**Decision:** The owner explicitly approved public v1 publication after reviewing
the final checks and bounded commit-metadata limitation. The approved snapshot
`c351f9c074d1141e4835708a34e514020230b82b` was made public on September 19.
Release-status documentation, the prepared repository presentation, the profile
update, and an annotated `v1.0.0` tag/release after final CI were also authorized.

Publication verification:

- The clean local and remote `main` matched the selected publication snapshot.
  Its [validation run](https://github.com/arviiyer/tamriel-homelab/actions/runs/35485194349)
  passed Publication safety and Secret scan and is publicly accessible.
- All 145 Python tests and the full component checks passed again for publication,
  including six PromQL cases, 12 alert rules, Grafana loading, Falco validation,
  Ansible syntax/inventory/apt policy, restricted SSH/sudo, isolated restore,
  systemd policy, ShellCheck, Trivy scanning/compatibility, and the disposable
  target build. The full privileged delivery drill retains its August 24 record.
- The private-identifier audit passed against the exact snapshot, and Gitleaks
  found no secrets in current files or all 18 local commits including reflogs.
  All three retained Actions logs passed both scans before visibility changed.
- Reviewed the 129-path publication inventory, snapshot changes, environment-value
  examples, retained commit inventory, claim mappings, and prior review records.
  The earlier full-file/history audit remains the baseline for unchanged artifacts.
- All 16 ref-reachable commits used public no-reply identities. The two
  superseded reflog-only commits remained outside current refs; fresh GitHub
  commit-object requests returned not found. The owner accepted that these checks
  cannot certify server-cache removal or prove the old objects were never uploaded.
- All four images matched their approved import bytes and passed metadata/OCR
  checks. No new production artifact was imported.
- All 59 unique publication links passed anonymous HTTP checks. Signed-out
  Chromium loaded the README, gallery, and diagram-bearing evidence pages: five
  Mermaid diagrams and four gallery images rendered. Local heading-fragment
  checks passed independently.
- GitHub private vulnerability reporting was enabled and read back as enabled.
  The prepared repository description and ten topics were applied.
- The approved [profile update](https://github.com/arviiyer/arviiyer/commit/b8e4543ce1ab56a558c41c41c6608d649ba3218d)
  places the Tamriel entry first, replaces the Tools badge wall with a concise
  skills line, and preserves the other projects and certifications. Its source,
  rendered profile, and four new links were verified without authentication.

The owner requested copy-ready resume wording rather than a resume-document
edit. The owner subsequently pinned Tamriel first on the
[GitHub profile](https://github.com/arviiyer); the screenshot and GitHub
pinned-items API confirmed it. The [release record](release-readiness.md)
preserves these presentation boundaries. The resume-document edit is the only
remaining presentation follow-up.

The annotated `v1.0.0` tag and GitHub release were published at
`a1a1b707aa76c4bc9c74b50d40674efc14d4c37d` after its
[public CI run](https://github.com/arviiyer/tamriel-homelab/actions/runs/35486327489)
passed both jobs. Final signed-out checks passed for 60 publication links, five
diagrams, four gallery images, and ten release/profile/CI links. Later commits
require their own CI result; GitHub Releases records the fixed v1 target.
Raw check output, OCR, local previews, and profile editing intermediates were
kept outside the portfolio repository.

## September 19 Candidate Review

Historical pre-publication record; the staging commit/push and release decisions
below were subsequently completed as described above.

The previous staging task is complete: `f66028e74001db2025bd134ae5f369d268f90135`
is on `main`, and its
[GitHub Actions run](https://github.com/arviiyer/tamriel-homelab/actions/runs/35025863015)
passed both Publication safety and Secret scan on September 15. The exact
revision and job results were rechecked on September 19. The working tree was
clean at the start of this review; GitHub visibility remains private.

The current working-tree candidate updates the status documents, adds a short
README route to case studies and screenshots, and corrects the vulnerability
case study's stale statement about pending PromQL validation. The two resume
bullets retain their existing evidence boundaries.

**Local result:** Candidate checks passed. The owner authorized one documentation
commit and branch-only push to private staging after checks. The baseline CI
result covers `f66028e`; the candidate commit must receive its own CI result.

Validation completed:

- All 145 Python tests passed, with no failures, errors, or skips.
- Six dashboard PromQL cases, all 12 Prometheus alert rules, Grafana
  provisioning/loading, Falco configuration/rules, and Falcosidekick rendering
  passed.
- Ansible syntax and effective inventory, Debian apt-policy compatibility,
  restricted SSH/sudo policy, systemd validation, and the isolated synthetic
  restore drill passed.
- The disposable delivery image built successfully. The full privileged delivery
  drill retains its August 24 record.
- ShellCheck, all 23 workflow-listed Python compilation checks, Trivy repository
  scanning, and Trivy CLI/schema/baseline compatibility passed. The repository
  scan used the existing path-scoped exception.
- Checksum-verified Gitleaks 8.30.1 found no secrets in the working tree or the 17
  local commits including reflog-only history. The external private-identifier
  audit passed using the existing input in place.
- Local Markdown links, image references, and heading fragments across all 37
  Markdown files passed review checks. Working-tree and retained-history
  whitespace checks passed.

Reader and publication review:

- Followed the README's intended 30-second overview and 90-second evidence paths
  through all three case studies, component documentation, and validation records.
  Reviewed the two resume bullets against the claim matrix and supporting code.
- Rendered all five Mermaid diagrams locally with Mermaid CLI 11.17.0. Local
  Chromium previews of the README, gallery, and three case studies loaded their
  images and anchors without horizontal page overflow; inspected the previews.
  GitHub rendering and signed-out access still require post-publication review.
- Rechecked all four images visually, with OCR, and for PNG metadata. They remain
  byte-identical to the approved image-import commit, RGB-only with IHDR/IDAT/IEND
  chunks, and free of OCR matches against the existing private-identifier list.
- Inventoried all 129 tracked paths and 15 ref-reachable commits. All reachable
  author/committer identities and the effective new-commit identity use no-reply
  emails. The two reflog-only commits still match sanitized reachable trees.
  Remote heads/tags showed only `main`; no pull requests were listed.
- Reviewed the five-file documentation diff manually. The September 15
  full-file/history audit remains the manual baseline for unchanged artifacts;
  the final publication snapshot still requires the release-time review.

Local tools used Python 3.14.7 and Ansible Core 2.21.3; hosted CI uses Python 3.13.
Validation output, local previews, and OCR stayed outside the repository. The
review was completed locally before the authorized staging action. Publication,
profile edits, and tagging still require the separate release decision.

## September 15 Release-Readiness Review

Historical record: the authorized staging commit, push, and exact-revision CI
verification described below were subsequently completed, as recorded above.

**Decision:** Hold publication. The minimum-v1 content and bounded resume/GitHub
wording are prepared in the [release checklist](release-readiness.md), but the
owner's public-release decision remains open. The metadata review permits an
ordinary private-staging push; the owner authorized one commit and branch-only
push of this reviewed change set after final checks. Public visibility, profile
edits, tags, and later unrelated commits are not part of that approval.

Changes prepared:

- Fixed the public Grafana failed-repository counter: summing zero-valued failed
  samples always returned zero; counting them reports the failures correctly.
- Added six pinned-promtool cases against the actual dashboard expression,
  covering healthy, failed, mixed, attempt-only, and missing-telemetry behavior;
  integrated the check into CI and local verification.
- Qualified the operated screenshot's secret-history label beside the image,
  documented Trivy finding-identity continuity limits, and corrected the SSH
  role's unsupported `Match`-policy implication.
- Added architecture/catalog evidence boundaries and replaced overbroad resume
  drafts with two evidence-backed bullets and prepared GitHub presentation.
- Separated optional evidence improvements from minimum-v1 release gates.

Validation completed locally:

- All 145 Python tests passed, with no failures, errors, or skips.
- Six dashboard PromQL regression cases passed; the old expression failed both
  the all-failed and mixed-repository cases before the fix.
- All 12 Prometheus alert rules, Grafana provisioning/loading, Falco dry-run
  configuration/rules, and Falcosidekick Compose rendering passed.
- Ansible playbook syntax, effective inventory, Debian apt-policy compatibility,
  restricted SSH/sudo validation, systemd policy, and the isolated restore drill
  passed.
- The disposable delivery image built successfully. This was build-only, not a
  new privileged delivery or rollback drill; the full drill remains dated August 24.
- ShellCheck and all 23 workflow-listed Python compilation checks passed.
- The pinned Trivy repository scan passed its HIGH/CRITICAL vulnerability,
  misconfiguration, and secret policy with the existing scoped exception.
  CLI/schema compatibility and baseline initialization also passed; the pinned
  Alpine fixture is end-of-life and is not a recommended deployment image.
- Checksum-verified Gitleaks 8.30.1 found no secrets in the working tree or all 16
  local commits, including reflog-only history. This is not an identity audit.
- Generic publication-safety checks, local Markdown links, working-tree
  whitespace, and ref-reachable history whitespace checks passed.
- The private-identifier audit also passed after locating the existing input in
  the external evidence workspace's audit directory. The earlier filename search
  had missed the hidden workspace. The checker used the file in place without
  displaying or importing its values, checking current files, the staged index,
  ref-reachable history, and metadata and paths. This covers the existing list;
  it does not establish that the list contains every possible private identifier.

Local Python was 3.14.7 with Ansible Core 2.21.3; hosted CI uses Python 3.13. The
September 12 GitHub run passed for the starting baseline, not the changes in this
review. After the approved commit and push, verify private staging CI for the
exact new revision; the local results do not substitute for that run.

Manual review covered all 126 tracked files at the starting revision, including
86 non-Markdown text artifacts, 36 Markdown files, and four screenshot/review
pairs. All ref-reachable historical changes were inspected, plus the two
reflog-only commits and two excluded dangling Markdown drafts. Image structure
and visible content were checked; no images changed, and OCR was not repeated.
Generic review found no new source-boundary disclosure in the current/ref-reachable
publication content. It cannot replace the private-identifier audit.

Final review also covered all 17 changed or new publication candidates, including
the PromQL regression and release checklist, with no additional findings.

Remaining safety and release gates:

- Repeat the now-passed private-identifier audit against the final publication
  snapshot. The existing input remains outside the repository in the evidence
  workspace's audit directory; its exact path and values stay private.
- The [commit metadata review](release-readiness.md#commit-metadata-review)
  confirmed that current refs and the effective new-commit identity use no-reply
  emails. Two superseded commits are reachable only through local reflogs, and
  an ordinary branch-only push will not send them. Fresh GitHub commit-object
  requests returned not found; only `main` and no pull requests were visible.
  No rewrite or local pruning is needed for private staging. Remote-retention
  uncertainty remains part of the owner's public-release decision; do not restore
  those commits or publish the local `.git` directory.
- Private vulnerability-reporting availability could not be confirmed during
  private staging. Verify it as part of publication, before relying on the
  reporting channel in `SECURITY.md`.
- Verify private staging CI for the approved commit. The release date, public
  visibility, signed-out links, profile application, and tag still require the
  release sequence and separate owner approvals.

## Completed Work

### Portfolio Foundation

- Recruiter-facing `README.md`
- Publication roadmap and definition of done
- Public/private publication policy
- Content strategy and reader journey
- Sanitized architecture narrative
- Primary trust-boundary and data-flow diagram
- Sanitized network and identity design
- Four public architecture decision records
- Threat model and trust-zone model
- Capability-oriented platform catalog
- Claim-to-evidence matrix
- Screenshot review policy
- Deny-by-default tracked-content allowlist
- Current-tree and retained-history publication-safety checks
- External known-identifier denylist boundary and 17 policy tests
- Public Git metadata rewritten to a GitHub no-reply identity
- External evidence-redaction workspace established with restrictive permissions
- Local Gitleaks current-tree and complete-history scans passed
- Private source audit completed across 14 repositories with refreshed remote
  refs; the historical credential issue was corrected in current source,
  rotated, validated through a fresh login, and documented privately
- Phase 0 publication-safety exit gate met
- Private GitHub staging repository created; default-branch validation and the
  checksum-pinned complete-history secret scan passed
- Tracked paths reviewed with no raw exports or prohibited file types found
- Markdown-link checks
- GitHub workflow with immutable action references
- Gitleaks history-scanning workflow
- Digest-pinned whole-repository Trivy vulnerability, misconfiguration, and
  secret scanning, with one documented path-scoped exception for the
  root-required disposable delivery target
- Private staging default-branch validation passed with the repository scan
  enabled

### Reviewed Runtime Captures

- Four owner-reviewed images in the [runtime gallery](../evidence/screenshots/README.md):
  Trivy finding summary, Forgejo Compose validation, a delivered Discord alert,
  and three-node Proxmox cluster health
- Matching review records retain capture month, source classification, redactions,
  checks, reviewer, and evidence boundaries; visible captions are short and date-free
- Original scan-result timestamp and project-aligned cluster display name retained
  with explicit owner approval; other identifying context cropped or masked
- Originals, intermediate crops, and OCR output remain outside the repository
- Initial Phase 5 capture/review work complete; all four images are public

These are point-in-time observations, not proof of sustained uptime, automatic
failover, completed remediation, or enforced repository protections. Publication
does not strengthen those operational claims.

September 12 pre-commit verification passed: all 145 Python tests, publication
safety including the existing external private-identifier denylist, checksum-pinned Gitleaks scans
of the working tree and retained history, Markdown links, and whitespace checks.
The full required container/tool checks also passed: Ansible syntax, isolated
restore, systemd policy, restricted SSH/sudo policy, Prometheus rules, Trivy
repository scanning, Falco configuration/rules/routing, Grafana provisioning, and
ShellCheck. CI additionally exposed a stale Alpine curl pin in the disposable
delivery-image build. The pin was refreshed and a fresh build passed. The existing
build-only check is now part of the local pre-commit list as well as CI; it does
not execute the privileged drill. The four PNGs match the reviewed drafts
byte-for-byte; metadata and OCR
were rechecked after import. Public visibility and public CI remain release gates.

### Trivy Evidence Slice

Status: **Publicly evidenced implementation and observed finding/alert presentation**

Implemented under `automation/trivy/`:

- Exact-revision repository checkout
- HTTPS/external Git credential boundary
- Compose image extraction with unresolved-variable rejection
- Image, configuration, and current-tree secret scanning
- Explicit baseline initialization
- Baseline schema, file inventory, and SHA-256 integrity manifest
- Stable vulnerability and misconfiguration identities
- Severity-increase and newly-available-fix transitions
- Detailed machine-readable delta report
- Fail-closed baseline promotion and rollback
- Concurrent-run locking
- Separate findings and scan-health metrics
- Twelve Prometheus alert rules
- Actionable vulnerability-management case study

Validation completed:

- 27 tests passed
- Real digest-pinned Trivy 0.73 output passed through `delta.py`
- ShellCheck passed
- Twelve Prometheus rules passed `promtool`
- Reviewed [operated dashboard](../evidence/screenshots/README.md#vulnerability-management)
  and [one delivered fix-aware alert](../evidence/screenshots/README.md#actionable-security-alert)

Remaining proof:

- Ongoing scan completeness and notification reliability if stronger operational
  claims are made; the two captures are not proven to represent the same scan

### Fail-Closed Delivery Evidence Slice

Status: **Publicly evidenced as a validated implementation**

Implemented under `automation/ci/`:

- Manual full-SHA promotion from protected `main`
- Deployment-secret-free exact-revision validation
- Promotion job requiring its label to map to a dedicated ephemeral runner
- Promotion-side metadata recheck without repository-content execution
- Account-wide and per-key forced-command SSH policy
- Source-restricted deployment credential and narrow sudo boundary
- Target-side revision and forward-ancestry validation
- Live Compose drift rejection
- Single-service, image-digest-only candidate policy
- Durable pending transaction and current/previous revision state
- Health-gated state promotion and automatic recovery
- Guarded rollback using the target's recorded previous revision
- Explicit handling for pre-replacement and ambiguous post-replacement state
  write failures
- Fail-closed infrastructure-delivery case study and sequence diagram
- Opt-in network-isolated disposable-target drill using real forced-command SSH,
  sudo, Git, Compose, service health, automatic recovery, and guarded rollback

Validation completed:

- 30 workflow-policy, real-Git, transaction, recovery, and rollback tests passed
- Temporary real Git graph rejected a commit outside protected `main`
- Effective OpenSSH forced command passed for matching and nonmatching sources
- Narrow sudo policy passed `visudo`
- Dated disposable-target exercise passed healthy promotion, shell rejection,
  non-image policy rejection, failed-health recovery, explicit rollback, and
  cleanup
- Reviewed validation record:
  `evidence/drills/2026-08-24-fail-closed-delivery-rollback.md`
- Reviewed [Forgejo Compose validation](../evidence/screenshots/README.md#forgejo-validation)
  associated with a dependency-update PR; this is not promotion or protection evidence

Remaining proof:

- Capture a reviewed operated promotion and rollback result
- Confirm the private repository's required checks and permission boundary
- Confirm the promotion label maps only to a dedicated ephemeral runner
- Repeat on a production-equivalent disposable VM if stronger filesystem and init
  evidence is required

### Ansible Evidence Slice

Status: **Drafted static evidence**

Implemented under `automation/ansible/`:

- Sanitized RFC 5737 example inventory
- Separate hypervisor and service-host SSH policies
- Early-precedence OpenSSH drop-in
- Explicit key and console-recovery attestations
- Rejection of password connection variables
- Rejection of competing cumulative controls, `Match` blocks, extra includes,
  symlinked drop-ins, and nested includes
- Candidate and complete OpenSSH syntax validation
- Systemd rollback watchdog for changed SSH policy
- Fresh SSH reconnect and per-user/per-source `sshd -T -C` validation
- Rollback timer/service cancellation and checksum commit boundary
- Debian security-only unattended-upgrades origin pattern
- Exact cumulative-origin clearing and case-insensitive merged-policy validation
- Isolated apt candidate parsing and paired-policy rollback
- Automatic reboot disabled
- Serial full upgrades with separate cleanup tasks and failure-phase reporting

Validation completed:

- 18 static policy tests passed
- Baseline and controlled-upgrade playbooks passed Ansible syntax checks
- Effective example inventory precedence passed
- Digest-pinned Debian 13 `apt-config` compatibility passed

Remaining proof:

- Execute SSH and apt transactions on a disposable Debian host with active
  console access
- Intentionally trigger rollback and record the result
- Re-run to prove idempotency
- Record controlled-upgrade success and failure behavior

Until that live exercise exists, do not describe this slice as operated or
fully executable evidence in the public claim matrix.

### Falco Evidence Slice

Status: **Drafted static evidence**

Implemented under `automation/falco/`:

- Exact Falco package version and checksum-pinned package-signing key
- Modern eBPF target and BPF JIT preconditions
- Parameterized, credential-free Falcosidekick endpoint
- Container-context plugin and required JSON event output
- Candidate configuration and rules validation before activation
- Immutable local-rules releases and managed-configuration rollback
- Loopback process-health verification across a stability interval
- Automatic ruleset mutation disabled
- Two synthetic exceptions constrained by process and workload identity
- Digest-pinned, non-root, read-only Falcosidekick Compose example
- Separate Loki and Alertmanager priority thresholds
- Synthetic event contract and runtime event-flow document

Validation completed:

- 15 offline policy tests passed
- Falco 0.44.1 accepted the rendered configuration and both rulesets
- Falcosidekick 2.34.1 Compose rendering passed
- Falco deployment playbook passed Ansible syntax validation

Remaining proof:

- Execute deployment and an intentional rollback on a disposable compatible
  Debian guest
- Capture a reviewed operated alert or dashboard screenshot
- Confirm the event reaches both the log and alerting paths

### Security Dashboard Evidence Slice

Status: **Drafted static evidence**

Implemented under `automation/monitoring/`:

- Purpose-written dashboard with 18 query and visualization panels organized
  under three row headers
- Separate control-health, actionable-finding, and runtime-detection sections
- Current public Trivy metric and `repository` label contracts
- Zero-finding fallbacks gated by the successful-baseline timestamp
- Falco Loki queries using the public `source="syscall"` stream contract
- Synthetic Prometheus and Loki datasource UIDs and `example.com` endpoints
- File-owned dashboard provisioning with UI updates disabled
- Dashboard descriptions that state what each panel does and does not prove

Validation completed:

- 11 structural, query-reference, provisioning, and publication-safety tests
  passed
- Grafana 12.4.1 loaded both datasources and the dashboard from read-only
  provisioning mounts
- The Grafana API returned the expected dashboard and folder UIDs
- Reviewed [operated Trivy dashboard capture](../evidence/screenshots/README.md#vulnerability-management)
  linked to Trivy evidence; not a capture of this public provisioning example

Remaining proof:

- Validate the remaining queries against synthetic Prometheus and Loki data;
  the failed-repository counter now has six executable PromQL cases
- Publish selected sanitized central scrape and log configuration
- Validate the public dashboard's behavior independently of the operated Trivy view
- Capture separate Falco runtime evidence before strengthening that claim

### Recovery and Storage Evidence Slice

Status: **Publicly evidenced synthetic restore and executable storage policy**

Implemented under `automation/recovery/`:

- Strict synthetic model separating service-local state from shared bulk data
- Illustrative generation labels with no private schedule or retention claim
- Bounded uncompressed-tar format and exact manifest inventory
- External and per-file SHA-256 integrity checks
- Duplicate-key, schema, boundary, path, member-type, size, and digest rejection
- No-follow archive opening and bounded immutable byte snapshot
- Private sibling staging with fixed modes and synchronized files
- Atomic no-replace destination publication and failed-staging cleanup
- Hardened storage-dependent systemd service with mount and boundary assertions
- Dynamic malicious fixtures and an offline unprivileged restore drill
- Recovery and storage-dependency case study and inline flow diagram

Validation completed:

- 27 model, archive, restore, cleanup, CLI, and systemd policy tests passed
- Dated drill passed valid restore, corruption, traversal, link, boundary, path
  absence, and cleanup scenarios
- `systemd-analyze verify` accepted the storage-readiness unit
- Publication-safety policy now rejects common backup, dump, archive, VM-image,
  and restore-output paths
- Reviewed validation record:
  `evidence/drills/2026-08-24-isolated-synthetic-restore.md`

Remaining proof:

- Private PBS, Restic, snapshot, retention, integrity, and alerting evidence
- Runtime storage mount, marker, startup refusal, and mount-loss exercise
- Application-specific or VM-level isolated restore evidence
- Reviewed backup or recovery runtime screenshot

The public archive format is purpose-written synthetic evidence. Do not describe
it as PBS, Restic, VM-image, database, or operated private-platform recovery.

## Current Validation Commands

Run from the repository root:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m unittest discover -s automation/trivy/tests -p 'test_*.py' -v
python3 -m unittest discover -s automation/ansible/tests -p 'test_*.py' -v
python3 -m unittest discover -s automation/ci/tests -p 'test_*.py' -v
python3 -m unittest discover -s automation/falco/tests -p 'test_*.py' -v
python3 -m unittest discover -s automation/monitoring/tests -p 'test_*.py' -v
python3 automation/monitoring/tests/validate_promql.py
python3 -m unittest discover -s automation/recovery/tests -p 'test_*.py' -v
python3 automation/recovery/tests/run_isolated_restore_drill.py
systemd-analyze verify --recursive-errors=no \
  automation/recovery/systemd/example-storage-dependent.service
bash automation/ci/tests/validate_target.sh
bash automation/ci/tests/run_disposable_host_drill.sh --build-only
bash scripts/check-public-safety.sh
python3 scripts/check-markdown-links.py
docker run --rm -v "$PWD:/workspace:ro" \
  aquasec/trivy@sha256:7cced7cae583819fc7806d4cbc0dbbc7cad18b99f7d3e235192e6da8c091045c \
  fs --scanners vuln,misconfig,secret --severity HIGH,CRITICAL --exit-code 1 \
  --ignorefile /workspace/automation/trivy/repository-ignore.yaml \
  --no-progress --skip-version-check /workspace
git diff --check
```

The private release gate additionally runs the same safety checker with
`PUBLIC_SAFETY_DENYLIST_FILE` set to the fixed-string identifier file maintained
outside this repository. Never copy that file or its values into this workspace.

Ansible syntax validation requires `ansible-core==2.21.3`:

```bash
cd automation/ansible
ansible-playbook --syntax-check playbooks/site.yml
ansible-playbook --syntax-check playbooks/controlled-upgrade.yml

cd ../falco
ansible-playbook --syntax-check playbooks/falco.yml
```

Container-backed checks and immutable image digests are documented in
`AGENTS.md` and `.github/workflows/validate.yml`.

The privileged integration drill is intentionally opt-in rather than part of
normal CI:

```bash
bash automation/ci/tests/run_disposable_host_drill.sh
```

## Known Publication Gates

- Never publish raw OPNsense XML exports.
- Never copy private `.git` directories or histories.
- Preserve screenshot review records and the distinction between observed results
  and unverified operational claims.
- Repeat the tracked-file and complete-history review immediately before the
  repository becomes public.

## Resume Evidence Status

- Trivy delta-based vulnerability scanning: publicly evidenced implementation,
  reviewed finding presentation, and one observed delivered notification.
- Exact-revision fail-closed delivery: publicly evidenced as validated on an
  isolated disposable synthetic target; operated promotion/rollback evidence pending.
- Forgejo Compose validation: one successful run associated with a dependency-update
  PR is publicly evidenced; enforced merge checks and permissions remain unverified.
- Ansible hardening and patching: drafted static evidence; live transaction
  pending.
- Architecture and threat model: Phase 2 narrative complete with a primary
  trust-boundary diagram, network and identity design, and four ADRs; reviewed
  three-node cluster health now supports point-in-time platform evidence, not
  sustained availability or broader network/storage claims.
- Falco runtime detection: drafted static evidence; live transaction and runtime
  alert pending.
- Security observability dashboard: drafted evidence; six synthetic PromQL cases
  cover the failed-repository counter, while other query execution and central
  configuration remain pending. The reviewed operated Trivy view
  does not validate the public dashboard's queries or Falco panels.
- Isolated synthetic restore: publicly evidenced; private backup implementation
  and operated recovery evidence pending.
- Storage-readiness startup policy: executable static evidence; live mount and
  boot-failure transaction pending.
- Networking: drafted design; zone-policy validation and operated evidence
  pending.

The [finalized bounded resume wording](release-readiness.md#resume-wording) maps
only to `Publicly evidenced` rows in `evidence/validation-matrix.md`. Apply it to
the actual resume after public access and signed-out links are verified.

## Next Restart Point

The repository is public. Use the publication review and release record above,
the exact GitHub Actions revision, and the versioned release as the current
reference. Keep the external redaction workspace outside this checkout.

Recommended order:

1. Re-read `AGENTS.md`, this handoff, and the publication policy.
2. Verify the checked-out revision, public CI, and release tag before describing a
   snapshot as validated. Historical runs cover only their recorded revisions.
3. Complete the owner-managed resume-document edit if still outstanding.
4. Select one optional evidence task below. Keep drafted operational claims
   bounded until that evidence exists.
5. Review, validate, and obtain commit/push approval for new changes. Use the
   existing external private-identifier audit input in place; do not import it.

Do not use the public repository as a deployment checkout or connect any exercise
to a production target. The disposable-host Ansible and Falco exercises remain
separate evidence tasks.

## Optional Follow-Up Evidence

1. Remaining Prometheus/Loki query execution and central telemetry configuration
2. Disposable-host Ansible and Falco transactions
3. Network segmentation and migration postmortem
4. Dependency-update, operated promotion/rollback, and private backup/recovery evidence

These are not additional minimum-v1 gates. Keep their claims limited until the
corresponding evidence exists.
