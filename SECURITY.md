# Security Policy

## Scope

This repository contains sanitized portfolio examples and must not contain live
deployment credentials or production configuration.

## Reporting

After public release, report suspected credential exposure or unsafe
publication through GitHub private vulnerability reporting. Do not open a public
issue containing the suspected secret or private infrastructure detail.

## Response

If sensitive material is discovered:

1. Treat the affected credential or key as exposed.
2. Rotate or revoke it in the private environment.
3. Remove the material from the public branch and history.
4. Review adjacent artifacts and source repositories for related exposure.
5. Document the public corrective action without reproducing the secret.

History rewriting is not a substitute for credential rotation.
