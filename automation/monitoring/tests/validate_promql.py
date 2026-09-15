from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml


MONITORING_ROOT = Path(__file__).resolve().parents[1]
PROMETHEUS_IMAGE = (
    "prom/prometheus@sha256:"
    "508729e0e2d18e11fd742a5a5ca70e557b940a93948c3c95fd0123a6fd538b69"
)


def main() -> None:
    dashboard = json.loads(
        (MONITORING_ROOT / "grafana/dashboards/security-control-overview.json")
        .read_text(encoding="utf-8")
    )
    [panel] = [
        panel for panel in dashboard["panels"]
        if panel["title"] == "Failed Repositories"
    ]
    [target] = panel["targets"]
    fixture = yaml.safe_load(
        (MONITORING_ROOT / "tests/failed_repositories.test.yml")
        .read_text(encoding="utf-8")
    )
    for case in fixture["tests"]:
        for query in case["promql_expr_test"]:
            query["expr"] = target["expr"]

    subprocess.run(
        [
            "docker", "run", "--rm", "--network", "none", "-i",
            "--entrypoint", "promtool", PROMETHEUS_IMAGE,
            "test", "rules", "/dev/stdin",
        ],
        input=yaml.safe_dump(fixture),
        text=True,
        check=True,
        timeout=120,
    )
    print(f"Failed Repositories: {len(fixture['tests'])} PromQL cases passed.")


if __name__ == "__main__":
    main()
