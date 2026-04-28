#!/usr/bin/env node
// tonone-git-gate — PreToolUse hook for Bash
//
// Blocks `git commit` and `git push` when on main (not in a worktree).
// Ensures all commits stay on the worktree branch until explicitly shipped.
//
// Opt-out: write .claude/skip-worktree (valid 2 hours) for deliberate main
// operations (docs, CHANGELOG, version bumps).

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

let input = "";
const timeout = setTimeout(() => process.exit(0), 3000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  clearTimeout(timeout);
  try {
    const data = JSON.parse(input);
    const toolName = data.tool_name || "";
    const command = (data.tool_input && data.tool_input.command) || "";

    // Only gate Bash tool calls
    if (toolName !== "Bash") process.exit(0);

    // Only gate git commit and git push
    if (!/\bgit\s+(commit|push)\b/.test(command)) process.exit(0);

    // Check opt-out marker (valid 2 hours)
    const skipMarker = ".claude/skip-worktree";
    if (fs.existsSync(skipMarker)) {
      const stat = fs.statSync(skipMarker);
      if (Date.now() - stat.mtimeMs < 2 * 60 * 60 * 1000) process.exit(0);
    }

    // Check if already in a worktree
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
      process.exit(0); // Not a git repo — allow
    }

    if (gitDir !== commonDir) process.exit(0); // Already in worktree — allow

    // On main. Find the most-recent pre-created worktree.
    const worktreesDir = ".claude/worktrees";
    let worktreePath = null;
    let branchName = null;

    try {
      if (fs.existsSync(worktreesDir)) {
        const entries = fs
          .readdirSync(worktreesDir)
          .map((e) => {
            const p = path.join(worktreesDir, e);
            try {
              return { name: e, mtime: fs.statSync(p).mtimeMs, p };
            } catch {
              return null;
            }
          })
          .filter(Boolean)
          .sort((a, b) => b.mtime - a.mtime);
        for (const { name, p } of entries) {
          if (fs.existsSync(p)) {
            worktreePath = p;
            branchName = name;
            break;
          }
        }
      }
    } catch {}

    const redirect = worktreePath
      ? `Call EnterWorktree("${worktreePath}") first, then retry your command.\nBranch: ${branchName}`
      : `No worktree found. Edit a file first to auto-create one, then retry.`;

    process.stdout.write(
      `\nGIT_GATE: Commits and pushes are blocked on main.\n` +
        `${redirect}\n\n` +
        `To commit on main intentionally (docs, CHANGELOG, version bumps), ` +
        `write .claude/skip-worktree first, then retry.\n`,
    );
    process.exit(1);
  } catch {
    // Silent fail — never block the user's workflow on a hook crash
    process.exit(0);
  }
});
