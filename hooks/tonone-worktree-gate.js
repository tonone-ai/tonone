#!/usr/bin/env node
// tonone-worktree-gate — PreToolUse hook for Edit/Write/NotebookEdit
//
// Safety net: if an agent tries to edit files while on main AND a recent
// implementation plan exists, block and tell the agent to call EnterWorktree.
//
// Opt-out: agent creates .claude/skip-worktree (valid for 2 hours) to allow
// deliberate main-branch edits (docs, CHANGELOG, version bumps, etc).

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

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
    const filePath =
      toolInput.file_path || toolInput.notebook_path || "";
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
      const ageMs = Date.now() - stat.mtimeMs;
      if (ageMs < 2 * 60 * 60 * 1000) {
        process.exit(0); // Valid opt-out — allow
      }
      // Stale marker (>2h) — fall through to check
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

    // Check for a recent plan (modified within last 24h) as implementation signal
    const gstackProjects = path.join(os.homedir(), ".gstack", "projects");
    let hasRecentPlan = false;
    try {
      const result = execSync(
        `find "${gstackProjects}" -name "*.md" -path "*/ceo-plans/*" -mtime -1 2>/dev/null`,
        { encoding: "utf8" },
      ).trim();
      hasRecentPlan = result.length > 0;
    } catch {
      hasRecentPlan = false;
    }

    if (!hasRecentPlan) {
      process.exit(0); // No recent plan = exploratory session, allow
    }

    // Check for a pre-created worktree to guide Claude
    let worktreeHint = "";
    try {
      const worktreesDir = ".claude/worktrees";
      if (fs.existsSync(worktreesDir)) {
        const entries = fs
          .readdirSync(worktreesDir)
          .filter((e) => e.startsWith("impl-"))
          .sort()
          .reverse();
        if (entries.length > 0) {
          worktreeHint = `\nA pre-created worktree is available: .claude/worktrees/${entries[0]}`;
        }
      }
    } catch {}

    // Block with actionable message
    process.stderr.write(
      `WORKTREE_REQUIRED: You have an active implementation plan but are editing files directly on main.\n` +
        `This can conflict with other concurrent sessions.\n\n` +
        `Options:\n` +
        `(a) Call EnterWorktree to create an isolated workspace.${worktreeHint}\n` +
        `(b) If this edit is intentionally on main (docs, CHANGELOG, version bumps),\n` +
        `    write .claude/skip-worktree first, then retry the edit.\n`,
    );
    process.exit(1);
  } catch {
    // Silent fail — never block the user on a hook crash
    process.exit(0);
  }
});
