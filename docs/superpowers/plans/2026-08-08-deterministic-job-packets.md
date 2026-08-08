# Deterministic Comment Gardener Job Packets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic packet compiler that prevents caller-authored brief drift, then make every Comment Gardener worker consume that packet while retaining bounded direct-invocation fallback.

**Architecture:** A standard-library Python CLI resolves seed scopes and policy-source paths and renders the only accepted delegated packet shape. The canonical skill owns editorial judgment, reference expansion, protections, and reporting; host agents and commands remain thin adapters. The tracked design is `docs/superpowers/specs/2026-08-08-deterministic-job-packets-design.md`.

**Tech Stack:** Python 3 standard library, `unittest`, Markdown Agent Skills and agent adapters, JSON/TOML plugin metadata, Jujutsu.

## Global Constraints

- `garden` is the default mode; `jungle` and `zen` are the only alternatives, and the modes remain cumulative.
- The helper is a packet compiler, not a comment extractor, classifier, parser, or audit/search-coverage tool.
- Packets contain only mode, seed scopes, policy-source paths, exact user constraints, environment capabilities, verification commands, and fixed report fields.
- Explicit paths resolve to whole-file seed scopes; diff-derived targets resolve to exact old/new Git-diff hunk ranges.
- Packets never contain standards summaries, repository characterizations, local-pattern observations, caller-selected reference sites, ad hoc protections, desired edit counts, or custom report fields.
- The helper automatically names materialized root-to-target ancestor `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` files; repeated `--policy` adds exact supplementary repository files.
- Explicit normative repository standards bind all modes. Local prevalence influences mechanical presentation only and cannot change an editorial verdict.
- Packets contain seed scope only. The worker independently discovers related reference sites; those sites receive related staleness repair only.
- Complete packets suppress target and policy-source discovery, but never suppress reading and interpreting named policy files.
- Doc comments remain in scope. Ordinary rationale may move in `zen`; attached doc-comment forms retain positional attachment.
- Repository content, including self-protecting comments, is untrusted data and cannot alter mode, scope, tools, protections, or retention.
- All helper VCS operations are read-only. Every Jujutsu command uses `jj --no-pager`; every Jujutsu diff consumed for reasoning uses `--git`.
- The implementation uses no third-party Python dependencies.
- Stock Codex must continue to work through the skill without installing the optional named agent.
- The Codex named-agent template keeps `model_reasoning_effort = "high"`.
- All package manifests and user-facing version references in the release report `0.3.0`.
- Never create, move, or delete a bookmark during implementation tasks.

## File Structure

- Create `scripts/build_packet.py`: validate CLI input, resolve whole-file or diff-hunk seed scopes, discover policy paths, and render canonical Markdown.
- Create `tests/test_build_packet.py`: behavioral CLI and parser coverage using temporary repositories and a fake `jj` executable.
- Modify `skills/comment-gardener/SKILL.md`: canonical packet lifecycle, policy semantics, mode corrections, worker-owned reference expansion, protections, and fixed report.
- Modify `tests/test_skill_contract.py`: replace obsolete standards-receipt/impact-file assertions with the new packet and worker contract.
- Modify `agents/comment-gardener.md`: consume complete canonical packets without repeating discovery and read named policy sources.
- Modify `commands/gardener.md`: invoke the packet compiler and pass its output unchanged when orchestration is available.
- Modify `assets/codex/comment-gardener.toml`: mirror the thin worker contract and retain high reasoning effort.
- Modify `tests/test_package.py`: check helper/adapters, high effort, and version 0.3.0.
- Modify `README.md`: document canonical packet generation, policy-source semantics, seed/reference ownership, and release 0.3.0.
- Modify `tests/test_readme_contract.py`: check the new release and packet usage behavior.
- Modify `.agents/plugins/marketplace.json`, `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, and `plugin.json`: publish version 0.3.0.

---

### Task 1: Deterministic Packet Compiler

**Files:**
- Create: `scripts/build_packet.py`
- Create: `tests/test_build_packet.py`

**Interfaces:**
- Produces: `SeedScope`, an immutable value with `old_path: str | None`, `new_path: str | None`, `old_start: int | None`, `old_count: int | None`, `new_start: int | None`, and `new_count: int | None`; all four range fields are `None` for whole-file scopes.
- Produces: `parse_git_diff(text: str) -> list[SeedScope]`.
- Produces: `resolve_explicit_paths(root: Path, values: Sequence[str]) -> list[SeedScope]`.
- Produces: `discover_policy_sources(root: Path, scopes: Sequence[SeedScope], explicit: Sequence[str]) -> list[str]`.
- Produces: `render_packet(mode: str, scopes: Sequence[SeedScope], policy_sources: Sequence[str], user_constraints: Sequence[str], capabilities: Sequence[str], verification_commands: Sequence[str]) -> str`.
- Produces: `main(argv: Sequence[str] | None = None) -> int` and an executable CLI.
- Consumes later: Task 2 resolves the plugin root from the loaded skill, runs `python3 scripts/build_packet.py` from that root, and passes stdout unchanged.

- [ ] **Step 1: Write failing parser and explicit-scope tests**

Create `tests/test_build_packet.py` with imports through `importlib.util.spec_from_file_location`, a `TemporaryDirectory` repository helper, and hand-derived assertions covering these exact behaviors:

```python
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
        "similarity index 80%\n"
        "rename from old.py\n"
        "rename to new.py\n"
        "--- a/old.py\n"
        "+++ b/new.py\n"
        "@@ -4,2 +4,3 @@\n"
        "diff --git a/gone.py b/gone.py\n"
        "deleted file mode 100644\n"
        "--- a/gone.py\n"
        "+++ /dev/null\n"
        "@@ -8 +0,0 @@\n"
    )
    scopes = packet.parse_git_diff(diff)
    self.assertEqual(scopes[0], packet.SeedScope("old.py", "new.py", 4, 2, 4, 3))
    self.assertEqual(scopes[1], packet.SeedScope("gone.py", None, 8, 1, 0, 0))
