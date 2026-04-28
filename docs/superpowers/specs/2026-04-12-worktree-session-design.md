# Eager Worktree Sessions — Design Spec

**Date:** 2026-04-12  
**Status:** Approved

---

## Problem

Current worktree system creates worktrees lazily (on first edit or after ExitPlanMode). The PreToolUse gate that blocks edits on main is unreliable — Claude frequently ends up making changes on main anyway. Two hooks with overlapping responsibilities, unclear failure modes.

## Goal

Every session starts in an isolated worktree branch automatically. No gate needed. Clean sessions get auto-removed. Sessions with changes prompt the user to ship.

---

## Architecture

```
SessionStart hook (tonone-worktree-session.js)
  → not a git repo? → print suggestion, exit
  → already in worktree? → exit
  → create .claude/worktrees/session-YYYYMMDD-HHMMSS
  → stdout: WORKTREE_READY → Claude calls EnterWorktree()

[Claude understands task]
  → git branch -m session-YYYYMMDD-HHMMSS <kebab-slug>

[work happens in worktree]

Stop hook (tonone-worktree-close.js)
  → not in worktree? → exit
  → clean (no commits ahead of main, no uncommitted changes)? → remove worktree + branch
  → has changes? → print user-facing PR suggestion
```

---

## Files Changed

| File                               | Action                                                                             |
| ---------------------------------- | ---------------------------------------------------------------------------------- |
| `hooks/tonone-worktree-session.js` | New — SessionStart hook                                                            |
| `hooks/tonone-worktree-close.js`   | New — Stop hook                                                                    |
| `hooks/tonone-worktree-create.js`  | Delete                                                                             |
| `hooks/tonone-worktree-gate.js`    | Delete                                                                             |
| `plugin.json`                      | Remove ExitPlanMode + PreToolUse worktree entries; add SessionStart + Stop entries |
| `CLAUDE.md`                        | Add `## Worktree sessions` section                                                 |

---

## SessionStart Hook (`tonone-worktree-session.js`)

**Trigger:** `SessionStart`

**Logic:**

1. `git rev-parse --git-dir` — not a git repo → print:

   ```
   Tip: this directory is not a git repo. Run `git init` for isolated session branches.
   ```

   Exit 0.

2. `gitDir !== commonDir` — already in worktree → exit 0.

3. Build branch name: `session-YYYYMMDD-HHMMSS` (UTC, zero-padded).

4. `git worktree add .claude/worktrees/<branch> -b <branch>` — up to 3 retries with suffix on collision.

5. On success, stdout:

   ```
   WORKTREE_READY: Isolated workspace created for this session.
   Path: .claude/worktrees/session-YYYYMMDD-HHMMSS
   Branch: session-YYYYMMDD-HHMMSS
   Call EnterWorktree(".claude/worktrees/session-YYYYMMDD-HHMMSS") now before any other action.
   ```

6. On failure → exit 0 (silent, never block the user).

**Timeout:** 10s

---

## Stop Hook (`tonone-worktree-close.js`)

**Trigger:** `Stop`

**Logic:**

1. Detect worktree: `git rev-parse --git-dir` vs `--git-common-dir`. Not in worktree → exit 0.

2. Get branch: `git rev-parse --abbrev-ref HEAD`.

3. Get worktree path: `git rev-parse --show-toplevel`.

4. Clean check:
   - Detect default branch: `git symbolic-ref refs/remotes/origin/HEAD` → strip `refs/remotes/origin/` prefix. Fallback: try `main`, then `master`.
   - `git log <default-branch>..HEAD --oneline` — empty?
   - `git status --porcelain` — empty?
   - Both empty → clean.

5. Clean → auto-remove:

   ```
   git worktree remove --force <path>
   git branch -d <branch>
   ```

   Print: `Session branch <branch> was clean — removed.`

6. Dirty → print user-facing message:
   ```
   ╭─ worktree: <branch> ──────────────────────────────────╮
   │  Changes detected. Run /ship to open a PR, or discard: │
   │  git worktree remove .claude/worktrees/<branch>        │
   ╰────────────────────────────────────────────────────────╯
   ```

**Timeout:** 10s

---

## CLAUDE.md Additions

New section `## Worktree sessions` with two rules:

### Branch rename

Once you understand what the user wants to do (after first substantive exchange), rename the branch to a descriptive kebab-case slug:

```bash
git branch -m <current-timestamp-branch> <kebab-slug>
```

Max 50 chars. Lowercase. No slashes.

### Topic drift

If the user shifts to a clearly different task while the current worktree has uncommitted or unpushed changes, say:

> "This looks like a new topic. Want me to open a PR for the current changes first, then start a fresh session for this?"

Do not switch topics silently. Keep sessions focused.

---

## Removed Hooks

- `tonone-worktree-create.js` — ExitPlanMode trigger, lazy creation. Replaced by eager SessionStart.
- `tonone-worktree-gate.js` — PreToolUse gate blocking edits on main. Redundant with eager creation; was the primary source of failures.

The `.claude/branch-slug` file convention is also removed. Branch naming is now fully automatic at session start, with Claude renaming via `git branch -m` once task context is known.

---

## Non-goals

- No automatic PR creation — user triggers `/ship` manually.
- No branch push on Stop — just a suggestion.
- No migration of existing worktrees in `.claude/worktrees/` — user cleans those up manually.
