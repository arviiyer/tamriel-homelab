from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path


MONITORING_ROOT = Path(__file__).resolve().parents[1]
GRAFANA_IMAGE = (
    "grafana/grafana@sha256:"
    "e932bd6ed0e026595b08483cd0141e5103e1ab7ff8604839ff899b8dc54cabcb"
)


def docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args],
        check=check,
        capture_output=True,
        text=True,
        timeout=120,
    )


def wait_for_json(
    container: str, path: str, attempts: int = 45
) -> dict[str, object]:
    for _ in range(attempts):
        response = docker(
            "exec",
            container,
            "wget",
            "-qO-",
            f"http://127.0.0.1:3000{path}",
            check=False,
        )
        try:
            if response.returncode == 0:
                return json.loads(response.stdout)
        except json.JSONDecodeError:
            pass
        time.sleep(1)
    raise RuntimeError(f"Grafana did not make {path} available")


def main() -> None:
    container = f"tamriel-grafana-validation-{os.getpid()}"
    dashboard_provider = (
        MONITORING_ROOT
        / "grafana"
        / "provisioning"
        / "dashboards"
        / "security.yml"
    ).resolve()
    datasource_provider = (
        MONITORING_ROOT
        / "grafana"
        / "provisioning"
        / "datasources"
        / "security.yml"
    ).resolve()
    dashboards = (MONITORING_ROOT / "grafana" / "dashboards").resolve()

    started = False

    def cleanup() -> None:
        docker("rm", "-f", container, check=False)

    def handle_signal(signum: int, _frame: object) -> None:
        cleanup()
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        docker(
            "run",
            "--rm",
            "-d",
            "--name",
            container,
            "--network",
            "none",
            "-e",
            "GF_AUTH_ANONYMOUS_ENABLED=true",
            "-e",
            "GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer",
            "-e",
            "GF_AUTH_DISABLE_LOGIN_FORM=true",
            "-e",
            "GF_ANALYTICS_REPORTING_ENABLED=false",
            "-e",
            "GF_ANALYTICS_CHECK_FOR_UPDATES=false",
            "-e",
            "GF_ANALYTICS_CHECK_FOR_PLUGIN_UPDATES=false",
            "-e",
            "GF_PLUGINS_PREINSTALL_DISABLED=true",
            "-v",
            f"{dashboard_provider}:/etc/grafana/provisioning/dashboards/security.yml:ro",
            "-v",
            f"{datasource_provider}:/etc/grafana/provisioning/datasources/security.yml:ro",
            "-v",
            f"{dashboards}:/var/lib/grafana/dashboards/security:ro",
            GRAFANA_IMAGE,
        )
        started = True

        health = wait_for_json(container, "/api/health")
        if health.get("database") != "ok" or health.get("version") != "12.4.1":
            raise RuntimeError(f"unexpected Grafana health response: {health}")

        response = wait_for_json(
            container, "/api/dashboards/uid/security-control-overview"
        )
        dashboard = response.get("dashboard", {})
        metadata = response.get("meta", {})
        if dashboard.get("uid") != "security-control-overview":
            raise RuntimeError("Grafana did not load the expected dashboard UID")
        if dashboard.get("title") != "Security Control Overview":
            raise RuntimeError("Grafana did not load the expected dashboard title")
        if metadata.get("folderUid") != "security-evidence":
            raise RuntimeError("Grafana did not use the expected public folder UID")
        if metadata.get("provisioned") is not True:
            raise RuntimeError("Grafana did not mark the dashboard as provisioned")

        for uid, datasource_type in (
            ("security-prometheus", "prometheus"),
            ("security-loki", "loki"),
        ):
            datasource = wait_for_json(container, f"/api/datasources/uid/{uid}")
            if datasource.get("uid") != uid or datasource.get("type") != datasource_type:
                raise RuntimeError(f"Grafana did not load datasource {uid}")

        print("Grafana provisioning smoke test passed.")
    except Exception:
        if started:
            result = docker("logs", container, check=False)
            logs = result.stdout + result.stderr
            if logs:
                print(logs)
        raise
    finally:
        cleanup()


if __name__ == "__main__":
    main()
