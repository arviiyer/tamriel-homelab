#!/usr/bin/env python3
"""Validate example Compose files and exercise them in disposable projects."""

from __future__ import annotations

import argparse
import json
import math
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
    "caddy": ROOT / "networking/caddy/compose.yml",
    "host-metrics": ROOT / "monitoring/host-metrics/compose.yml",
}
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, capture_output=True, text=True, timeout=180)


def render(path: Path) -> dict:
    result = run("docker", "compose", "-f", str(path), "config", "--format", "json")
    return json.loads(result.stdout)


def validate() -> None:
    for name, path in EXAMPLES.items():
        config = render(path)
        for service in config["services"].values():
            assert "@sha256:" in service["image"], f"{name}: image must be pinned"
            assert not service.get("privileged"), f"{name}: privileged container"
            assert not service.get("network_mode"), f"{name}: shared network namespace"
            for port in service.get("ports", []):
                assert port["host_ip"] == "127.0.0.1", f"{name}: non-loopback port"
            for volume in service.get("volumes", []):
                if volume["type"] == "bind":
                    assert volume.get("read_only"), f"{name}: writable bind mount"
        assert all(not n.get("external") for n in config["networks"].values()), name
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
        self.project = f"tamriel-example-{uuid.uuid4().hex[:12]}"
        config = render(self.path)
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
        return run(*self.command, *args, check=check)

    def url(self, service, port):
        address = self.compose("port", service, str(port)).stdout.strip()
        assert address.startswith("127.0.0.1:"), "expected a loopback-only endpoint"
        return f"http://{address}"

    def exec(self, service, *args, check=True):
        user = ["--user", "1000:1000"] if service.startswith("syncthing") else []
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
            checks = {"syncthing": syncthing, "caddy": caddy, "host-metrics": host_metrics}
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
