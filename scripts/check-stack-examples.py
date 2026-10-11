#!/usr/bin/env python3
"""Check connected examples with disposable data, local receivers, and mock identity/VPN peers."""

from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import urllib.request
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("services", ROOT / "scripts/check-service-examples.py")
services = importlib.util.module_from_spec(spec)
spec.loader.exec_module(services)
run, request, wait_for = services.run, services.request, services.wait_for
CADDY = "caddy:2-alpine@sha256:d8542f48d34a9cf4e4c11a478865229840e87e4c96ea3f439101f31a5d35f75f"
PYTHON = "python@sha256:9d2e5553305c7c7b0097999bb17187c69b921ccd6bc9d40e4bb5ebe652c00285"
ALLOY = "grafana/alloy:v1.18.1@sha256:0f4434c92b3e6cdac38bb129b344e1790c246f7b6e2eaffcc16a5fa363240e33"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


services.HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


class Project:
    def __init__(self, directory, source):
        self.directory = Path(directory)
        self.source = source
        shutil.copytree(ROOT / source, self.directory, dirs_exist_ok=True)
        self.command = ["docker", "compose", "-p", "tamriel-stack-" + uuid.uuid4().hex[:12],
                        "--project-directory", str(self.directory),
                        "-f", str(self.directory / "compose.yml")]
        self.env = dict(os.environ)

    def add(self, name, content):
        path = self.directory / name
        path.write_text(json.dumps(content))
        self.command.extend(["-f", str(path)])

    def compose(self, *args, check=True):
        return run(*self.command, *args, check=check, env=self.env)

    def url(self, service, port):
        return "http://" + self.compose("port", service, str(port)).stdout.strip()

    def cleanup(self):
        self.compose("down", "--volumes", "--remove-orphans", check=False)
        if self.source == "media/servarr" and (self.directory / "config").exists():
            # The runner UID can differ from Seerr's fixed UID, including in CI.
            run("docker", "run", "--rm", "--network", "none", "--user", "0:0",
                "-v", f"{self.directory / 'config'}:/config", "--entrypoint", "chown",
                CADDY, "-R", f"{os.getuid()}:{os.getgid()}", "/config")


def media_environment(path):
    return dict(os.environ, PUID=str(os.getuid()), PGID=str(os.getgid()),
                DOWNLOADS_PATH=str(path / "downloads"), MEDIA_PATH=str(path / "media"),
                WIREGUARD_PRIVATE_KEY=base64.b64encode(secrets.token_bytes(32)).decode(),
                WIREGUARD_ADDRESSES="192.0.2.2/32", SERVER_COUNTRIES="Sweden",
                COMPOSE_PROFILES="music,usenet,indexer-helper", MEDIA_BIND_IP="127.0.0.1")


def validate():
    with tempfile.TemporaryDirectory(prefix="tamriel-stack-config-") as directory:
        path = Path(directory)
        config = services.render(ROOT / "media/servarr/compose.yml", env=media_environment(path))
        apps = config["services"]
        for name, app in apps.items():
            assert "@sha256:" in app["image"], name
            assert not app.get("privileged"), name
            for port in app.get("ports", []):
                assert port["host_ip"] == "127.0.0.1", name
            if name not in ("gluetun", "seerr"):
                assert app["network_mode"] == "service:gluetun", name
                assert not app.get("ports") and not app.get("networks"), name
                assert app["depends_on"]["gluetun"]["condition"] == "service_healthy", name
            for mount in app.get("volumes", []):
                if mount["target"].startswith("/data/"):
                    assert not mount.get("bind", {}).get("create_host_path", False), name
        assert apps["gluetun"]["cap_add"] == ["NET_ADMIN"]
        assert apps["gluetun"]["devices"][0]["source"] == "/dev/net/tun"
        assert not apps["seerr"].get("network_mode")
        assert apps["gluetun"]["environment"].get("FIREWALL", "on") == "on"
        for manager in ("sonarr", "radarr", "lidarr"):
            mounts = {v["target"]: v["source"] for v in apps[manager]["volumes"]}
            assert mounts["/data/downloads"] == str(path / "downloads")
            assert mounts["/data/media"] == str(path / "media")
        # The separate projects must agree on the private interface and library.
        lan_env = dict(media_environment(path), MEDIA_BIND_IP="192.0.2.84",
                       JELLYFIN_UID="1000", JELLYFIN_GID="1000")
        lan = services.render(ROOT / "media/servarr/compose.yml", env=lan_env)
        jellyfin = services.render(ROOT / "media/jellyfin/compose.yml", env=lan_env)
        for app in [*lan["services"].values(), jellyfin["services"]["jellyfin"]]:
            for port in app.get("ports", []):
                assert port["host_ip"] == "192.0.2.84"
        library = next(v for v in jellyfin["services"]["jellyfin"]["volumes"] if v["target"] == "/media")
        assert library["source"] == str(path / "media") and library["read_only"]
        proxy = Project(path / "access", "networking/private-access")
        shutil.copyfile(proxy.directory / "environment.example", proxy.directory / ".env")
        proxy.compose("config", "--quiet")
        services.render(ROOT / "monitoring/host-metrics/compose.yml",
                        ROOT / "monitoring/host-metrics/alerts.override.yml")
    print("PASS: media namespaces, storage mappings, private proxy, and alert Compose configuration")


