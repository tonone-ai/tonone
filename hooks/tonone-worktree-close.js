#!/usr/bin/env node
// tonone-worktree-close — Stop hook
//
// If the current session is in a worktree with changes, prints a /ship prompt.
// Clean worktrees are left in place — pruning happens at SessionStart, not here,
// because Stop fires after every assistant turn (not just at true session exit).
// Silent-fails on any error — never block the user's workflow.

const { execSync } = require("child_process");
const path = require("path");

/** Detect default branch: remote HEAD → fallback to main → master. */
function defaultBranch() {
  try {
    const ref = execSync("git symbolic-ref refs/remotes/origin/HEAD", {
      encoding: "utf8",
    }).trim();
    return ref.replace("refs/remotes/origin/", "");
  } catch {}
  for (const name of ["main", "master"]) {
    try {
      execSync(`git rev-parse --verify ${name}`, {
        encoding: "utf8",
        stdio: "pipe",
      });
      return name;
    } catch {}
  }
  return "main";
}

let input = "";
const timeout = setTimeout(() => process.exit(0), 9000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  clearTimeout(timeout);
  try {
    // 1. Detect whether we're in a linked worktree
    let gitDir, commonDir;
    try {
      gitDir = execSync("git rev-parse --git-dir", { encoding: "utf8" }).trim();
      commonDir = execSync("git rev-parse --git-common-dir", {
        encoding: "utf8",
      }).trim();
    } catch {
      process.exit(0);
    }
    if (gitDir === commonDir) process.exit(0); // Not in a worktree

    // 2. Gather context
    const branch = execSync("git rev-parse --abbrev-ref HEAD", {
      encoding: "utf8",
    }).trim();
    const worktreePath = execSync("git rev-parse --show-toplevel", {
      encoding: "utf8",
    }).trim();
    // commonDir is something like /abs/path/to/main/.git
    const mainRepoPath = path.resolve(commonDir, "..");

    // 3. Clean check: no commits ahead of default branch, no uncommitted changes
    const base = defaultBranch();
    let commits = "";
    let uncommitted = "";
    try {
      commits = execSync(`git log ${base}..HEAD --oneline`, {
        encoding: "utf8",
      }).trim();
    } catch {
      // If default branch lookup fails, treat as dirty — safer to warn than delete
      commits = "unknown";
    }
    try {
      uncommitted = execSync("git status --porcelain", {
        encoding: "utf8",
      }).trim();
    } catch {}

    const isClean = commits === "" && uncommitted === "";

    if (!isClean) {
      // Suggest shipping — only print when there are actual changes
      console.log(
        `\nWorktree: ${branch}\n` +
          `Changes detected. Run /ship to open a PR.\n` +
          `To discard: git -C "${mainRepoPath}" worktree remove --force "${worktreePath}" ` +
          `&& git -C "${mainRepoPath}" branch -D ${branch}\n`,
      );
    }
    // Clean worktree: silent exit. Pruning of stale clean worktrees happens at
    // SessionStart via `git worktree prune`, not here — the Stop hook fires after
    // every assistant turn, so auto-deleting here kills the worktree mid-session.
  } catch {
    // Silent fail
  }
  process.exit(0);
});
