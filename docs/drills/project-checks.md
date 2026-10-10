# Project example checks

[Projects](../../projects/README.md) · [Setup guide checks](setup-guide-checks.md)

Checked on October 10, 2026. The examples ran locally or in disposable containers.
Generated files, models, and test data stayed outside the repository.

## Results

| Project | Checked |
|---|---|
| Printer Monitor | Three Python tests, installation into an empty home directory, JSON sample output, and the GTK sample window. The local CUPS queue was available while its printer was offline. |
| Reading brief | Seven Python tests, sample publication, read-only JSON/RSS routes, unavailable-first-brief handling, and retaining the previous brief after inference failure. Export ran against a disposable FreshRSS account. The pinned GGUF downloaded with the expected SHA-256; the actual llama.cpp container tokenized both sample articles and returned valid sentence IDs. |
| Seerr approver | Eight Go tests with the race detector and `go vet`; Docker build. Fake Seerr/Discord transports checked permissions, CSRF, webhook authentication, owner/location checks, signed actions, approval replay, denial/cancellation, stale requests, and avoiding blind write retries. |
| Forge | Five Go tests with the race detector and `go vet`; Terraform formatting, provider validation, and a two-VM mocked plan. Browser checks launched a second sample VM, retained the protected first VM, toggled protection, and destroyed only the new VM. |
| Sandbox | Four Python tests and all four generated browser scenarios: completed, stopped, missing evidence, and failed reset. |

The project index and all five guides passed local Markdown link checks and
Chromium rendering at 1280-pixel and 390-pixel widths, including diagrams and
images. The Forge and Sandbox demo interfaces also fit the narrow viewport.

The model-container smoke test caught an unquoted YAML flow-list entry in the
temporary mount options. Quoting the complete mount fixed startup; the actual
model check then passed.

## Scope of these results

- Jev's live ranking API was not called. The model check covers local sentence
  selection, not the quality of a complete ranked daily brief.
- Discord Gateway delivery and real Seerr decisions need a configured bot and
  test requests. The tests exercise the REST interaction handlers with fixtures.
- Forge's plan checks used a mocked provider. They did not create, power, or
  destroy a VM on the lab cluster.
- Sandbox's public viewer replays generated events. It does not validate a
  Windows agent, hypervisor reset, console relay, or network isolation.

## Repeat the checks

From the repository root:

```bash
python3 -m unittest discover -s projects/printer-monitor/tests -v
python3 -m unittest discover -s projects/reading-brief/tests -v
python3 -m unittest discover -s projects/sandbox/tests -v
go -C projects/seerr-discord-approver test -race ./...
go -C projects/seerr-discord-approver vet ./...
go -C projects/forge test -race ./...
go -C projects/forge vet ./...
bash projects/forge/check-terraform.sh
docker build -t seerr-approver-check projects/seerr-discord-approver
python3 scripts/check-markdown-links.py
```

The [project workflow](../../.github/workflows/projects.yml) runs the unit,
configuration, and mocked Terraform checks. Follow each guide's first-task
section for the interactive checks and live integrations.
