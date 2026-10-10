# Roadmap

## Documentation

- Add reviewed screenshots of Homarr, Immich, FreshRSS, Jellyfin or Seerr,
  general Grafana monitoring, and TrueNAS or PBS beside their descriptions. The
  [screenshot notes](evidence/screenshots/README.md#next-captures) list useful views.
- Replace the Trivy dashboard capture after correcting its file-scan panel label.
- Identify the exact Speedtest application and add its setup and project link.
- Review the deployed Readarr and Promtail setups before writing installation
  guides for them.
- Add small configuration examples for CrowdSec, ClamAV, Terraform provisioning,
  and Renovate as their guides grow.

## Lab and automation

- Test the remaining Grafana queries with generated Prometheus and Loki data.
- Try Ansible SSH/update changes and Falco deployment, including rollback, on
  disposable Debian hosts.
- Test network segmentation, DNS, and authentication flows; write up the failed
  network migration.
- Check Forgejo branch protections and deployment-runner permissions.
- Document dependency updates, deployment runs, and backup/restore exercises.
- Test service startup with a missing or incorrect storage mount.
