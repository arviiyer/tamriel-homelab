# Sharing files and screenshots

Use role-based hostnames such as `apps-01`, documentation addresses, and
`example.com` in runnable examples. Keep credentials and installation data in
your own working directory.

## Files

Share individual configuration examples and scripts after checking their
contents. Keep private Git histories, deployment state, raw infrastructure
exports, logs, packet captures, analysis data, and secret-bearing files outside
this repository. Encrypted credentials are still credentials.

Examples should be usable with the documented requirements. Explain any
important difference from the lab setup where it affects those instructions.

## Screenshots

Keep enough of the interface to explain what is shown. Hostnames, IP addresses,
VM IDs, storage paths, versions, and resource usage can remain. Remove secrets,
access-granting URLs, and private personal information, including any in image
metadata. Use a crop or small opaque mask for sensitive content.

The [screenshot checklist](../screenshots/README.md#adding-screenshots) covers
adding an image. Captions should describe the image and identify sample data
or a different application version where relevant.

## Checks

```bash
bash scripts/check-public-safety.sh
python3 scripts/check-markdown-links.py
```

Run the affected component's tests too. Report an exposed secret or another
security issue through [private reporting](../SECURITY.md).
