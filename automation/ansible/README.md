# Host Hardening and Controlled Patching

This public Ansible slice demonstrates the host controls used across the
homelab: key-only SSH, automatic security updates, and serial full-package
upgrades. It uses role-based aliases and documentation-only addresses.

It is a portable example, not the production inventory or deployment source.

## Design Goals

- Apply SSH policy without rewriting the distribution-managed main file.
- Refuse an empty or malformed SSH user allowlist.
- Protect SSH changes with an automatic rollback watchdog.
- Validate the candidate, complete daemon configuration, reconnect, and
  per-user effective policy before canceling rollback.
- Reset and re-establish the Ansible connection after reloading OpenSSH.
- Preserve key-only root administration only where the platform requires it.
- Apply security updates automatically without automatic reboot.
- Apply full upgrades to one host at a time and stop on the first failure.
- Report required reboots for an explicit maintenance decision.

## Layout

```text
automation/ansible/
├── ansible.cfg
├── inventory.example.yml
├── group_vars/all.yml
├── playbooks/
│   ├── controlled-upgrade.yml
│   ├── site.yml
│   ├── ssh-hardening.yml
│   └── unattended-upgrades.yml
├── roles/
│   ├── ssh_hardening/
│   └── unattended_upgrades/
└── tests/
    └── test_policy.py
```

## SSH Hardening

The role installs `/etc/ssh/sshd_config.d/00-ansible-hardening.conf` rather than taking
ownership of `/etc/ssh/sshd_config`. Before installation, it confirms that the
primary configuration includes the distribution drop-in directory and rejects
additional includes, `Match` blocks, symlinked drop-ins, nested includes, and
competing cumulative user/group access controls.

The policy enforces:

- public-key authentication;
- password and keyboard-interactive authentication disabled;
- an explicit non-empty `AllowUsers` list;
- bounded authentication attempts;
- idle-session keepalive limits;
- Kerberos, GSSAPI, X11 forwarding, and empty passwords disabled; and
- root login disabled except for explicitly modeled key-only platform nodes.

The early filename is intentional because OpenSSH uses the first obtained scalar
value. The role renders a candidate outside the live directory, saves the prior
policy, and arms a transient systemd rollback timer. It then installs the
candidate, runs `sshd -t`, reloads `ssh`, resets the Ansible connection, and
waits for a new key-based connection. Effective values are checked for every
allowed user using `sshd -T -C`; only then is rollback canceled. A failed task
restores the previous policy immediately, while the watchdog protects against a
lost controller connection.

Commit stops both the rollback timer and service, verifies neither remains
active, and rechecks the live policy checksum before transaction data is removed.

The inventory must attest that key access and an out-of-band console recovery
path were tested. Password connection variables are rejected, and the active
Ansible user must be present in `ssh_allowed_users`. It must also provide the
management client's source address so `sshd -T -C` evaluates any `Match Address`
policy in the real administrative context.

The playbook uses `serial: 1` and `any_errors_fatal: true`; one failed reconnect
stops the rollout before another host is changed.

## Security Updates

The unattended-upgrades role:

- fails if the apt package index cannot be refreshed;
- installs `unattended-upgrades` and `apt-listchanges`;
- limits automatic package origins to configured security channels;
- validates generated apt configuration before replacement;
- removes unused dependencies; and
- sends events to syslog.

The public role targets Debian and uses `Origins-Pattern` with Debian's security
origin, codename, and label rather than the legacy archive-based origin syntax.
After installation, it asserts the effective apt configuration contains the
security-only pattern, contains no anonymous or named legacy origin children,
keeps periodic upgrades enabled, and leaves automatic reboot disabled. The two
apt files are installed as a rollback-backed pair; unresolved transaction files
block retries until an operator inspects them.

Automatic reboot is disabled in the public policy. Rebooting a virtualization,
edge, identity, or storage host is an availability decision and remains outside
an unattended package-update task.

## Controlled Full Upgrades

`playbooks/controlled-upgrade.yml` handles non-security package upgrades as a
separate maintenance action. It uses:

```yaml
serial: 1
any_errors_fatal: true
max_fail_percentage: 0
```

Each host completes package-index refresh, an `apt-get` full upgrade, separate
autoremove and autoclean tasks, and reboot requirement inspection before the
next host starts. The rescue path reports the last completed phase and reboot
state after a package failure, then stops the rollout. The playbook never invokes
the reboot module.

Full upgrades are intentionally excluded from `site.yml`. Applying baseline
configuration should not implicitly perform broad package upgrades.

## Example Inventory

The example separates platform nodes from service and edge hosts:

- `hypervisors` use key-only root access because the modeled platform requires
  root SSH for cluster operations;
- `service_vms` and `edge` use a non-root operator and disable root login; and
- all addresses come from RFC 5737 documentation ranges.

Use verified SSH host keys. `ansible.cfg` keeps host-key checking enabled and
does not define a private-key or vault-password path.

## Run

Requirements:

- Python 3.12+
- `ansible-core` 2.21.3
- Debian-family managed hosts with the OpenSSH drop-in include enabled

Inspect the effective inventory:

```bash
cd automation/ansible
ansible-inventory --list
```

The SSH role intentionally refuses check mode because check mode cannot execute
the daemon validation, reconnect, or rollback transaction. Review diffs and
stage the first deployment on one host with verified console access instead.

The unattended-upgrades role also refuses check mode because it parses isolated
candidates and verifies merged apt state after installation. Stage it on a
disposable Debian host before broad rollout.

Apply baseline policy:

```bash
ansible-playbook playbooks/site.yml
```

Run a controlled full upgrade during a maintenance window:

```bash
ansible-playbook playbooks/controlled-upgrade.yml
```

The documentation-only inventory is not expected to be reachable. Replace it
with a private inventory outside this repository before executing a playbook.

## Validate

```bash
python3 -m unittest discover \
  -s automation/ansible/tests \
  -p 'test_*.py' \
  -v

cd automation/ansible
ansible-playbook --syntax-check playbooks/site.yml
ansible-playbook --syntax-check playbooks/controlled-upgrade.yml
```

The offline tests render both SSH policy variants, inspect unattended-upgrades
output, verify example inventory semantics, and assert the serial/no-reboot
upgrade controls.

## Production Differences

The private environment contains additional inventory groups, deployment
accounts, schedules, platform exceptions, notification destinations, and
recovery paths. Those details are deliberately excluded.

Two older production-derived behaviors are also not reproduced here:

- apt repository failures are not ignored; broken package metadata stops the
  role and must be repaired; and
- unattended automatic reboot is disabled; reboot coordination remains an
  explicit maintenance workflow.

## Limitations

- The roles support Debian-family systems only.
- OpenSSH service naming and drop-in support are modeled for current Debian and
  Proxmox installations.
- Syntax and rendering tests do not prove a live SSH transaction. The first
  deployment still requires a staged host and active recovery console.
- Serial patching reduces blast radius but does not validate application-level
  health between hosts. A future public example may add explicit service health
  gates for selected workload roles.
