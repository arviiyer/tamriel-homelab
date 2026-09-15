# AGENTS.md

## Scope

This repository is the sanitized public portfolio for the Tamriel homelab. It is
not the production source of truth and must never become a deployment checkout.

The repository has two goals:

- explain the architecture and engineering decisions clearly to recruiters and
  technical reviewers;
- provide safe, executable evidence for selected security, automation,
  observability, delivery, and recovery claims.

## Read First

- `ROADMAP.md`
- `docs/publication-policy.md`
- `docs/content-plan.md`
- `evidence/validation-matrix.md`

## Source Boundary

- Private production repositories and their Git histories stay outside this
  repository.
- Never add a GitHub remote to a production repository for publication.
- Never copy a production repository wholesale, including its `.git` directory.
- Import only individual, reviewed artifacts. Rewrite environment-specific
  configuration around public examples and synthetic fixtures.
- Never use this repository to store deployment credentials or live state.

## Publication Rules

- Use public aliases such as `pve-01`, `apps-01`, and `security-01`.
- Use RFC 5737 documentation addresses and `example.com` in public examples.
- Do not publish real IP addresses, domains, VM IDs, MAC addresses, host keys,
  fingerprints, account names, paths, schedules, or emergency procedures.
- Do not publish raw firewall exports, encrypted secret blobs, private keys,
  secret-bearing environment files, state files, logs, malware, PCAPs, or
  captured evidence.
- Do not publish the complete production detection-suppression set.
- Real screenshots must pass the checklist in
  `evidence/screenshots/README.md` and be force-added after review.
- Every headline claim must link to code, public CI, a sanitized validation
  record, or reviewed runtime evidence.

## Editing Approach

- Prefer a small, purpose-written public example over a large sanitized dump.
- Preserve the behavior and engineering decision being demonstrated, not the
  production identifiers around it.
- Mark planned or unverified work honestly. Do not turn design intent into a
  completed claim.
- Keep documentation recruiter-readable first, with implementation detail one
  link away.

## Verification

Run before every commit:

```bash
bash scripts/check-public-safety.sh
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
(cd automation/ansible && ansible-playbook --syntax-check playbooks/site.yml)
(cd automation/ansible && ansible-playbook --syntax-check playbooks/controlled-upgrade.yml)
(cd automation/falco && ansible-playbook --syntax-check playbooks/falco.yml)
docker run --rm -v "$PWD:/workspace:ro" --entrypoint promtool \
  prom/prometheus@sha256:508729e0e2d18e11fd742a5a5ca70e557b940a93948c3c95fd0123a6fd538b69 \
  check rules /workspace/automation/trivy/prometheus-rules.yml
docker run --rm -v "$PWD:/workspace:ro" \
  aquasec/trivy@sha256:7cced7cae583819fc7806d4cbc0dbbc7cad18b99f7d3e235192e6da8c091045c \
  fs --scanners vuln,misconfig,secret --severity HIGH,CRITICAL --exit-code 1 \
  --ignorefile /workspace/automation/trivy/repository-ignore.yaml \
  --no-progress --skip-version-check /workspace
python3 automation/falco/tests/render_config.py /tmp/tamriel-falco.yaml
docker run --rm \
  -v /tmp/tamriel-falco.yaml:/tmp/falco.yaml:ro \
  -v "$PWD/automation/falco/roles/falco/files/falco_rules.local.yaml:/etc/falco/falco_rules.local.yaml:ro" \
  --entrypoint falco \
  falcosecurity/falco@sha256:d0cfe422d6ac0e0f20857798f46c7d7273210e1b064b22821e4e6e7f843cde6b \
  --dry-run -c /tmp/falco.yaml \
  -r /etc/falco/falco_rules.yaml \
  -r /etc/falco/falco_rules.local.yaml
docker compose --env-file automation/falco/falcosidekick/environment.example \
  -f automation/falco/falcosidekick/compose.yml config --quiet
rm -f /tmp/tamriel-falco.yaml
python3 automation/monitoring/tests/validate_grafana.py
git diff --check
```

Run artifact-specific tests documented beside each automation component as they
are added.
