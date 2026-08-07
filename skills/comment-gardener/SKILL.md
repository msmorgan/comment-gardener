---
name: comment-gardener
description: Use when pruning or polishing code comments or docstrings within an explicitly targeted scope.
---

# Comment Gardener

Improve comment quality without changing program behavior. Work conservatively: a questionable comment stays.

## Resolve the target first

Never scan the repository without an explicit target brief.

VCS commands are read-only. Never commit, absorb, squash, rebase, restore, bookmark, push, or otherwise mutate VCS state. The Gardener edits working-copy files only.

| Brief | Files to resolve |
| --- | --- |
| `<path>...` | Only named files and files recursively beneath named directories |
| `--changeset` | In jj: `jj diff -r @ --name-only`; in Git: combine `git diff HEAD --name-only` with `git ls-files --others --exclude-standard` |
| `--stack` | In jj: `jj diff -r 'immutable_heads()..@' --name-only` |
| `-r <revset>` | In jj: `jj diff -r '<revset>' --name-only` |
| empty | Stop with `Empty target brief: 0 files processed.` |

`--changeset` means the current working-copy revision, not the mutable stack. If resolution returns no files, stop. Skip binary, generated, vendored, and minified files unless explicitly named.

For large targets, process batches of 5–10 files or roughly 5,000 lines and keep one cumulative tally.

## Classify before editing

Prune comment prose that is clearly:

- a trivial restatement of adjacent code;
- AI narration or step-by-step monologue;
- obsolete scratchpad or resolved debugging text; or
- commented-out code with no current rationale, issue, or action marker.

Preserve comments that explain rationale, contracts, invariants, hazards, compatibility, performance, mathematics, security, concurrency, or non-obvious constraints.

Treat these as semantic code, not ordinary comments:

- shebangs and encoding declarations;
- compiler, linker, build, formatter, linter, type-checker, coverage, and code-generation directives;
- pragmas, source-map/sourceURL markers, SQL optimizer hints, and tool annotations;
- conditional-compilation regions such as `#if 0 … #endif`; and
- comments whose removal would join or retokenize surrounding code.

Markdown body prose is documentation, not a code comment. Leave it unchanged unless the user explicitly targets documentation; HTML comments and comments inside code fences still follow the normal safety rules.

Do not edit protected semantic code during normal gardening. If a protected conditional region appears to contain prose or dead code, list it as a protected candidate in the report. An explicit request about conditional regions is required before touching it.

Docstrings can be runtime values or public contracts. Preserve their semantic content. Only polish a docstring when the target brief explicitly includes docstrings and the edit cannot weaken its contract; otherwise report it as a candidate.

For example, preserve the separator in `left/**/right`: deleting it creates the different token `leftright`.

## Edit and verify

1. Read each file in structural context; do not classify comments with symbol-only grep.
2. Make the smallest comment-only edit. Preserve surrounding whitespace and line structure when either can affect tokens, directives, diagnostics, or generated mappings.
3. Inspect the complete VCS diff after every batch.
4. If any executable token, directive, literal value, or unrelated prose changed, edit only the Gardener's own hunk to undo that mistake. Never use a VCS restore operation, which could discard the user's work. Do not claim safety from visual similarity alone.
5. Run relevant repository checks when available.

## Report

Report the target brief, files processed, comments pruned or polished, important comments preserved, protected candidates, and verification performed. If nothing was safe to change, say so plainly.
