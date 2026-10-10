#!/usr/bin/env python3
"""Exercise real Authentik login and group access in a disposable HTTPS stack."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import secrets
import socket
import tempfile
from urllib.parse import urlsplit
import uuid

from playwright.sync_api import TimeoutError as BrowserTimeout
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("services", ROOT / "scripts/check-service-examples.py")
services = importlib.util.module_from_spec(spec)
spec.loader.exec_module(services)
AUTHENTIK = "ghcr.io/goauthentik/server:2026.8.3@sha256:ab9b4e8cc4ab3f8d1198d2db6aeea66bafea1963b3f2843589e0d163f97d9849"
POSTGRES = "postgres:17-alpine@sha256:742f40ea20b9ff2ff31db5458d127452988a2164df9e17441e191f3b72252193"
CADDY = "caddy:2-alpine@sha256:d8542f48d34a9cf4e4c11a478865229840e87e4c96ea3f439101f31a5d35f75f"


def unused_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    with tempfile.TemporaryDirectory(prefix="authentik-guide-") as directory:
        path = Path(directory)
        path.chmod(0o755)
        port = unused_port()
        auth_url = f"https://auth.example.com:{port}"
        app_url = f"https://app.example.com:{port}"
        password, token, db_password = (secrets.token_hex(24) for _ in range(3))
        environment = {
            "AUTHENTIK_POSTGRESQL__HOST": "postgresql",
            "AUTHENTIK_POSTGRESQL__USER": "authentik",
            "AUTHENTIK_POSTGRESQL__NAME": "authentik",
            "AUTHENTIK_POSTGRESQL__PASSWORD": db_password,
            "AUTHENTIK_SECRET_KEY": secrets.token_hex(48),
            "AUTHENTIK_BOOTSTRAP_PASSWORD": password,
            "AUTHENTIK_BOOTSTRAP_TOKEN": token,
            "AUTHENTIK_BOOTSTRAP_EMAIL": "operator@example.com",
            "AUTHENTIK_ERROR_REPORTING__ENABLED": "false",
        }
        config = (Path(__file__).parent / "Caddyfile").read_text()
        config = config.replace("admin localhost:2019", "admin off")
        config = config.replace("\ttls {\n\t\tdns cloudflare {env.CLOUDFLARE_API_TOKEN}\n\t}", "\ttls internal")
        (path / "Caddyfile").write_text(config)
        (path / "upstream.Caddyfile").write_text(':8088 {\n respond "Private example application"\n}\n')
        common = {"image": AUTHENTIK, "environment": environment,
                  "depends_on": {"postgresql": {"condition": "service_healthy"}}}
        compose = {
            "services": {
                "postgresql": {"image": POSTGRES,
                    "environment": {"POSTGRES_USER": "authentik", "POSTGRES_DB": "authentik",
                                    "POSTGRES_PASSWORD": db_password},
                    "healthcheck": {"test": ["CMD", "pg_isready", "-U", "authentik"],
                                    "interval": "2s", "timeout": "3s", "retries": 30}},
                "server": {**common, "command": "server", "ports": ["127.0.0.1::9000"]},
                "worker": {**common, "command": "worker"},
                "application": {"image": CADDY,
                    "volumes": ["./upstream.Caddyfile:/etc/caddy/Caddyfile:ro"]},
                "caddy": {"image": CADDY,
                    "environment": {"AUTH_DOMAIN": f"auth.example.com:{port}",
                        "APP_DOMAIN": f"app.example.com:{port}",
                        "AUTH_UPSTREAM": "server:9000", "APP_UPSTREAM": "application:8088",
                        "PROXY_LISTEN_ADDRESSES": "0.0.0.0", "TRUSTED_CIDRS": "0.0.0.0/0"},
                    "ports": [f"127.0.0.1:{port}:{port}"],
                    "volumes": ["./Caddyfile:/etc/caddy/Caddyfile:ro"],
                    "networks": {"default": {"aliases": ["auth.example.com", "app.example.com"]}}},
            }
        }
        file = path / "compose.json"
        file.write_text(json.dumps(compose))
        file.chmod(0o600)
        command = ["docker", "compose", "-p", "auth-guide-" + uuid.uuid4().hex[:10], "-f", str(file)]

        def dc(*args, **kwargs):
            return services.run(*command, *args, **kwargs)

        try:
            dc("up", "-d")
            api_url = "http://" + dc("port", "server", "9000").stdout.strip() + "/api/v3/"

            def api(route, method="GET", body=None):
                code, data = services.request(api_url + route, method=method, data=body,
                                             headers={"Authorization": "Bearer " + token})
                if code >= 400:
                    raise RuntimeError(f"Authentik {route}: HTTP {code}: {data[:500]}")
                return json.loads(data) if data else None

            def ready():
                try:
                    return api("core/users/me/")
                except RuntimeError:
                    return False

            services.wait_for("Authentik bootstrap", ready, seconds=240)
            def default_flows():
                flows = api("flows/instances/?page_size=100")["results"]
                by_slug = {item["slug"]: item["pk"] for item in flows}
                required = {"default-provider-authorization-explicit-consent",
                            "default-provider-invalidation-flow", "default-authentication-flow"}
                return by_slug if required <= by_slug.keys() else None

            flow = services.wait_for("Authentik default flows", default_flows, seconds=180)
            group = api("core/groups/", "POST", {"name": "homelab-users"})
            for username, groups in (("allowed-reader", [group["pk"]]), ("denied-reader", [])):
                user = api("core/users/", "POST", {
                    "username": username, "name": username, "email": username + "@example.com",
                    "is_active": True, "groups": groups,
                })
                api(f"core/users/{user['pk']}/set_password/", "POST", {"password": password})
            provider = api("providers/proxy/", "POST", {
                "name": "Example provider", "mode": "forward_single", "external_host": app_url,
                "authorization_flow": flow["default-provider-authorization-explicit-consent"],
                "invalidation_flow": flow["default-provider-invalidation-flow"],
            })
            app = api("core/applications/", "POST", {
                "name": "Example app", "slug": "example-app", "provider": provider["pk"],
                "policy_engine_mode": "any",
            })
            api("policies/bindings/", "POST", {"target": app["pk"], "group": group["pk"], "order": 0})
            outpost = next(item for item in api("outposts/instances/")["results"]
                           if item.get("managed") == "goauthentik.io/outposts/embedded")
            ca = dc("exec", "-T", "caddy", "cat", "/data/caddy/pki/authorities/local/root.crt").stdout
            (path / "ca.pem").write_text(ca)
            for service in ("server", "worker"):
                dc("cp", str(path / "ca.pem"), f"{service}:/usr/local/share/ca-certificates/example-root.crt")
                dc("exec", "-T", "--user", "0:0", service, "update-ca-certificates")
            dc("restart", "server", "worker")
            api_url = "http://" + dc("port", "server", "9000").stdout.strip() + "/api/v3/"
            services.wait_for("Authentik after CA installation", ready, seconds=120)
            settings = outpost["config"]
            settings.update(authentik_host=auth_url + "/")
            api(f"outposts/instances/{outpost['pk']}/", "PATCH",
                {"providers": [provider["pk"]], "config": settings})

            services.run("curl", "--fail", "--silent", "--show-error", "--cacert", str(path / "ca.pem"),
                         "--resolve", f"auth.example.com:{port}:127.0.0.1", auth_url + "/if/flow/default-authentication-flow/")
            print("PASS: Caddy certificate chain and hostname verification", flush=True)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(args=[
                    "--host-resolver-rules=MAP auth.example.com 127.0.0.1,MAP app.example.com 127.0.0.1",
                    "--no-proxy-server",
                ])

                def login(username):
                    # curl above verifies the local CA; Chromium has its own trust store.
                    context = browser.new_context(ignore_https_errors=True)
                    page = context.new_page()
                    page.set_default_timeout(45000)
                    def request_failed(request):
                        if request.failure != "net::ERR_ABORTED":
                            print("Browser request failed:",
                                  urlsplit(request.url)._replace(query="", fragment="").geturl(),
                                  request.failure, flush=True)

                    page.on("requestfailed", request_failed)
                    def login_page():
                        response = page.goto(app_url, wait_until="domcontentloaded")
                        if page.locator("input[name='uidField']").count():
                            return True
                        if response.status >= 400:
                            return False
                        try:
                            page.locator("input[name='uidField']").wait_for(timeout=5000)
                            return True
                        except BrowserTimeout:
                            return False

                    try:
                        services.wait_for("Authentik login page", login_page, seconds=90)
                    except RuntimeError:
                        print("Login page:", page.url, page.locator("body").inner_text(), flush=True)
                        raise
                    page.locator("input[name='uidField']").fill(username)
                    page.locator("ak-stage-identification button[type='submit']").click()
                    page.locator("ak-stage-password input[type='password']").fill(password)
                    page.locator("ak-stage-password button[type='submit']").click()
                    return context, page

                context, page = login("allowed-reader")
                expect(page.get_by_text("You're about to sign into Example app.", exact=True)).to_be_visible(timeout=45000)
                page.get_by_role("button", name="Continue", exact=True).click()
                expect(page.locator("body")).to_have_text("Private example application", timeout=45000)
                context.close()
                print("PASS: real Authentik login, consent, and allowed group", flush=True)
                context, page = login("denied-reader")
                expect(page.get_by_text("Request has been denied.", exact=False)).to_be_visible(timeout=45000)
                assert "Private example application" not in page.locator("body").inner_text()
                context.close()
                print("PASS: user outside the application group is denied", flush=True)
                dc("stop", "server")
                context = browser.new_context(ignore_https_errors=True)
                response = context.new_page().goto(app_url)
                assert response.status == 502
                context.close()
                browser.close()
                print("PASS: identity outage does not expose the upstream", flush=True)
        finally:
            dc("down", "--volumes", "--remove-orphans")


if __name__ == "__main__":
    main()
