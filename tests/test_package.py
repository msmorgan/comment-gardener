import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path):
    return json.loads((ROOT / relative_path).read_text())


class PackageContractTest(unittest.TestCase):
    def test_legacy_harness_artifacts_are_absent(self):
        self.assertFalse((ROOT / "gemini-extension.json").exists())
        self.assertFalse((ROOT / ".agents/comment-gardener.json").exists())
        self.assertFalse((ROOT / "agents/comment-gardener.md").exists())

    def test_claude_manifest_is_metadata_only_at_0_1_0(self):
        manifest = load_json(".claude-plugin/plugin.json")
        self.assertEqual(manifest["version"], "0.1.0")
        self.assertNotIn("skills", manifest)
        self.assertNotIn("commands", manifest)
        self.assertNotIn("agents", manifest)

    def test_codex_manifest_discovers_the_canonical_skill(self):
        manifest = load_json(".codex-plugin/plugin.json")
        self.assertEqual(manifest["name"], "comment-gardener")
        self.assertEqual(manifest["version"], "0.1.0")
        self.assertEqual(manifest["skills"], "./skills/")

    def test_marketplaces_publish_the_plugin(self):
        claude = load_json(".claude-plugin/marketplace.json")
        codex = load_json(".agents/plugins/marketplace.json")

        self.assertEqual(claude["plugins"][0]["name"], "comment-gardener")
        self.assertEqual(claude["plugins"][0]["version"], "0.1.0")
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
