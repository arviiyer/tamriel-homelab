# Roadmap

## Documentation

The [documentation plan](docs/documentation-plan.md) records the comparison with
TechHut's homelab, proposed layout, inputs needed, and work order.

- [x] Review the application inventory and usage in the private reference and service repositories.
- [x] Add Immich, FreshRSS, and Jellyfin setup notes linked from the catalogue.
- [x] Update the homepage and publish category introductions with working navigation.
- [x] Start the service catalogue with the tools documented in this repository.
- [x] Add personal applications, usage notes, and setup links to the catalogue.
- [x] Place existing screenshots beside the relevant service descriptions.
- [ ] Add reviewed personal-app, general monitoring, and storage/backup captures.
- [x] Expand category guides with provisioning, GPU, DNS/sign-in, and application backup details.
- [x] Add a Media page covering Jellyfin, Seerr, the download stack, and storage.
- [x] Add the first personal-app, networking, and monitoring examples: Syncthing, Caddy, and host metrics.
- [x] Allow the new category folders and check local image and heading links.
- [x] Extend configuration validation and integration checks to the new examples.
- [ ] Identify the exact Speedtest application and add its setup and project link.
- [ ] Review the age and maintenance status of the deployed Readarr and Promtail setups before writing installation guides for them.

The [homepage](README.md), [app catalogue](apps/README.md), category guides, and
existing screenshots are connected. The inventory comes from the private
architecture reference, dated service notes, and Compose definitions. New
application, general-monitoring, and storage screenshots remain to be collected
and reviewed. The [documentation plan](docs/documentation-plan.md) records the
source review and examples.

## Lab and automation

- Test the remaining Grafana queries with generated Prometheus and Loki data.
- Try Ansible SSH/update changes and Falco deployment, including rollback, on
  disposable Debian hosts.
- Test network segmentation, DNS, and authentication flows; write up the failed
  network migration.
- Check Forgejo branch protections and deployment-runner permissions.
- Document dependency updates, deployment runs, and backup/restore exercises.
- Test service startup with a missing or incorrect storage mount.
