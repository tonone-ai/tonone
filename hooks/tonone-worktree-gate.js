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

// Keep GATED in sync with the PreToolUse matcher in .claude-plugin/plugin.json
const GATED = ["Edit", "Write", "NotebookEdit"];
const SKIP_MARKER = ".claude/skip-worktree";
const SKIP_MARKER_TTL_MS = 2 * 60 * 60 * 1000; // 2 hours

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
    if (!GATED.includes(toolName)) process.exit(0);

    // Whitelist: always allow creating the opt-out marker itself
    const filePath = toolInput.file_path || toolInput.notebook_path || "";
    if (
      filePath === SKIP_MARKER ||
      filePath.endsWith("/.claude/skip-worktree")
    ) {
      process.exit(0);
    }

    // Check for opt-out marker (valid for SKIP_MARKER_TTL_MS)
    try {
      const stat = fs.statSync(SKIP_MARKER);
      if (Date.now() - stat.mtimeMs < SKIP_MARKER_TTL_MS) {
        process.exit(0);
      }
    } catch {
      // Marker absent — continue
    }

    // Check if already in a worktree (single subprocess call)
    let gitDir, commonDir;
    try {
      const out = execSync("git rev-parse --git-dir --git-common-dir", {
        encoding: "utf8",
      }).trim().split("\n");
      gitDir = out[0];
      commonDir = out[1];
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
