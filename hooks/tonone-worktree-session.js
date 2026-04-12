#!/usr/bin/env node
// tonone-worktree-session — SessionStart hook
//
// Creates an isolated git worktree branch at the start of every session.
// Prints WORKTREE_READY so Claude calls EnterWorktree() before taking action.
// Silent-fails on any error — never block the user's workflow.

const { execSync, spawnSync } = require("child_process");
const path = require("path");

let input = "";
const timeout = setTimeout(() => process.exit(0), 9000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  clearTimeout(timeout);
  try {
    // 1. Bail if not a git repo
    let gitDir, commonDir;
    try {
      gitDir = execSync("git rev-parse --git-dir", { encoding: "utf8" }).trim();
      commonDir = execSync("git rev-parse --git-common-dir", { encoding: "utf8" }).trim();
    } catch {
      console.log(
        "Tip: this directory is not a git repo. " +
        "Run `git init` to get isolated session branches automatically."
      );
      process.exit(0);
    }

    // 2. Already in a worktree — nothing to do
    if (gitDir !== commonDir) process.exit(0);

    // 3. Build branch name: session-YYYYMMDD-HHMMSS (UTC)
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const date = `${now.getUTCFullYear()}${pad(now.getUTCMonth() + 1)}${pad(now.getUTCDate())}`;
    const time = `${pad(now.getUTCHours())}${pad(now.getUTCMinutes())}${pad(now.getUTCSeconds())}`;
    const base = `session-${date}-${time}`;

    // 4. Create worktree — up to 3 retries on name collision
    let worktreePath = null;
    let branchName = null;
    for (let i = 0; i < 3; i++) {
      const candidate = i === 0 ? base : `${base}-${i + 1}`;
      const wPath = path.join(".claude", "worktrees", candidate);
      const result = spawnSync(
        "git", ["worktree", "add", wPath, "-b", candidate],
        { encoding: "utf8" }
      );
      if (result.status === 0) {
        worktreePath = wPath;
        branchName = candidate;
        break;
      }
    }

    // 5. Silent fail if creation failed — never block the user
    if (!worktreePath) process.exit(0);

    // 6. Tell Claude to enter the worktree
    console.log(
      `WORKTREE_READY: Isolated workspace created for this session.\n` +
      `Path: ${worktreePath}\n` +
      `Branch: ${branchName}\n\n` +
      `Call EnterWorktree("${worktreePath}") now before any other action.\n` +
      `Once you understand the task, rename the branch:\n` +
      `  git branch -m ${branchName} <kebab-slug>`
    );
  } catch {
    // Silent fail
  }
  process.exit(0);
});
