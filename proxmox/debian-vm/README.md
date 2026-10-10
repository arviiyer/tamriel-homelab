# A Debian VM for Docker

[Home](../../README.md) · [Proxmox](../README.md) · [Storage](../../storage/README.md)

Most of my services run in Debian VMs, grouped by role. This is the starting
point for the app and media guides. A single Proxmox host is enough to follow it.

## Create the VM

Requirements: a working Proxmox VE host, free local storage, and a network with
DHCP or an assigned static address. Download the current Debian stable amd64
installer from [Debian](https://www.debian.org/distrib/), verify its checksum,
and upload it to the Proxmox ISO storage.

In **Create VM**:

| Setting | Starting point |
|---|---|
| Name | `apps-01` |
| OS | Debian installer ISO, Linux guest |
| System | q35, OVMF (UEFI), EFI disk on local storage, QEMU agent enabled |
| Disk | VirtIO SCSI, 64 GiB on local storage; increase for application data |
| CPU | 2 cores, `host` type for a VM staying on compatible hardware |
| Memory | 4 GiB for a small app host; size photo/ML/media workloads separately |
| Network | VirtIO on the intended bridge, with the appropriate VLAN tag if used |

Install Debian with **SSH server** and **standard system utilities**, without a
desktop. Create a regular user, called `operator` in these examples, and give it
administrative access. Use a DHCP reservation for the VM's MAC address or a static
address outside the DHCP pool. Check the gateway and DNS server before proceeding.

Inside the VM, as root (or through `sudo` if already configured):

```bash
apt update
apt install sudo qemu-guest-agent curl ca-certificates gnupg nfs-common
usermod -aG sudo operator
systemctl start qemu-guest-agent
```

Install your SSH public key from your workstation with
`ssh-copy-id operator@apps-01`. Confirm a fresh SSH login and `sudo -v` before
closing the console. Proxmox should now display the guest address and be able to
shut down the guest through the agent.

## Install Docker

The following uses Docker's Debian package repository. Run it inside the VM:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg \
  -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
printf 'Types: deb\nURIs: https://download.docker.com/linux/debian\nSuites: %s\nComponents: stable\nArchitectures: %s\nSigned-By: /etc/apt/keyrings/docker.asc\n' \
  "$VERSION_CODENAME" "$(dpkg --print-architecture)" | \
  sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker run --rm hello-world
sudo docker compose version
```

The service guides use `docker` without `sudo`. To follow that convention, add
your administration account to the Docker group and reconnect:

```bash
sudo usermod -aG docker operator
```

Docker-group membership grants control of the host. Use it for the account
administering these stacks. See [Docker's Debian instructions](https://docs.docker.com/engine/install/debian/)
for package conflicts or distribution-specific changes.

Keep application configuration and databases on the VM disk. Mount large shared
files separately using the [NFS guide](../../storage/nfs/README.md).

## Remote access and monitoring

Install Tailscale with its [Debian instructions](https://tailscale.com/download/linux),
then enroll the VM:

```bash
sudo tailscale up --accept-dns=false
tailscale status
```

I retain the VM's normal DNS configuration. Client devices can use the tailnet's
DNS settings separately. Permit only the intended administrators in the tailnet
policy and check access from a second device.

Install a host exporter:

```bash
sudo apt install prometheus-node-exporter
sudo systemctl enable --now prometheus-node-exporter
curl -fsS http://127.0.0.1:9100/metrics | head
```

Allow the monitoring host to reach TCP 9100 and add this VM to its
[scrape configuration](../../monitoring/host-metrics/README.md#adapting-it).
For key-only SSH and automatic security updates, use the
[Ansible guide](../../automation/ansible/README.md) after confirming a working key login.

## Reusing a template

I provision from Debian templates through the Forge portal. For a reusable
template, start with Debian's official cloud image and follow Proxmox's
[cloud-init instructions](https://pve.proxmox.com/wiki/Cloud-Init_Support).
Set each clone's user, SSH key, hostname, and network settings in cloud-init
before its first boot. The source image must have a unique machine identity
generated for each clone.

Install or enroll Tailscale after cloning. Application databases, SSH host keys,
service credentials, and device enrollment belong to the individual VM. GPU
firmware belongs on the [media guest](../../media/jellyfin/README.md#pass-the-gpu-to-the-vm).

After cloning, check the VM's identity and address, guest agent, SSH login,
Tailscale enrollment, monitoring target, and backup-job membership.

## Backups and maintenance

Add the VM to [PBS](../../storage/pbs/README.md) before filling it with important
data. Test rebooting it and opening its applications again. For NAS-backed apps,
check that their mounts are ready before Docker starts.

My app and media VMs outgrew their original 32 GiB root disks. Container logs,
browser core dumps, and retained rollback images all contributed. I now use
64 GiB disks there and bound the noisy containers' logs. Check both
`docker system df -v` and `docker ps --size` when investigating disk growth.

| Symptom | First thing to check |
|---|---|
| Guest address missing in Proxmox | Guest agent installed, started, and enabled in VM options |
| VM cannot resolve names | Guest resolver, assigned DNS server, and firewall DNS path |
| Docker permission denied after group change | Reconnect the SSH session |
| Container unreachable from another host | Published interface, Docker forwarding rules, and upstream firewall |
| App starts before its files arrive | [Mount ordering](../../storage/nfs/README.md#wait-for-mounts) |
