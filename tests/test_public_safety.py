from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SOURCE_SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check-public-safety.sh"


class PublicationSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.repository = self.root / "repository"
        self.repository.mkdir()

        self.run_command("git", "init", "--quiet")
        self.run_command("git", "config", "user.name", "Example Author")
        self.run_command("git", "config", "user.email", "author@example.com")

        script = self.repository / "scripts/check-public-safety.sh"
        script.parent.mkdir()
        shutil.copyfile(SOURCE_SCRIPT, script)
        (self.repository / "README.md").write_text("# Safe fixture\n")
        self.commit("initial fixture")

    def run_command(self, *command: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command,
            cwd=self.repository,
            check=True,
            text=True,
            capture_output=True,
        )

    def commit(self, message: str) -> None:
        self.run_command("git", "add", ".")
        self.run_command("git", "commit", "--quiet", "-m", message)

    def run_checker(
        self, denylist: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        if denylist is not None:
            environment["PUBLIC_SAFETY_DENYLIST_FILE"] = str(denylist)
        return subprocess.run(
            ["bash", "scripts/check-public-safety.sh"],
            cwd=self.repository,
            check=False,
            text=True,
            capture_output=True,
            env=environment,
        )

    def create_denylist(self, token: str) -> Path:
        denylist = self.root / "private-identifiers.txt"
        denylist.write_text(f"{token}\n")
        return denylist

    def test_safe_repository_passes(self) -> None:
        result = self.run_checker()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Publication safety generic checks passed", result.stdout)

    def test_checker_scans_its_own_content(self) -> None:
        script = self.repository / "scripts/check-public-safety.sh"
        with script.open("a") as output:
            output.write("# Unsafe fixture: " + "10." + "23.45.67\n")

        result = self.run_checker()

        self.assertEqual(result.returncode, 1)
        self.assertIn("scripts/check-public-safety.sh", result.stderr)

    def test_external_denylist_redacts_current_tree_match(self) -> None:
        token = "private-environment-token.example.invalid"
        denylist = self.create_denylist(token)
        (self.repository / "notes.md").write_text(f"Value: {token}\n")

        result = self.run_checker(denylist)
        output = result.stdout + result.stderr

        self.assertEqual(result.returncode, 1)
        self.assertIn("match found in the current tree", result.stderr)
        self.assertNotIn(token, output)

    def test_external_denylist_checks_retained_history(self) -> None:
        token = "historical-private-token.example.invalid"
        denylist = self.create_denylist(token)
        historical_file = self.repository / "historical.md"
        historical_file.write_text(f"Value: {token}\n")
        self.commit("add unsafe history fixture")
        historical_file.unlink()
        self.commit("remove unsafe history fixture")

        result = self.run_checker(denylist)
        output = result.stdout + result.stderr

        self.assertEqual(result.returncode, 1)
        self.assertIn("retained Git history", result.stderr)
        self.assertNotIn(token, output)

    def test_external_denylist_checks_staged_index(self) -> None:
        token = "staged-private-token.example.invalid"
        denylist = self.create_denylist(token)
        staged_file = self.repository / "staged.md"
        staged_file.write_text(f"Value: {token}\n")
        self.run_command("git", "add", staged_file.name)
        staged_file.write_text("Sanitized working tree\n")

        result = self.run_checker(denylist)
        output = result.stdout + result.stderr

        self.assertEqual(result.returncode, 1)
        self.assertIn("staged index", result.stderr)
        self.assertNotIn(token, output)

    def test_generic_rules_check_staged_index(self) -> None:
        staged_file = self.repository / "staged.md"
        staged_file.write_text("Private address: " + "10." + "34.56.78\n")
        self.run_command("git", "add", staged_file.name)
        staged_file.write_text("Sanitized working tree\n")

        result = self.run_checker()

        self.assertEqual(result.returncode, 1)
        self.assertIn("staged index", result.stderr)

    def test_generic_rules_check_retained_history(self) -> None:
        local_path = "/" + "home/example-user/codebase/private-checkout\n"
        historical_file = self.repository / "historical-path.md"
        historical_file.write_text(local_path)
        self.commit("add local path fixture")
        historical_file.unlink()
        self.commit("remove local path fixture")

        result = self.run_checker()

        self.assertEqual(result.returncode, 1)
        self.assertIn("retained Git history", result.stderr)
        self.assertIn("historical-path.md", result.stderr)

    def test_denylist_inside_repository_is_rejected(self) -> None:
        denylist = self.repository / "private-identifiers.txt"
        denylist.write_text("private-environment-token.example.invalid\n")

        result = self.run_checker(denylist)

        self.assertEqual(result.returncode, 1)
        self.assertIn("must remain outside the repository", result.stderr)

    def test_empty_denylist_is_rejected(self) -> None:
        denylist = self.root / "private-identifiers.txt"
        denylist.write_text("")

        result = self.run_checker(denylist)

        self.assertEqual(result.returncode, 1)
        self.assertIn("contains no entries", result.stderr)

    def test_missing_denylist_is_rejected(self) -> None:
        denylist = self.root / "missing-private-identifiers.txt"

        result = self.run_checker(denylist)

        self.assertEqual(result.returncode, 1)
        self.assertIn("not a readable regular file", result.stderr)

    def test_crlf_denylist_is_rejected(self) -> None:
        denylist = self.root / "private-identifiers.txt"
        denylist.write_bytes(b"private-environment-token.example.invalid\r\n")

        result = self.run_checker(denylist)

        self.assertEqual(result.returncode, 1)
        self.assertIn("CRLF", result.stderr)

    def test_denylist_matching_is_case_insensitive(self) -> None:
        token = "PRIVATE-ENVIRONMENT-TOKEN.EXAMPLE.INVALID"
        denylist = self.create_denylist(token)
        (self.repository / "notes.md").write_text(f"Value: {token.lower()}\n")

        result = self.run_checker(denylist)

        self.assertEqual(result.returncode, 1)
        self.assertIn("match found in the current tree", result.stderr)

    def test_prohibited_extensions_are_case_insensitive(self) -> None:
        capture = self.repository / "capture.PCAP"
        capture.write_text("synthetic fixture\n")
        self.run_command("git", "add", capture.name)

        result = self.run_checker()

        self.assertEqual(result.returncode, 1)
        self.assertIn("prohibited tracked path: capture.PCAP", result.stderr)

    def test_top_level_secrets_directory_is_rejected(self) -> None:
        secret_file = self.repository / "secrets/config.txt"
        secret_file.parent.mkdir()
        secret_file.write_text("synthetic fixture\n")
        self.run_command("git", "add", "secrets/config.txt")

        result = self.run_checker()

        self.assertEqual(result.returncode, 1)
        self.assertIn("prohibited tracked path: secrets/config.txt", result.stderr)

    def test_non_screenshot_binary_is_rejected(self) -> None:
        binary_file = self.repository / "fixture.bin"
        binary_file.write_bytes(b"synthetic\x00fixture")
        self.run_command("git", "add", binary_file.name)

        result = self.run_checker()

        self.assertEqual(result.returncode, 1)
        self.assertIn("non-text publication file", result.stderr)

    def test_symbolic_link_is_rejected(self) -> None:
        link = self.repository / "linked-readme"
        link.symlink_to("README.md")
        self.run_command("git", "add", link.name)

        result = self.run_checker()

        self.assertEqual(result.returncode, 1)
        self.assertIn("symbolic links are prohibited", result.stderr)

    def test_screenshot_requires_review_record(self) -> None:
        screenshot = self.repository / "evidence/screenshots/example.png"
        screenshot.parent.mkdir(parents=True)
        screenshot.write_bytes(b"synthetic image fixture")
        self.run_command("git", "add", str(screenshot.relative_to(self.repository)))

        result = self.run_checker()

        self.assertEqual(result.returncode, 1)
        self.assertIn("example.review.md", result.stderr)


if __name__ == "__main__":
    unittest.main()
