# Diagrams

Diagram sources remain inline beside their explanatory context. Exported assets
will live here only if the publication format later requires them.

Diagrams use role-based aliases and emphasize trust boundaries, control flow,
and state ownership. They do not include production addresses, domains, host
identities, or management paths.

Available inline diagrams:

- [Primary platform trust-boundary and data-flow model](../README.md#architecture)
- [Vulnerability scan and alert pipeline](../automation/trivy/README.md#data-flow)
- [Runtime detection event flow](../automation/falco/event-flow.md#runtime-event-flow)
- [Pull request to controlled deployment sequence](../docs/case-studies/fail-closed-infrastructure-delivery.md#trust-flow)
- [Backup verification to isolated restore flow](../docs/case-studies/recovery-and-storage-dependencies.md#recovery-flow)

An exported standalone asset is not currently required because GitHub renders
the reviewed Mermaid sources directly beside their explanatory context.
