# Comment Gardener

Comment Gardener is a conservative Agent Skill for pruning narrative filler, trivial restatements, obsolete scratch notes, and unexplained commented-out code. It preserves rationale, contracts, directives, invariants, and other semantic comments, then requires a complete diff review.

Version 0.1.0 supports Claude Code, AGY (Antigravity), and Codex.

## Safety model

Comment syntax is not always non-semantic. Comment Gardener therefore preserves:

- shebangs, encoding declarations, pragmas, and tool directives;
- build, generation, lint, type-checking, coverage, and source-map annotations;
- SQL optimizer hints and similar tool-consumed comments;
- conditional-compilation regions such as `#if 0 … #endif`;
- public contracts and runtime-significant docstrings; and
- comments needed to keep surrounding tokens separate.

Suspicious prose or dead code inside a protected conditional region is reported as a protected candidate instead of silently edited. The skill makes best-effort comment-only edits and verifies the VCS diff; review that diff before accepting the result.

All VCS access is read-only. The Gardener edits working-copy files, but never commits, absorbs, rebases, restores, creates or moves bookmarks, or pushes.

## Install

### Claude Code

```console
claude plugin marketplace add msmorgan/comment-gardener
claude plugin install comment-gardener@comment-gardener --scope user
```

### AGY

```console
agy plugin install https://github.com/msmorgan/comment-gardener
```

### Codex

```console
codex plugin marketplace add msmorgan/comment-gardener
codex plugin add comment-gardener@comment-gardener
```

Start a new harness session after installation so its skill catalog reloads.

## Use

| Harness | Example |
| --- | --- |
| Claude Code | `/comment-gardener:gardener --changeset` |
| AGY | `/gardener --changeset` |
| Codex | `Use $comment-gardener:comment-gardener on --changeset` |

Target modes:

- `<path>...` processes explicitly named files or directories.
- `--changeset` processes only the current jj working-copy revision (`@`).
- `--stack` processes the mutable jj stack (`immutable_heads()..@`).
- `-r <revset>` processes an explicit jj revset.
- An empty target brief is a no-op.

Large targets are processed in small batches. The final report includes edits, preserved highlights, protected candidates, and verification performed.

## License

MIT. See [LICENSE](LICENSE).