def media(project):
    project.env = media_environment(project.directory)
    for name in ("downloads", "media/movies", "media/tv", "media/music"):
        (project.directory / name).mkdir(parents=True, exist_ok=True)
    for app in ("qbittorrent", "sonarr", "radarr", "prowlarr", "lidarr", "nzbget", "seerr"):
        (project.directory / "config" / app).mkdir(parents=True)
    run("docker", "run", "--rm", "--network", "none", "--user", "0:0",
        "-v", f"{project.directory / 'config/seerr'}:/config", "--entrypoint", "chown",
        CADDY, "1000:1000", "/config")
    # A local namespace peer replaces only the provider-dependent VPN process.
    # This does not test tunnel establishment or the real Gluetun firewall.
    override = project.directory / "test.override.yml"
    override.write_text(f"""services:
  gluetun:
    image: {CADDY}
    entrypoint: [/bin/sh, -c, 'sleep 3600']
    cap_add: !reset []
    devices: !reset []
    ports: !override
      - '127.0.0.1::8989'
      - '127.0.0.1::7878'
      - '127.0.0.1::8080'
      - '127.0.0.1::9696'
      - '127.0.0.1::8686'
      - '127.0.0.1::6789'
    healthcheck:
      test: [CMD, /bin/true]
      interval: 1s
      timeout: 1s
      retries: 3
  seerr:
    ports: !override
      - '127.0.0.1::5055'
""")
    project.command += ["-f", str(override)]
    project.compose("up", "-d", "--pull", "missing")
    for name, port, folder in (("sonarr", 8989, "tv"), ("radarr", 7878, "movies")):
        url = project.url("gluetun", port)
        wait_for(name, lambda: request(url + "/ping")[0] == 200, seconds=180)
        key = ET.parse(project.directory / "config" / name / "config.xml").findtext("ApiKey")
        status, body = request(url + "/api/v3/rootfolder", method="POST",
                               headers={"X-Api-Key": key}, data={"path": "/data/media/" + folder})
        assert status == 201, f"{name} cannot use library: {status} {body[:100]}"
        assert json.loads(body)["path"] == "/data/media/" + folder
    seerr = project.url("seerr", 5055)
    wait_for("Seerr", lambda: request(seerr + "/api/v1/settings/public")[0] == 200, seconds=180)
    # Seerr must reach managers via gluetun rather than its own localhost.
    project.compose("exec", "-T", "seerr", "wget", "-qO-", "http://gluetun:7878/ping")
    for port, endpoint in ((9696, "/ping"), (8686, "/ping"), (8080, "/"), (6789, "/")):
        url = project.url("gluetun", port)
        wait_for(str(port), lambda: request(url + endpoint)[0] in (200, 401), seconds=180)
    # Model the VM's private interface with this temporary Docker bridge gateway.
    # Seerr reaches Jellyfin through a host-published port in a separate project.
    container = project.compose("ps", "-q", "seerr").stdout.strip()
    network = json.loads(run("docker", "inspect", container).stdout)[0]["NetworkSettings"]["Networks"]
    gateway = next(iter(network.values()))["Gateway"]
    peer_dir = project.directory / "jellyfin"
    peer_dir.mkdir()
    peer = services.Project("jellyfin", peer_dir)
    peer.env["MEDIA_PATH"] = str(project.directory / "media")
    (peer_dir / "ports.yml").write_text(
        f"services:\n  jellyfin:\n    ports: !override\n      - '{gateway}::8096'\n")
    try:
        peer.compose("up", "-d", "--pull", "missing")
        endpoint = "http://" + peer.compose("port", "jellyfin", "8096").stdout.strip() + "/health"
        wait_for("Jellyfin private port", lambda: request(endpoint) == (200, "Healthy"))
        result = project.compose("exec", "-T", "seerr", "wget", "-qO-", endpoint)
        assert result.stdout.strip() == "Healthy"
        project.compose("exec", "-T", "radarr", "touch", "/data/media/.shared-library-check")
        peer.exec("jellyfin", "sh", "-c",
                  "test -r /media/.shared-library-check && test ! -w /media/.shared-library-check")
    finally:
        peer.compose("down", "--volumes", "--remove-orphans", check=False)
    print("PASS: media startup, manager access, Seerr-to-Jellyfin connection, and shared library (mock VPN)")


