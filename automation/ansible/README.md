# SSH and updates

[Home](../../README.md) · [Automation](../README.md)

Ansible examples for key-only SSH, automatic security updates, and full upgrades
one host at a time.

## Setup

Requirements: Python 3.12+, `ansible-core` 2.21.3, and Debian-family hosts with
OpenSSH drop-in support. The [example inventory](inventory.example.yml) uses
documentation addresses:

- `hypervisors` keep key-only root access for cluster operations;
- `service_vms` and `edge` use a non-root operator and disable root login.

Host-key checking stays enabled. Before using the role, test key access and
console recovery and set the corresponding inventory flags. Include the Ansible
user in `ssh_allowed_users` and supply the admin client's source address.
The role rejects password connection variables.

## Run

Inspect the example inventory:

```bash
cd automation/ansible
ansible-inventory --list
```

To use the roles, copy them into your own Ansible project and supply an inventory.
Run from that project's Ansible directory:

```bash
ansible-playbook -i /path/to/private/inventory.yml playbooks/site.yml
ansible-playbook -i /path/to/private/inventory.yml playbooks/controlled-upgrade.yml
```

Both roles reject check mode because they need to run service checks and test
reconnections and rollback. Full upgrades are excluded from `site.yml`.

## Tests

From the repository root, with the dependencies in [requirements.txt](requirements.txt):

```bash
python3 -m unittest discover -s automation/ansible/tests -p 'test_*.py' -v
cd automation/ansible
ansible-playbook --syntax-check playbooks/site.yml
ansible-playbook --syntax-check playbooks/controlled-upgrade.yml
```

Tests check the SSH variants, update configuration, inventory, and one-host-at-a-time
upgrades without reboots. CI also checks the resolved inventory and parses apt
configuration with Debian tools. Disposable-host testing is on the
[roadmap](../../ROADMAP.md).

## SSH changes and rollback

The role installs `00-ansible-hardening.conf` in `/etc/ssh/sshd_config.d/`.
The early filename matters because OpenSSH uses the first value it reads for
single-value options.
It checks the main file's drop-in include and rejects competing access controls,
extra/nested includes, symlinked drop-ins, and existing `Match` blocks. Those
configurations need adjusting before using the role.

The policy requires public keys and a non-empty `AllowUsers` list. It disables
password/keyboard-interactive authentication, empty passwords, Kerberos, GSSAPI,
and X11 forwarding; it also sets authentication-attempt and keepalive limits.
Root policy depends on the inventory group.

Before activation, the role renders a candidate, saves the old file, and arms a
systemd rollback timer. It installs the candidate, runs `sshd -t`, reloads SSH,
resets the Ansible connection, and waits for a fresh key-based connection.
`sshd -T -C` checks effective policy for each allowed user and source context.

Only then does it stop the rollback timer and service, verify both are inactive,
and check the live checksum before cleanup. Task failure restores the old
configuration; the timer handles a lost controller connection.
`serial: 1` and `any_errors_fatal: true` stop a failed rollout before the next host.

## Security updates

The role installs `unattended-upgrades` and `apt-listchanges` and stops if apt
indexes cannot be refreshed. It checks both candidate apt files before installing
them together, with rollback on failure. It then checks the effective settings:
security-only `Origins-Pattern`, no legacy origins, periodic updates enabled,
and automatic reboot disabled.

Leftover transaction files block retries until inspected. Unused dependencies
are removed and events go to syslog. Example defaults use daily updates and
seven-day cleanup.

## Full upgrades

The upgrade playbook refreshes metadata, runs an `apt-get` full upgrade, performs
separate autoremove/autoclean tasks, and checks whether a reboot is needed.
Failure reports the last completed phase and reboot state, then stops. It never
reboots automatically.

The playbook runs one host at a time. Application-level health checks between
hosts can be added for individual workloads.
