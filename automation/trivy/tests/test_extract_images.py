from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


TRIVY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TRIVY_ROOT))

import extract_images  # noqa: E402


class ExtractImagesTests(unittest.TestCase):
    def test_extracts_unique_images_from_supported_compose_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "compose.yaml").write_text(
                """
                services:
                  api:
                    image: registry.example.com/platform/api:1.0.0
                  worker:
                    image: registry.example.com/platform/api:1.0.0
                """,
                encoding="utf-8",
            )
            nested = root / "nested"
            nested.mkdir()
            (nested / "docker-compose.yml").write_text(
                """
                services:
                  database:
                    image: postgres:18-alpine
                  local-build:
                    build: .
                """,
                encoding="utf-8",
            )

            self.assertEqual(
                ["postgres:18-alpine", "registry.example.com/platform/api:1.0.0"],
                extract_images.extract_images(root),
            )

    def test_rejects_unresolved_image_variable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "compose.yaml").write_text(
                "services:\n  api:\n    image: ${API_IMAGE}\n", encoding="utf-8"
            )

            with self.assertRaises(extract_images.ComposeError):
                extract_images.extract_images(root)

    def test_rejects_malformed_compose(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "compose.yaml").write_text(
                "services: [not-a-mapping]\n", encoding="utf-8"
            )

            with self.assertRaises(extract_images.ComposeError):
                extract_images.extract_images(root)

    def test_ignores_git_internal_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git_dir = root / ".git"
            git_dir.mkdir()
            (git_dir / "compose.yaml").write_text(
                "services:\n  hidden:\n    image: hidden:latest\n", encoding="utf-8"
            )

            self.assertEqual([], extract_images.extract_images(root))


if __name__ == "__main__":
    unittest.main()
