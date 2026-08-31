# Project Handoff

**Updated:** August 31, 2026

## Current Objective

Build a resume-worthy public portfolio for the actively operated Tamriel
homelab without publishing production secrets, topology, exports, or repository
history.

The public repository is a purpose-built case study and executable evidence
collection. It is not a deployment source or mirror of the private Forgejo
repositories.

## Repository State

- Workspace: separate local public-portfolio checkout
- Branch: `main`
- Git history: purpose-built public commits sanitized, rewritten, and pushed
  only to the private GitHub staging repository
- Remotes: `origin` points to the private GitHub staging repository
- GitHub repository: private; not yet published
- Publication status: private remote work in progress

Do not make the repository public until the v1 publication gate in `ROADMAP.md`
is met.

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

### Trivy Evidence Slice

Status: **Executable evidence**

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

Remaining proof:

- Redacted Grafana or alert screenshot from the operated environment
- Publicly visible GitHub Actions result after publication

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

Remaining proof:

- Capture a reviewed Forgejo validation and promotion result
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
- Record a publicly visible GitHub Actions result after publication

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

Remaining proof:

- Validate the queries against synthetic Prometheus and Loki data
- Publish selected sanitized central scrape and log configuration
- Capture and review an operated dashboard screenshot
- Link the screenshot to the Trivy and Falco evidence claims

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
python3 -m unittest discover -s automation/recovery/tests -p 'test_*.py' -v
python3 automation/recovery/tests/run_isolated_restore_drill.py
systemd-analyze verify --recursive-errors=no \
  automation/recovery/systemd/example-storage-dependent.service
bash automation/ci/tests/validate_target.sh
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
- Add four reviewed runtime screenshots.
- Repeat the tracked-file and complete-history review immediately before the
  repository becomes public.

## Resume Evidence Status

- Trivy delta-based vulnerability scanning: executable evidence; runtime
  screenshot pending.
- Exact-revision fail-closed delivery: publicly evidenced as validated on an
  isolated disposable synthetic target; operated workflow evidence pending.
- Ansible hardening and patching: drafted static evidence; live transaction
  pending.
- Architecture and threat model: Phase 2 narrative complete with a primary
  trust-boundary diagram, network and identity design, and four ADRs; runtime
  evidence pending.
- Falco runtime detection: drafted static evidence; live transaction and runtime
  alert pending.
- Security observability dashboard: drafted static evidence; synthetic query
  execution and operated screenshot pending.
- Isolated synthetic restore: publicly evidenced; private backup implementation
  and operated recovery evidence pending.
- Storage-readiness startup policy: executable static evidence; live mount and
  boot-failure transaction pending.
- Networking: drafted design; zone-policy validation and operated evidence
  pending.

Do not finalize the resume bullets until all clauses map to `Publicly evidenced`
rows in `evidence/validation-matrix.md`.

## Next Restart Point

Prepare the four initial runtime screenshots in the established external review
workspace.

Recommended order:

1. Re-read `AGENTS.md`, this handoff, and the publication policy.
2. Map each screenshot to one claim in the validation matrix before capture.
3. Prioritize the Grafana security dashboard, Forgejo validation result, security
   alert or scan result, and Proxmox cluster summary.
4. Crop, apply opaque redaction, strip metadata, run OCR, and obtain the required
   second review.
5. Add only final reviewed images with matching `.review.md` records.

Do not use the public repository as a deployment checkout or connect any exercise
to a production target. The disposable-host Ansible and Falco exercises remain
separate evidence tasks.

## Later Order

1. Network segmentation and migration postmortem
2. Disposable-host Ansible and Falco exercises
3. Publication review, profile, and resume alignment