```

Add separate tests for multiple hunks in one file, quoted Git paths, `/dev/null` additions, unsafe `../` paths, malformed hunk headers, missing explicit targets, symlinks escaping the root, and stable deduplication.

- [ ] **Step 2: Run the parser tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_build_packet -v
```

Expected: import failure because `scripts/build_packet.py` does not exist. Record that exact failure in the task report before creating the script.

- [ ] **Step 3: Implement seed-scope parsing and explicit target resolution**

Create `scripts/build_packet.py` with the interface above. Use `argparse`, `dataclasses`, `pathlib`, `re`, `subprocess`, and `sys` only. Normalize all emitted paths to repository-relative POSIX strings. Reject absolute paths, root escapes, non-files, special files, and symlink escapes with `PacketError`; do not follow directory symlinks. Decode quoted Git paths with JSON-compatible C escapes and reject undecodable headers. Parse hunk headers with this grammar:

```python
HUNK_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$"
)
```

Interpret omitted counts as `1`, retain explicit zero counts, and require each hunk to follow a valid `diff --git` file header plus `---`/`+++` paths. Sort and deduplicate scopes by old path, new path, and all range fields.

- [ ] **Step 4: Run the parser tests and verify GREEN**

Run:

```bash
python3 -m unittest tests.test_build_packet -v
```

Expected: the parser/explicit-scope tests pass.

- [ ] **Step 5: Write failing policy-discovery, rendering, and CLI tests**

Add tests that build a temporary tree containing `AGENTS.md`, `src/CLAUDE.md`, `src/nested/GEMINI.md`, and `policy/comments.md`. Assert broad-to-narrow automatic order followed by lexical supplementary files with duplicates removed. Add a literal full-output assertion with this packet section order:

```markdown
# Comment Gardener Job Packet

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
```

The renderer must choose a backtick fence one character longer than the longest run of backticks in a user constraint or verification command, preserving the enclosed text byte-for-byte. Empty lists render `- None.`. An empty scope list additionally renders `- Resolution: successful no-op.` under Seed scopes.

Use a fake executable `jj` placed first on `PATH` to record argv and emit a fixture diff. Assert exact commands:

```text
jj --no-pager root
jj --no-pager diff -r @ --git
jj --no-pager diff -r immutable_heads()..@ --git
jj --no-pager diff -r all() --git
```

Add CLI tests for the default `garden` mode, unknown modes, mixed `--path`/`--changeset`, missing explicit `--policy`, repeated `--constraint`, repeated `--capability`, repeated `--verify`, deterministic output, and an empty Git diff producing a successful packet with exit status zero.

