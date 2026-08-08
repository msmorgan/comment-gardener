import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()


class ReadmeContractTest(unittest.TestCase):
    def test_readme_names_current_release(self):
        self.assertIn("Version 0.3.0", README)

    def test_readme_documents_canonical_packet_behavior(self):
        for text in [
            "scripts/build_packet.py",
            "passes the packet unchanged",
            "policy-source paths",
            "reference sites",
            "related staleness only",
        ]:
            self.assertIn(text, README)

    def test_named_agent_prefers_skill_driven_installation(self):
        ask = "Ask Codex to use the Comment Gardener skill to install the named agent"
        direct = "Direct Python commands require a plugin checkout and must run from its root"

        self.assertIn(ask, README)
        self.assertIn("project scope", README)
        self.assertIn("global scope", README)
        self.assertIn(direct, README)
        self.assertLess(README.index(ask), README.index(direct))


if __name__ == "__main__":
    unittest.main()
