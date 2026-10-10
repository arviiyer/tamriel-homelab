#!/usr/bin/env python3
"""Download and verify the model pinned in model.json."""
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

root = Path(__file__).resolve().parent
model = json.loads((root / "model.json").read_text())
directory = root / "models"
directory.mkdir(exist_ok=True)
target = directory / model["filename"]
if target.exists():
    with target.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != model["sha256"]:
            raise SystemExit("Existing model checksum mismatch")
    print("Model already present and verified")
else:
    if shutil.disk_usage(directory).free < model["bytes"] + 512 * 1024**2:
        raise SystemExit("Not enough space for the model")
    temporary = target.with_suffix(".partial")
    url = f'https://huggingface.co/{model["repository"]}/resolve/{model["revision"]}/{model["filename"]}'
    checksum = hashlib.sha256()
    try:
        with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as output:
            while block := response.read(8 * 1024**2):
                output.write(block)
                checksum.update(block)
        if temporary.stat().st_size != model["bytes"] or checksum.hexdigest() != model["sha256"]:
            raise ValueError("Model size or SHA-256 mismatch")
        temporary.chmod(0o644)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    print("Model downloaded and verified")
