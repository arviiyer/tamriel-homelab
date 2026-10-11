# SSH and updates

[Home](../../README.md) · [Automation](../README.md)

I run Ansible from the security VM to maintain the lab hosts. These playbooks
configure key-only SSH, automatic security updates, and full upgrades one host
at a time.

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

On your control machine, copy this example into a private working directory and
install its Python dependencies. Debian controllers also need `python3-venv`.
From the repository root:

```bash
mkdir -p "$HOME/homelab-examples"
mkdir "$HOME/homelab-examples/ansible"
cp -R automation/ansible/roles automation/ansible/playbooks \
  automation/ansible/ansible.cfg automation/ansible/inventory.example.yml \
  automation/ansible/requirements.txt "$HOME/homelab-examples/ansible/"
cd "$HOME/homelab-examples/ansible"
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
cp inventory.example.yml inventory.yml
```

Edit `inventory.yml` to include only your intended hosts and their real addresses.
Set the admin source address and allowed users before using the SSH role. Start
with a disposable VM prepared using the [Debian guide](../../proxmox/debian-vm/README.md).
Verify its SSH fingerprint through the Proxmox console and accept that host key
on the controller before running Ansible.

Check connectivity and sudo on that one VM, then apply the roles to it:

```bash
ansible -i inventory.yml apps-01 -K -m ansible.builtin.ping
ansible -i inventory.yml apps-01 -b -K -m ansible.builtin.command -a 'id -u'
ansible-playbook -i inventory.yml playbooks/site.yml --limit apps-01 -K
```

`-K` prompts for the sudo password; omit it for an account already configured
for passwordless sudo. The become check should return `0`. After the playbook,
open a fresh SSH connection and check `sudo sshd -T`,
`systemctl status unattended-upgrades`, and an application on the VM. Broaden
the inventory only after those checks succeed.

For a full upgrade:

```bash
ansible-playbook -i inventory.yml playbooks/controlled-upgrade.yml --limit apps-01 -K
```

Review its reboot-required result and plan the reboot separately. Check the
application again before upgrading the next workload.

Both roles reject check mode because they need to run service checks and test
reconnections and rollback. Full upgrades are excluded from `site.yml`.

Keep the inventory and roles in your private configuration repository. Back up
the VM before changing the SSH policy or OS packages. When updating these roles,
repeat the one-host run and compare the effective SSH and apt configuration.

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
