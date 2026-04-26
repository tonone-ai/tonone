#!/usr/bin/env node
// tonone-worktree-session — SessionStart hook
//
// Runs at the start of every session. Two jobs:
//   1. Prune dead git worktrees so stale entries don't accumulate.
//   2. If the session is already inside a linked worktree (resuming a prior
//      session), emit WORKTREE_READY so Claude knows the context without
//      having to re-run worktree setup.
//
// If this is a fresh main-branch session, emit the worktree cheatsheet so
// Claude has the create/enter commands handy.
//
// This hook NEVER exits 1 — it is informational only. Blocking happens in
// tonone-worktree-gate.js (PreToolUse) and tonone-git-gate.js (PreToolUse).

const { execSync } = require("child_process");

let input = "";
const timeout = setTimeout(() => process.exit(0), 3000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  clearTimeout(timeout);
  try {
    // Prune stale worktree entries (no-op if nothing to prune)
    try {
      execSync("git worktree prune", { encoding: "utf8", stdio: "pipe" });
    } catch {}

    // Detect whether this session is already inside a linked worktree
    let gitDir, commonDir;
    try {
      const parts = execSync("git rev-parse --git-dir --git-common-dir", {
        encoding: "utf8",
      })
        .trim()
        .split("\n");
      if (parts.length < 2) process.exit(0); // Unexpected output — allow
      gitDir = parts[0];
      commonDir = parts[1];
    } catch {
      process.exit(0); // Not a git repo
    }

    if (gitDir !== commonDir) {
      // Resuming a linked worktree session
      let branch = "";
      let worktreePath = "";
      try {
        branch = execSync("git rev-parse --abbrev-ref HEAD", {
          encoding: "utf8",
        }).trim();
        worktreePath = execSync("git rev-parse --show-toplevel", {
          encoding: "utf8",
        }).trim();
      } catch {}

      process.stdout.write(
        `WORKTREE_READY: session is inside worktree "${branch}" at ${worktreePath}.\n` +
          `You are already in the correct context. Proceed with edits directly.\n` +
          `To rename this branch: git branch -m ${branch} <new-name>\n`
      );
    } else {
      // Fresh main-branch session -- print cheatsheet
      process.stdout.write(
        `WORKTREE_READY: on main branch. When you make your first edit, the gate\n` +
          `hook will fire. Create a worktree at that point:\n` +
          `  git worktree add .claude/worktrees/<slug> -b <slug>\n` +
          `  EnterWorktree(".claude/worktrees/<slug>")\n` +
          `To rename later: git branch -m <old-name> <new-name>\n`
      );
    }
  } catch {
    // Silent fail -- never block user workflow on a hook crash
  }
  process.exit(0);
});
