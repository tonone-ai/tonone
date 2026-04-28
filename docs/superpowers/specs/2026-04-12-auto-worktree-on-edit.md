# Auto-Worktree on First Edit

**Date:** 2026-04-12  
**Status:** Approved

## Problem

The auto-worktree system triggers only on `ExitPlanMode`. Ad-hoc sessions that skip plan mode (quick bug fixes, small changes) always run on main. No worktree is created, no isolation happens.

## Goal

Any edit on main automatically redirects to an isolated worktree. Zero user friction — Claude handles the transition invisibly.

## Design

### Gate hook — `tonone-worktree-gate.js`

**Trigger:** `PreToolUse` on `Edit | Write | NotebookEdit`

**Flow:**

```
Edit attempted on main
  │
  ├─ Already in worktree? → exit 0 (allow)
  ├─ .claude/skip-worktree present and < 2h old? → exit 0 (allow)
  ├─ Writing .claude/skip-worktree itself? → exit 0 (allow)
  │
  └─ On main with no opt-out
       │
       ├─ Pre-existing worktree in .claude/worktrees/impl-*? → use it
       ├─ No pre-existing? → create impl-YYYYMMDD-HHMMSS-PID
       │
       ├─ Creation succeeded? → exit 1, stdout:
       │    "WORKTREE_READY: Worktree created at <path>.
       │     Call EnterWorktree('<path>') then retry your edit."
       │
       └─ Creation failed? → exit 0 (silent fallthrough, allow on main)
```

**Removed:** `hasRecentPlan` check (gstack plan gate). Gate now fires unconditionally on main.

**Worktree reuse:** If `.claude/worktrees/` already has `impl-*` entries (pre-created by `tonone-worktree-create.js` on `ExitPlanMode`), the gate picks the most recent one (lexicographic sort descending) instead of creating a new one.

### Create hook — `tonone-worktree-create.js`

No changes. Still fires on `ExitPlanMode` to pre-create a worktree proactively. When a plan exits, the worktree is ready before the first edit fires.

### Exit message tone

Current gate message is alarming ("WORKTREE_REQUIRED: You have an active implementation plan but are editing files directly on main. This can conflict..."). New message is instructional and neutral:

```
WORKTREE_READY: Isolated workspace created for this session.
Path: .claude/worktrees/impl-20260412-143022-12345
Branch: impl-20260412-143022-12345

Call EnterWorktree(".claude/worktrees/impl-20260412-143022-12345") now, then retry your edit.
```

### Opt-out

`.claude/skip-worktree` — write this file to allow deliberate main-branch edits (CHANGELOG, version bumps, docs). Valid for 2 hours from last modification.

## Tests

**Remove:** `test_gate_block_message_is_actionable` — references old `hasRecentPlan` behavior and is environment-dependent.

**Add:**

- `test_gate_exits_0_if_already_in_worktree` — mock `git rev-parse --git-dir` ≠ `--git-common-dir`
- `test_gate_exits_0_on_skip_marker` — existing behavior, keep
- `test_gate_message_format_on_main` — check stdout contains `WORKTREE_READY` and `EnterWorktree`

Note: full blocking behavior (exit 1) remains environment-dependent (requires real git repo not in worktree). Tests cover message format and opt-out paths; integration behavior is validated manually.

## Files Changed

| File                              | Change                                                                 |
| --------------------------------- | ---------------------------------------------------------------------- |
| `hooks/tonone-worktree-gate.js`   | Rewrite: drop plan check, add inline worktree creation, update message |
| `tests/test_hooks.py`             | Remove 1 test, add 2 tests                                             |
| `.claude-plugin/plugin.json`      | No change                                                              |
| `hooks/tonone-worktree-create.js` | No change                                                              |
