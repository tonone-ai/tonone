# Auto-Worktree on First Edit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Any Edit/Write on main auto-creates an isolated worktree and redirects Claude there — zero user friction, no plan-mode prerequisite.

**Architecture:** Rewrite `tonone-worktree-gate.js` to drop the `hasRecentPlan` gstack check and add inline worktree creation. On first file-modifying tool call on main: create (or reuse) a worktree, exit 1 with `WORKTREE_READY` stdout so Claude calls `EnterWorktree` and retries. Silent fallthrough on creation failure. `tonone-worktree-create.js` and `plugin.json` unchanged.

**Tech Stack:** Node.js (no dependencies), Python/pytest for tests

---

## File Map

| File | Change |
|------|--------|
| `hooks/tonone-worktree-gate.js` | Rewrite |
| `tests/test_hooks.py` | Update 1 test |
| `/Users/f/.claude/plugins/cache/tonone-ai/tonone/0.6.9/hooks/tonone-worktree-gate.js` | Sync after rewrite |

---

## Task 1: Update failing test (TDD — red first)

**Files:**
- Modify: `tests/test_hooks.py:138-144`

- [ ] **Step 1: Update the source-inspection test**

Replace `test_gate_block_message_is_actionable` with a version that expects `WORKTREE_READY` (not `WORKTREE_REQUIRED`) on stdout (not stderr):

```python
def test_gate_message_is_actionable():
    """When gate blocks, stdout must contain WORKTREE_READY, EnterWorktree, and skip-worktree opt-out."""
    source = GATE.read_text()
    assert "WORKTREE_READY" in source
    assert "EnterWorktree" in source
    assert ".claude/skip-worktree" in source
    assert "process.exit(1)" in source
```

- [ ] **Step 2: Run test — confirm it fails**

```bash
cd /Users/f/repos/tn/tonone
python -m pytest tests/test_hooks.py::test_gate_message_is_actionable -v
```

Expected: `FAILED` — `WORKTREE_READY` not in source (current source has `WORKTREE_REQUIRED`).

---

## Task 2: Rewrite `tonone-worktree-gate.js`

**Files:**
- Modify: `hooks/tonone-worktree-gate.js`

- [ ] **Step 1: Replace the file with the new implementation**

Write `hooks/tonone-worktree-gate.js`:

```javascript
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
        if (entries.length > 0) {
          worktreePath = path.join(worktreesDir, entries[0]);
          branchName = entries[0];
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
```

- [ ] **Step 2: Run full test suite**

```bash
cd /Users/f/repos/tn/tonone
python -m pytest tests/test_hooks.py -v
```

Expected output — all pass:
```
tests/test_hooks.py::test_hook_files_exist PASSED
tests/test_hooks.py::test_worktree_create_is_valid_js PASSED
tests/test_hooks.py::test_worktree_gate_is_valid_js PASSED
tests/test_hooks.py::test_create_ignores_non_exit_plan_mode PASSED
tests/test_hooks.py::test_create_handles_invalid_json PASSED
tests/test_hooks.py::test_gate_allows_non_gated_tools PASSED
tests/test_hooks.py::test_gate_allows_skip_marker_creation PASSED
tests/test_hooks.py::test_gate_allows_skip_marker_with_absolute_path PASSED
tests/test_hooks.py::test_gate_handles_invalid_json PASSED
tests/test_hooks.py::test_gate_message_is_actionable PASSED
```

- [ ] **Step 3: Commit**

```bash
git add hooks/tonone-worktree-gate.js tests/test_hooks.py
git commit -m "feat(worktree): auto-create worktree on first edit — drop plan gate, inline creation"
```

---

## Task 3: Sync to plugin cache

**Files:**
- Modify: `/Users/f/.claude/plugins/cache/tonone-ai/tonone/0.6.9/hooks/tonone-worktree-gate.js`

- [ ] **Step 1: Copy rewritten hook to plugin cache**

```bash
cp /Users/f/repos/tn/tonone/hooks/tonone-worktree-gate.js \
   /Users/f/.claude/plugins/cache/tonone-ai/tonone/0.6.9/hooks/tonone-worktree-gate.js
```

- [ ] **Step 2: Smoke test — trigger Edit on main and confirm WORKTREE_READY fires**

Run a manual test: pipe an Edit payload to the cached hook from a non-worktree directory:

```bash
cd /Users/f/repos/tn/tonone
echo '{"tool_name":"Edit","tool_input":{"file_path":"hooks/tonone-worktree-gate.js"}}' \
  | node /Users/f/.claude/plugins/cache/tonone-ai/tonone/0.6.9/hooks/tonone-worktree-gate.js
echo "exit: $?"
```

Expected: stdout contains `WORKTREE_READY`, exit code 1.

Note: a worktree will be created at `.claude/worktrees/impl-*`. Clean it up afterward:

```bash
# List created worktrees
git worktree list

# Remove test worktree (replace <name> with the impl-* name)
git worktree remove .claude/worktrees/<name> --force
git branch -d <name>
```
