from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SOURCE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check-markdown-links.py"


class MarkdownLinkTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name)
        script = self.root / "scripts/check-markdown-links.py"
        script.parent.mkdir()
        shutil.copyfile(SOURCE_SCRIPT, script)

    def write(self, name: str, content: str) -> None:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def check(self) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "scripts/check-markdown-links.py"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_relative_links_and_images_pass(self) -> None:
        self.write("README.md", '[Guide](docs/guide.md#setup)\n![View](view.png "Lab")\n')
        self.write("docs/guide.md", "# Guide\n\n## Setup\n[Home](../README.md)\n")
        self.write("view.png", "synthetic image fixture\n")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_link_and_image_are_both_reported(self) -> None:
        self.write("README.md", "[Guide](missing.md)\n![View](missing.png)\n")
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("README.md: missing target missing.md", result.stderr)
        self.assertIn("README.md: missing target missing.png", result.stderr)

    def test_linked_image_checks_inner_and_outer_targets(self) -> None:
        self.write("README.md", "[![View](missing.png)](guide.md#absent)\n")
        self.write("guide.md", "# Guide\n")
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing target missing.png", result.stderr)
        self.assertIn("missing heading guide.md#absent", result.stderr)

    def test_same_page_and_duplicate_heading_links(self) -> None:
        self.write("README.md", """# Guide
[First](#notes) [Explicit suffix](#notes-1) [Duplicate](#notes-2)
## Notes
## Notes-1
## Notes
""")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.write("README.md", "# Guide\n[Missing](#absent)\n")
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing heading #absent", result.stderr)

    def test_formatted_headings_and_encoded_fragments(self) -> None:
        self.write("README.md", """# Guide
[Tools](#caddy-and-authentik) [Label](#useful-notes) [Field](#db_name)
[Accents](#caf%C3%A9) [Legacy heading](#the-setup)
## **Caddy** and [Authentik](https://example.com) ##
## _Useful_ notes
## `db_name`
## Café
The setup
---------
""")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_code_examples_are_excluded(self) -> None:
        self.write("README.md", """# Guide
`[Example](missing.md)` and ``![Example](missing.png)``
```markdown
## Sample
[Example](missing.md)
```
~~~~markdown
![Example](missing.png)
~~~
## Another sample
~~~~
    [Example](missing.md)
""")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)
        with (self.root / "README.md").open("a") as output:
            output.write("\n[Sample](#sample) [Other](#another-sample)\n")
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing heading #sample", result.stderr)
        self.assertIn("missing heading #another-sample", result.stderr)

    def test_paths_with_spaces_and_parentheses(self) -> None:
        self.write("README.md", """# Guide
[Encoded](docs/setup%20notes.md#setup)
[Angle](<docs/setup notes.md#setup> "Title")
[Parentheses](docs/setup(example).md)
""")
        self.write("docs/setup notes.md", "# Setup\n")
        self.write("docs/setup(example).md", "# Example\n")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_directory_fragments_resolve_to_readme(self) -> None:
        self.write("README.md", "[Guide](docs/#setup)\n")
        self.write("docs/README.md", "# Setup\n")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.root / "docs/README.md").unlink()
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("no README for docs/#setup", result.stderr)

    def test_external_links_are_skipped(self) -> None:
        self.write("README.md", """# Guide
[Web](https://example.com/missing#missing)
[Email](mailto:operator@example.com)
![Remote image](//example.com/image.png)
""")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
