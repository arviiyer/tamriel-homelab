# Roadmap

## Documentation

The [documentation plan](docs/documentation-plan.md) records the comparison with
TechHut's homelab, proposed layout, inputs needed, and work order.

- [ ] Confirm the application inventory, personal usage, and three services to feature.
- [x] Update the homepage and publish category introductions with working navigation.
- [x] Start the service catalogue with the tools documented in this repository.
- [ ] Add personal applications, usage notes, and setup links to the catalogue.
- [x] Place existing screenshots beside the relevant service descriptions.
- [ ] Add reviewed personal-app, general monitoring, and storage/backup captures.
- [ ] Expand category guides with confirmed provisioning, GPU, DNS/sign-in, and application backup details.
- [ ] Add the first personal-app, networking, and monitoring examples.
- [x] Allow the new category folders and check local image and heading links.
- [ ] Extend configuration validation to new example locations as examples are added.

The [homepage](README.md), [documented-services catalogue](apps/README.md),
category introductions, and existing screenshots are connected. Completing the
first milestone needs the personal app inventory and new reviewed captures.
The plan lists the details to collect.

## Lab and automation

- Test the remaining Grafana queries with generated Prometheus and Loki data.
- Try Ansible SSH/update changes and Falco deployment, including rollback, on
  disposable Debian hosts.
- Test network segmentation, DNS, and authentication flows; write up the failed
  network migration.
- Check Forgejo branch protections and deployment-runner permissions.
- Document dependency updates, deployment runs, and backup/restore exercises.
- Test service startup with a missing or incorrect storage mount.
