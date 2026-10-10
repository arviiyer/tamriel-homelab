# Roadmap

## Lab and automation

- Test the remaining Grafana queries with generated Prometheus and Loki data.
- Try Ansible SSH/update changes and Falco deployment, including rollback, on
  disposable Debian hosts.
- Migrate existing Promtail hosts to Alloy and review the remaining Readarr use
  now that its upstream project is retired.
- Test routed VLAN and tailnet access with disposable clients.
- Plan the management/server VLAN split separately from the existing client zones.
- Connect UPS USB monitoring and configure low-battery shutdown through NUT.
- Check Forgejo branch protections and deployment-runner permissions.
- Document dependency updates, deployment runs, and backup/restore exercises.
- Test service startup with a missing or incorrect storage mount.
