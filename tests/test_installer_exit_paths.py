import os
import tempfile
import unittest
from pathlib import Path

from tests.test_install_codex_agent import run_installer


def repository_free_temp_parent() -> Path:
    candidates = (Path("/dev/shm"), Path("/var/tmp"), Path(tempfile.gettempdir()))
    for candidate in candidates:
        ancestors = (candidate, *candidate.parents)
        has_repository = any(
            (ancestor / ".jj").exists() or (ancestor / ".git").exists()
            for ancestor in ancestors
        )
        if candidate.is_dir() and os.access(candidate, os.W_OK) and not has_repository:
            return candidate
    raise RuntimeError("no repository-free temporary directory is available")


class InstallerExitPathTest(unittest.TestCase):
    def test_project_scope_without_repository_root_returns_2(self):
        with tempfile.TemporaryDirectory(dir=repository_free_temp_parent()) as raw:
            root = Path(raw)
            nested = root / "not-a-repository" / "nested"
            nested.mkdir(parents=True)

            result = run_installer(
                "--project", cwd=nested, codex_home=root / "codex-home"
            )

            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stdout, "")
            self.assertIn("no project root found", result.stderr)
            self.assertFalse((root / ".codex").exists())

    def test_removing_already_absent_owned_target_returns_0(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            codex_home = root / "codex-home"

            result = run_installer(
                "--global", "--remove", cwd=root, codex_home=codex_home
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("already absent", result.stdout)
            self.assertFalse(
                (codex_home / "agents/comment-gardener.toml").exists()
            )


if __name__ == "__main__":
    unittest.main()
