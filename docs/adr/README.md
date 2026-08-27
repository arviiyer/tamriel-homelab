# Architecture Decision Records

These short records capture the transferable decisions behind the sanitized
public architecture. They describe decision boundaries and consequences rather
than production topology or configuration.

| ADR | Decision | Public evidence status |
|---|---|---|
| [0001](0001-private-management-access.md) | Keep management access private by default | Drafted architecture evidence |
| [0002](0002-separate-transactional-and-bulk-state.md) | Separate transactional state from shared bulk storage | Drafted private design; public storage policy is executable evidence |
| [0003](0003-separate-validation-from-promotion.md) | Separate change validation from privileged promotion | Publicly evidenced as a validated implementation |
| [0004](0004-restore-before-replacement.md) | Restore into isolation before authoritative replacement | Publicly evidenced for the synthetic restore boundary |

`Accepted` means the decision is part of the represented architecture. It does
not by itself mean that implementation or operation is publicly evidenced. The
[claim-to-evidence matrix](../../evidence/validation-matrix.md) remains the
authority for public claim status.