def access(project):
    image = "tamriel-caddy-example:check"
    env = dict(os.environ)
    if run("docker", "buildx", "version", check=False).returncode:
        env["DOCKER_BUILDKIT"] = "0"
    run("docker", "build", "-t", image, str(ROOT / "networking/private-access"), env=env)
    environment = dict(AUTH_DOMAIN="auth.example.com", APP_DOMAIN="app.example.com",
                       AUTH_UPSTREAM="identity:9000", APP_UPSTREAM="application:8088",
                       PROXY_LISTEN_ADDRESSES="0.0.0.0", TRUSTED_CIDRS="0.0.0.0/0",
                       CLOUDFLARE_API_TOKEN=secrets.token_hex(24))
    original = project.directory / "Caddyfile"
    original.write_text(original.read_text() + "\n" + (project.directory / "media.caddy").read_text())
    arguments = ["docker", "run", "--rm"]
    for key, value in environment.items():
        arguments += ["-e", f"{key}={value}"]
    run(*arguments, "-v", f"{original}:/etc/caddy/Caddyfile:ro", image,
        "caddy", "adapt", "--config", "/etc/caddy/Caddyfile", "--validate")
    config = original.read_text().replace("admin localhost:2019", "admin off")
    config = config.replace("\ttls {\n\t\tdns cloudflare {env.CLOUDFLARE_API_TOKEN}\n\t}\n", "")
    config = config.replace("media.example.com {", "http://media.example.com {")
    config = config.replace("requests.example.com {", "http://requests.example.com {")
    config = config.replace("192.0.2.84:8096", "application:8088")
    config = config.replace("192.0.2.84:5055", "identity:9000")
    original.write_text(config)
    environment.update(AUTH_DOMAIN="http://auth.example.com", APP_DOMAIN="http://app.example.com")
    (project.directory / "identity.Caddyfile").write_text(""":9000 {
  handle /outpost.goauthentik.io/auth/caddy {
    route {
    @allowed header Cookie session=allowed
    respond @allowed "" 200
    @denied header Cookie session=denied
    respond @denied "" 403
    redir https://auth.example.com/login 302
    }
  }
  respond "outpost" 200
}
""")
    (project.directory / "application.Caddyfile").write_text(':8088 {\n respond "private app" 200\n}\n')
    compose = {"services": {
        "caddy": {"image": image, "environment": environment, "read_only": True,
                  "cap_drop": ["ALL"], "cap_add": ["NET_BIND_SERVICE"],
                  "security_opt": ["no-new-privileges:true"],
                  "ports": ["127.0.0.1::80"],
                  "sysctls": {"net.ipv4.ip_unprivileged_port_start": "1024"},
                  "networks": ["default", "access"],
                  "volumes": ["./Caddyfile:/etc/caddy/Caddyfile:ro", "caddy-data:/data", "caddy-config:/config"]},
        **{name: {"image": CADDY, "volumes": [f"./{name}.Caddyfile:/etc/caddy/Caddyfile:ro"]}
           for name in ("identity", "application")}},
        "networks": {"default": {"internal": True}, "access": {}},
        "volumes": {"caddy-data": {}, "caddy-config": {}}}
    (project.directory / "compose.yml").write_text(json.dumps(compose))
    project.compose("up", "-d")
    url = project.url("caddy", 80)
    headers = {"Host": "app.example.com"}
    wait_for("anonymous redirect", lambda: request(url, headers=headers)[0] == 302)
    assert request(url, headers={**headers, "X-Authentik-Username": "operator"})[0] == 302
    assert request(url, headers={**headers, "Cookie": "session=denied"})[0] == 403
    assert request(url, headers={**headers, "Cookie": "session=allowed"}) == (200, "private app")
    assert request(url + "/outpost.goauthentik.io/start", headers=headers) == (200, "outpost")
    # Media routes use application login, so no forward-auth cookie is required.
    assert request(url, headers={"Host": "media.example.com"}) == (200, "private app")
    assert request(url, headers={"Host": "requests.example.com"}) == (200, "outpost")
    project.compose("stop", "identity")
    assert request(url, headers={**headers, "Cookie": "session=allowed"})[0] == 502
    assert request(url, headers={"Host": "media.example.com"}) == (200, "private app")
    project.compose("exec", "-T", "application", "wget", "-qO-", "http://localhost:8088")
    environment["TRUSTED_CIDRS"] = "192.0.2.0/24"
    (project.directory / "compose.yml").write_text(json.dumps(compose))
    project.compose("up", "-d", "--no-deps", "caddy")
    url = project.url("caddy", 80)
    wait_for("source rejection", lambda: request(url, headers=headers)[0] == 403)
    for host in ("media.example.com", "requests.example.com"):
        assert request(url, headers={"Host": host})[0] == 403
    print("PASS: Caddy DNS module/config, redirects, access denial, outpost routing, and identity failure (mock identity)")


