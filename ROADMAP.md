# Publication Roadmap

## Objective

Publish a resume-worthy, technically credible representation of an actively
operated homelab without exposing production secrets, topology, or operational
history.

The finished repository must let a recruiter understand the platform in 30
seconds and let a technical reviewer verify a meaningful claim within 90
seconds.

## Positioning

**Project name:** Tamriel Homelab

**Subtitle:** Security-Engineered Self-Hosted Infrastructure

**Primary audiences:** Security Engineering, Cloud Security, DevSecOps, and
SOC/Detection Engineering hiring teams.

The complete homelab is represented through five engineering pillars:

1. Platform and storage
2. Network segmentation and identity
3. Detection and observability
4. Automation and controlled delivery
5. Backup, recovery, and operational resilience

Security is the design principle across the platform, not a separate list of
tools.

## Phase 0: Publication Safety

**Status:** In progress

- [x] Create a separate repository outside all production repositories.
- [x] Start a fresh Git history with no production commits or reflogs.
- [x] Use a deny-by-default `.gitignore` for new top-level content.
- [x] Document the public/private source boundary.
- [ ] Complete remediation of credentials identified in private source audits.
- [ ] Confirm raw infrastructure exports are excluded from every public path.
- [ ] Establish a temporary evidence-redaction workspace outside this repo.
- [ ] Complete a history-wide secret scan before the first public push.

**Exit gate:** No known production credential, raw export, or private history is
present in the repository, and all known source-repository credential issues
have a documented private remediation outcome.

## Phase 1: Portfolio Foundation

**Status:** In progress

- [x] Define the project name and positioning.
- [x] Draft the recruiter-facing README structure.
- [x] Define the publication policy and screenshot review process.
- [x] Create an initial claim-to-evidence matrix.
- [ ] Add repository topics and final GitHub description at publication time.
- [ ] Choose and document the public v1 release date.

**Exit gate:** The repository explains its purpose, scope, safety model, and work
plan without relying on private documentation.

## Phase 2: Architecture Narrative

**Status:** In progress

- [ ] Produce the primary trust-boundary and data-flow diagram.
- [x] Document the sanitized platform architecture.
- [x] Document the threat model and control rationale.
- [x] Create a capability-oriented platform catalog.
- [ ] Document network and identity design.
- [ ] Document delivery and recovery design.
- [ ] Record key architecture decisions as short ADRs.

**Exit gate:** A reader can understand the platform without seeing any production
identifier or raw configuration.

## Phase 3: Executable Automation Evidence

**Status:** In progress

- [x] Extract and harden the Trivy scan pipeline.
- [x] Correct and test vulnerability delta identity behavior.
- [x] Add synthetic Trivy fixtures and Python unit tests.
- [x] Publish sanitized Prometheus security alert rules.
- [x] Publish sanitized Grafana dashboard provisioning.
- [x] Publish selected Ansible hardening roles with example inventory.
- [x] Publish generic Falco deployment and narrow tuning examples.
- [x] Publish a sanitized exact-revision CI/CD example.
- [x] Add component-level usage and verification documentation for Trivy.
- [x] Add component-level usage and verification documentation for Ansible.

**Exit gate:** Public automation runs against synthetic data and passes CI from a
clean checkout without production access.

## Phase 4: Engineering Case Studies

**Status:** In progress

- [x] Actionable vulnerability management and alert-noise reduction
- [x] Fail-closed infrastructure delivery and rollback
- [ ] Network migration failure, blast-radius analysis, and redesign
- [ ] Backup, isolated restore, and storage dependency management

Each case study must include the problem, constraints, decision, implementation,
validation, result, and limitations.

**Exit gate:** At least three case studies connect a design decision to public
code or reviewed runtime evidence.

## Phase 5: Runtime Evidence

**Status:** Planned

- [ ] Capture a Grafana security dashboard.
- [ ] Capture a successful Forgejo pull-request validation run.
- [ ] Capture a reviewed security alert or scan result.
- [ ] Capture a Proxmox cluster summary.
- [ ] Capture a dependency-update pull request.
- [ ] Perform and document a safe restore or rollback drill.
- [ ] Redact, strip metadata from, and OCR-review selected screenshots.

The initial release should use four high-quality screenshots rather than a large
gallery.

**Exit gate:** Every published screenshot has a date, purpose, redaction record,
and corresponding public claim.

## Phase 6: Public Validation

**Status:** Started

- [x] Add a local publication-safety check.
- [x] Add baseline GitHub validation and secret scanning.
- [x] Add ShellCheck for published shell automation.
- [x] Add Ansible syntax validation.
- [x] Add Prometheus rule validation.
- [x] Add Grafana JSON validation.
- [x] Add Markdown link validation.
- [ ] Add Trivy repository scanning.
- [x] Confirm all current actions are pinned to immutable commit SHAs.

**Exit gate:** Default-branch CI is green and validates every executable artifact
published in the repository.

## Phase 7: Resume and GitHub Alignment

**Status:** Planned

- [ ] Finalize two evidence-backed resume bullets.
- [ ] Link the project title directly to the public repository.
- [ ] Add the project to the GitHub profile README.
- [ ] Pin it as the first recruiter-facing repository.
- [ ] Replace the profile badge wall with concise project evidence.
- [ ] Ensure repository description and topics match resume terminology.

**Exit gate:** Resume, GitHub profile, and repository use the same defensible
claims and terminology.

## Phase 8: Public v1 Release

**Status:** Planned

- [ ] Review every tracked file manually.
- [ ] Run local validation and secret scanning.
- [ ] Review the complete public Git history.
- [ ] Create the GitHub repository only after the review passes.
- [ ] Push and confirm public CI.
- [ ] Test every README link while signed out of GitHub.
- [ ] Tag `v1.0.0` after the public page is verified.

## Version 1 Scope

### Required

- Recruiter-facing README
- Sanitized architecture diagram and threat model
- Capability-oriented platform catalog
- Selected executable automation with tests
- At least three engineering case studies
- Four reviewed runtime screenshots
- One dated recovery or rollback drill
- Claim-to-evidence matrix
- Green public CI and secret scanning

### Excluded

- Production repository mirrors or histories
- Raw firewall and network-controller exports
- Full media/download stack configuration
- Exact infrastructure topology or emergency procedures
- Malware sandbox source code
- Real malware, PCAPs, logs, or evidence
- A separate portfolio website

## Definition of Done

The repository is resume-ready when:

- the platform and its ownership are clear within 30 seconds;
- a reviewer can verify a nontrivial claim within 90 seconds;
- every headline claim links to evidence;
- public CI passes from a clean checkout;
- no production secret or identifying topology is present;
- screenshots prove real operation without leaking private details;
- at least one failure or recovery exercise is documented;
- limitations are stated honestly; and
- resume wording exactly matches what the repository demonstrates.
