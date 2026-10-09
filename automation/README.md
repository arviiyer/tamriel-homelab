# Automation

Scripts, roles, workflows, and configuration examples. Each component has setup
instructions and test commands.

| Component | What it does |
|---|---|
| [Trivy](trivy/README.md) | Scan images and repositories, compare findings, alert on changes |
| [Deployment](ci/README.md) | Deploy the commit checked by CI; roll back unhealthy changes |
| [Recovery](recovery/README.md) | Check archives and restore into a new directory |
| [Ansible](ansible/README.md) | Configure SSH and updates; upgrade one host at a time |
| [Falco](falco/README.md) | Detect suspicious runtime activity and route events |
| [Grafana](monitoring/README.md) | Display scan results and Falco events |
