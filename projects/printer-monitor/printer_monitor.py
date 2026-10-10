#!/usr/bin/env python3
"""Read a CUPS queue and IPP supplies, or show the same status in a GTK window."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import threading
from urllib.parse import unquote, urlsplit


STATES = {3: "Ready", 4: "Printing", 5: "Needs attention"}
JOB_STATES = {3: "Pending", 4: "Held", 5: "Printing", 6: "Stopped"}
DEFAULT_CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "printer-monitor/config.json"


def values(value):
    return list(value) if isinstance(value, (list, tuple)) else ([] if value is None else [value])


def percentage(value):
    try:
        number = int(value)
    except (ValueError, TypeError):
        return None
    return number if 0 <= number <= 100 else None


def supplies(attributes):
    names = values(attributes.get("marker-names"))
    levels = values(attributes.get("marker-levels"))
    low = values(attributes.get("marker-low-levels"))
    return [{"name": str(name),
             "level": percentage(levels[i]) if i < len(levels) else None,
             "low": percentage(low[i]) if i < len(low) else None}
            for i, name in enumerate(names)]


def settings(path):
    config = json.loads(Path(path).read_text())
    uri = urlsplit(config["device_uri"])
    if (uri.scheme not in {"ipp", "ipps"} or not uri.hostname or uri.username
            or uri.password or not uri.path or uri.query or uri.fragment):
        raise ValueError("device_uri must be an ipp:// or ipps:// URL without credentials")
    if not isinstance(config.get("queue"), str) or not config["queue"].strip():
        raise ValueError("Set queue to a CUPS queue name from lpstat -p")
    refresh = config.get("refresh_seconds", 30)
    if type(refresh) is not int or not 5 <= refresh <= 3600:
        raise ValueError("refresh_seconds must be an integer between 5 and 3600")
    config["refresh_seconds"] = refresh
    return config


def snapshot(config, cups_module=None):
    if cups_module is None:
        import cups as cups_module
    result = {"online": False, "state": "Offline", "model": "Printer",
              "detail": "Check printer power and its connection", "supplies": [],
              "paper": "Unknown", "jobs": [], "queue_available": False}
    try:
        queue = cups_module.Connection()
        queue.getPrinterAttributes(config["queue"])
        result["queue_available"] = True
        for number, job in queue.getJobs(which_jobs="not-completed", my_jobs=False).items():
            path = unquote(urlsplit(str(job.get("job-printer-uri", ""))).path)
            if path != "/printers/" + config["queue"]:
                continue
            result["jobs"].append({"id": number, "name": str(job.get("job-name", "Untitled")),
                                   "state": JOB_STATES.get(job.get("job-state"), "Unknown")})
        result["jobs"].sort(key=lambda job: job["id"])
    except (cups_module.IPPError, RuntimeError, OSError) as error:
        result["queue_error"] = str(error)
    try:
        uri = urlsplit(config["device_uri"])
        options = {"host": uri.hostname, "port": uri.port or 631}
        if uri.scheme == "ipps":
            options["encryption"] = cups_module.HTTP_ENCRYPTION_ALWAYS
        device = cups_module.Connection(**options)
        attributes = device.getPrinterAttributes(uri=config["device_uri"])
        reasons = [str(x).removesuffix("-report").replace("-", " ")
                   for x in values(attributes.get("printer-state-reasons")) if x != "none"]
        result.update(online=True, state=STATES.get(attributes.get("printer-state"), "Unknown"),
                      model=str(attributes.get("printer-make-and-model", "Printer")),
                      detail=str(attributes.get("printer-state-message", "")).strip()
                      or ", ".join(reasons) or "Connected and ready for jobs",
                      supplies=supplies(attributes),
                      paper=", ".join(map(str, values(attributes.get("media-ready")))) or "Unknown")
        if attributes.get("printer-is-accepting-jobs") is False:
            result["detail"] += "; not accepting jobs"
    except (cups_module.IPPError, RuntimeError, OSError) as error:
        result["error"] = str(error)
    return result


def sample_snapshot():
    return {"online": True, "state": "Ready", "model": "IPP printer",
            "detail": "Sample data, no printer connection", "paper": "iso_a4_210x297mm",
            "supplies": [{"name": "Color", "level": 65, "low": 10},
                         {"name": "Black", "level": 30, "low": 10}],
            "jobs": [], "queue_available": True}


def graphical(config, demo=False):
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Adw, Gio, GLib, Gtk

    class Window(Adw.ApplicationWindow):
        def __init__(self, application):
            super().__init__(application=application, title="Printer Monitor")
            self.set_default_size(580, 520)
            self.loading = False
            toolbar = Adw.ToolbarView()
            header = Adw.HeaderBar()
            header.set_title_widget(Adw.WindowTitle(title="Printer Monitor",
                                                  subtitle="Sample data" if demo else config["queue"]))
            refresh = Gtk.Button(icon_name="view-refresh-symbolic")
            refresh.set_tooltip_text("Refresh status")
            refresh.connect("clicked", self.refresh)
            header.pack_end(refresh)
            toolbar.add_top_bar(header)
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
            for side in ["top", "bottom", "start", "end"]:
                getattr(content, "set_margin_" + side)(24)
            self.state = Gtk.Label(label="Checking printer…", xalign=0)
            self.state.add_css_class("title-1")
            self.detail = Gtk.Label(xalign=0, wrap=True)
            self.detail.add_css_class("dim-label")
            content.append(self.state)
            content.append(self.detail)
            self.supply_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            content.append(self.supply_box)
            group = Adw.PreferencesGroup(title="Printer")
            self.model = Adw.ActionRow(title="Model")
            self.paper = Adw.ActionRow(title="Loaded paper")
            self.jobs = Adw.ActionRow(title="Print queue")
            for row in [self.model, self.paper, self.jobs]:
                group.add(row)
            content.append(group)
            actions = Gtk.Box(spacing=12, homogeneous=True)
            for label, command in [("Open print queue", ["system-config-printer"]),
                                   ("Scan document", ["simple-scan"] + ([config["scanner"]] if config.get("scanner") else []))]:
                button = Gtk.Button(label=label, sensitive=not demo)
                button.connect("clicked", lambda _button, cmd=command: self.launch(cmd))
                actions.append(button)
            content.append(actions)
            self.updated = Gtk.Label(label="")
            self.updated.add_css_class("dim-label")
            content.append(self.updated)
            scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
            scroll.set_child(content)
            toolbar.set_content(scroll)
            self.set_content(toolbar)
            self.timer = GLib.timeout_add_seconds(config["refresh_seconds"], self.refresh)
            self.connect("close-request", self.closed)
            self.refresh()

        def closed(self, *_):
            GLib.source_remove(self.timer)
            return False

        def launch(self, command):
            try:
                subprocess.Popen(command, start_new_session=True)
            except OSError:
                self.detail.set_label("Install " + command[0] + " to use this button")

        def refresh(self, *_):
            if not self.loading:
                self.loading = True
                threading.Thread(target=self.collect, daemon=True).start()
            return GLib.SOURCE_CONTINUE

        def collect(self):
            try:
                result = sample_snapshot() if demo else snapshot(config)
            except Exception as error:
                result = {"state": "Could not read printer", "detail": str(error),
                          "supplies": [], "model": "Unknown", "paper": "Unknown",
                          "jobs": [], "queue_available": False}
            GLib.idle_add(self.apply, result)

        def apply(self, result):
            self.state.set_label(result["state"])
            self.detail.set_label(result["detail"])
            self.model.set_subtitle(result["model"])
            self.paper.set_subtitle(result["paper"])
            jobs = result["jobs"]
            self.jobs.set_subtitle("; ".join(f'#{j["id"]}: {j["name"]} ({j["state"]})' for j in jobs)
                                   or ("No active jobs" if result["queue_available"] else "Queue unavailable"))
            while child := self.supply_box.get_first_child():
                self.supply_box.remove(child)
            for supply in result["supplies"]:
                level = supply["level"]
                label = Gtk.Label(label=supply["name"], xalign=0)
                bar = Gtk.ProgressBar(show_text=True, fraction=(level or 0) / 100,
                                      text="Unknown" if level is None else f"{level}% estimated")
                if level is not None and supply["low"] is not None and level <= supply["low"]:
                    bar.add_css_class("error")
                self.supply_box.append(label)
                self.supply_box.append(bar)
            if not result["supplies"]:
                self.supply_box.append(Gtk.Label(label="Supply levels unavailable", xalign=0))
            self.updated.set_label(f'Updates every {config["refresh_seconds"]} seconds')
            self.loading = False
            return GLib.SOURCE_REMOVE

    application = Adw.Application(application_id="com.example.PrinterMonitor",
                                  flags=Gio.ApplicationFlags.NON_UNIQUE)
    application.connect("activate", lambda app: Window(app).present())
    return application.run([])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--status", action="store_true", help="Print JSON without opening the GUI")
    parser.add_argument("--demo", action="store_true", help="Show sample data without querying a printer")
    args = parser.parse_args()
    try:
        config = {"queue": "printer", "refresh_seconds": 30} if args.demo else settings(args.config)
        if args.status:
            result = sample_snapshot() if args.demo else snapshot(config)
            print(json.dumps(result, indent=2))
            return 0 if result["online"] else 1
        return graphical(config, args.demo)
    except (OSError, ValueError, KeyError, ImportError) as error:
        parser.exit(2, f"printer-monitor: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
