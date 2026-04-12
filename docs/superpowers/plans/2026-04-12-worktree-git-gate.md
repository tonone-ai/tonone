# Worktree Git Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Block `git commit` and `git push` on main via a new Bash PreToolUse hook, closing the last gap in worktree isolation.

**Architecture:** New `hooks/tonone-git-gate.js` mirrors the existing `tonone-worktree-gate.js` pattern — parse stdin, check opt-out, check worktree status, block or pass. Registered in `.claude-plugin/plugin.json` under `PreToolUse` with matcher `Bash`. Tests added to `tests/test_hooks.py` following existing hook test conventions.

**Tech Stack:** Node.js (hook), Python pytest (tests), JSON (plugin.json)

---

### Task 1: Write failing tests for `tonone-git-gate.js`

**Files:**
- Modify: `tests/test_hooks.py`

- [ ] **Step 1: Add GIT_GATE path constant and tests at the bottom of `tests/test_hooks.py`**

Append after the last line of `tests/test_hooks.py`:

```python
# ---------------------------------------------------------------------------
# tonone-git-gate.js
# ---------------------------------------------------------------------------

GIT_GATE = REPO / "hooks" / "tonone-git-gate.js"


def test_git_gate_file_exists():
    """Git gate hook file must exist."""
    assert GIT_GATE.exists(), f"Missing: {GIT_GATE}"


def test_git_gate_is_valid_js():
    """tonone-git-gate.js must be syntactically valid Node.js."""
    result = subprocess.run(
        ["node", "--check", str(GIT_GATE)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_git_gate_allows_non_git_commands():
    """Gate exits 0 for Bash commands that are not git commit/push."""
    for cmd in ["npm test", "echo hello", "git status", "git log", "git add ."]:
        rc, _, _ = run_hook(GIT_GATE, {
            "tool_name": "Bash",
            "tool_input": {"command": cmd},
        })
        assert rc == 0, f"Expected exit 0 for command={cmd!r}, got {rc}"


def test_git_gate_allows_non_bash_tools():
    """Gate exits 0 for tools other than Bash."""
    for tool in ["Edit", "Write", "Read", "Agent"]:
        rc, _, _ = run_hook(GIT_GATE, {
            "tool_name": tool,
            "tool_input": {"command": "git commit -m 'test'"},
        })
        assert rc == 0, f"Expected exit 0 for tool={tool}, got {rc}"


def test_git_gate_handles_invalid_json():
    """Git gate exits 0 on invalid stdin — must never block user on a crash."""
    proc = subprocess.run(
        ["node", str(GIT_GATE)],
        input="not json",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0


def test_git_gate_message_is_actionable():
    """When git gate blocks, source must contain GIT_GATE, EnterWorktree, and skip-worktree."""
    source = GIT_GATE.read_text()
    assert "GIT_GATE" in source
    assert "EnterWorktree" in source
    assert ".claude/skip-worktree" in source
    assert "process.exit(1)" in source
```

- [ ] **Step 2: Run the new tests to verify they fail (file doesn't exist yet)**

```bash
cd /Users/f/repos/tn/tonone && python -m pytest tests/test_hooks.py::test_git_gate_file_exists tests/test_hooks.py::test_git_gate_is_valid_js -v
```

Expected: FAIL — `Missing: .../hooks/tonone-git-gate.js`

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_hooks.py
git commit -m "test(worktree): add failing tests for tonone-git-gate.js"
```

---

### Task 2: Implement `hooks/tonone-git-gate.js`

**Files:**
- Create: `hooks/tonone-git-gate.js`

- [ ] **Step 1: Create the hook file**

```javascript
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
    const command = (data.tool_input && data.tool_input.command) || "";

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
      gitDir = execSync("git rev-parse --git-dir", { encoding: "utf8" }).trim();
      commonDir = execSync("git rev-parse --git-common-dir", {
        encoding: "utf8",
      }).trim();
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
```

- [ ] **Step 2: Run all git gate tests**

```bash
cd /Users/f/repos/tn/tonone && python -m pytest tests/test_hooks.py -k git_gate -v
```

Expected: all PASS

- [ ] **Step 3: Run the full test suite to check for regressions**

```bash
cd /Users/f/repos/tn/tonone && python -m pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 4: Commit the hook**

```bash
git add hooks/tonone-git-gate.js
git commit -m "feat(worktree): add tonone-git-gate — block git commit/push on main"
```

---

### Task 3: Register hook in `plugin.json`

**Files:**
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Add the Bash PreToolUse entry**

In `.claude-plugin/plugin.json`, inside the `"PreToolUse"` array (after the existing `Edit|Write|NotebookEdit` entry), add:

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-git-gate.js\"",
      "timeout": 5
    }
  ]
}
```

The full `"PreToolUse"` section should look like:

```json
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
  },
  {
    "matcher": "Bash",
    "hooks": [
      {
        "type": "command",
        "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-git-gate.js\"",
        "timeout": 5
      }
    ]
  }
]
```

- [ ] **Step 2: Validate plugin.json is valid JSON**

```bash
node -e "JSON.parse(require('fs').readFileSync('.claude-plugin/plugin.json','utf8')); console.log('valid')"
```

Expected: `valid`

- [ ] **Step 3: Copy hook to plugin cache so it's live immediately**

```bash
cp hooks/tonone-git-gate.js /Users/f/.claude/plugins/cache/tonone-ai/tonone/0.6.9/hooks/tonone-git-gate.js
cp .claude-plugin/plugin.json /Users/f/.claude/plugins/cache/tonone-ai/tonone/0.6.9/.claude-plugin/plugin.json
```

- [ ] **Step 4: Run full test suite one final time**

```bash
cd /Users/f/repos/tn/tonone && python -m pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "feat(worktree): register git gate in plugin.json PreToolUse Bash"
```

---

### Task 4: Smoke test

- [ ] **Step 1: Reload plugins in Claude Code**

Run `/reload-plugins` in Claude Code. Verify the new hook is listed.

- [ ] **Step 2: Verify git gate blocks on main**

From the main repo (not a worktree), try:

```bash
git commit --allow-empty -m "smoke test"
```

Expected: hook fires, Claude sees `GIT_GATE: Commits and pushes are blocked on main.` with `EnterWorktree(...)` instruction. Command blocked (exit 1).

- [ ] **Step 3: Verify git gate allows in worktree**

Enter the existing worktree and verify commit works:

```bash
# Claude calls EnterWorktree(".claude/worktrees/impl-20260412-134252-50041")
# Then:
git commit --allow-empty -m "smoke test from worktree"
```

Expected: commits successfully to `impl-20260412-134252-50041` branch.

- [ ] **Step 4: Verify opt-out works**

```bash
touch .claude/skip-worktree
git commit --allow-empty -m "deliberate main commit"
rm .claude/skip-worktree
```

Expected: commit succeeds on main when skip-worktree exists.
