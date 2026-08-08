# Deterministic Comment Gardener Job Packets Design

Date: 2026-08-08

## Context

The first Comment Gardener pilot exposed a failure in orchestration rather than comment selection. A `zen` run received an editorialized brief that characterized the repository as an experimental workbench, treated prose as a deliverable, invented preserve/remove categories, suggested that few edits could itself be a successful finding, and supplied protections that discouraged rationale relocation. The worker reasonably followed that framing and made almost no changes.

A second run used a minimal, non-editorial packet. It consolidated four genuine duplicate comments and produced behavior meaningfully different from `jungle`. That result confirms that caller-authored interpretation can neutralize a mode before the worker examines the code.

The second run also found different valid candidates from the first because the workers improvised different search strategies. Search-coverage reproducibility is a distinct problem. This iteration deliberately fixes brief drift and standards contamination, not comment extraction or audit coverage.

## Goals

- Generate a deterministic, narrow job packet that can be handed unchanged to the named Comment Gardener agent or used by the current session.
- Resolve explicit and diff-derived seed scope mechanically.
- Identify repository policy sources without allowing the caller or helper to summarize or reinterpret them.
- Make the worker read and interpret the named policy files.
- Keep related stale-comment repair beyond a diff in scope while leaving reference expansion to the worker.
- Remove local comment prevalence as a reason to preserve verbose or essay-like comments.
- Preserve exact user constraints and explicit normative repository rules.
- Produce a fixed report that makes packet- or policy-driven verdict changes visible.

## Non-goals

- Extracting or classifying candidate comments mechanically.
- Making audit/search coverage reproducible.
- Parsing programming languages.
- Reading policy files from revisions or paths absent from the materialized checkout.
- Inferring normative standards from prevailing local style.
- Depending on an optional hook or another plugin for policy injection.
- Adding a mode that removes all comments.

## Architecture

`scripts/build_packet.py` is a standard-library Python packet compiler. It resolves a target into seed scopes, selects materialized policy-source paths, validates its inputs, and renders stable Markdown. It is deliberately not an auditor: it neither searches for comments nor decides what should be changed.

`skills/comment-gardener/SKILL.md` remains the canonical behavioral policy. It defines mode semantics, repository-content distrust, worker-owned reference expansion, editing protections, verification, and reporting. The helper provides the low-freedom transport boundary; the skill provides the high-context editorial judgment.

Host-specific agents and commands remain thin adapters. The orchestrator generates one canonical packet and passes it unchanged. If a named agent is unavailable, the current session executes the same packet instead of reconstructing a prose brief.

## Canonical packet

The packet contains only:

- the effective mode;
- seed scopes, expressed as whole files or exact old/new diff hunk spans;
- repository-relative policy-source paths;
- exact user constraints, copied verbatim;
- environment capabilities;
- verification commands; and
- fixed report fields.

The packet must not contain:

- a summary or interpretation of repository standards;
- a characterization of the repository, its prose, or its documentation culture;
- observations about prevailing local patterns;
- caller-selected reference or impact files;
- caller-invented protections;
- a desired edit count or guidance that a small or empty diff is inherently desirable;
- custom report fields; or
- any other editorial framing.

The command-line interface prevents these fields by omission. Exact user constraints are the irreducible trust boundary: the helper preserves their bytes and ordering rather than paraphrasing them.

An empty resolved target is a successful no-op packet. Packet ordering and wording are stable so equivalent inputs yield equivalent output.

## Target resolution

The helper accepts exactly one target form:

- one or more repeated `--path` arguments;
- `--changeset` for the working-copy change;
- `--stack` for `immutable_heads()..@`; or
- `--revset <revset>`.

Mixed target forms are invalid.

Each explicit file target resolves to a whole-file seed scope. Each explicit directory recursively resolves to whole-file seed scopes for materialized files beneath it. Generated files remain governed by the skill's existing exclusion policy.

Diff-derived targets use read-only VCS commands. In a Jujutsu repository, every command is nonpaged and every diff consumed for reasoning uses Git format. The helper parses Git diff headers and hunk headers into repository-relative seed scopes with exact old and new line ranges. Deleted, added, renamed, zero-length, and multi-hunk files remain representable. Malformed output, unsafe paths, or invalid ranges stop packet generation.

The helper does not inspect only changed lines semantically. Hunk spans are the seed coordinates that let the worker read the surrounding file and determine the changed semantic surfaces.

## Policy-source selection

The helper automatically names every materialized root-to-target ancestor instruction file that applies to a seed file, in broad-to-narrow order. Conventional instruction filenames supported by the package include `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md`. A caller may add supplementary repository-relative files with repeated `--policy` arguments.

