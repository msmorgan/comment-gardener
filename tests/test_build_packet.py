import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_packet.py"
SPEC = importlib.util.spec_from_file_location("build_packet", SCRIPT)
packet = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = packet
SPEC.loader.exec_module(packet)


class RepositoryTestCase(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()


class PacketParserTest(RepositoryTestCase):
    def test_explicit_file_and_directory_resolve_to_sorted_whole_files(self):
        (self.root / "src").mkdir()
        (self.root / "src/z.py").write_text("z = 1\n")
        (self.root / "src/a.py").write_text("a = 1\n")
        scopes = packet.resolve_explicit_paths(self.root, ["src"])
        self.assertEqual(
            [(scope.new_path, scope.old_start) for scope in scopes],
            [("src/a.py", None), ("src/z.py", None)],
        )

    def test_git_diff_parses_added_deleted_renamed_and_zero_length_hunks(self):
        diff = (
            "diff --git a/old.py b/new.py\n"
            "similarity index 80%\nrename from old.py\nrename to new.py\n"
            "--- a/old.py\n+++ b/new.py\n@@ -4,2 +4,3 @@\n"
            "diff --git a/gone.py b/gone.py\ndeleted file mode 100644\n"
            "--- a/gone.py\n+++ /dev/null\n@@ -8 +0,0 @@\n"
            "diff --git a/new.py b/new.py\nnew file mode 100644\n"
            "--- /dev/null\n+++ b/new.py\n@@ -0,0 +1 @@\n"
        )
        self.assertEqual(
            packet.parse_git_diff(diff),
            [
                packet.SeedScope("gone.py", None, 8, 1, 0, 0),
                packet.SeedScope("old.py", "new.py", 4, 2, 4, 3),
                packet.SeedScope(None, "new.py", 0, 0, 1, 1),
            ],
        )

    def test_multiple_hunks_are_sorted_and_stably_deduplicated(self):
        diff = (
            "diff --git a/z.py b/z.py\n--- a/z.py\n+++ b/z.py\n"
            "@@ -6,0 +7,2 @@\n@@ -1 +1 @@\n@@ -1 +1 @@\n"
            "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n"
            "@@ -2 +3 @@ context\n"
        )
        self.assertEqual(
            packet.parse_git_diff(diff),
            [
                packet.SeedScope("a.py", "a.py", 2, 1, 3, 1),
                packet.SeedScope("z.py", "z.py", 1, 1, 1, 1),
                packet.SeedScope("z.py", "z.py", 6, 0, 7, 2),
            ],
        )

    def test_quoted_git_paths_decode_json_compatible_escapes(self):
        diff = (
            'diff --git "a/sp ace\\t.py" "b/sp ace\\t.py"\n'
            '--- "a/sp ace\\t.py"\n+++ "b/sp ace\\t.py"\n@@ -1 +1 @@\n'
        )
        self.assertEqual(packet.parse_git_diff(diff)[0].new_path, "sp ace\t.py")

    def test_diff_rejects_unsafe_malformed_and_incomplete_headers(self):
        invalid_diffs = (
            "diff --git a/../bad.py b/../bad.py\n--- a/../bad.py\n+++ b/../bad.py\n@@ -1 +1 @@\n",
            "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -wat +1 @@\n",
            "@@ -1 +1 @@\n",
            "diff --git a/a.py b/a.py\n@@ -1 +1 @@\n",
            "diff --git a/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n",
            'diff --git "a/bad\\q.py" "b/bad\\q.py"\n--- "a/bad\\q.py"\n+++ "b/bad\\q.py"\n@@ -1 +1 @@\n',
        )
        for diff in invalid_diffs:
            with self.subTest(diff=diff), self.assertRaises(packet.PacketError):
                packet.parse_git_diff(diff)

    def test_hunk_content_that_resembles_file_markers_is_not_reparsed(self):
        diff = (
            "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n"
            "@@ -1 +1 @@\n--- not-a-file-marker\n+++ not-a-file-marker\n"
        )
        self.assertEqual(
            packet.parse_git_diff(diff),
            [packet.SeedScope("a.py", "a.py", 1, 1, 1, 1)],
        )

    def test_explicit_missing_escape_special_and_symlink_targets_fail(self):
        with tempfile.TemporaryDirectory() as outside_directory:
            outside = Path(outside_directory) / "outside.py"
            outside.write_text("x\n")
            (self.root / "escape.py").symlink_to(outside)
            fifo = self.root / "named-pipe"
            os.mkfifo(fifo)
            targets = ("missing.py", "../outside.py", str(outside), "escape.py", "named-pipe")
            for target in targets:
                with self.subTest(target=target), self.assertRaises(packet.PacketError):
                    packet.resolve_explicit_paths(self.root, [target])

    def test_directory_containing_special_file_fails(self):
        (self.root / "src").mkdir()
        (self.root / "src/a.py").write_text("x\n")
        os.mkfifo(self.root / "src/pipe")

        with self.assertRaises(packet.PacketError):
            packet.resolve_explicit_paths(self.root, ["src"])

    def test_directory_symlinks_are_not_followed_and_duplicates_are_removed(self):
        (self.root / "src").mkdir()
        (self.root / "src/a.py").write_text("x\n")
        with tempfile.TemporaryDirectory() as outside_directory:
            outside = Path(outside_directory)
            (outside / "outside.py").write_text("x\n")
            (self.root / "src/link").symlink_to(outside, target_is_directory=True)
            self.assertEqual(
                packet.resolve_explicit_paths(self.root, ["src", "src/a.py"]),
                [packet.SeedScope(None, "src/a.py", None, None, None, None)],
            )


class PacketPolicyAndRenderingTest(RepositoryTestCase):
    def test_policy_sources_are_broad_to_narrow_then_supplementary_lexical(self):
        (self.root / "src/nested").mkdir(parents=True)
        (self.root / "policy").mkdir()
        for name in (
            "AGENTS.md",
            "CLAUDE.md",
            "src/CLAUDE.md",
            "src/nested/GEMINI.md",
            "policy/z.md",
            "policy/a.md",
        ):
            (self.root / name).write_text("policy\n")
        scopes = [packet.SeedScope(None, "src/nested/a.py", None, None, None, None)]
        self.assertEqual(
            packet.discover_policy_sources(
                self.root,
                scopes,
                ["policy/z.md", "AGENTS.md", "policy/a.md", "policy/a.md"],
            ),
            [
                "AGENTS.md",
                "CLAUDE.md",
                "src/CLAUDE.md",
                "src/nested/GEMINI.md",
                "policy/a.md",
                "policy/z.md",
            ],
        )

    def test_policy_discovery_uses_both_rename_paths(self):
        (self.root / "old").mkdir()
        (self.root / "new").mkdir()
        (self.root / "old/CLAUDE.md").write_text("old\n")
        (self.root / "new/GEMINI.md").write_text("new\n")
        scopes = [packet.SeedScope("old/a.py", "new/a.py", 1, 1, 1, 1)]
        self.assertEqual(
            packet.discover_policy_sources(self.root, scopes, []),
            ["old/CLAUDE.md", "new/GEMINI.md"],
        )

    def test_missing_unsafe_and_symlink_policy_sources_fail(self):
        with tempfile.TemporaryDirectory() as outside_directory:
            outside = Path(outside_directory) / "outside.md"
            outside.write_text("x\n")
            (self.root / "policy-link.md").symlink_to(outside)
            for value in ("missing.md", "../outside.md", str(outside), "policy-link.md"):
                with self.subTest(value=value), self.assertRaises(packet.PacketError):
                    packet.discover_policy_sources(self.root, [], [value])

    def test_literal_packet_output(self):
        expected = """# Comment Gardener Job Packet

## Mode
`zen`

## Seed scopes
- `src/a.py`: whole file

## Policy sources
- `AGENTS.md`

## Exact user constraints
1. ````text
Keep issue citations.
````

## Environment capabilities
- `language-aware references: unavailable`

## Verification commands
1. ````console
python3 -m unittest
````

## Required report
- Effective mode
- Policy sources read
- Seed scopes
- Reference expansion
- Edits
- Preserved and protected comments
- Ambiguities
- Verification commands and results
- Packet fields or policy clauses that changed a verdict
"""
        actual = packet.render_packet(
            "zen",
            [packet.SeedScope(None, "src/a.py", None, None, None, None)],
            ["AGENTS.md"],
            ["Keep issue citations."],
            ["language-aware references: unavailable"],
            ["python3 -m unittest"],
        )
        self.assertEqual(actual, expected)

    def test_ranges_and_empty_lists_have_canonical_rendering(self):
        ranged = packet.render_packet(
            "garden",
            [packet.SeedScope("old.py", "new.py", 4, 2, 7, 0)],
            [],
            [],
            [],
            [],
        )
        self.assertIn("- `new.py`: old 4,2; new 7,0", ranged)
        self.assertEqual(ranged.count("- None."), 4)
        empty = packet.render_packet("garden", [], [], [], [], [])
        self.assertIn("## Seed scopes\n- Resolution: successful no-op.\n- None.", empty)

    def test_fences_preserve_values_byte_for_byte(self):
        constraint = "start\n`````\nend\n"
        command = "printf '`x`'"
        rendered = packet.render_packet("garden", [], [], [constraint], [], [command])
        self.assertIn("1. ``````text\n" + constraint + "\n``````", rendered)
        self.assertIn("1. ````console\n" + command + "\n````", rendered)


class PacketCliTest(RepositoryTestCase):
    def run_cli(self, *arguments, environment=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            cwd=self.root,
            env=environment,
            text=True,
            capture_output=True,
        )

    def environment_with_path(self, path):
        environment = os.environ.copy()
        environment["PATH"] = str(path)
        return environment

    def install_fake_jj(self, diff):
        binary_directory = self.root / "bin"
        binary_directory.mkdir()
        log = self.root / "jj-argv.log"
        fixture = self.root / "fixture.diff"
        fixture.write_text(diff)
        fake = binary_directory / "jj"
        fake.write_text(
            f"#!{sys.executable}\n"
            "import os\nimport sys\nfrom pathlib import Path\n"
            "with Path(os.environ['FAKE_JJ_LOG']).open('a') as stream:\n"
            "    stream.write(' '.join(sys.argv[1:]) + '\\n')\n"
            "if sys.argv[1:] == ['--no-pager', 'root']:\n"
            "    print(os.environ['FAKE_JJ_ROOT'])\n"
            "elif sys.argv[1:3] == ['--no-pager', 'diff']:\n"
            "    sys.stdout.write(Path(os.environ['FAKE_JJ_DIFF']).read_text())\n"
            "else:\n    raise SystemExit(9)\n"
        )
        fake.chmod(0o755)
        environment = self.environment_with_path(binary_directory)
        environment.update(
            {
                "FAKE_JJ_LOG": str(log),
                "FAKE_JJ_ROOT": str(self.root),
                "FAKE_JJ_DIFF": str(fixture),
            }
        )
        return environment, log

    def test_default_mode_and_empty_target_are_successful_noop(self):
        result = self.run_cli(environment=self.environment_with_path(self.root))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("## Mode\n`garden`", result.stdout)
        self.assertIn("- Resolution: successful no-op.", result.stdout)

    def test_unknown_mode_mixed_targets_and_missing_policy_fail_without_output(self):
        (self.root / "a.py").write_text("x\n")
        failures = (
            ("--mode", "unknown"),
            ("--path", "a.py", "--changeset"),
            ("--policy", "missing.md"),
        )
        environment = self.environment_with_path(self.root)
        for arguments in failures:
            with self.subTest(arguments=arguments):
                result = self.run_cli(*arguments, environment=environment)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertNotEqual(result.stderr, "")

    def test_repeated_fields_are_preserved_and_output_is_deterministic(self):
        (self.root / "a.py").write_text("x\n")
        (self.root / "z.py").write_text("z\n")
        (self.root / "z-policy.md").write_text("z\n")
        (self.root / "a-policy.md").write_text("a\n")
        arguments = (
            "--path", "z.py", "--path", "a.py",
            "--policy", "z-policy.md", "--policy", "a-policy.md",
            "--constraint", "first", "--constraint", "second",
            "--capability", "cap-one", "--capability", "cap-two",
            "--verify", "check-one", "--verify", "check-two",
        )
        environment = self.environment_with_path(self.root)
        first = self.run_cli(*arguments, environment=environment)
        second = self.run_cli(*arguments, environment=environment)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertLess(first.stdout.index("`a.py`"), first.stdout.index("`z.py`"))
        self.assertLess(first.stdout.index("`a-policy.md`"), first.stdout.index("`z-policy.md`"))
        self.assertLess(first.stdout.index("first"), first.stdout.index("second"))
        self.assertLess(first.stdout.index("cap-one"), first.stdout.index("cap-two"))
        self.assertLess(first.stdout.index("check-one"), first.stdout.index("check-two"))

    def test_diff_targets_use_exact_jj_argv(self):
        diff = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n"
        environment, log = self.install_fake_jj(diff)
        cases = (
            (("--changeset",), "@"),
            (("--stack",), "immutable_heads()..@"),
            (("--revset", "all()"), "all()"),
        )
        for arguments, revision in cases:
            with self.subTest(arguments=arguments):
                if log.exists():
                    log.unlink()
                result = self.run_cli(*arguments, environment=environment)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertIn("- `a.py`: old 1,1; new 1,1", result.stdout)
                self.assertEqual(
                    log.read_text(),
                    f"--no-pager root\n--no-pager diff -r {revision} --git\n",
                )

    def test_empty_diff_is_successful_noop(self):
        environment, _ = self.install_fake_jj("")
        result = self.run_cli("--changeset", environment=environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("- Resolution: successful no-op.", result.stdout)

    def test_diff_target_requires_jj_and_emits_no_partial_packet(self):
        empty_path = self.root / "empty-bin"
        empty_path.mkdir()
        result = self.run_cli(
            "--changeset",
            environment=self.environment_with_path(empty_path),
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("Jujutsu", result.stderr)


if __name__ == "__main__":
    unittest.main()
