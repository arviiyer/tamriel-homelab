# Printer Monitor

[Home](../../README.md) · [Projects](../README.md)

I built a small desktop window for the USB printer attached to my laptop. It
shows whether the printer is ready, estimated ink levels, loaded paper, and
queued jobs, with buttons for the print queue and scanner. The lab version is
used with a Canon PIXMA TS3720.

![Printer Monitor showing sample supplies and status](../../screenshots/printer-demo.webp)

The public GTK app in sample mode.
[Screenshot review](../../screenshots/printer-demo.review.md).

A local app fits this job: the printer is available when the laptop is on, and
the status window does not need an exporter or a server-side dashboard. This
version makes the CUPS queue and IPP endpoint configurable and displays the
supplies reported by the printer.

## Install

Requirements: a Linux desktop, Python 3.10+, GTK 4, libadwaita 1.4+, pycups, and
an existing CUPS queue. For a supported USB printer, `ipp-usb` supplies a local
IPP endpoint. On Debian 13:

```bash
sudo apt install python3-gi python3-cups gir1.2-gtk-4.0 gir1.2-adw-1 \
  cups-client ipp-usb system-config-printer simple-scan curl
```

On Arch Linux, the corresponding packages are `python-gobject`, `python-pycups`,
`gtk4`, `libadwaita`, `cups`, `ipp-usb`, `system-config-printer`, and `simple-scan`.
Follow the [OpenPrinting setup notes](https://openprinting.github.io/driverless/)
to add a queue if printing is not already working.

Download the files into your own working directory:

```bash
mkdir -p "$HOME/homelab-projects"
mkdir "$HOME/homelab-projects/printer-monitor"
cd "$HOME/homelab-projects/printer-monitor"
(
  set -eu
  for file in printer_monitor.py config.example.json install.sh printer-monitor.desktop; do
    curl -fLo "$file" "https://raw.githubusercontent.com/arviiyer/tamriel-homelab/main/projects/printer-monitor/$file"
  done
)
python3 printer_monitor.py --demo
```

The sample window works without a printer. Its buttons are disabled and its
header says **Sample data**. For terminal output, use `--demo --status`.

## Connect your printer

Find the queue and device URI:

```bash
lpstat -p
lpstat -v
ipp-usb status
```

`ipp-usb status` applies to USB devices supported by IPP-over-USB. A CUPS queue
URI can be a discovery address; `device_uri` needs the printer's actual
`ipp://` or `ipps://` endpoint. For a network printer, use its documented address.

```bash
mkdir -p "$HOME/.config/printer-monitor"
cp config.example.json "$HOME/.config/printer-monitor/config.json"
```

Edit that file:

| Setting | Value |
|---|---|
| `queue` | Exact CUPS queue name from `lpstat -p` |
| `device_uri` | IPP endpoint, such as `ipp://localhost:60000/ipp/print` from `ipp-usb` |
| `scanner` | Optional device name from `scanimage -L`; empty lets Document Scanner choose |
| `refresh_seconds` | Refresh interval, default 30 |

Run a first check, then install the launcher:

```bash
python3 printer_monitor.py --status
bash install.sh
"$HOME/.local/bin/printer-monitor"
```

The JSON should report `online: true` and `queue_available: true`. Open the app
from your desktop menu after ensuring `~/.local/bin` is on your desktop's PATH.
Use `--config /absolute/path/config.json` for another configuration.

## Use it

Send a small document through your normal print dialog and watch the queue.
Turn the printer off and refresh to check its offline display. Queue state and
device state are queried separately, so queued jobs can remain visible while
the printer is disconnected.

Ink readings are estimates supplied by the device. Unsupported or negative
levels display **Unknown**. Different printers expose different marker names;
the app does not infer ink levels from printed page counts.

The print and scan buttons launch `system-config-printer` and `simple-scan`.
The monitor itself reads status and does not submit, cancel, or change jobs.

## Updates and troubleshooting

Download the reviewed Python file and rerun `bash install.sh` to update. Keep
your `config.json`; the app has no database or historical metrics to back up.

| Symptom | Check |
|---|---|
| Queue unavailable | Exact queue name, CUPS service, and local permission to list jobs |
| Printer offline but queue exists | Printer power, cable, and the current IPP endpoint |
| Ink is unknown | Whether the device returns IPP `marker-names` and `marker-levels` |
| A button does nothing | Its companion application is installed; scanner name is current |
| GTK import error | Use the distribution Python with its GI packages rather than an isolated virtual environment |

From the repository root, parsing and queue-isolation checks need only Python:

```bash
python3 -m unittest discover -s projects/printer-monitor/tests -v
python3 projects/printer-monitor/printer_monitor.py --demo --status
```

[Source](printer_monitor.py) · [IPP-over-USB](https://github.com/OpenPrinting/ipp-usb)
