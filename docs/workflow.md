# TASK EXECUTION PROTOCOL

You MUST follow this sequence strictly:

---

## 1. PLAN MODE

Before planning:
- Run `make ci` to surface any latent lint/type issues before starting — especially after a quiet period. Commit hooks only check the files in each commit, so pre-existing issues in untouched files stay hidden until they block an unrelated commit. See `docs/learnings.md`.
- Read the relevant task entry in `docs/epics/backlog.md` (the specific task, not the full file).
- Consult `docs/design.md` only when the broader architecture or product decisions are needed to understand the task.

Then:
- Understand the task and its scope
- Identify missing information
- Ask questions if needed
- Propose approach

🚨 STOP if any uncertainty exists

---

## 2. EXEC MODE

Only after approval. Approval = any affirmative response ("yes", "looks good", "go ahead", etc.).

- Implement minimal solution
- No scope expansion
- No refactors outside task

If something clearly broken is discovered outside the task scope: flag it and ask whether to fix it now or later. Never fix it silently.

---

## 3. VALIDATION MODE
- Explain changes
- Provide test steps
- List edge cases
- **Learning notes** — Call out the non-obvious technical additions from this task
  (patterns, library choices, tricky implementation details) with a short explanation
  of *why* it was done that way. The aim is that you learn from the change, not just
  receive it. Skip the trivial/obvious; focus on what's genuinely worth knowing.
- **Out-of-scope flags** — Flag any build errors, warnings, broken code, or other red
  herrings noticed along the way, even if unrelated to the current task. Record them
  here so they can be fixed later — never fix them silently and never leave them
  unmentioned.

---

## RULES

### Tasks
- Backlog-first: prefer tasks defined in `docs/epics/backlog.md`.
- Ad-hoc tasks are allowed if explicitly requested and clearly reasoned.
- After any ad-hoc task, update `docs/epics/backlog.md` to reflect what was implemented so everything stays accounted for.
- When a task is completed, mark it as `✅` in the task heading in `docs/epics/backlog.md`. Example: `#### TASK-1.1 ✅`

### Commits
- One task = one commit.
- No mixing tasks in a single commit.
- No hidden refactors.
- Commit message format: Conventional Commits — `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, etc.
  - Example: `feat(auth): add session cookie issuance on OAuth callback`