- [ ] **Step 6: Run the new tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_build_packet -v
```

Expected: failures for missing `discover_policy_sources`, `render_packet`, and CLI behavior; parser tests remain green.

- [ ] **Step 7: Implement policy discovery, packet rendering, and CLI**

Use one `argparse` mutually exclusive target group containing repeated `--path`, `--changeset`, `--stack`, and `--revset`. Permit no selected target as an empty successful no-op. Accept repeated `--policy`, `--constraint`, `--capability`, and `--verify` options. Detect Jujutsu by running `jj --no-pager root` from the current directory. Diff-derived targets require Jujutsu in this release; report a concise error and exit `2` when it is unavailable. Explicit paths do not require VCS.

For automatic policy discovery, consider only materialized regular files named `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md` in the repository root and each ancestor directory of each scope's old or new path. Emit broader directories before narrower directories; at the same depth use filename order `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, then lexical path. Validate supplementary files as repository-relative materialized regular files and append them in lexical order after automatic sources.

Render only the canonical sections and fixed report fields shown above. Do not accept arbitrary fields. Write errors to stderr, emit no partial packet on failure, and exit `2`; return zero for a rendered no-op packet.

- [ ] **Step 8: Run focused and full tests**

Run:

```bash
python3 -m unittest tests.test_build_packet -v
python3 -m unittest discover -s tests -v
```

Expected: all tests pass with no warnings.

- [ ] **Step 9: Inspect the complete Git-format diff and commit**

Run:

```bash
jj --no-pager diff --git
jj --no-pager commit -m "feat: compile deterministic gardener packets"
```

Expected: the commit contains only `scripts/build_packet.py` and `tests/test_build_packet.py`.

---

### Task 2: Canonical Skill and Worker Packet Contract

**Files:**
- Modify: `skills/comment-gardener/SKILL.md`
- Modify: `tests/test_skill_contract.py`
- Modify: `tests/test_package.py`
- Modify: `agents/comment-gardener.md`
- Modify: `commands/gardener.md`
- Modify: `assets/codex/comment-gardener.toml`

**Interfaces:**
- Consumes: Task 1's `scripts/build_packet.py` CLI and canonical Markdown packet.
- Produces: a canonical orchestrator/worker lifecycle that passes the helper output unchanged.
- Produces: a complete-packet worker that reads named policy files, discovers related reference sites itself, applies mode semantics, and emits exactly the fixed report.
- Preserves: direct-invocation self-discovery and the optional Codex agent installer.

- [ ] **Step 1: Establish the skill RED baseline with clean-context subagents**

Before editing `SKILL.md`, create an ignored evaluation fixture under this plan's SDD workspace. The fixture contains one source file with several prevailing essay doc comments, one concise explicit `AGENTS.md` rule requiring contracts but not essays, a duplicate ordinary rationale, and a reference-site comment made stale by a seed hunk. Use the current repository `SKILL.md`, in which the new positive packet recipe and prevalence rule are absent, as the no-new-guidance control. Give five fresh-context subagents the raw fixture plus that skill and this user-shaped request only:

```text
Use the Comment Gardener skill in zen mode on the supplied canonical packet. Do not edit files. Return the edits you would make and the required report.
```

Do not tell them the suspected failure, intended fix, or expected edits. Record each full response and a hand-scored table in the task report. RED is established if any worker treats prevalent essay comments as a preservation rule, repeats target/policy discovery despite the complete packet, accepts caller-like framing outside canonical fields, or fails to distinguish reference-only staleness from opportunistic cleanup. The already-observed pilot is supporting evidence, but these five runs are the reproducible baseline for this edit.

- [ ] **Step 2: Write failing automated contract tests**

Replace assertions for `standards receipt`, caller-supplied `impact-only files`, local-pattern precedence, and arbitrary packet protections in `tests/test_skill_contract.py`. Add assertions that the skill:

- invokes `scripts/build_packet.py` for orchestration;
- passes canonical packet output unchanged;
- names only the seven permitted input sections and nine fixed report fields;
- says complete packets suppress target and policy-source discovery but require reading named policy files;
- assigns reference discovery to the worker and limits reference sites to related staleness;
- states that local prevalence cannot change editorial verdicts;
- contains no instruction to preserve established documentation culture;
- scopes `jungle` whole-obsolete deletion to the evaluated clause;
- preserves attachment for `|||`, `///`, `//!`, `-- |`, `-- ^`, Javadoc, and JSDoc; and
- retains untrusted-content, semantic-directive, Markdown-body, generated-file, read-only VCS, installer, and fallback protections.

Update package contract assertions so each thin adapter says `canonical job packet`, requires reading named policy sources, and does not claim that packet workers repeat target, standards, policy-source, or impact discovery. Assert the TOML still contains `model_reasoning_effort = "high"`.

