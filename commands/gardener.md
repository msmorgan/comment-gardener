---
name: gardener
description: Prune narrative filler, trivial restatements, and obsolete scratchpad comments from code files or the current changeset.
---

# `/gardener` Slash Command Adapter

The `/gardener` (or `/comment-gardener`) slash command provides a direct entry point for pruning narrative filler, trivial comment restatements, and obsolete scratchpad notes from specified files or the current changeset.

---

## Usage Syntax

```bash
/gardener <target-path>
/gardener --changeset
/comment-gardener <target-path>
/comment-gardener --changeset
```

---

## Supported Arguments

- `<target-path>`: Path to a specific code file or directory to process (e.g., `src/components`, `lib/parser.ts`).
- `--changeset`: Query and process all touched files in the current active revision (using `jj diff -r 'immutable_heads()..@' --summary` or `git diff --name-only`).

---

## Delegation & Execution Rules

When this command is invoked:

1. **Argument & Brief Resolution:**
   - Check user arguments for target paths or the `--changeset` flag.
   - **Empty Brief Behavior:** If no arguments or target paths are provided, do NOT modify any files. Immediately output:
     ```text
     Empty target brief: 0 files processed.
     ```

2. **Skill Delegation:**
   - Delegate full processing to `skills/comment-gardener/SKILL.md`.
   - Strictly enforce all core directives:
     - **Zero Logic Mutations:** Never modify executable code.
     - **Comment-Only Scope:** Target only comments and docstrings.
     - **Preserve Markdown Prose:** Do not edit general markdown body text.
     - **Language-Agnostic Parsing:** Parse comments according to language context.

3. **Output Reporting:**
   - Format final execution results using the standard summary report defined in `skills/comment-gardener/SKILL.md`.
