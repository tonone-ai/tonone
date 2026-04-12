# Auto-Worktree Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically create and enter a git worktree when implementation starts, so concurrent Claude Code sessions can't conflict with each other.

**Architecture:** Two hooks in `plugin.json` handle isolation. Hook 1 (`tonone-worktree-create.js`, PostToolUse on ExitPlanMode) pre-creates a worktree when a plan is approved. Hook 2 (`tonone-worktree-gate.js`, PreToolUse on Edit/Write/NotebookEdit) acts as a safety net — if an agent tries to edit files while on main with a recent active plan, it blocks and tells the agent to call `EnterWorktree` first. An opt-out path (`.claude/skip-worktree` marker file) allows deliberate main-branch edits (docs, CHANGELOG, version bumps).

**Tech Stack:** Node.js (hooks follow existing `tonone-agent-tracker.js` pattern), Python pytest (existing test suite), git worktree commands.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `hooks/tonone-worktree-create.js` | Create | PostToolUse hook — creates worktree on ExitPlanMode |
| `hooks/tonone-worktree-gate.js` | Create | PreToolUse hook — safety net gate on Edit/Write/NotebookEdit |
| `.claude-plugin/plugin.json` | Modify | Register both hooks |
| `.gitignore` | Modify | Ignore `.claude/worktrees/` and `.claude/skip-worktree` |
| `tests/test_hooks.py` | Create | Logic and syntax tests for both hooks |
| `tests/test_structure.py` | Modify | Add existence check for both hook files |

---

## Task 1: Update .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add the two new gitignore entries**

Open `.gitignore` and append to the `# Claude Code personal config` section (after line 66, `.claude/skills/`):

```
.claude/worktrees/
.claude/skip-worktree
```

The `.gitignore` section should look like:
```
# Claude Code personal config (project .claude/ dirs are committed)
.claude/settings.json
.claude/settings.local.json
.claude/agents/code-reviewer.md
.claude/agents/frontend-developer.md
.claude/commands/
.claude/skills/
.claude/worktrees/
.claude/skip-worktree
```

- [ ] **Step 2: Verify entries are correct**

Run:
```bash
git check-ignore -v .claude/worktrees/notifications
git check-ignore -v .claude/skip-worktree
```

Expected output for each: a line referencing `.gitignore` with the matching pattern.

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore .claude/worktrees/ and .claude/skip-worktree"
```

---

## Task 2: Write failing hook tests

**Files:**
- Create: `tests/test_hooks.py`

- [ ] **Step 1: Write the test file**

```python
"""
Tests for tonone worktree hooks.

These tests validate:
- JS syntax is valid (node --check)
- Non-targeted tool names are passed through (exit 0)
- The opt-out whitelist for .claude/skip-worktree is respected
- ExitPlanMode is the only trigger for the creator hook
"""

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).parent.parent
GATE = REPO / "hooks" / "tonone-worktree-gate.js"
CREATE = REPO / "hooks" / "tonone-worktree-create.js"