def alerts(project):
    project.command += ["-f", str(project.directory / "alerts.override.yml")]
    receiver = """from http.server import BaseHTTPRequestHandler, HTTPServer
class Receiver(BaseHTTPRequestHandler):
    def do_POST(self):
        body = self.rfile.read(int(self.headers['Content-Length']))
        with open('/output/received.jsonl', 'ab') as f:
            f.write(body + b'\\n')
        self.send_response(204)
        self.end_headers()
HTTPServer(('0.0.0.0', 9094), Receiver).serve_forever()
"""
    (project.directory / "receiver.py").write_text(receiver)
    output = project.directory / "output"
    output.mkdir()
    project.add("receiver.yml", {"services": {"receiver": {
        "image": PYTHON, "user": f"{os.getuid()}:{os.getgid()}",
        "command": ["python", "/receiver.py"], "networks": ["metrics"],
        "volumes": ["./receiver.py:/receiver.py:ro", "./output:/output"]}}})
    config = {"route": {"receiver": "test", "group_by": ["alertname", "host"],
                        "group_wait": "1s", "group_interval": "1s", "repeat_interval": "12h"},
              "receivers": [{"name": "test", "discord_configs": [
                  {"webhook_url": "http://receiver:9094", "send_resolved": True}]}]}
    (project.directory / "alertmanager.yml").write_text(json.dumps(config))
    override = project.directory / "ports.yml"
    override.write_text("""services:
  prometheus:
    ports: !override ['127.0.0.1::9090']
  grafana:
    ports: !reset []
  alertmanager:
    ports: !reset []
""")
    project.command += ["-f", str(override)]
    project.compose("run", "--rm", "--no-deps", "--entrypoint", "promtool", "prometheus",
                    "check", "config", "/etc/prometheus/prometheus.yml")
    project.compose("run", "--rm", "--no-deps", "--entrypoint", "amtool", "alertmanager",
                    "check-config", "/etc/alertmanager/alertmanager.yml")
    project.compose("up", "-d", "node-exporter", "prometheus", "alertmanager", "receiver")
    url = project.url("prometheus", 9090)
    wait_for("Prometheus", lambda: request(url + "/-/ready")[0] == 200)
    wait_for("healthy exporter", lambda: '"1"' in request(url + "/api/v1/query?query=up")[1])
    project.compose("stop", "node-exporter")

    def notified(state):
        path = output / "received.jsonl"
        return path.exists() and any(
            state in line and "HostUnavailable" in line for line in path.read_text().splitlines())

    wait_for("firing Discord payload", lambda: notified("FIRING"), seconds=240)
    project.compose("start", "node-exporter")
    wait_for("resolved Discord payload", lambda: notified("RESOLVED"), seconds=90)
    print("PASS: exporter failure and recovery reach the local Discord-compatible receiver")


def alloy():
    run("docker", "run", "--rm", "-v", f"{ROOT / 'monitoring/logs/config.alloy'}:/etc/alloy/config.alloy:ro",
        ALLOY, "validate", "/etc/alloy/config.alloy")
    print("PASS: Alloy journal configuration")


def smoke(name):
    source = {"media": "media/servarr", "access": "networking/private-access",
              "alerts": "monitoring/host-metrics"}[name]
    with tempfile.TemporaryDirectory(prefix="tamriel-stack-") as directory:
        project = Project(directory, source)
        try:
            {"media": media, "access": access, "alerts": alerts}[name](project)
        except (AssertionError, RuntimeError, subprocess.CalledProcessError):
            print(project.compose("logs", "--tail=15", check=False).stdout)
            raise
        finally:
            project.cleanup()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--smoke", choices=["media", "access", "alerts", "alloy", "all"])
    args = parser.parse_args()
    if args.validate:
        validate()
    else:
        for name in ["media", "access", "alerts", "alloy"] if args.smoke == "all" else [args.smoke]:
            alloy() if name == "alloy" else smoke(name)


if __name__ == "__main__":
    main()
