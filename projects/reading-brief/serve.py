#!/usr/bin/env python3
"""Read-only JSON/RSS endpoint for the last published briefing."""
import argparse
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def rss(payload):
    root = ET.Element("rss", version="2.0")
    channel = ET.SubElement(root, "channel")
    ET.SubElement(channel, "title").text = "Daily reading brief"
    ET.SubElement(channel, "link").text = payload["homepage_url"]
    ET.SubElement(channel, "description").text = "Source excerpts for " + payload["day"]
    for article in payload["articles"]:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = article["title"]
        ET.SubElement(item, "link").text = article["freshrss_url"]
        ET.SubElement(item, "guid", isPermaLink="false").text = payload["day"] + ":" + article["id"]
        ET.SubElement(item, "description").text = escape(article["summary"]).replace("\n", "<br>")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def handler(directory):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in {"/health", "/briefing.json", "/status.json", "/feed.xml"}:
                self.send_error(404)
                return
            kind = "application/json"
            if self.path == "/health":
                body = b'{"status":"ok"}\n'
            else:
                try:
                    payload = json.loads((Path(directory) / "briefing.json").read_text())
                except (OSError, ValueError):
                    self.send_error(503, "No completed briefing")
                    return
                if self.path == "/feed.xml":
                    body, kind = rss(payload), "application/rss+xml"
                elif self.path == "/status.json":
                    body = json.dumps({"day": payload["day"], "mode": payload["mode"],
                                       "articles": len(payload["articles"])}).encode()
                else:
                    body = json.dumps({"day": payload["day"], "generated_at": payload["generated_at"],
                                       "articles": [{key: a[key] for key in ["id", "title", "source", "summary", "freshrss_url"]}
                                                    for a in payload["articles"]]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", kind + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
    return Handler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", default="data/public")
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8094)
    args = parser.parse_args()
    ThreadingHTTPServer((args.bind, args.port), handler(args.directory)).serve_forever()
