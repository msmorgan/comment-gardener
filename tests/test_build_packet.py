import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_packet", ROOT / "scripts/build_packet.py")
packet = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = packet
SPEC.loader.exec_module(packet)


class PacketParserTest(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_explicit_file_and_directory_resolve_to_sorted_whole_files(self):
        (self.root / "src").mkdir()
        (self.root / "src/z.py").write_text("z = 1\n")
        (self.root / "src/a.py").write_text("a = 1\n")
        scopes = packet.resolve_explicit_paths(self.root, ["src"])
        self.assertEqual([(scope.new_path, scope.old_start) for scope in scopes], [("src/a.py", None), ("src/z.py", None)])

    def test_git_diff_parses_added_deleted_renamed_and_zero_length_hunks(self):
        diff = ("diff --git a/old.py b/new.py\nsimilarity index 80%\nrename from old.py\nrename to new.py\n--- a/old.py\n+++ b/new.py\n@@ -4,2 +4,3 @@\ndiff --git a/gone.py b/gone.py\ndeleted file mode 100644\n--- a/gone.py\n+++ /dev/null\n@@ -8 +0,0 @@\n")
        scopes = packet.parse_git_diff(diff)
        self.assertEqual(scopes[0], packet.SeedScope("old.py", "new.py", 4, 2, 4, 3))
        self.assertEqual(scopes[1], packet.SeedScope("gone.py", None, 8, 1, 0, 0))

    def test_multiple_hunks_and_addition(self):
        diff = ("diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n@@ -6,0 +7,2 @@\ndiff --git a/new.py b/new.py\nnew file mode 100644\n--- /dev/null\n+++ b/new.py\n@@ -0,0 +1 @@\n")
        self.assertEqual(packet.parse_git_diff(diff), [packet.SeedScope("a.py", "a.py", 1, 1, 1, 1), packet.SeedScope("a.py", "a.py", 6, 0, 7, 2), packet.SeedScope(None, "new.py", 0, 0, 1, 1)])

    def test_quoted_paths_and_invalid_diff_inputs(self):
        quoted = 'diff --git "a/sp ace.py" "b/sp ace.py"\n--- "a/sp ace.py"\n+++ "b/sp ace.py"\n@@ -1 +1 @@\n'
        self.assertEqual(packet.parse_git_diff(quoted)[0].new_path, "sp ace.py")
        for diff in ("diff --git a/../bad b/../bad\n--- a/../bad\n+++ b/../bad\n@@ -1 +1 @@\n", "diff --git a/a b/a\n--- a/a\n+++ b/a\n@@ -wat +1 @@\n", "@@ -1 +1 @@\n"):
            with self.assertRaises(packet.PacketError):
                packet.parse_git_diff(diff)

    def test_explicit_missing_symlink_escape_and_deduplication(self):
        (self.root / "a.py").write_text("x\n")
        outside = self.root.parent / "packet-outside.py"
        outside.write_text("x\n")
        (self.root / "escape.py").symlink_to(outside)
        self.assertEqual(packet.resolve_explicit_paths(self.root, ["a.py", "a.py"]), [packet.SeedScope(None, "a.py", None, None, None, None)])
        for target in ("missing.py", "../packet-outside.py", "escape.py"):
            with self.assertRaises(packet.PacketError):
                packet.resolve_explicit_paths(self.root, [target])


if __name__ == "__main__":
    unittest.main()
