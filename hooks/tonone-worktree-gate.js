#!/usr/bin/env node
// tonone-worktree-gate — PreToolUse hook for Edit/Write/NotebookEdit
//
// On any file-modifying tool call while on main: auto-creates (or reuses) an
// isolated worktree and tells Claude to enter it before proceeding.
//
// Opt-out: write .claude/skip-worktree (valid 2 hours) for deliberate main
// edits (docs, CHANGELOG, version bumps).

const { execSync, spawnSync } = require("child_process");
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

    // On main. Try to reuse a worktree pre-created by tonone-worktree-create.
    const worktreesDir = ".claude/worktrees";
    let worktreePath = null;
    let branchName = null;

    try {
      if (fs.existsSync(worktreesDir)) {
        // Lexicographic descending = most-recent impl-YYYYMMDD-HHMMSS-PID first
        const entries = fs
          .readdirSync(worktreesDir)
          .filter((e) => e.startsWith("impl-"))
          .sort()
          .reverse();
        for (const entry of entries) {
          const candidate = path.join(worktreesDir, entry);
          if (fs.existsSync(candidate)) {
            worktreePath = candidate;
            branchName = entry;
            break;
          }
        }
      }
    } catch {}

    // No pre-existing worktree — create one now.
    if (!worktreePath) {
      const now = new Date();
      const pad = (n) => String(n).padStart(2, "0");
      const dateStr = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}`;
      const timeStr = `${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
      const base = `impl-${dateStr}-${timeStr}-${process.pid}`;

      for (let i = 0; i < 5; i++) {
        const suffix = i === 0 ? "" : `-${i + 1}`;
        const candidate = base + suffix;
        const wPath = path.join(worktreesDir, candidate);
        const result = spawnSync(
          "git",
          ["worktree", "add", wPath, "-b", candidate],
          { encoding: "utf8" },
        );
        if (result.status === 0) {
          worktreePath = wPath;
          branchName = candidate;
          break;
        }
      }
    }

    // Creation failed — silent fallthrough, allow edit on main.
    if (!worktreePath) {
      process.exit(0);
    }

    // Block and redirect to worktree.
    process.stdout.write(
      `\nWORKTREE_READY: An isolated workspace is ready for this session.\n` +
        `Path: ${worktreePath}\n` +
        `Branch: ${branchName}\n\n` +
        `Call EnterWorktree("${worktreePath}") now, then retry your edit. ` +
        `This keeps your changes isolated from other concurrent sessions.\n` +
        `\nTo edit on main intentionally (docs, CHANGELOG, version bumps), ` +
        `write .claude/skip-worktree first, then retry.\n`,
    );
    process.exit(1);
  } catch {
    process.exit(0);
  }
});