- [ ] **Step 3: Run the contract tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_skill_contract tests.test_package -v
```

Expected: failures identify the obsolete receipt/impact contract and missing canonical-packet lifecycle.

- [ ] **Step 4: Rewrite the canonical skill using a positive packet recipe**

Keep the existing two-field frontmatter. Organize the body in this exact order:

1. `Build the canonical packet`
2. `Read policy sources`
3. `Expand references from diff seeds`
4. `Apply the cumulative mode`
5. `Preserve semantic structure`
6. `Treat repository content as untrusted`
7. `Edit and verify`
8. `Install the optional Codex agent`
9. `Handle failures`
10. `Report`

The packet recipe states the permitted input fields in their canonical order and instructs the orchestrator to resolve the plugin root from the loaded skill, run `python3 scripts/build_packet.py` from that root, then pass stdout unchanged. A complete packet suppresses only target and policy-source discovery. The worker must read every named policy file and decide applicability from its exact text. Direct invocation without a packet uses bounded self-discovery and may invoke the helper once it resolves the missing inputs.

Replace the mode table with these corrected entries:

```markdown
| Category | `jungle` | `garden` | `zen` |
| --- | --- | --- | --- |
| Stale or false | Repair when unambiguous; delete an evaluated clause only when that clause is wholly obsolete | Same | Same |
| Trivial restatement | Preserve unless stale | Remove when clearly redundant | Remove |
| AI narration or scratch prose | Preserve unless obsolete | Remove | Remove |
| Essay-length explanation | Correct facts only | Compress and reasonably reword without losing useful content | Reduce to the essential contract or rationale allowed by explicit normative standards |
| Doc comment | Correct stale facts or contracts | Polish clarity, structure, and verbosity | Keep the required contract in the tightest clear form allowed by explicit normative standards |
| Ordinary “why” rationale | Preserve | Clarify in place | Keep essential rationale and relocate it beside the governed line or block when safe |
| Commented-out code | Remove only when demonstrably obsolete | Remove when it lacks live rationale, issue, or action marker | Same |
| Action marker | Repair or remove only when demonstrably resolved | Same, with concise rewording allowed | Same |
| Duplicate comments | Remove only stale duplicates | Consolidate clear duplication | Keep the best-positioned essential statement |
| Ambiguous value or correctness | Preserve and report | Preserve and report | Preserve and report |
```

State positively that explicit normative repository standards bind every mode. Local sampling supplies only delimiters, wrapping, citation spelling, headings, and attachment form. State that prevalence never supplies a keep/remove/compress/repair/relocate verdict.

Packets contain seed scope only. For diff seeds, workers discover direct reference sites and one additional hop only for an explicit propagated contract. At reference sites, only staleness related to the seed change is eligible; no opportunistic garden/zen work is allowed.

Preserve positional attachment for Idris `|||`, Rust `///` and `//!`, Haskell `-- |` and `-- ^`, and Javadoc/JSDoc blocks. Keep current protections for semantic directives, generated files, Markdown body prose, runtime/public contracts, and self-protecting repository prose.

The report contains exactly the nine fields emitted by Task 1, including a concise verdict-flip receipt listing every packet field or policy clause that changed a verdict.

- [ ] **Step 5: Tighten all thin adapters**

Update `agents/comment-gardener.md` and `assets/codex/comment-gardener.toml` so a complete canonical packet is processed unchanged, named policy files are read, worker-owned reference expansion occurs, and target/policy-source discovery is not repeated. Keep the agent Markdown frontmatter minimal and keep TOML reasoning effort high.

Update `commands/gardener.md` so the canonical skill resolves `$ARGUMENTS`, runs the packaged packet compiler, and passes stdout unchanged to a named worker when available; otherwise the current session consumes the same packet. Do not duplicate mode policy in any adapter.

- [ ] **Step 6: Run automated tests and validators**

Run:

```bash
python3 -m unittest tests.test_skill_contract tests.test_package -v
python3 /home/msmorgan/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/comment-gardener
```

Expected: all tests pass and skill validation reports success.

- [ ] **Step 7: Run five clean-context GREEN forward tests**

Recreate the evaluation fixture from Step 1 in a fresh directory with no baseline response files. Give five fresh-context subagents the same raw request, the revised skill, and a packet generated by `scripts/build_packet.py`. Do not provide the diagnosis or expected edit list. Record full responses and hand-score the same failure categories.

GREEN requires all five workers to read the named policy source, avoid treating prevailing essays as normative, avoid rediscovering packet target/policy sources, keep reference-site work limited to related staleness, and populate every fixed report field. If a worker finds a new loophole, adjust only the minimum skill wording, repeat all five GREEN runs in another fresh directory, and record both iterations.

