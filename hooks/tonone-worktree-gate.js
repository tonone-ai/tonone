#!/usr/bin/env node
// tonone-worktree-gate — PreToolUse hook for Edit/Write/NotebookEdit
//
// Blocks file-modifying tool calls on main and asks Claude to create a
// descriptively-named worktree before proceeding. Claude knows the task
// context by the time the first edit fires, so it can choose a meaningful
// branch name without a later rename step.
//
// Opt-out: write .claude/skip-worktree (valid 2 hours) for deliberate
// main-branch edits (CHANGELOG, version bumps, docs).

const { execSync } = require("child_process");
const fs = require("fs");

let input = "";
const timeout = setTimeout(() => process.exit(0), 3000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  clearTimeout(timeout);
  try {
    const data = JSON.parse(input);
    const toolName = data.tool_name || "";
    const toolInput = data.tool_input || {};

    // Only gate file-modifying tools
    const GATED = ["Edit", "Write", "NotebookEdit"];
    if (!GATED.includes(toolName)) process.exit(0);

    // Whitelist: always allow creating the opt-out marker itself
    const filePath = toolInput.file_path || toolInput.notebook_path || "";
    if (
      filePath === ".claude/skip-worktree" ||
      filePath.endsWith("/.claude/skip-worktree")
    ) {
      process.exit(0);
    }

    // Check for opt-out marker (valid for 2 hours)
    const skipMarker = ".claude/skip-worktree";
    if (fs.existsSync(skipMarker)) {
      const stat = fs.statSync(skipMarker);
      if (Date.now() - stat.mtimeMs < 2 * 60 * 60 * 1000) {
        process.exit(0);
      }
    }

    // Check if already in a worktree
    let gitDir, commonDir;
    try {
      gitDir = execSync("git rev-parse --git-dir", { encoding: "utf8" }).trim();
      commonDir = execSync("git rev-parse --git-common-dir", {
        encoding: "utf8",
      }).trim();
    } catch {
      process.exit(0); // Not a git repo — allow
    }

    if (gitDir !== commonDir) {
      process.exit(0); // Already in a worktree — allow
    }

    // On main. Block and ask Claude to create a named worktree.
    process.stdout.write(
      `\nWORKTREE_REQUIRED: You're about to edit on main. Create a named worktree first.\n\n` +
        `Pick a descriptive kebab-case slug for this task (e.g. "fix-auth-bug", "add-stripe-webhooks"), then run:\n` +
        `  git worktree add .claude/worktrees/<slug> -b <slug>\n` +
        `  EnterWorktree(".claude/worktrees/<slug>")\n\n` +
        `Then retry your edit.\n\n` +
        `To edit main intentionally (CHANGELOG, version bumps, docs), ` +
        `create .claude/skip-worktree first, then retry.\n`
    );
    process.exit(1);
  } catch {
    process.exit(0);
  }
});
