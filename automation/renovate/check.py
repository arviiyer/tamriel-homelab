#!/usr/bin/env python3
"""Validate Renovate configuration and extract a disposable Compose dependency offline."""

import json
import os
from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parent


def run(*args, **kwargs):
    result = subprocess.run(args, capture_output=True, text=True,
                            timeout=180, **kwargs)
    if result.returncode:
        print(result.stdout)
        print(result.stderr)
        result.check_returncode()
    return result.stdout


def main():
    rendered = run(
        "docker", "compose", "-f", str(ROOT / "compose.yml"), "config", "--format", "json",
        env=dict(os.environ, RENOVATE_TOKEN="configuration-check-only"),
    )
    image = json.loads(rendered)["services"]["renovate"]["image"]
    run(
        "docker", "run", "--rm", "--network", "none",
        "--mount", f"type=bind,src={ROOT / 'config.js'},dst=/example/config.js,readonly",
        "--entrypoint", "renovate-config-validator", image, "--strict", "/example/config.js",
    )
    print("PASS: Renovate strict configuration validation", flush=True)

    with tempfile.TemporaryDirectory(prefix="renovate-example-") as temporary:
        fixture = Path(temporary)
        # The container uses its own unprivileged UID; only synthetic files live here.
        fixture.chmod(0o755)
        (fixture / "compose.yml").write_text(
            "services:\n  web:\n    image: nginx:1.28.0\n", encoding="utf-8",
        )
        (fixture / "package.json").write_text(
            '{"dependencies":{"example-package":"1.0.0"}}\n', encoding="utf-8",
        )
        # Exercise the same manager policy without contacting Forgejo or a registry.
        (fixture / "local.cjs").write_text(
            "const config = require('/example/config.js'); delete config.endpoint;\n"
            "module.exports = { ...config, platform: 'local', repositories: [] };\n",
            encoding="utf-8",
        )
        for file in fixture.iterdir():
            file.chmod(0o644)
        output = run(
            "docker", "run", "--rm", "--network", "none",
            "--mount", f"type=bind,src={ROOT / 'config.js'},dst=/example/config.js,readonly",
            "--mount", f"type=bind,src={fixture},dst=/fixture,readonly",
            "--workdir", "/fixture",
            "--env", "RENOVATE_CONFIG_FILE=/fixture/local.cjs",
            "--env", "LOG_LEVEL=debug", "--env", "LOG_FORMAT=json",
            image, "--dry-run=extract",
        )
        records = [json.loads(line) for line in output.splitlines() if line.startswith("{")]
        errors = [record for record in records if record.get("level", 0) >= 40]
        assert not errors, errors
        extracted = next(record["packageFiles"] for record in records
                         if record.get("msg") == "Extracted dependencies")
        assert set(extracted) == {"docker-compose"}, extracted
        files = extracted["docker-compose"]
        assert len(files) == 1 and files[0]["packageFile"] == "compose.yml", files
        dependency = files[0]["deps"][0]
        assert dependency["depName"] == "nginx" and dependency["currentValue"] == "1.28.0"
        assert dependency["datasource"] == "docker", dependency
    print("PASS: Compose image extracted; npm file ignored", flush=True)


if __name__ == "__main__":
    main()
