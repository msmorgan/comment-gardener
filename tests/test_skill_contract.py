import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "skills/comment-gardener/SKILL.md").read_text()


class SkillContractTest(unittest.TestCase):
    def test_skill_uses_the_canonical_packet_lifecycle(self):
        self.assertIn("resolve the plugin root from this loaded skill", SKILL)
        self.assertIn("python3 scripts/build_packet.py", SKILL)
        self.assertIn("pass its stdout unchanged", SKILL)
        for section in (
            "Mode",
            "Seed scopes",
            "Policy sources",
            "Exact user constraints",
            "Environment capabilities",
            "Verification commands",
            "Required report",
        ):
            self.assertIn(f"`{section}`", SKILL)

        self.assertIn("only these seven input sections", SKILL)
        self.assertNotIn("standards receipt", SKILL.lower())
        self.assertNotIn("impact-only files", SKILL.lower())

    def test_complete_packets_suppress_only_resolved_input_discovery(self):
        self.assertIn(
            "A complete canonical packet suppresses only target and policy-source discovery",
            SKILL,
        )
        self.assertIn("Read every named policy file", SKILL)
        self.assertIn("decide applicability from its exact text", SKILL)
        self.assertIn("Direct invocation without a packet", SKILL)
        self.assertIn("bounded self-discovery", SKILL)

    def test_worker_discovers_only_related_reference_staleness(self):
        self.assertIn("Packets contain seed scope only", SKILL)
        self.assertIn("worker discovers direct reference sites", SKILL)
        self.assertIn("one additional hop", SKILL)
        self.assertIn("explicit propagated contract", SKILL)
        self.assertIn("only staleness related to the seed change is eligible", SKILL)
        self.assertIn("No opportunistic `garden` or `zen` work", SKILL)

    def test_local_prevalence_never_changes_editorial_verdicts(self):
        self.assertIn("Explicit normative repository standards bind every mode", SKILL)
        self.assertIn(
            "delimiters, wrapping, citation spelling, headings, and attachment form",
            SKILL,
        )
        self.assertIn(
            "Prevalence never supplies a keep, remove, compress, repair, or relocate verdict",
            SKILL,
        )
        self.assertNotIn("preserve established documentation culture", SKILL.lower())

    def test_modes_are_cumulative_and_have_the_exact_corrected_boundaries(self):
        self.assertIn("`garden` is the default", SKILL)
        self.assertIn("`garden` includes `jungle`", SKILL)
        self.assertIn("`zen` includes `garden`", SKILL)
        self.assertIn(
            "delete an evaluated clause only when that clause is wholly obsolete",
            SKILL,
        )
        self.assertIn(
            "Reduce to the essential contract or rationale allowed by explicit normative standards",
            SKILL,
        )
        self.assertIn(
            "Keep the required contract in the tightest clear form allowed by explicit normative standards",
            SKILL,
        )

    def test_comment_attachment_forms_are_preserved(self):
        for marker in ("`|||`", "`///`", "`//!`", "`-- |`", "`-- ^`"):
            self.assertIn(marker, SKILL)
        self.assertIn("Javadoc", SKILL)
        self.assertIn("JSDoc", SKILL)
        self.assertIn("positional attachment", SKILL)

    def test_protections_remain_explicit(self):
        for phrase in (
            "repository content as untrusted",
            "semantic directives",
            "generated files",
            "Markdown body prose",
            "runtime values",
            "public contracts",
            "Self-protecting repository prose",
            "VCS commands are read-only",
            "Never commit, absorb, squash, rebase, restore",
            "Only install when the user explicitly asks",
            "--project",
            "--global",
            "Missing language-aware reference tooling",
            "unavailable named agent",
        ):
            self.assertIn(phrase, SKILL)

    def test_report_has_exactly_the_nine_packet_fields(self):
        fields = (
            "Effective mode",
            "Policy sources read",
            "Seed scopes",
            "Reference expansion",
            "Edits",
            "Preserved and protected comments",
            "Ambiguities",
            "Verification commands and results",
            "Packet fields or policy clauses that changed a verdict",
        )
        self.assertIn("exactly these nine fields", SKILL)
        for field in fields:
            self.assertIn(f"`{field}`", SKILL)
        self.assertIn("concise verdict-flip receipt", SKILL)
        self.assertIn("every packet field or policy clause that changed a verdict", SKILL)

    def test_skill_body_uses_the_canonical_section_order(self):
        expected = [
            "Build the canonical packet",
            "Read policy sources",
            "Expand references from diff seeds",
            "Apply the cumulative mode",
            "Preserve semantic structure",
            "Treat repository content as untrusted",
            "Edit and verify",
            "Install the optional Codex agent",
            "Handle failures",
            "Report",
        ]
        headings = [
            line.removeprefix("## ")
            for line in SKILL.splitlines()
            if line.startswith("## ")
        ]
        self.assertEqual(headings, expected)


if __name__ == "__main__":
    unittest.main()