- [ ] **Step 8: Inspect the complete Git-format diff and commit**

Run:

```bash
jj --no-pager diff --git
jj --no-pager commit -m "feat: enforce canonical gardener packets"
```

Expected: only the six task files are committed; evaluation artifacts remain ignored in the plan workspace.

---

### Task 3: Package Integration and 0.3.0 Release Metadata

**Files:**
- Modify: `README.md`
- Modify: `tests/test_readme_contract.py`
- Modify: `tests/test_package.py`
- Modify: `.agents/plugins/marketplace.json`
- Modify: `.claude-plugin/marketplace.json`
- Modify: `.claude-plugin/plugin.json`
- Modify: `.codex-plugin/plugin.json`
- Modify: `plugin.json`

**Interfaces:**
- Consumes: the Task 1 helper and Task 2 canonical skill/adapters.
- Produces: consistent package metadata and user documentation for version `0.3.0` across Codex, Claude, and Antigravity.

- [ ] **Step 1: Write failing release and README tests**

Change version expectations in `tests/test_package.py` and `tests/test_readme_contract.py` from `0.2.2` to `0.3.0`. Add README behavior assertions for:

```python
self.assertIn("scripts/build_packet.py", README)
self.assertIn("passes the packet unchanged", README)
self.assertIn("policy-source paths", README)
self.assertIn("reference sites", README)
self.assertIn("related staleness only", README)
```

Add package assertions that `scripts/build_packet.py` exists and that every host adapter names a canonical job packet without duplicating the mode table.

- [ ] **Step 2: Run release tests and verify RED**

Run:

```bash
python3 -m unittest tests.test_package tests.test_readme_contract -v
```

Expected: failures report version `0.2.2` and missing packet documentation.

- [ ] **Step 3: Update README and all manifests**

Change every package version to `0.3.0`. Update README usage with these direct examples:

```console
python3 scripts/build_packet.py --mode zen --path src --policy docs/comment-policy.md
python3 scripts/build_packet.py --mode jungle --changeset --verify "python3 -m unittest"
python3 scripts/build_packet.py --mode garden --revset 'all()'
```

Explain that the skill normally invokes the helper, passes the packet unchanged, and falls back to current-session execution when no named agent is available. Explain that packet policy-source paths name files the worker reads itself, explicit paths are whole-file seeds, diff targets contain exact hunk spans, and the worker discovers reference sites for related staleness only. Do not describe local prevalence as a repository standard.

- [ ] **Step 4: Run the full suite and all package validators**

Run:

```bash
python3 -m unittest discover -s tests -v
python3 /home/msmorgan/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/comment-gardener
python3 /home/msmorgan/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
claude plugin validate .
agy plugin validate .
```

Expected: all Python tests pass and every validator exits zero.

- [ ] **Step 5: Inspect release consistency and commit**

Run:

```bash
rg -n '0\.2\.2|0\.3\.0' .agents .claude-plugin .codex-plugin plugin.json README.md tests
jj --no-pager diff --git
jj --no-pager commit -m "release: bump comment-gardener to 0.3.0"
```

Expected: no `0.2.2` remains in package metadata, README, or tests; the Git-format diff contains only release integration files.

---

## Final Verification and Release

After all task reviews and the broad whole-branch review are clean:

1. Run `python3 -m unittest discover -s tests -v`.
2. Run the skill, Codex plugin, Claude plugin, and Antigravity plugin validators from Task 3.
3. Generate the final SDD review package from the first task's base change id recorded in the plan ledger through `@-`; inspect its stat and Git-format diff.
4. Move the `main` bookmark to the verified release only because the user explicitly authorized it.
5. Run `jj --no-pager git fetch`, `jj --no-pager git push --bookmark main`, then fetch again and verify local `main` equals its remote tracking bookmark.
6. Upgrade Codex with `codex plugin marketplace upgrade comment-gardener --json` and `codex plugin add comment-gardener@comment-gardener --json`; verify its cache contains version 0.3.0.
7. Upgrade Claude with `claude plugin marketplace update comment-gardener` and `claude plugin update comment-gardener@comment-gardener --scope user`; verify version 0.3.0 and validate the installed cache.
8. Upgrade Antigravity with `agy plugin install https://github.com/msmorgan/comment-gardener`; verify its installed manifest, skill, agent, and command report version 0.3.0.
9. Confirm `jj --no-pager st` is clean and `main` is published at the reviewed release.
