import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer

spec = importlib.util.spec_from_file_location("feed", Path(__file__).parents[1] / "serve.py")
feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)


class FeedTests(unittest.TestCase):
    def test_only_public_routes_are_served_and_rss_text_is_escaped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            server = ThreadingHTTPServer(("127.0.0.1", 0), feed.handler(path))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(base + "/briefing.json")
                self.assertEqual(error.exception.code, 503)
                error.exception.close()
                (path / "briefing.json").write_text(json.dumps({
                    "day": "2026-01-01", "generated_at": "2026-01-01T06:20:00+00:00", "mode": "sample",
                    "homepage_url": "https://home.example.com", "articles": [{
                        "id": "1", "title": "Example", "source": "Example feed", "summary": "Source excerpts:\n<img src=x>",
                        "freshrss_url": "https://rss.example.com", "hash": "private-internal-field",
                    }],
                }))
                with urllib.request.urlopen(base + "/briefing.json") as response:
                    self.assertNotIn("hash", json.load(response)["articles"][0])
                with urllib.request.urlopen(base + "/feed.xml") as response:
                    description = ET.fromstring(response.read()).findtext("channel/item/description")
                    self.assertIn("&lt;img", description)
                    self.assertNotIn("<img", description)
                for route in ["/", "/../brief.sqlite", "/brief.sqlite"]:
                    with self.subTest(route=route), self.assertRaises(urllib.error.HTTPError) as error:
                        urllib.request.urlopen(base + route)
                    self.assertEqual(error.exception.code, 404)
                    error.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()


if __name__ == "__main__":
    unittest.main()
