# Security Policy

## Scope

This repository contains homelab examples and must not contain live
deployment credentials or production configuration.

## Reporting

Report security issues through [GitHub private vulnerability reporting](https://github.com/arviiyer/tamriel-homelab/security/advisories/new).
Do not open a public
issue containing the suspected secret or private infrastructure detail.

## Response

If sensitive material is discovered:

1. Treat the affected credential or key as exposed.
2. Rotate or revoke it in the private environment.
3. Remove the material from the public branch and history.
4. Check nearby files and source repositories for related exposure.
5. Document the public corrective action without reproducing the secret.

History rewriting is not a substitute for credential rotation.
