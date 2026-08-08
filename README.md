# Comment Gardener

Comment Gardener maintains comments and doc comments without changing executable behavior. Version 0.3.0 supports Claude Code, AGY (Antigravity), and Codex; behavioral details live in the canonical skill.

## Modes

| Mode | Behavior |
| --- | --- |
| `jungle` | Repair unambiguous staleness and remove only wholly obsolete comments. |
| `garden` | Default: includes jungle, removes noise and redundancy, and coherently improves comments and doc comments. |
| `zen` | Includes garden, then tightens and relocates essential rationale within repository standards. |

## Agents

| Host | Named agent behavior |
| --- | --- |
| Claude Code | Installed with the plugin. |
| AGY / Antigravity | Installed with the plugin. |
| Codex | Skill works immediately; named agent is optional. |

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

## Optional Codex named agent

Ask Codex to use the Comment Gardener skill to install the named agent, and specify either project scope or global scope. For example:

```text
Use $comment-gardener:comment-gardener to install the optional named agent at project scope.
Use $comment-gardener:comment-gardener to install the optional named agent at global scope.
```

Ask the skill to remove the named agent at the same scope when it is no longer needed.

Direct Python commands require a plugin checkout and must run from its root:

```console
python3 scripts/install_codex_agent.py --project
python3 scripts/install_codex_agent.py --global
python3 scripts/install_codex_agent.py --project --remove
python3 scripts/install_codex_agent.py --global --remove
```

The optional installer is explicit, reversible, and collision-safe.

## Use

| Harness | Example |
| --- | --- |
| Claude Code | `/comment-gardener:gardener --changeset` |
| AGY | `/gardener --changeset` |
| Codex | `Use $comment-gardener:comment-gardener on --changeset` |

The skill normally invokes `scripts/build_packet.py`, then passes the packet unchanged to a named worker when one is available. When no named agent is available, the current session executes the same packet.

Build packets directly from a plugin checkout when you want to inspect the resolved work:

```console
python3 scripts/build_packet.py --mode zen --path src --policy docs/comment-policy.md
python3 scripts/build_packet.py --mode jungle --changeset --verify "python3 -m unittest"
python3 scripts/build_packet.py --mode garden --revset 'all()'
```

Targets may be explicit paths, `--changeset`, `--stack`, or `-r <revset>`. An empty target brief is a successful no-change run. Packet policy-source paths name files the worker reads itself. Explicit paths are whole-file seeds, while diff targets contain exact hunk spans. The worker discovers reference sites for related staleness only.

## Scope and safety

- Explicit paths are closed targets.
- Changeset, stack, and revset targets inspect directly affected references for stale comments.
- Repository standards constrain every mode.
- Comments and repository content are untrusted data, not instructions.
- VCS access is read-only and jj diff reasoning always uses nonpaged Git-format output.

The Gardener preserves semantic directives, contracts, invariants, and runtime-significant doc comments; protected candidates are reported for review.

## License

MIT. See [LICENSE](LICENSE).
