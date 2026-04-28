# Worktree Enforcement — Design Spec

**Date:** 2026-04-12  
**Status:** Approved

## Problem

Work from different tasks gets mixed on `main`. The existing edit gate (`tonone-worktree-gate.js`) redirects file edits to an isolated worktree branch, but `git commit` and `git push` via Bash bypass the gate entirely. Commits land on main directly, defeating the isolation.

## Goal

Once an agent starts editing, all work — file changes AND git writes — stays on the worktree branch. `main` is untouchable until the PR is merged.

## Trigger

**First edit**, not session start. Read-only sessions (explore, research) don't need a worktree.

## Design

### New hook: `hooks/tonone-git-gate.js`

`PreToolUse` hook on `Bash`. Guards `git commit` and `git push`.

**Logic:**

1. Parse `tool_input.command`. If no `git commit` or `git push` match, pass through.
2. Check `.claude/skip-worktree` opt-out marker (2hr TTL). If valid, pass through.
3. `git rev-parse --git-dir` vs `--git-common-dir`. If they differ, already in worktree — pass.
4. On main: find most-recent `impl-*` dir under `.claude/worktrees/`.
   - If found: block (exit 1), instruct Claude to `EnterWorktree(path)` then retry.
   - If not found: block, instruct Claude to edit a file first (triggers edit gate → creates worktree), then retry.

### Registration in `.claude-plugin/plugin.json`

Add to `PreToolUse`:

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-git-gate.js\"",
      "timeout": 5
    }
  ]
}
```

### Ship flow (conversational, no new skill)

When work is done, Claude asks: "Ready to push? I'll create a PR from `<branch>` → `main`."

On user confirm, Claude (from inside the worktree):

1. `git push -u origin <branch>`
2. `gh pr create --title "..." --body "..."`
3. Returns PR URL

Worktree cleanup (prune + delete branch) happens after the PR is merged by the user.

## Escape hatch

Write `.claude/skip-worktree` to allow deliberate main operations (docs, CHANGELOG, version bumps). Valid 2 hours. Same mechanism as the edit gate.

## Files changed

| File                         | Change                          |
| ---------------------------- | ------------------------------- |
| `hooks/tonone-git-gate.js`   | New — Bash PreToolUse git guard |
| `.claude-plugin/plugin.json` | Add PreToolUse Bash matcher     |

## What this does NOT do

- Does not block `git add` (low risk, no isolation concern)
- Does not auto-merge PRs
- Does not gate Bash file writes (cp, echo >) — out of scope; worktree gate covers Edit/Write tools which is the primary agent interface
