import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_packet.py"
SPEC = importlib.util.spec_from_file_location("final_findings_build_packet", SCRIPT)
packet = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = packet
SPEC.loader.exec_module(packet)


class FinalFindingsTest(unittest.TestCase):
    def test_absolute_installed_helper_preserves_target_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "target.py").write_text("x\n")

            result = subprocess.run(
                [sys.executable, str(SCRIPT.resolve()), "--path", "target.py"],
                cwd=target,
                text=True,
                capture_output=True,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("- `target.py`: whole file", result.stdout)
        self.assertNotIn(str(ROOT), result.stdout)

    def test_skill_and_command_use_absolute_helper_from_target_cwd(self):
        skill = (ROOT / "skills/comment-gardener/SKILL.md").read_text()
        command = (ROOT / "commands/gardener.md").read_text()
        self.assertIn("absolute path to `scripts/build_packet.py`", skill)
        self.assertIn("preserve the user's target working directory", skill)
        self.assertIn("absolute helper path", command)
        self.assertIn("preserving the user's target working directory", command)

    def test_structural_inline_scalars_fail_closed(self):
        unsafe_values = ("line\n## Mode", "line\r## Seed scopes", "`breakout`")
        for value in unsafe_values:
            with (
                self.subTest(kind="path", value=value),
                self.assertRaises(packet.PacketError),
            ):
                packet.render_packet(
                    "garden",
                    [packet.SeedScope(None, value, None, None, None, None)],
                    [],
                    [],
                    [],
                    [],
                )
            with (
                self.subTest(kind="policy", value=value),
                self.assertRaises(packet.PacketError),
            ):
                packet.render_packet("garden", [], [value], [], [], [])
            with (
                self.subTest(kind="capability", value=value),
                self.assertRaises(packet.PacketError),
            ):
                packet.render_packet("garden", [], [], [], [value], [])

    def test_fenced_values_cannot_add_structural_headings(self):
        injected = "first\n## Mode\r\n## Required report\n```\nlast"
        rendered = packet.render_packet(
            "garden",
            [],
            [],
            [injected],
            [],
            [injected],
        )
        self.assertIsNone(packet.validate_packet(rendered))

    def test_unsafe_cli_scalars_fail_without_a_packet_or_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            unsafe_target = "bad\n## Mode`x`.py"
            (target / unsafe_target).write_text("x\n")
            unsafe_policy = "bad\r## Required report`x`.md"
            (target / unsafe_policy).write_text("policy\n")
            cases = (
                ("--path", unsafe_target),
                ("--policy", unsafe_policy),
                ("--capability", "bad\n## Mode`x`"),
            )
            for arguments in cases:
                with self.subTest(arguments=arguments):
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), *arguments],
                        cwd=target,
                        text=True,
                        capture_output=True,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, "")
                    self.assertNotIn("Traceback", result.stderr)

    def test_pure_rename_emits_and_renders_both_paths(self):
        diff = (
            "diff --git a/old-name.py b/new-name.py\n"
            "similarity index 100%\n"
            "rename from old-name.py\n"
            "rename to new-name.py\n"
        )
        scope = packet.SeedScope("old-name.py", "new-name.py", None, None, None, None)
        self.assertEqual(packet.parse_git_diff(diff), [scope])
        rendered = packet.render_packet("garden", [scope], [], [], [], [])
        self.assertIn(
            "old `old-name.py`; new `new-name.py`: rename-only whole file",
            rendered,
        )

    def test_renamed_hunk_renders_both_paths(self):
        scope = packet.SeedScope("old.py", "new.py", 4, 2, 7, 3)
        rendered = packet.render_packet("garden", [scope], [], [], [], [])
        self.assertIn("old `old.py`; new `new.py`: old 4,2; new 7,3", rendered)

    def test_octal_git_path_escapes_decode_as_filesystem_bytes(self):
        diff = (
            'diff --git "a/caf\\303\\251.py" "b/caf\\303\\251.py"\n'
            '--- "a/caf\\303\\251.py"\n+++ "b/caf\\303\\251.py"\n'
            "@@ -1 +1 @@\n-old\n+new\n"
        )
        self.assertEqual(
            packet.parse_git_diff(diff)[0].new_path,
            "caf\N{LATIN SMALL LETTER E WITH ACUTE}.py",
        )

    def test_hunk_ranges_and_body_counts_are_semantically_validated(self):
        invalid_diffs = (
            "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -0,0 +0,0 @@\n",
            "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -0 +1 @@\n-old\n+new\n",
            "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +0 @@\n-old\n+new\n",
            "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1,2 +1 @@\n-old\n+new\n",
            "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1,2 @@\n-old\n+new\n",
            "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n?malformed\n",
        )
        for diff in invalid_diffs:
            with self.subTest(diff=diff), self.assertRaises(packet.PacketError):
                packet.parse_git_diff(diff)

    def test_hunk_body_preserves_non_lf_line_separators(self):
        separators = ("\f", "\v", "\x85", "\u2028", "\u2029")
        expected = [packet.SeedScope(None, "a.py", 0, 0, 1, 1)]
        for separator in separators:
            with self.subTest(separator=repr(separator)):
                diff = (
                    "diff --git a/a.py b/a.py\n"
                    "--- /dev/null\n"
                    "+++ b/a.py\n"
                    "@@ -0,0 +1 @@\n"
                    f"+new{separator}page\n"
                )
                self.assertEqual(packet.parse_git_diff(diff), expected)

    def test_numeric_hunk_failures_are_packet_errors(self):
        enormous = "9" * 5000
        diff = (
            f"diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -{enormous} +1 @@\n"
        )
        with self.assertRaises(packet.PacketError):
            packet.parse_git_diff(diff)

    def test_unreadable_directory_fails_as_packet_error_and_cli_status_two(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            blocked = target / "blocked"
            blocked.mkdir()
            (blocked / "a.py").write_text("x\n")
            blocked.chmod(0)
            try:
                with self.assertRaises(packet.PacketError):
                    packet.resolve_explicit_paths(target, ["blocked"])
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "--path", "blocked"],
                    cwd=target,
                    text=True,
                    capture_output=True,
                )
            finally:
                blocked.chmod(0o700)

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("Traceback", result.stderr)

    def test_policy_discovery_traversal_oserror_is_a_packet_error(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            scope = packet.SeedScope(None, "target.py", None, None, None, None)
            with (
                mock.patch.object(
                    packet.Path,
                    "is_file",
                    side_effect=PermissionError("blocked"),
                ),
                self.assertRaises(packet.PacketError),
            ):
                packet.discover_policy_sources(target, [scope], [])

    def test_skill_resolves_policy_scope_and_precedence_from_each_source(self):
        skill = (ROOT / "skills/comment-gardener/SKILL.md").read_text()
        self.assertIn(
            "resolve every policy source's scope and precedence from that source's exact text",
            skill,
        )
        self.assertIn("narrower policy sources", skill)
        self.assertIn("supplementary policy sources", skill)
        self.assertIn("Packet order never supplies policy precedence", skill)
        self.assertIn("local prevalence never supplies policy precedence", skill)
        self.assertIn("Equal-authority conflicts preserve", skill)
        self.assertIn("preserve the entire affected comment unchanged", skill)

    def test_no_eligible_comments_do_not_validate_packet_framing(self):
        skill = (ROOT / "skills/comment-gardener/SKILL.md").read_text()
        self.assertIn(
            "No eligible comments is a successful no-op, but is not evidence that the packet was well framed",
            skill,
        )


if __name__ == "__main__":
    unittest.main()
