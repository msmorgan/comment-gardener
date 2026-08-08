import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/install_codex_agent.py"
TEMPLATE = ROOT / "assets/codex/comment-gardener.toml"


def run_installer(*args, cwd, codex_home):
    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class CodexAgentInstallerTest(unittest.TestCase):
    def test_project_install_finds_nearest_repository_root(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / ".jj").mkdir()
            nested = root / "src" / "nested"
            nested.mkdir(parents=True)
            result = run_installer("--project", cwd=nested, codex_home=root / "home")
            installed = root / ".codex/agents/comment-gardener.toml"
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(installed.read_bytes(), TEMPLATE.read_bytes())

    def test_global_install_uses_codex_home_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            codex_home = root / "codex-home"
            first = run_installer("--global", cwd=root, codex_home=codex_home)
            second = run_installer("--global", cwd=root, codex_home=codex_home)
            self.assertEqual((first.returncode, second.returncode), (0, 0))
            self.assertEqual(
                (codex_home / "agents/comment-gardener.toml").read_bytes(),
                TEMPLATE.read_bytes(),
            )

    def test_install_refuses_dangling_symlink_destination(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            codex_home = root / "codex-home"
            target = codex_home / "agents/comment-gardener.toml"
            redirected = root / "redirected.toml"
            target.parent.mkdir(parents=True)
            target.symlink_to(redirected)
            result = run_installer("--global", cwd=root, codex_home=codex_home)
            self.assertEqual(result.returncode, 2)
            self.assertTrue(target.is_symlink())
            self.assertFalse(redirected.exists())

    def test_install_refuses_symlinked_parent_component(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            codex_home = root / "codex-home"
            redirected = root / "redirected-agents"
            codex_home.mkdir()
            redirected.mkdir()
            (codex_home / "agents").symlink_to(redirected, target_is_directory=True)
            result = run_installer("--global", cwd=root, codex_home=codex_home)
            self.assertEqual(result.returncode, 2)
            self.assertTrue((codex_home / "agents").is_symlink())
            self.assertFalse((redirected / "comment-gardener.toml").exists())

    def test_install_refuses_to_overwrite_different_content(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            codex_home = root / "codex-home"
            target = codex_home / "agents/comment-gardener.toml"
            target.parent.mkdir(parents=True)
            target.write_text("foreign = true\n")
            result = run_installer("--global", cwd=root, codex_home=codex_home)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(target.read_text(), "foreign = true\n")

    def test_remove_deletes_only_matching_content(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            codex_home = root / "codex-home"
            self.assertEqual(
                run_installer("--global", cwd=root, codex_home=codex_home).returncode,
                0,
            )
            removed = run_installer(
                "--global", "--remove", cwd=root, codex_home=codex_home
            )
            self.assertEqual(removed.returncode, 0, removed.stderr)
            self.assertFalse((codex_home / "agents/comment-gardener.toml").exists())

    def test_remove_refuses_foreign_content(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            codex_home = root / "codex-home"
            target = codex_home / "agents/comment-gardener.toml"
            target.parent.mkdir(parents=True)
            target.write_text("foreign = true\n")
            result = run_installer(
                "--global", "--remove", cwd=root, codex_home=codex_home
            )
            self.assertEqual(result.returncode, 2)
            self.assertEqual(target.read_text(), "foreign = true\n")


if __name__ == "__main__":
    unittest.main()
