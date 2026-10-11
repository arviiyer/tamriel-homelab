# UPS monitoring and shutdown

[Home](../../README.md) · [Monitoring](../README.md) · [Proxmox](../../proxmox/README.md)

The CyberPower CP1500PFCLCD currently provides power only. I still need to connect
its USB data cable. The setup below uses TrueNAS as the NUT server, with clients
on the three Proxmox nodes and the Raspberry Pi.

## The setup

```text
CyberPower UPS ── USB ── TrueNAS
                           │ TCP 3493
                           ├── Proxmox nodes
                           └── Raspberry Pi
```

Connect a USB-A-to-USB-B data cable from the NAS to the UPS. The NAS, nodes, Pi,
and network equipment between them need battery-backed power. Allow the clients
to reach TCP 3493 on the NAS. These examples use `192.0.2.20` for the NAS;
replace it with your address.

The shutdown order is: Proxmox guests, then the Pi, then TrueNAS. The Pi stays
up longer because it provides DNS and the cluster quorum device.

The example timings below assume the Proxmox nodes finish stopping their guests
within three minutes. Measure a normal host shutdown first. Allow enough battery
runtime for the initial delay, client shutdowns, and the NAS shutdown, with some
time to spare.

## TrueNAS

Open **System → Services → UPS** and set:

| Setting | Value |
|---|---|
| Identifier | `ups` |
| UPS Mode | **Master** (the NUT primary) |
| Driver | CyberPower CP1500PFCLCD using `usbhid-ups` |
| Port or Hostname | `auto` |
| Monitor User | `upsmon`, with a new password |
| Remote Monitor | Enabled |
| Shutdown Mode | **UPS goes on battery** |
| Shutdown Timer | `60` seconds |
| Host Sync | `300` seconds |
| Shutdown Command | Leave blank for the normal system shutdown |
| Power off UPS | Off for the first test |

Starting shutdown after a minute leaves more battery for stopping the VMs than
waiting for low battery. Low battery also triggers shutdown if it arrives sooner.

Under **Extra Users**, add a separate login for the clients:

```ini
[ups-clients]
    password = replace-with-client-password
    upsmon secondary
```

Use a generated password without spaces or `#`, and use that same password in
the client configuration below. Save, start the UPS service, and enable
**Start Automatically**. In the TrueNAS shell, check:

```bash
upsc ups@localhost
```

Look for the UPS model, `battery.charge`, `battery.runtime` (seconds), `ups.load`,
and `ups.status`. `OL` means utility power; `OB` means battery power.

## Proxmox and Raspberry Pi clients

These client settings need NUT 2.8.1 or newer for `SHUTDOWNEXIT` support.
Run these commands from a root shell on each physical host. Proxmox handles its
guests during host shutdown, so they do not need their own NUT clients.

```bash
apt update
apt install nut-client
```

Set the mode in `/etc/nut/nut.conf`:

```ini
MODE=netclient
```

Replace `/etc/nut/upsmon.conf` with:

```ini
MONITOR ups@192.0.2.20 1 ups-clients replace-with-client-password secondary
MINSUPPLIES 1
SHUTDOWNCMD "/sbin/shutdown -h +0"
SHUTDOWNEXIT no
FINALDELAY 5
```

On the Pi, use `FINALDELAY 240` instead. Keep this delay longer than the slowest
Proxmox guest shutdown, and TrueNAS **Host Sync** longer than the Pi delay plus
its own shutdown time.

On each Proxmox node, run `systemctl edit nut-monitor.service` and add:

```ini
[Unit]
Before=pve-guests.service
```

Systemd reverses that ordering at shutdown: guests stop before NUT disconnects.
Together with `SHUTDOWNEXIT no`, this lets TrueNAS wait for the guests rather
than just the initial shutdown request. **Host Sync** is the maximum wait, so it
must cover the slowest client.

Start the client on each host:

```bash
chown root:nut /etc/nut/upsmon.conf
chmod 640 /etc/nut/upsmon.conf
systemctl daemon-reload
systemctl enable nut-monitor.service
systemctl restart nut-monitor.service
upsc ups@192.0.2.20 ups.status
journalctl -u nut-monitor.service -n 30 --no-pager
```

Check the journal for a successful connection without login errors. `upsc` can
read status without authenticating, so it does not check the monitor password.

## Try it

For a short outage test, switch off the UPS wall supply, check for `OB`, and
restore power before the 60-second timer expires. Status should return to `OL`
and the hosts should stay running.

For a full shutdown test, finish backups and save your work first. Run this in
the TrueNAS shell; it shuts down the NAS and every connected NUT client:

```bash
sudo upsmon -c fsd
```

Check that the VMs finish stopping while their NFS shares are still available,
then the Pi and NAS shut down. Once that sequence works, enable **Power off UPS**
and test the power-off/return sequence during a planned outage. Check the hosts'
firmware power-recovery settings too; the ROG Ally may need a manual start.

After starting the lab again, check UPS status, cluster quorum, and the
[NFS mounts](../../storage/nfs/README.md#wait-for-mounts) before opening the apps.

[TrueNAS UPS settings](https://www.truenas.com/docs/scale/25.10/scaleuireference/systemsettings/services/upsservicesscreenscale/) ·
[NUT client settings](https://networkupstools.org/docs/man/upsmon.conf.html) ·
[CP1500PFCLCD driver details](https://networkupstools.org/ddl/Cyber_Power_Systems/CP1500PFCLCD.html)