def run_hook(hook_path: Path, stdin_data: dict) -> tuple[int, str, str]:
    """Run a hook script with JSON on stdin. Returns (returncode, stdout, stderr)."""
    proc = subprocess.run(
        ["node", str(hook_path)],
        input=json.dumps(stdin_data),
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# Syntax
# ---------------------------------------------------------------------------


def test_worktree_create_is_valid_js():
    """tonone-worktree-create.js must be syntactically valid Node.js."""
    result = subprocess.run(
        ["node", "--check", str(CREATE)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_worktree_gate_is_valid_js():
    """tonone-worktree-gate.js must be syntactically valid Node.js."""
    result = subprocess.run(
        ["node", "--check", str(GATE)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# tonone-worktree-create.js
# ---------------------------------------------------------------------------


def test_create_ignores_non_exit_plan_mode():
    """Creator hook exits 0 silently for tools other than ExitPlanMode."""
    for tool in ["Agent", "Edit", "Write", "Bash", "Read"]:
        rc, out, _ = run_hook(CREATE, {"tool_name": tool, "tool_input": {}})
        assert rc == 0, f"Expected exit 0 for tool={tool}, got {rc}"
        assert "WORKTREE_READY" not in out, f"Unexpected output for tool={tool}"


def test_create_handles_invalid_json():
    """Creator hook exits 0 (not crash) when fed invalid stdin."""
    proc = subprocess.run(
        ["node", str(CREATE)],
        input="not json",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0


# ---------------------------------------------------------------------------
# tonone-worktree-gate.js
# ---------------------------------------------------------------------------


def test_gate_allows_non_gated_tools():
    """Gate hook exits 0 for tools that don't modify files."""
    for tool in ["Bash", "Read", "Glob", "Grep", "Agent", "WebSearch"]:
        rc, _, _ = run_hook(GATE, {"tool_name": tool, "tool_input": {}})
        assert rc == 0, f"Expected exit 0 for tool={tool}, got {rc}"


def test_gate_allows_skip_marker_creation():
    """Writing .claude/skip-worktree is always allowed — it's the opt-out path."""
    rc, _, _ = run_hook(GATE, {
        "tool_name": "Write",
        "tool_input": {"file_path": ".claude/skip-worktree"},
    })
    assert rc == 0


def test_gate_allows_skip_marker_with_absolute_path():
    """Writing .claude/skip-worktree with absolute path is also allowed."""
    rc, _, _ = run_hook(GATE, {
        "tool_name": "Edit",
        "tool_input": {"file_path": "/some/repo/.claude/skip-worktree"},
    })
    assert rc == 0


def test_gate_handles_invalid_json():
    """Gate hook exits 0 (not crash) when fed invalid stdin."""
    proc = subprocess.run(
        ["node", str(GATE)],
        input="not json",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0


def test_gate_block_message_is_actionable():
    """When gate blocks, stderr must contain both action options."""
    # This test only fires if we're NOT in a worktree AND have a recent plan.
    # We test the message format by checking the gate exits non-zero under those conditions.
    # Since we can't control the environment reliably in unit tests, we validate
    # the structure of the blocking message by inspecting the source directly.
    source = GATE.read_text()
    assert "WORKTREE_REQUIRED" in source
    assert "EnterWorktree" in source
    assert ".claude/skip-worktree" in source
    assert "exit 1" in source or "process.exit(1)" in source
```

- [ ] **Step 2: Run tests — expect failures (files don't exist yet)**

```bash
python3 -m pytest tests/test_hooks.py -v
```

Expected output: `ERROR` or `FAILED` on the `node --check` tests (hook files don't exist), `PASSED` on `test_gate_block_message_is_actionable` (reads source — will fail because file missing).

All tests should show `FAILED` or `ERROR` for now. That's correct — red before green.

---

## Task 3: Implement `hooks/tonone-worktree-create.js`

**Files:**
- Create: `hooks/tonone-worktree-create.js`

- [ ] **Step 1: Create the hook file**

```javascript
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

const { execSync } = require("child_process");
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
      try {
        execSync(`git worktree add "${wPath}" -b "${candidate}"`, {
          encoding: "utf8",
          stdio: ["ignore", "pipe", "pipe"],
        });
        worktreePath = wPath;
        branchName = candidate;
        break;
      } catch {
        continue; // Name collision or other transient error — retry
      }
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
```

- [ ] **Step 2: Run tests — creator tests should pass**

```bash
python3 -m pytest tests/test_hooks.py::test_worktree_create_is_valid_js tests/test_hooks.py::test_create_ignores_non_exit_plan_mode tests/test_hooks.py::test_create_handles_invalid_json -v
```

Expected: all 3 PASS.

- [ ] **Step 3: Commit**

```bash
git add hooks/tonone-worktree-create.js
git commit -m "feat: add tonone-worktree-create hook (PostToolUse on ExitPlanMode)"
```

---

## Task 4: Implement `hooks/tonone-worktree-gate.js`

**Files:**
- Create: `hooks/tonone-worktree-gate.js`

- [ ] **Step 1: Create the hook file**

```javascript
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
```

- [ ] **Step 2: Run all hook tests — all should pass**

```bash
python3 -m pytest tests/test_hooks.py -v
```

Expected: all 9 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add hooks/tonone-worktree-gate.js
git commit -m "feat: add tonone-worktree-gate hook (PreToolUse safety net)"
```

---

## Task 5: Register hooks in `plugin.json`

**Files:**
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Add the two hook entries**

The `hooks` block currently has `SessionStart` and `PostToolUse` (for `Agent`). Add:
- `PostToolUse` entry for `ExitPlanMode` → `tonone-worktree-create.js`
- `PreToolUse` entry for `Edit|Write|NotebookEdit` → `tonone-worktree-gate.js`

The full updated `hooks` block:

```json
"hooks": {
  "SessionStart": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/install-statusline.sh\""
        }
      ]
    }
  ],
  "PostToolUse": [
    {
      "matcher": "Agent",
      "hooks": [
        {
          "type": "command",
          "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-agent-tracker.js\"",
          "timeout": 5
        }
      ]
    },
    {
      "matcher": "ExitPlanMode",
      "hooks": [
        {
          "type": "command",
          "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-worktree-create.js\"",
          "timeout": 10
        }
      ]
    }
  ],
  "PreToolUse": [
    {
      "matcher": "Edit|Write|NotebookEdit",
      "hooks": [
        {
          "type": "command",
          "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-worktree-gate.js\"",
          "timeout": 5
        }
      ]
    }
  ]
}
```

- [ ] **Step 2: Validate the JSON**

```bash
python3 -c "import json; json.load(open('.claude-plugin/plugin.json')); print('valid')"
```

Expected: `valid`

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "feat: register worktree hooks in plugin.json"
```

---

## Task 6: Add structure tests for new hook files

**Files:**
- Modify: `tests/test_structure.py`

- [ ] **Step 1: Add hook existence test**

Add this test to `tests/test_structure.py`, after the existing plugin tests (around line 80):

```python
def test_worktree_hooks_exist():
    """Both worktree isolation hooks must exist — they are interdependent (creator + gate)."""
    for hook in ["tonone-worktree-create.js", "tonone-worktree-gate.js"]:
        p = REPO / "hooks" / hook
        assert p.exists(), f"Missing worktree hook: hooks/{hook}"


def test_worktree_hooks_registered_in_plugin_json():
    """Root plugin.json must register both worktree hooks."""
    plugin = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text())
    hooks = plugin.get("hooks", {})

    # Check PostToolUse has ExitPlanMode matcher
    post_matchers = [
        h.get("matcher") for h in hooks.get("PostToolUse", [])
    ]
    assert "ExitPlanMode" in post_matchers, (
        "plugin.json PostToolUse missing ExitPlanMode matcher for worktree creator"
    )

    # Check PreToolUse has Edit|Write|NotebookEdit matcher
    pre_matchers = [
        h.get("matcher") for h in hooks.get("PreToolUse", [])
    ]
    assert any("Edit" in (m or "") for m in pre_matchers), (
        "plugin.json PreToolUse missing Edit matcher for worktree gate"
    )
```

Note: `json` is already imported at the top of `test_structure.py` (it's used for plugin parsing).

- [ ] **Step 2: Run the full test suite**

```bash
python3 -m pytest tests/ -v
```

Expected: all tests PASS. The two new structure tests should pass (hooks exist, plugin.json registered them). All pre-existing tests should still pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_structure.py
git commit -m "test: add structure tests for worktree hooks"
```

---

## Task 7: Smoke test the full flow

This is a manual verification task. No automated test — it requires an interactive Claude Code session.

- [ ] **Step 1: Verify ExitPlanMode fires PostToolUse hook**

In a new Claude Code session on main:
1. Enter plan mode: ask Claude to write a plan (any trivial plan)
2. Approve the plan (ExitPlanMode)
3. Check if a new worktree was created:

```bash
git worktree list
ls .claude/worktrees/
```

Expected: a new `impl-YYYYMMDD-HHMMSS-PID` entry appears.

- [ ] **Step 2: Verify Claude sees the WORKTREE_READY message**

After approving the plan, check if Claude mentions `WORKTREE_READY` or `EnterWorktree` in its response. If it does, PostToolUse stdout IS visible — ideal path works.

If Claude does NOT mention it but a worktree was created: fallback path (gate hook) will handle it.

- [ ] **Step 3: Verify the gate hook fires**

Still on main (without entering the worktree), ask Claude to edit any file. It should be blocked with `WORKTREE_REQUIRED` in the error message and instructions to call `EnterWorktree`.

- [ ] **Step 4: Verify opt-out works**

Ask Claude to create `.claude/skip-worktree`, then edit a file on main. The edit should succeed.

- [ ] **Step 5: Verify cleanup**

Exit the session without making changes in the worktree (use a fresh session that only plans, doesn't edit). Run:

```bash
git worktree list
```

If the worktree has no changes, `ExitWorktree` (or session end) should clean it up automatically. Confirm it's gone.

- [ ] **Step 6: Run full test suite one final time**

```bash
python3 -m pytest tests/ -v
```

Expected: all tests PASS.

---

## Self-Review

**Spec coverage:**
- [x] PostToolUse on ExitPlanMode creates worktree → Task 3
- [x] PreToolUse gate blocks edits on main with active plan → Task 4
- [x] Opt-out via `.claude/skip-worktree` → Task 4 (hook), Task 1 (gitignore)
- [x] Race-safe branch naming (PID suffix) → Task 3
- [x] Stale plan filter (24h mtime) → Task 4
- [x] Stale opt-out filter (2h mtime) → Task 4
- [x] Plugin registration → Task 5
- [x] Gitignore entries → Task 1
- [x] Tests → Tasks 2, 6
- [x] Smoke test → Task 7

**Placeholder scan:** No TBDs, TODOs, or "similar to Task N" patterns. All code blocks are complete.

**Type consistency:** No shared types between tasks — each hook is a standalone Node.js script. `GATED` array in gate hook matches tool names used in plugin.json matcher string.
