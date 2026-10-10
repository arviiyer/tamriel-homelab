# Clone a Debian VM with Terraform

[Home](../../README.md) · [Proxmox](../README.md) · [Debian VM](../debian-vm/README.md)

My Forge portal uses Terraform to clone Debian templates. This smaller example
creates one VM directly: two CPU cores, 4 GiB RAM, a 64 GiB local disk, DHCP, and
an operator account with your SSH public key. It uses the same `bpg/proxmox`
provider and full-clone approach.

## Before starting

You need Terraform 1.7 or newer, a reachable Proxmox VE API, an unused VM ID, and
a Debian cloud-init template on the destination node. Follow the
[template notes](../debian-vm/README.md#reusing-a-template) first. The template
needs its OS disk on `scsi0`, the guest agent installed, and no enrolled Tailscale
identity. Its existing disk must be no larger than 64 GiB for this example.

In Proxmox, create a dedicated API user and privilege-separated token. Grant both
the user and token the required clone, VM configuration, power-management, and
datastore-allocation permissions. Limit them to the template, destination VM or
pool, node, and storage you intend to use. The provider's
[permissions reference](https://registry.terraform.io/providers/bpg/proxmox/latest/docs#permissions)
lists the privileges for your Proxmox release.

Use a certificate trusted by the machine running Terraform. For Proxmox's own
CA, obtain and verify its public CA certificate through your administration
channel and install it in the controller's trust store. The example keeps TLS
verification enabled. Cloning and these cloud-init fields use the API, so this
example does not need a Proxmox node's SSH private key.

## Create the clone

From this repository's root, copy the individual configuration files into a new
directory outside the checkout:

```bash
mkdir -p "$HOME/homelab-examples"
mkdir "$HOME/homelab-examples/vm"
cp proxmox/terraform/{main.tf,variables.tf,terraform.tfvars.example} "$HOME/homelab-examples/vm/"
cd "$HOME/homelab-examples/vm"
chmod 700 .
cp terraform.tfvars.example terraform.tfvars
```

Edit every example value. `template_id` is the existing template; `vm_id` is the
new, unused ID. Use an absolute path to your `.pub` key. Supply the API token
through the provider's environment variable, in the form
`terraform@pve!clone=TOKEN_SECRET`:

```bash
read -r -s -p 'Proxmox API token: ' PROXMOX_VE_API_TOKEN
printf '\n'
export PROXMOX_VE_API_TOKEN
umask 077
terraform init
terraform validate
terraform plan -out=clone.plan
```

The first plan should show one VM being created and no deletions. Review its
node, storage, name, ID, and network bridge, then apply that saved plan:

```bash
terraform apply clone.plan
terraform output
unset PROXMOX_VE_API_TOKEN
```

Check the VM's cloud-init task and guest-agent address in Proxmox. SSH in as
`operator`, check `hostnamectl` and `cloud-init status --wait`, and continue with
the [Docker setup](../debian-vm/README.md#install-docker). If the template needs
sudo installed or configured, complete that through its console first.

## Updates and deletion

Keep this directory's state and `.terraform.lock.hcl` with your private
configuration backups. Terraform needs the same state to manage the same VM.
Commit the lock file in that private configuration repository; state, credentials,
and saved plans stay private. Re-export the token before later plan/apply runs.

Run `terraform plan` after changing the configuration. Cloud-init is primarily
first-boot configuration; use Ansible for ongoing changes. Before changing the
template ID or VM identity, check whether the plan proposes replacement.

To remove this disposable clone, run `terraform plan -destroy -out=destroy.plan`,
review the one VM being removed, then `terraform apply destroy.plan`. Back up any
data you intend to keep before deletion. The source template is not managed by
this configuration.

| Symptom | Check |
|---|---|
| API returns 403 | Token and parent-user permissions, including storage and template access |
| Certificate verification fails | Endpoint hostname and trusted Proxmox CA |
| Clone fails on disk configuration | Template's `scsi0` disk, size, and destination storage |
| No reported IP | DHCP, guest agent, and completed cloud-init |
| A second run proposes another VM | Working directory, state file, and selected workspace |

## Checks

Run `bash proxmox/terraform/check.sh` from the repository root. It uses a temporary
directory and generated public key for provider initialization, schema validation,
and mock-provider plans. It does not create a VM; the Proxmox and guest checks
above verify an actual clone.
