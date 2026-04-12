#!/usr/bin/env node
// tonone-worktree-create — PostToolUse hook for ExitPlanMode
//
// When a plan is approved (ExitPlanMode fires), pre-creates a git worktree
// so Claude can call EnterWorktree before making any file changes.
//
// If PostToolUse hook stdout is surfaced to Claude: Claude sees WORKTREE_READY
// and calls EnterWorktree proactively.
//
// If PostToolUse hook stdout is NOT surfaced to Claude: the worktree is still
// created on disk. tonone-worktree-gate.js will tell Claude about it when it
// tries to make its first file edit.

const { execSync, spawnSync } = require("child_process");
const path = require("path");

let input = "";
const timeout = setTimeout(() => process.exit(0), 5000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  clearTimeout(timeout);
  try {
    const data = JSON.parse(input);

    // Only fire on ExitPlanMode
    if (data.tool_name !== "ExitPlanMode") process.exit(0);

    // Check if already in a worktree
    let gitDir, commonDir;
    try {
      gitDir = execSync("git rev-parse --git-dir", { encoding: "utf8" }).trim();
      commonDir = execSync("git rev-parse --git-common-dir", {
        encoding: "utf8",
      }).trim();
    } catch {
      process.exit(0); // Not a git repo — nothing to do
    }

    if (gitDir !== commonDir) {
      process.exit(0); // Already in a worktree — nothing to do
    }

    // Build a race-safe branch name: impl-YYYYMMDD-HHMMSS-PID
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const dateStr = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}`;
    const timeStr = `${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
    const base = `impl-${dateStr}-${timeStr}-${process.pid}`;

    // Try to create the worktree (with collision retry)
    let worktreePath = null;
    let branchName = null;
    for (let i = 0; i < 5; i++) {
      const suffix = i === 0 ? "" : `-${i + 1}`;
      const candidate = base + suffix;
      const wPath = path.join(".claude", "worktrees", candidate);
      const result = spawnSync(
        "git",
        ["worktree", "add", wPath, "-b", candidate],
        { encoding: "utf8" },
      );
      if (result.status !== 0) {
        continue; // Name collision or other transient error — retry
      }
      worktreePath = wPath;
      branchName = candidate;
      break;
    }

    if (!worktreePath) {
      // Failed after 5 attempts — silent fail.
      // The gate hook will handle it when Claude tries to edit.
      process.exit(0);
    }

    // Tell Claude to enter the worktree before making changes.
    // This message is visible to Claude if PostToolUse hook stdout is surfaced.
    // If not visible, the gate hook serves as the fallback trigger.
    console.log(
      `\nWORKTREE_READY: An isolated workspace was created for this implementation session.\n` +
        `Path: ${worktreePath}\n` +
        `Branch: ${branchName}\n\n` +
        `Call EnterWorktree("${worktreePath}") now before making any file changes. ` +
        `This prevents conflicts with other concurrent sessions.`,
    );
  } catch {
    // Silent fail — never block the user's workflow on a hook crash
  }
  process.exit(0);
});
