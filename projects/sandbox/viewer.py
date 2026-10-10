#!/usr/bin/env python3
"""Local read-only viewer for generated sandbox lifecycle scenarios."""
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from lifecycle import SCENARIOS, replay

TEMPLATE = (Path(__file__).parent / "index.html").read_text()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlsplit(self.path)
        if url.path not in {"/", "/run.json"}:
            self.send_error(404)
            return
        scenario = parse_qs(url.query).get("scenario", ["complete"])[0]
        if scenario not in SCENARIOS:
            self.send_error(400, "Unknown scenario")
            return
        run = replay(scenario)
        if url.path == "/run.json":
            body, kind = json.dumps(run.snapshot(), indent=2), "application/json"
        else:
            rows = "".join("<tr>" + "".join(f"<td>{escape(event[key])}</td>" for key in ["time", "type", "detail"]) + "</tr>" for event in run.events)
            body = TEMPLATE.replace("{{events}}", rows)
            for key, value in {"state": run.state, "worker": run.worker, "evidence": run.evidence, "scenario": scenario}.items():
                body = body.replace("{{" + key + "}}", escape(value))
            kind = "text/html"
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    print("Sandbox workflow demo: http://127.0.0.1:8096", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8096), Handler).serve_forever()
