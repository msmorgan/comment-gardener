import json
import os
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path):
    return json.loads((ROOT / relative_path).read_text())


def load_adapter(relative_path):
    override = os.environ.get("COMMENT_GARDENER_NAMED_AGENT_CONTRACT_PATH")
    if override and relative_path == "agents/comment-gardener.md":
        return Path(override).read_text()
    return (ROOT / relative_path).read_text()


def complete_packet_rediscovery_patterns():
    subject = r"(?:targets?|standards?|policy(?:-source)?s?|impact)"
    action = (
        r"(?:re-?discover\w*|re-?resolve\w*|search[^.\n]{0,40}again|"
        r"scan[^.\n]{0,40}again|repeat[^.\n]{0,20}discover\w*)"
    )
    return (
        re.compile(rf"{action}[^.\n]{{0,120}}{subject}", re.IGNORECASE),
        re.compile(rf"{subject}[^.\n]{{0,120}}{action}", re.IGNORECASE),
    )


class PackageContractTest(unittest.TestCase):
    def test_legacy_harness_artifacts_are_absent(self):
        self.assertFalse((ROOT / "gemini-extension.json").exists())
        self.assertFalse((ROOT / ".agents/comment-gardener.json").exists())

    def test_claude_manifest_uses_directory_discovery(self):
        manifest = load_json(".claude-plugin/plugin.json")
        self.assertNotIn("skills", manifest)
        self.assertNotIn("commands", manifest)
        self.assertNotIn("agents", manifest)
        self.assertTrue((ROOT / "skills/comment-gardener/SKILL.md").is_file())
        self.assertTrue((ROOT / "commands/gardener.md").is_file())
        self.assertTrue((ROOT / "agents/comment-gardener.md").is_file())

    def test_agy_manifest_exposes_skill_command_and_agent(self):
        manifest = load_json("plugin.json")
        self.assertEqual(manifest["skills"], ["skills/comment-gardener"])
        self.assertEqual(manifest["commands"], ["commands/gardener.md"])
        self.assertEqual(manifest["agents"], ["agents/comment-gardener.md"])

    def test_agy_manifest_preserves_claude_metadata(self):
        claude = load_json(".claude-plugin/plugin.json")
        agy = load_json("plugin.json")
        self.assertEqual(agy["author"], claude["author"])
        self.assertEqual(agy["repository"], claude["repository"])
        self.assertEqual(agy["license"], claude["license"])

    def test_named_agent_is_a_thin_adapter(self):
        text = load_adapter("agents/comment-gardener.md")
        self.assertIn("comment-gardener:comment-gardener", text)
        self.assertIn("canonical job packet", text)
        self.assertIn("unchanged", text)
        self.assertIn("target and policy-source selection as resolved", text)
        self.assertIn("read every named policy source", text)
        self.assertIn("discover related reference sites", text)
        self.assertIn("self-discover", text)
        for pattern in complete_packet_rediscovery_patterns():
            self.assertNotRegex(text, pattern)
        self.assertNotIn("## Cumulative mode policy", text)

    def test_command_passes_arguments_to_the_canonical_skill(self):
        text = load_adapter("commands/gardener.md")
        self.assertIn("comment-gardener:comment-gardener", text)
        self.assertIn("$ARGUMENTS", text)
        self.assertIn("canonical job packet", text)
        self.assertIn("scripts/build_packet.py", text)
        self.assertIn("stdout unchanged", text)
        self.assertIn("named `comment-gardener` worker", text)
        self.assertIn("current session consumes the same packet", text)
        self.assertIn("read every named policy source", text)
        self.assertIn("discover related reference sites", text)
        for pattern in complete_packet_rediscovery_patterns():
            self.assertNotRegex(text, pattern)
        self.assertNotIn("## Cumulative mode policy", text)

    def test_codex_agent_is_a_thin_packet_adapter(self):
        text = load_adapter("assets/codex/comment-gardener.toml")
        self.assertIn('model_reasoning_effort = "high"', text)
        self.assertIn("canonical job packet", text)
        self.assertIn("unchanged", text)
        self.assertIn("target and policy-source selection as resolved", text)
        self.assertIn("read every named policy source", text)
        self.assertIn("discover related reference sites", text)
        for pattern in complete_packet_rediscovery_patterns():
            self.assertNotRegex(text, pattern)

    def test_codex_manifest_discovers_the_canonical_skill(self):
        manifest = load_json(".codex-plugin/plugin.json")
        self.assertEqual(manifest["name"], "comment-gardener")
        self.assertEqual(manifest["version"], "0.2.2")
        self.assertEqual(manifest["skills"], "./skills/")

    def test_all_package_versions_are_0_2_2(self):
        paths = [
            ".agents/plugins/marketplace.json",
            ".claude-plugin/marketplace.json",
            ".claude-plugin/plugin.json",
            ".codex-plugin/plugin.json",
            "plugin.json",
        ]
        for path in paths:
            data = load_json(path)
            if path.endswith("marketplace.json"):
                self.assertEqual(data["plugins"][0]["version"], "0.2.2", path)
            else:
                self.assertEqual(data["version"], "0.2.2", path)

    def test_codex_manifest_keeps_skill_only_discovery(self):
        manifest = load_json(".codex-plugin/plugin.json")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertNotIn("agents", manifest)
        self.assertIn("jungle", " ".join(manifest["interface"]["defaultPrompt"]))
        self.assertIn("zen", " ".join(manifest["interface"]["defaultPrompt"]))

    def test_marketplaces_publish_the_plugin(self):
        claude = load_json(".claude-plugin/marketplace.json")
        codex = load_json(".agents/plugins/marketplace.json")
        self.assertEqual(claude["plugins"][0]["name"], "comment-gardener")
        self.assertEqual(claude["plugins"][0]["version"], "0.2.2")
        self.assertEqual(codex["plugins"][0]["name"], "comment-gardener")
        self.assertEqual(codex["plugins"][0]["source"], {"source": "url", "url": "./"})

    def test_skill_frontmatter_has_only_discovery_fields(self):
        text = (ROOT / "skills/comment-gardener/SKILL.md").read_text()
        self.assertTrue(text.startswith("---\n"))
        frontmatter = text.split("---\n", 2)[1]
        keys = [line.split(":", 1)[0] for line in frontmatter.splitlines() if ":" in line]
        self.assertEqual(keys, ["name", "description"])
        description = next(
            line.split(":", 1)[1].strip()
            for line in frontmatter.splitlines()
            if line.startswith("description:")
        )
        self.assertTrue(description.startswith("Use when "))

    def test_skill_forbids_vcs_mutations(self):
        text = (ROOT / "skills/comment-gardener/SKILL.md").read_text()
        self.assertIn("VCS commands are read-only", text)
        self.assertIn("Never commit, absorb, squash, rebase, restore", text)
        self.assertIn("edit only the Gardener's own hunk", text)


if __name__ == "__main__":
    unittest.main()
