#!/usr/bin/env python3
"""Check the documented Unbound config behind a fresh Pi-hole instance."""

import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("services", ROOT / "scripts/check-service-examples.py")
services = importlib.util.module_from_spec(spec)
spec.loader.exec_module(services)
DEBIAN = "debian@sha256:3a39a0592364683e6bab97937b72cad5a8fa6dcbbee90edb3bb48c7f8e94f258"
PIHOLE = "pihole/pihole:2026.09.0@sha256:5b9c8cf51de7d6d3f2240dbe72baf5f06e1fd39cb4d77a99fab4fa13e23bd1be"


def main():
    with tempfile.TemporaryDirectory(prefix="dns-guide-") as directory:
        path = Path(directory)
        path.chmod(0o755)
        readme = (Path(__file__).parent / "README.md").read_text()
        config = re.search(r"^```yaml\n(.*?)^```", readme, re.M | re.S).group(1)
        (path / "pi-hole.conf").write_text(config)
        (path / "Dockerfile").write_text(
            f"FROM {DEBIAN}\n"
            "RUN apt-get update && apt-get install -y --no-install-recommends "
            "unbound dns-root-data dnsutils ca-certificates && rm -rf /var/lib/apt/lists/*\n"
            "COPY pi-hole.conf /etc/unbound/unbound.conf.d/pi-hole.conf\n"
            # The package's systemd unit normally initializes the trust anchor.
            "RUN /usr/libexec/unbound-helper root_trust_anchor_update && unbound-checkconf\n"
            'CMD ["unbound", "-d"]\n'
        )
        compose = {"services": {
            "resolver": {"build": str(path)},
            "pihole": {
                "image": PIHOLE,
                "network_mode": "service:resolver",
                "environment": {
                    "FTLCONF_dns_upstreams": "127.0.0.1#5335",
                    "FTLCONF_dns_hosts": "192.0.2.5 app.example.com",
                    "FTLCONF_webserver_port": "8080",
                    "FTLCONF_webserver_api_password": secrets.token_hex(24),
                    "FTLCONF_dns_listeningMode": "LOCAL",
                },
            },
        }}
        file = path / "compose.json"
        file.write_text(json.dumps(compose))
        file.chmod(0o600)
        name = "dns-guide-" + uuid.uuid4().hex[:10]
        command = ["docker", "compose", "-p", name, "-f", str(file)]

        def dc(*args):
            return services.run(*command, *args)

        def query(name, port=53, *flags):
            return dc("exec", "-T", "resolver", "dig", "@127.0.0.1", "-p", str(port),
                      "+time=15", "+tries=2", *flags, name).stdout

        try:
            env = dict(os.environ)
            if services.run("docker", "buildx", "version", check=False).returncode:
                env["DOCKER_BUILDKIT"] = "0"
            services.run("docker", "build", "--force-rm", "-t", name + "-resolver", str(path), env=env)
            dc("up", "-d", "--no-build")

            def ready():
                try:
                    return "192.0.2.5" in query("app.example.com")
                except subprocess.CalledProcessError:
                    return False

            services.wait_for("Pi-hole local record", ready, seconds=120)
            for port in (5335, 53):
                normal = query("example.com", port)
                assert "status: NOERROR" in normal and re.search(r"ANSWER: [1-9]", normal), normal
                invalid = query("fail01.dnssec.works", port)
                assert "status: SERVFAIL" in invalid, invalid
            unchecked = query("fail01.dnssec.works", 5335, "+cdflag")
            assert "status: NOERROR" in unchecked and re.search(r"ANSWER: [1-9]", unchecked), unchecked
            print("PASS: Pi-hole local record, Unbound recursion, and DNSSEC rejection through both resolvers")
        finally:
            dc("down", "--volumes", "--remove-orphans", "--rmi", "local")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        print(error.stdout, error.stderr)
        raise
