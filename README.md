# 🌿 comment-gardener

A cross-compatible AI agent plugin, skill, and slash command for pruning narrative filler and maintaining high-quality code comments across software codebases without altering executable code logic.

`comment-gardener` is designed for two primary workflows:
1. **Pre-commit / Pre-absorb Cleanup**: Clean up AI self-talk monologues, scratchpad notes, and conversational filler from uncommitted changes before running `jj absorb` or opening a pull request.
2. **Codebase Retrofit**: Batch-process legacy codebases to prune trivial restatements and narrative filler while preserving critical "why" rationale and public API docstrings.

---

## 🎯 Core Directives & Invariants

`comment-gardener` operates under strict safety invariants:

- **Zero Logic Mutations:** Never alter, refactor, reorder, or delete executable code, imports, variable names, function signatures, data types, or control flow logic. Every executable byte remains untouched.
- **Comment-Only Target Scope:** Only modify inline comments, block comments, docstrings (`JSDoc`, `PyDoc`, `Rustdoc`, Idris `|||`, Go docstrings), conditional compilation blocks (`#if 0`), and embedded code block comments.
- **Markdown Prose Preservation:** Markdown files (`.md`, `.mdx`) and general prose documentation are not treated as code comments. Markdown body prose is preserved untouched unless explicit HTML comments (`<!-- ... -->`) or embedded code block comments match pruning criteria.

---

## ✂ Gardening Rules

### ✂ PRUNE (Delete Completely)
- **Trivial "What" Restatements:** Line-by-line descriptions of self-explanatory code operations (e.g. `x += 1 // increment x`).
- **AI Narrative & Monologues:** Conversational progress logging, step-by-step thinking, and narrative filler left behind by AI coding assistants (e.g. `// Now we create a helper function for error handling`).
- **Un-annotated Dead Code:** Commented-out code blocks without explicit rationale or `// TODO:` / `// FIXME:` tags.
- **Obsolete Scratchpad Notes:** Temporary debug flags, status notes, and resolved reminders.

### 🌿 NURTURE & POLISH (Retain & Refine)
- **Essential "Why" Rationale:** Non-obvious design choices, business logic quirks, edge-case workarounds, performance trade-offs, and mathematical formulas.
- **Safety & Concurrency Invariants:** Mutex acquire ordering rules, memory layout constraints, thread safety guarantees, and security invariants.
- **Public API Contracts & Docstrings:** JSDoc, PyDoc, Rustdoc, Idris `|||` docstrings, Go docstrings, and Doxygen blocks. Formatting is cleaned up and narrative noise is removed while parameter descriptions, return value contracts, side effects, and thrown exception specs are preserved.

---

## 🚀 Target Brief Modes

`comment-gardener` requires an explicit target brief to run. It will never perform silent auto-scans across an entire codebase without explicit target instructions.

| Mode | Command Example | Behavior |
| --- | --- | --- |
| **Explicit Paths** | `/gardener src/components` or `/gardener lib/parser.ts` | Processes specified file(s) or recursively scans target directory paths. |
| **Changeset Mode** | `/gardener --changeset` or `/gardener -r 'immutable_heads()..@'` | Queries touched files via `jj diff -r 'immutable_heads()..@' --summary` (or `git diff --name-only` fallback) and processes only modified/added files. |
| **Empty Brief** | `/gardener` (no arguments) | Does **not** touch any files. Immediately outputs: `Empty target brief: 0 files processed.` |

---

## ⚡ Large Codebase Gardening & Batching

When pointing `comment-gardener` at a large directory or multi-thousand line codebase (e.g. 100k–200k lines):

- **Sub-batch Processing:** The agent automatically decomposes large file lists into sequential sub-batches (5–10 files or ~5,000 lines per batch). It will **never** try to load 200,000 lines into prompt context at once.
- **Safe Incremental Progress:** Edits are written progressively sub-batch by sub-batch, making massive codebase retrofits fast, reliable, and easy to inspect.

---

## 🤖 Recommended Models

- **High-Throughput / Bulk Gardening Tier (Recommended Default):**
  - **Gemini Flash**.
  - Recommended for bulk codebase retrofits, scanning large file counts, and pre-commit cleanup. Provides high speed, 1M+ token context window, high accuracy, and low cost.
- **Precision / Deep Reasoning Tier:**
  - **Claude Sonnet**, **Gemini Pro**, or **Claude Opus**.
  - Recommended when polishing complex public API contracts, formal JSDoc/PyDoc specifications, or subtle mathematical and concurrency invariants.

---

## 📦 Installation & Setup

`comment-gardener` supports both **Claude Code** and **Antigravity CLI (AGY)** agent harnesses.

### Installing for Claude Code (`~/.claude/plugins`)

Clone or link the repository into your Claude Code plugins directory:

```bash
# Direct clone
git clone https://github.com/your-org/comment-gardener.git ~/.claude/plugins/comment-gardener

# Or symlink from a local working copy
ln -s /path/to/comment-gardener ~/.claude/plugins/comment-gardener
```

### Installing for AGY / Antigravity CLI (`~/.gemini/config/plugins`)

Clone or link the repository into your AGY plugins directory:

```bash
# Direct clone
git clone https://github.com/your-org/comment-gardener.git ~/.gemini/config/plugins/comment-gardener

# Or symlink from a local working copy
ln -s /path/to/comment-gardener ~/.gemini/config/plugins/comment-gardener
```

---

## 🔄 Recommended VCS Workflow: `jj absorb`

`comment-gardener` works seamlessly with modern version control systems like **Jujutsu (`jj`)** and **Git**.

### Pre-commit / Pre-absorb Workflow

1. Perform your regular development work or pair-programming session with an AI assistant.
2. Clean up uncommitted comments in modified files:
   ```bash
   /gardener --changeset
   ```
3. Review the summary report and inspect diffs using `jj diff` (or `git diff`).
4. Fold comment cleanup edits into parent commits using `jj absorb`:
   ```bash
   jj absorb
   ```

Because `comment-gardener` makes zero logic mutations, `jj absorb` can cleanly fold comment refinements into their exact origin revisions without conflict.

---

## 📄 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for more details.
