#!/usr/bin/env python3
"""Validate example Compose files and exercise them in disposable projects."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = {
    "syncthing": ROOT / "apps/syncthing/compose.yml",
    "freshrss": ROOT / "apps/freshrss/compose.yml",
    "jellyfin": ROOT / "media/jellyfin/compose.yml",
    "caddy": ROOT / "networking/caddy/compose.yml",
    "host-metrics": ROOT / "monitoring/host-metrics/compose.yml",
}
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def run(*args: str, check: bool = True, env=None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, check=check, capture_output=True, text=True, timeout=180, env=env,
    )


def render(*paths: Path, env=None) -> dict:
    files = [arg for path in paths for arg in ("-f", str(path))]
    result = run("docker", "compose", *files, "config", "--format", "json", env=env)
    return json.loads(result.stdout)


def validate() -> None:
    env = dict(os.environ, JELLYFIN_UID="1000", JELLYFIN_GID="1000", RENDER_GID="123")
    for name, path in EXAMPLES.items():
        config = render(path, env=env)
        for service in config["services"].values():
            assert "@sha256:" in service["image"], f"{name}: image must be pinned"
            assert not service.get("privileged"), f"{name}: privileged container"
            assert not service.get("network_mode"), f"{name}: shared network namespace"
            for port in service.get("ports", []):
                assert port["host_ip"] == "127.0.0.1", f"{name}: non-loopback port"
            for volume in service.get("volumes", []):
                if volume["type"] == "bind":
                    if name == "jellyfin" and volume["target"] in ("/config", "/cache"):
                        expected = path.parent / volume["target"].lstrip("/")
                        assert Path(volume["source"]) == expected, "unexpected data path"
                        assert not volume.get("read_only"), "application data must be writable"
                        continue
                    assert volume.get("read_only"), f"{name}: writable bind mount"
        assert all(not n.get("external") for n in config["networks"].values()), name
        if name == "jellyfin":
            gpu = render(path, path.with_name("gpu.override.yml"), env=env)
            service = gpu["services"]["jellyfin"]
            assert service["group_add"] == ["123"], "render group not passed through"
            assert service["devices"][0]["target"] == "/dev/dri/renderD128"
            assert not service.get("privileged"), "GPU override enables privileged mode"
            media = next(v for v in service["volumes"] if v["target"] == "/media")
            # Some Compose versions omit false fields from their JSON output.
            assert media["read_only"] and not media.get("bind", {}).get("create_host_path", False)
        print(f"PASS: {name} Compose and local-access checks", flush=True)


def request(url: str, *, headers: dict | None = None, method: str = "GET", data=None):
    body = None if data is None else json.dumps(data).encode()
    headers = dict(headers or {})
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with HTTP.open(req, timeout=5) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode()


def wait_for(description, predicate, seconds=90):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            value = predicate()
            if value:
                return value
        except (OSError, urllib.error.URLError, json.JSONDecodeError):
            pass
        time.sleep(1)
    raise RuntimeError(f"timed out: {description}")


class Project:
    def __init__(self, name: str, directory: Path):
        self.name = name
        self.path = EXAMPLES[name]
        self.directory = directory
        self.env = dict(os.environ)
        if name == "jellyfin":
            # Keep writable bind mounts and generated media outside the checkout.
            self.path = directory / "compose.yml"
            shutil.copyfile(EXAMPLES[name], self.path)
            for folder in ("config", "cache", "media"):
                (directory / folder).mkdir()
            self.env.update(JELLYFIN_UID=str(os.getuid()), JELLYFIN_GID=str(os.getgid()))
        self.project = f"tamriel-example-{uuid.uuid4().hex[:12]}"
        config = render(self.path, env=self.env)
        # !override replaces fixed ports with random loopback ports (Compose 2.24.4+).
        lines = ["services:"]
        for service, definition in config["services"].items():
            ports = definition.get("ports", [])
            if ports:
                lines.extend([f"  {service}:", "    ports: !override"])
                for port in ports:
                    binding = f'127.0.0.1::{port["target"]}/{port["protocol"]}'
                    lines.append(f'      - "{binding}"')
        if name == "syncthing":
            peer = dict(config["services"]["syncthing"])
            peer["ports"] = [{"target": 8384, "host_ip": "127.0.0.1", "protocol": "tcp"}]
            peer["volumes"] = [
                {"type": "volume", "source": "peer-data", "target": "/var/syncthing"}
            ]
            lines.append(f"  syncthing-peer: {json.dumps(peer)}")
            lines.extend(["volumes:", "  peer-data: {}"])
        override = directory / "ports.yml"
        override.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.command = [
            "docker", "compose", "-p", self.project,
            "-f", str(self.path), "-f", str(override),
        ]

    def compose(self, *args, check=True):
        return run(*self.command, *args, check=check, env=self.env)

    def url(self, service, port):
        address = self.compose("port", service, str(port)).stdout.strip()
        assert address.startswith("127.0.0.1:"), "expected a loopback-only endpoint"
        return f"http://{address}"

    def exec(self, service, *args, check=True):
        user = ["--user", "1000:1000"] if service.startswith("syncthing") else []
        if service == "freshrss":
            user = ["--user", "www-data"]
        return self.compose("exec", "-T", *user, service, *args, check=check)


def syncthing(project):
    endpoints = {}
    for service in ("syncthing", "syncthing-peer"):
        url = project.url(service, 8384)
        wait_for("Syncthing health", lambda: request(url + "/rest/noauth/health")[0] == 200)
        config = project.exec(service, "cat", "/var/syncthing/config/config.xml").stdout
        key = ET.fromstring(config).findtext("gui/apikey")
        assert key, "generated API key missing"
        headers = {"X-API-Key": key}
        status, body = request(url + "/rest/system/status", headers=headers)
        assert status == 200
        identity = json.loads(body)["myID"]
        endpoints[service] = (url, headers, identity)

    for service, (url, headers, identity) in endpoints.items():
        other = "syncthing-peer" if service == "syncthing" else "syncthing"
        other_id = endpoints[other][2]
        status, _ = request(
            url + "/rest/config/devices/" + other_id,
            headers=headers,
            method="PUT",
            data={"deviceID": other_id, "addresses": [f"tcp://{other}:22000"]},
        )
        assert status == 200, "device pairing configuration failed"
        status, _ = request(
            url + "/rest/config/folders/example",
            headers=headers,
            method="PUT",
            data={
                "id": "example",
                "path": "/var/syncthing/example-files",
                "type": "sendreceive",
                "rescanIntervalS": 1,
                "devices": [{"deviceID": identity}, {"deviceID": other_id}],
            },
        )
        assert status == 200, "shared folder configuration failed"

    project.exec(
        "syncthing", "sh", "-c",
        "mkdir -p /var/syncthing/example-files && "
        "printf 'example file\\n' > /var/syncthing/example-files/check.txt",
    )
    wait_for(
        "file transfer",
        lambda: project.exec(
            "syncthing-peer", "cat", "/var/syncthing/example-files/check.txt",
            check=False,
        ).stdout == "example file\n",
    )
    project.compose("restart", "syncthing")
    _, headers, identity = endpoints["syncthing"]
    # Docker can allocate a new random host port when a container restarts.
    url = project.url("syncthing", 8384)

    def identity_preserved():
        status, body = request(url + "/rest/system/status", headers=headers)
        return status == 200 and json.loads(body).get("myID") == identity

    wait_for("persistent Syncthing identity", identity_preserved)
    result = project.exec("syncthing", "cat", "/var/syncthing/example-files/check.txt")
    assert result.stdout == "example file\n"


def freshrss(project):
    url = project.url("freshrss", 80)
    wait_for("FreshRSS wizard", lambda: "FreshRSS" in request(url)[1])
    project.exec("freshrss", "cli/do-install.php", "--default-user", "reader",
                 "--auth-type", "form")
    project.exec("freshrss", "cli/create-user.php", "--user", "reader",
                 "--password", uuid.uuid4().hex)
    marker = "/var/www/FreshRSS/data/example.txt"
    project.exec("freshrss", "sh", "-c", f"printf 'before backup\\n' > {marker}")
    project.compose("stop", "freshrss")
    archive = project.directory / "data.tar.gz"
    with archive.open("wb") as output:
        subprocess.run(
            [*project.command, "run", "--rm", "-T", "--no-deps", "--entrypoint",
             "tar", "freshrss", "-C", "/var/www/FreshRSS", "-czf", "-", "data", "extensions"],
            stdout=output, stderr=subprocess.PIPE, check=True, timeout=180, env=project.env,
        )
    project.compose("start", "freshrss")
    project.exec("freshrss", "sh", "-c", f"printf 'after backup\\n' > {marker}")

    directory = project.directory / "restore"
    directory.mkdir()
    restored = Project("freshrss", directory)
    try:
        with archive.open("rb") as source:
            subprocess.run(
                [*restored.command, "run", "--rm", "-T", "--no-deps", "--entrypoint",
                 "tar", "freshrss", "-C", "/var/www/FreshRSS", "-xzf", "-"],
                stdin=source, capture_output=True, check=True, timeout=180, env=restored.env,
            )
        restored.compose("up", "-d")
        url = restored.url("freshrss", 80)
        wait_for("restored FreshRSS", lambda: "FreshRSS" in request(url)[1])
        assert "reader" in restored.exec("freshrss", "cli/list-users.php").stdout
        assert restored.exec("freshrss", "cat", marker).stdout == "before backup\n"
        assert project.exec("freshrss", "cat", marker).stdout == "after backup\n"
    finally:
        restored.compose("down", "--volumes", "--remove-orphans")


def jellyfin(project):
    url = project.url("jellyfin", 8096)
    wait_for("Jellyfin health", lambda: request(url + "/health") == (200, "Healthy"))
    status, body = request(url + "/System/Info/Public")
    assert status == 200 and json.loads(body)["StartupWizardCompleted"] is False
    assert project.exec("jellyfin", "id", "-u").stdout.strip() == str(os.getuid())
    project.exec(
        "jellyfin", "/usr/lib/jellyfin-ffmpeg/ffmpeg", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=blue:s=160x120:r=1", "-t", "1", "-c:v", "mpeg4",
        "/cache/example.mp4",
    )
    shutil.copyfile(project.directory / "cache/example.mp4",
                    project.directory / "media/example.mp4")
    project.exec(
        "jellyfin", "sh", "-c",
        "test -r /media/example.mp4 && test ! -w /media/example.mp4 && "
        "test -w /config && test -w /cache",
    )
    project.exec("jellyfin", "/usr/lib/jellyfin-ffmpeg/ffprobe", "-v", "error",
                 "-show_format", "/media/example.mp4")


def caddy(project):
    url = project.url("proxy", 8080)
    headers = {"Host": "app.example.com"}
    wait_for(
        "Caddy upstream",
        lambda: request(url, headers=headers)
        == (200, "Example application reached through Caddy"),
    )
    assert request(url, headers={"Host": "other.example.com"})[0] == 404
    project.compose("stop", "upstream")
    wait_for("Caddy upstream failure", lambda: request(url, headers=headers)[0] == 502)


def host_metrics(project):
    prometheus = project.url("prometheus", 9090)
    grafana = project.url("grafana", 3000)

    def query(expression):
        parameters = urllib.parse.urlencode({"query": expression})
        status, body = request(prometheus + "/api/v1/query?" + parameters)
        if status != 200:
            return None
        response = json.loads(body)
        assert response["status"] == "success", "PromQL query failed"
        return response["data"]["result"]

    dashboard = json.loads((ROOT / "monitoring/host-metrics/dashboard.json").read_text())
    for panel in dashboard["panels"]:
        expression = panel["targets"][0]["expr"]
        result = wait_for(f"dashboard panel: {panel['title']}", lambda: query(expression))
        for sample in result:
            value = float(sample["value"][1])
            assert math.isfinite(value) and 0 <= value <= 100, panel["title"]
    assert query('up{job="node"}')[0]["value"][1] == "1"
    path = grafana + "/api/dashboards/uid/host-metrics-example"
    wait_for("Grafana dashboard provisioning", lambda: request(path)[0] == 200)
    loaded = json.loads(request(path)[1])["dashboard"]
    expected = [p["targets"] for p in dashboard["panels"]]
    assert [p["targets"] for p in loaded["panels"]] == expected
    # Query through Grafana too, exercising the provisioned datasource URL and UID.
    datasource = (
        grafana + "/api/datasources/proxy/uid/example-prometheus/api/v1/query?query=up"
    )
    status, body = request(datasource)
    assert status == 200, "Grafana datasource unavailable"
    assert json.loads(body)["data"]["result"], "Grafana datasource returned no data"
    project.compose("stop", "node-exporter")
    wait_for("failed scrape recorded", lambda: query('up{job="node"} == 0'))


def smoke(name):
    with tempfile.TemporaryDirectory(prefix="tamriel-example-") as directory:
        project = Project(name, Path(directory))
        try:
            project.compose("up", "-d", "--pull", "missing")
            checks = {
                "syncthing": syncthing, "freshrss": freshrss, "jellyfin": jellyfin,
                "caddy": caddy, "host-metrics": host_metrics,
            }
            checks[name](project)
            print(f"PASS: {name} startup and behavior", flush=True)
        finally:
            project.compose("down", "--volumes", "--remove-orphans")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--smoke", choices=[*EXAMPLES, "all"])
    args = parser.parse_args()
    if args.validate:
        validate()
    else:
        for name in EXAMPLES if args.smoke == "all" else [args.smoke]:
            smoke(name)


if __name__ == "__main__":
    main()
