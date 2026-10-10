#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
: "${FRESHRSS_CONTAINER:?Set the FreshRSS container name}"
: "${FRESHRSS_USER:?Set the FreshRSS username}"
mkdir -p data/public
exec 9>data/run.lock
flock -n 9 || exit 0
umask 077
docker exec -i --user www-data "$FRESHRSS_CONTAINER" php -- \
  --user="$FRESHRSS_USER" --days=7 --limit=1000 < export.php > data/articles.ndjson.tmp
mv data/articles.ndjson.tmp data/articles.ndjson
python3 brief.py select
if python3 -c 'import json,sys; s=json.load(open("data/selection.json")); sys.exit(not (s.get("existing") or not s["articles"]))'; then
  if ! python3 -c 'import json,sys; sys.exit(not json.load(open("data/selection.json")).get("existing"))'; then
    python3 brief.py complete
  fi
  exit 0
fi
trap 'docker compose --profile inference stop model >/dev/null' EXIT
docker compose --profile inference up -d model
python3 - <<'PY'
import time
import urllib.request
for attempt in range(120):
    try:
        urllib.request.urlopen('http://127.0.0.1:8092/health', timeout=3).close()
        break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit('Local model did not become ready')
PY
python3 brief.py complete
