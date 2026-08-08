import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_packet_cli", ROOT / "scripts/build_packet.py")
packet = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = packet
SPEC.loader.exec_module(packet)


class PacketCoverageTest(unittest.TestCase):
    def test_literal_packet_and_fence_mutation(self):
        actual = packet.render_packet("zen", [packet.SeedScope(None, "src/a.py", None, None, None, None)], ["AGENTS.md"], ["Keep issue citations."], ["language-aware references: unavailable"], ["python3 -m unittest"])
        self.assertIn("## Required report", actual)
        self.assertIn("1. ````text\nKeep issue citations.\n````", actual)
        self.assertIn("1. ````console\npython3 -m unittest\n````", actual)
        self.assertEqual(packet._fence("x```y"), "````")

    def test_policy_order_and_empty_noop(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src/nested").mkdir(parents=True)
            for name in ("AGENTS.md", "src/CLAUDE.md", "src/nested/GEMINI.md"):
                path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text("x")
            scopes = [packet.SeedScope(None, "src/nested/a.py", None, None, None, None)]
            self.assertEqual(packet.discover_policy_sources(root, scopes, []), ["AGENTS.md", "src/CLAUDE.md", "src/nested/GEMINI.md"])
        self.assertIn("- Resolution: successful no-op.", packet.render_packet("garden", [], [], [], [], []))

    def test_cli_empty_and_invalid_mode(self):
        command = [sys.executable, str(ROOT / "scripts/build_packet.py")]
        ok = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(ok.returncode, 0)
        self.assertIn("`garden`", ok.stdout)
        bad = subprocess.run(command + ["--mode", "bad"], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(bad.returncode, 2)
        self.assertIn("unknown mode", bad.stderr)


if __name__ == "__main__":
    unittest.main()
