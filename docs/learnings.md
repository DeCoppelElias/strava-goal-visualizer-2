# Project Learnings

A running log of non-obvious lessons, kept concise for later extraction.

---

## 2026-06-18 — Lint/type tooling drift hid pre-existing debt

**What happened:** A small logging feature turned into a multi-hour task because
committing it kept failing on lint/type errors unrelated to the change.

**Root cause — two facts that combined:**

1. **Version skew.** The pre-commit hooks pinned *old* versions of ruff/mypy,
   while the local venv (`make lint` / `make typecheck`) used *newer* versions.
   The two disagreed on what counts as an error — sometimes unsatisfiable both
   ways (add a `# type: ignore` and one is happy, the other calls it "unused").

2. **Commit hooks only check the files in each commit — never the whole repo.**
   Recent commits had been docs-only, so the Python checkers were skipped for
   weeks. Already-committed files are *not* re-checked when rules later change;
   they're only re-judged when they appear in a new commit or a full-repo scan.
   So latent debt accumulated unseen and all surfaced the moment real code was
   finally committed.

   A side issue rode along: `pyproject.toml` had no `requires-python`, so every
   `uv run` tried to "fix" a stale `uv.lock`, rewriting it and breaking commits.

**Fixes applied:**
- Switched ruff/mypy to `repo: local` pre-commit hooks that invoke the venv's
  tools → **one source of truth**, so the commit gate and `make lint`/`typecheck`
  can never drift apart again. (Bonus: mypy sees all deps like `slowapi` natively;
  removed the hand-maintained `additional_dependencies` list.)
- Set `requires-python = ">=3.12"` and regenerated a stable `uv.lock`.
- Cleared the surfaced debt (unused `# type: ignore`, `enum.StrEnum`, S106 test
  ignore, wrapped long lines, formatting).

**Prevention going forward:**
- **Run `make ci` (full-repo scan) at the start of a task and after any quiet
  period** — it re-checks everything against current rules, surfacing latent
  debt up front instead of at commit time on an unrelated change.
- Keep each tool's version defined in **one** place (now done via `repo: local`).