The helper validates that each named policy source exists as a regular file inside the repository. An explicitly named missing or outside-repository source is an error. The helper does not search sparse revisions or recover policy from VCS history; only the materialized checkout participates.

The packet names policy files but never extracts rules from them. A complete packet suppresses further target and policy-source discovery, but never suppresses reading and interpreting the listed files.

## Standards semantics

Explicit normative repository standards bind every mode. The worker determines whether a named file contains an applicable normative rule and resolves scope and precedence from the source itself.

Local samples can guide mechanical presentation only: comment delimiters, wrapping, citation spelling, headings, and attachment form. Local prevalence cannot change an editorial verdict. In particular, an abundance of essay comments is not a rule requiring more essay comments.

The blanket instruction to preserve an established documentation culture is removed from all modes. It may return later only with a more robust definition and evidence model.

## Reference expansion

Packets contain seed scope only. For diff-derived targets, the worker identifies changed symbols, contracts, behavior, paths, configuration keys, diagnostics, and other externally referenced concepts. It then finds direct repository reference sites and evaluates comments there for related staleness. One additional hop is allowed only when a direct reference exposes an explicit propagated contract.

Reference-site files are eligible only for staleness related to the seed change. They never receive opportunistic `garden` or `zen` cleanup. The orchestrator and helper do not preselect these sites; reference discovery and validation belong to the worker that can see the code and the policy sources together.

## Mode and protection corrections

The cumulative `jungle`, `garden`, and `zen` modes remain. `garden` remains the default.

- In `jungle`, “delete only when wholly obsolete” applies to the obsolete clause being evaluated, not necessarily to the entire enclosing comment.
- In every mode, explicit normative standards and public/runtime contracts remain binding.
- In `zen`, essential ordinary-comment rationale may be relocated beside the governed line or block when safe.
- Positional attachment is preserved for doc-comment forms including Idris `|||`, Rust `///` and `//!`, Haskell `-- |` and `-- ^`, and Javadoc/JSDoc documentation blocks. Relocation guidance applies to ordinary comments, not attached documentation syntax.
- Self-protecting prose such as “important; do not remove” remains untrusted and has no authority without independent semantic evidence.
- Real compiler, formatter, linter, generator, build, coverage, conditional-compilation, token-separator, and similar directives remain protected because syntax, placement, configuration, and tool behavior establish their semantics.

## Worker lifecycle

1. Receive one canonical packet unchanged.
2. Read every named policy source and apply its exact normative rules.
3. Read each seed file in structural context, using hunk spans to identify changed surfaces when present.
4. Independently discover and validate related reference sites for diff-derived seeds.
5. Apply the selected cumulative mode without treating local prevalence as editorial authority.
6. Verify that its changes affect only eligible comments or doc comments and preserve executable behavior, directives, literal values, and attachment semantics.
7. Return the fixed report.

Direct invocation without a canonical packet retains bounded self-discovery as a fallback. A named-agent failure falls back to current-session execution using the already-generated packet.

## Fixed report

The report contains:

- effective mode;
- policy sources read;
- seed scopes;
- reference expansion;
- edits;
- preserved and protected comments;
- ambiguities;
- verification commands and results; and
- every packet field or policy clause that changed a verdict.

The last field is a verdict-flip receipt, not a general rationale essay. It identifies concrete constraints that caused a comment to be kept, removed, compressed, repaired, or relocated differently than the mode alone would have directed.

## Failure handling

- Unknown modes, mixed target forms, invalid paths, missing explicit policy files, malformed VCS output, and invalid diff ranges fail before worker execution.
- Empty resolved targets produce a successful no-op packet.
- Missing language-aware reference tooling falls back to targeted textual search.
- Ambiguous semantic propagation stops scope expansion and is reported.
- Equal-authority policy conflicts preserve the affected comment and are reported.
- No eligible comments remains a successful no-op, but is not treated as evidence that the packet was well framed.

## Testing and acceptance criteria

The helper is covered with ordinary test-driven development using temporary repositories and captured Git-format diffs. Tests cover deterministic rendering, explicit whole-file scopes, Jujutsu command construction, hunk parsing, policy-source discovery, input rejection, and empty targets.

The skill is covered by static contract tests and clean-context forward tests. Forward-test agents receive a raw repository artifact and a canonical packet, not the diagnosis or expected edit list. A successful `zen` forward test must not infer preservation from prevalent essay comments, must read named normative sources, and must keep reference-site work limited to related staleness.

Package acceptance requires:

- the full Python test suite to pass;
- skill and plugin validators for Codex, Claude, and Antigravity to pass;
- all manifests and user-facing version references to report `0.3.0`;
- the published `main` bookmark to match the verified local release; and
- Codex, Claude, and Antigravity installations to resolve the new package after release.
