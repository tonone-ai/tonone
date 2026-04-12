#!/usr/bin/env node
// tonone-worktree-close — Stop hook
//
// If the current session is in a clean worktree (no commits or uncommitted
// changes ahead of the default branch), auto-removes it.
// If the worktree has changes, prints a /ship prompt to the user.
// Silent-fails on any error — never block the user's workflow.

const { execSync } = require("child_process");
const path = require("path");

/** Detect default branch: remote HEAD → fallback to main → master. */
function defaultBranch() {
  try {
    const ref = execSync("git symbolic-ref refs/remotes/origin/HEAD", { encoding: "utf8" }).trim();
    return ref.replace("refs/remotes/origin/", "");
  } catch {}
  for (const name of ["main", "master"]) {
    try {
      execSync(`git rev-parse --verify ${name}`, { encoding: "utf8", stdio: "pipe" });
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
      commonDir = execSync("git rev-parse --git-common-dir", { encoding: "utf8" }).trim();
    } catch {
      process.exit(0);
    }
    if (gitDir === commonDir) process.exit(0); // Not in a worktree

    // 2. Gather context
    const branch = execSync("git rev-parse --abbrev-ref HEAD", { encoding: "utf8" }).trim();
    const worktreePath = execSync("git rev-parse --show-toplevel", { encoding: "utf8" }).trim();
    // commonDir is something like /abs/path/to/main/.git
    const mainRepoPath = path.resolve(commonDir, "..");

    // 3. Clean check: no commits ahead of default branch, no uncommitted changes
    const base = defaultBranch();
    let commits = "";
    let uncommitted = "";
    try {
      commits = execSync(`git log ${base}..HEAD --oneline`, { encoding: "utf8" }).trim();
    } catch {
      // If default branch lookup fails, treat as dirty — safer to warn than delete
      commits = "unknown";
    }
    try {
      uncommitted = execSync("git status --porcelain", { encoding: "utf8" }).trim();
    } catch {}

    const isClean = commits === "" && uncommitted === "";

    if (isClean) {
      // Auto-remove the worktree (run from main repo to avoid self-removal issues)
      execSync(`git -C "${mainRepoPath}" worktree remove --force "${worktreePath}"`, { encoding: "utf8" });
      try {
        execSync(`git -C "${mainRepoPath}" branch -d ${branch}`, { encoding: "utf8" });
      } catch {}
      console.log(`Session branch ${branch} was clean — removed.`);
    } else {
      // Suggest shipping
      console.log(
        `\nWorktree: ${branch}\n` +
        `Changes detected. Run /ship to open a PR.\n` +
        `To discard: git -C "${mainRepoPath}" worktree remove --force "${worktreePath}" ` +
        `&& git -C "${mainRepoPath}" branch -D ${branch}\n`
      );
    }
  } catch {
    // Silent fail
  }
  process.exit(0);
});
