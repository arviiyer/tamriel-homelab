import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timezone

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("brief", ROOT / "brief.py")
brief = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brief)


class BriefTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name)
        self.store = brief.Store(self.path / "brief.sqlite")
        self.addCleanup(self.store.db.close)
        self.profile = json.loads((ROOT / "profile.example.json").read_text())
        self.articles = brief.load_articles(ROOT / "articles.example.ndjson", self.profile)
        self.now = datetime.now(timezone.utc)
        for article in self.articles:
            article["published"] = self.now.timestamp()

    def selection(self):
        return {"day": "2026-01-01", "mode": "sample", "articles": brief.select(
            self.articles, self.profile, self.store, brief.DemoModels(), self.now)}

    def test_failed_inference_keeps_last_brief_and_history(self):
        public = self.path / "public"
        brief.atomic_json(public / "briefing.json", {"day": "previous"})
        before = (public / "briefing.json").read_bytes()

        class Broken(brief.DemoModels):
            def choose(self, article, sentences):
                raise ValueError("Truncated response")

        with self.assertRaises(ValueError):
            brief.complete(self.selection(), self.profile, self.store, Broken(), public)
        self.assertEqual((public / "briefing.json").read_bytes(), before)
        self.assertIsNone(self.store.completed("2026-01-01"))
        self.assertFalse(self.store.seen(self.articles[0]))

    def test_republication_repairs_missing_file_without_model_calls(self):
        selection = self.selection()
        payload = brief.complete(selection, self.profile, self.store, brief.DemoModels(), self.path)
        (self.path / "briefing.json").unlink()
        restored = brief.complete(selection, self.profile, self.store, None, self.path)
        self.assertEqual(restored, payload)
        self.assertTrue(self.store.seen(self.articles[0]))

    def test_duplicate_or_unknown_sentence_ids_rejected(self):
        sentences = [{"id": 0, "text": "Original"}]
        for ids in [[1], [0, 0], [True], [], "0"]:
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                brief.validate_ids(ids, sentences)

    def test_output_only_contains_source_excerpts(self):
        payload = brief.complete(self.selection(), self.profile, self.store, brief.DemoModels(), self.path)
        sources = {a["id"]: a["text"] for a in self.articles}
        for article in payload["articles"]:
            for quote in article["summary"].removeprefix("Source excerpts:\n").split("\n\n"):
                self.assertIn(quote[1:-1], sources[article["id"]])

    def test_short_advisory_entries_survive(self):
        text = "CVE-2026-12345 Example service authentication bypass\nCVE-2026-12346"
        self.assertEqual(len(brief.source_sentences(text)), 1)

    def test_wrapped_html_keeps_complete_sentences_and_structural_breaks(self):
        content = ("<p>A malformed document could cause denial of\n"
                   "service when the application processes its embedded images.</p>"
                   "<p>Install the <strong>security update</strong> before opening\n"
                   "documents received from an untrusted source.<br>"
                   "CVE-2026-12345 Example parser denial of service</p>"
                   "<script>Hidden content must not enter the excerpt.</script>")
        text = brief.clean_html(content)
        self.assertEqual(text.splitlines(), [
            "A malformed document could cause denial of service when the application processes its embedded images.",
            "Install the security update before opening documents received from an untrusted source.",
            "CVE-2026-12345 Example parser denial of service",
        ])
        self.assertEqual([s["text"] for s in brief.source_sentences(text)], text.splitlines())

    def test_exact_duplicates_and_read_entries_skipped(self):
        self.articles.append(dict(self.articles[0], id="3"))
        self.articles[1]["is_read"] = True
        self.assertEqual(len(self.selection()["articles"]), 1)


if __name__ == "__main__":
    unittest.main()
