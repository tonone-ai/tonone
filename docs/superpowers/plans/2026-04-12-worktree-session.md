# Eager Worktree Sessions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the unreliable lazy worktree + gate system with two clean hooks: eager creation at SessionStart and auto-cleanup at Stop.

**Architecture:** A `SessionStart` hook creates a timestamped worktree branch immediately, prints `WORKTREE_READY` so Claude calls `EnterWorktree()` before doing anything else. A `Stop` hook checks for changes — clean sessions are auto-removed, dirty sessions print a `/ship` prompt to the user. Claude renames the branch once the task is understood.

**Tech Stack:** Node.js 18+ (built-in `node:test` for tests), git worktree CLI

---

## File Map

| File                                   | Action | Responsibility                                                        |
| -------------------------------------- | ------ | --------------------------------------------------------------------- |
| `hooks/tonone-worktree-session.js`     | Create | SessionStart hook — eager worktree creation                           |
| `hooks/tonone-worktree-close.js`       | Create | Stop hook — auto-remove clean sessions, suggest PR for dirty ones     |
| `tests/hooks/test-worktree-session.js` | Create | Integration tests for session hook                                    |
| `tests/hooks/test-worktree-close.js`   | Create | Integration tests for close hook                                      |
| `hooks/tonone-worktree-create.js`      | Delete | Replaced by session hook                                              |
| `hooks/tonone-worktree-gate.js`        | Delete | Replaced by eager creation                                            |
| `.claude-plugin/plugin.json`           | Modify | Wire new hooks, remove old ExitPlanMode + PreToolUse worktree entries |
| `CLAUDE.md`                            | Modify | Replace `## Worktree branch naming` with `## Worktree sessions`       |

---

## Task 1: Write failing tests for tonone-worktree-session.js

**Files:**

- Create: `tests/hooks/test-worktree-session.js`

- [ ] **Step 1: Create the test file**

```js
// tests/hooks/test-worktree-session.js
const { test } = require("node:test");
const assert = require("node:assert");
const { execSync, spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const HOOK = path.join(__dirname, "../../hooks/tonone-worktree-session.js");

function makeTempRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "wt-sess-"));
  execSync("git init", { cwd: dir });
  execSync("git config user.email test@test.com", { cwd: dir });
  execSync("git config user.name Test", { cwd: dir });
  fs.writeFileSync(path.join(dir, "README.md"), "test");
  execSync("git add README.md", { cwd: dir });
  execSync("git commit -m init", { cwd: dir });
  return dir;
}

function cleanup(dir) {
  try {
    fs.rmSync(dir, { recursive: true, force: true });
  } catch {}
}

function runHook(cwd) {
  return spawnSync("node", [HOOK], {
    input: "{}",
    encoding: "utf8",
    cwd,
    timeout: 15000,
  });
}

test("not a git repo — exits 0 with git init tip", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "wt-nogit-"));
  try {
    const result = runHook(dir);
    assert.strictEqual(result.status, 0, result.stderr);
    assert.match(result.stdout, /git init/);
  } finally {
    cleanup(dir);
  }
});

test("already in a worktree — exits 0, no WORKTREE_READY", () => {
  const main = makeTempRepo();
  try {
    const wtPath = path.join(main, ".claude", "worktrees", "existing");
    fs.mkdirSync(path.join(main, ".claude", "worktrees"), { recursive: true });
    execSync(`git worktree add "${wtPath}" -b existing`, { cwd: main });
    const result = runHook(wtPath);
    assert.strictEqual(result.status, 0, result.stderr);
    assert.doesNotMatch(result.stdout, /WORKTREE_READY/);
  } finally {
    cleanup(main);
  }
});

test("on main — creates worktree, prints WORKTREE_READY with EnterWorktree call", () => {
  const dir = makeTempRepo();
  try {
    const result = runHook(dir);
    assert.strictEqual(result.status, 0, result.stderr);
    assert.match(result.stdout, /WORKTREE_READY/);
    assert.match(result.stdout, /EnterWorktree/);
    assert.match(result.stdout, /session-\d{8}-\d{6}/);
    // Verify the worktree directory was actually created on disk
    const wtDir = path.join(dir, ".claude", "worktrees");
    const entries = fs
      .readdirSync(wtDir)
      .filter((e) => e.startsWith("session-"));
    assert.ok(entries.length > 0, "expected a session-* worktree directory");
  } finally {
    cleanup(dir);
  }
});

test("on main — branch rename hint is included in output", () => {
  const dir = makeTempRepo();
  try {
    const result = runHook(dir);
    assert.strictEqual(result.status, 0, result.stderr);
    assert.match(result.stdout, /git branch -m/);
  } finally {
    cleanup(dir);
  }
});
```

- [ ] **Step 2: Run tests — confirm they fail (hook file missing)**

```bash
node --test tests/hooks/test-worktree-session.js
```

Expected: 4 tests fail with something like `Cannot find module` or similar because `hooks/tonone-worktree-session.js` does not exist yet.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/hooks/test-worktree-session.js
git commit -m "test(worktree): failing tests for tonone-worktree-session"
```

---

## Task 2: Implement tonone-worktree-session.js

**Files:**

- Create: `hooks/tonone-worktree-session.js`

- [ ] **Step 1: Create the hook**

```js
#!/usr/bin/env node
// tonone-worktree-session — SessionStart hook
//
// Creates an isolated git worktree branch at the start of every session.
// Prints WORKTREE_READY so Claude calls EnterWorktree() before taking action.
// Silent-fails on any error — never block the user's workflow.

const { execSync, spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

let input = "";
const timeout = setTimeout(() => process.exit(0), 9000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  clearTimeout(timeout);
  try {
    // 1. Bail if not a git repo
    let gitDir, commonDir;
    try {
      gitDir = execSync("git rev-parse --git-dir", { encoding: "utf8" }).trim();
      commonDir = execSync("git rev-parse --git-common-dir", {
        encoding: "utf8",
      }).trim();
    } catch {
      console.log(
        "Tip: this directory is not a git repo. " +
          "Run `git init` to get isolated session branches automatically.",
      );
      process.exit(0);
    }

    // 2. Already in a worktree — nothing to do
    if (gitDir !== commonDir) process.exit(0);

    // 3. Build branch name: session-YYYYMMDD-HHMMSS (UTC)
    const now = new Date();
    const pad = (n) => String(n).padStart(2, "0");
    const date = `${now.getUTCFullYear()}${pad(now.getUTCMonth() + 1)}${pad(now.getUTCDate())}`;
    const time = `${pad(now.getUTCHours())}${pad(now.getUTCMinutes())}${pad(now.getUTCSeconds())}`;
    const base = `session-${date}-${time}`;

    // 4. Create worktree — up to 3 retries on name collision
    let worktreePath = null;
    let branchName = null;
    for (let i = 0; i < 3; i++) {
      const candidate = i === 0 ? base : `${base}-${i + 1}`;
      const wPath = path.join(".claude", "worktrees", candidate);
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

    // 5. Silent fail if creation failed — never block the user
    if (!worktreePath) process.exit(0);

    // 6. Tell Claude to enter the worktree
    console.log(
      `WORKTREE_READY: Isolated workspace created for this session.\n` +
        `Path: ${worktreePath}\n` +
        `Branch: ${branchName}\n\n` +
        `Call EnterWorktree("${worktreePath}") now before any other action.\n` +
        `Once you understand the task, rename the branch:\n` +
        `  git branch -m ${branchName} <kebab-slug>`,
    );
  } catch {
    // Silent fail
  }
  process.exit(0);
});
```

- [ ] **Step 2: Run tests — all 4 must pass**

```bash
node --test tests/hooks/test-worktree-session.js
```

Expected output: `✓ not a git repo — exits 0 with git init tip`, `✓ already in a worktree — exits 0, no WORKTREE_READY`, `✓ on main — creates worktree, prints WORKTREE_READY with EnterWorktree call`, `✓ on main — branch rename hint is included in output`

- [ ] **Step 3: Commit**

```bash
git add hooks/tonone-worktree-session.js
git commit -m "feat(worktree): add tonone-worktree-session — eager SessionStart worktree creation"
```

---

## Task 3: Write failing tests for tonone-worktree-close.js

**Files:**

- Create: `tests/hooks/test-worktree-close.js`

- [ ] **Step 1: Create the test file**

```js
// tests/hooks/test-worktree-close.js
const { test } = require("node:test");
const assert = require("node:assert");
const { execSync, spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const HOOK = path.join(__dirname, "../../hooks/tonone-worktree-close.js");

function makeTempRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "wt-close-"));
  execSync("git init", { cwd: dir });
  execSync("git config user.email test@test.com", { cwd: dir });
  execSync("git config user.name Test", { cwd: dir });
  fs.writeFileSync(path.join(dir, "README.md"), "test");
  execSync("git add README.md", { cwd: dir });
  execSync("git commit -m init", { cwd: dir });
  return dir;
}

function makeWorktree(mainRepo, name = "test-branch") {
  const wtPath = path.join(mainRepo, ".claude", "worktrees", name);
  fs.mkdirSync(path.join(mainRepo, ".claude", "worktrees"), {
    recursive: true,
  });
  execSync(`git worktree add "${wtPath}" -b ${name}`, { cwd: mainRepo });
  return wtPath;
}

function cleanup(dir) {
  try {
    fs.rmSync(dir, { recursive: true, force: true });
  } catch {}
}

function runHook(cwd) {
  return spawnSync("node", [HOOK], {
    input: "{}",
    encoding: "utf8",
    cwd,
    timeout: 15000,
  });
}

test("not in a worktree (main repo) — exits 0, no output", () => {
  const dir = makeTempRepo();
  try {
    const result = runHook(dir);
    assert.strictEqual(result.status, 0, result.stderr);
    assert.strictEqual(result.stdout.trim(), "");
  } finally {
    cleanup(dir);
  }
});

test("clean worktree (no changes) — removes it and prints confirmation", () => {
  const dir = makeTempRepo();
  try {
    const wtPath = makeWorktree(dir);
    const result = runHook(wtPath);
    assert.strictEqual(result.status, 0, result.stderr);
    assert.match(result.stdout, /clean|removed/i);
    assert.ok(!fs.existsSync(wtPath), "worktree directory should be deleted");
  } finally {
    cleanup(dir);
  }
});

test("dirty worktree (committed changes) — prints /ship suggestion, keeps worktree", () => {
  const dir = makeTempRepo();
  try {
    const wtPath = makeWorktree(dir);
    fs.writeFileSync(path.join(wtPath, "feature.txt"), "new content");
    execSync("git add feature.txt", { cwd: wtPath });
    execSync('git commit -m "add feature"', { cwd: wtPath });
    const result = runHook(wtPath);
    assert.strictEqual(result.status, 0, result.stderr);
    assert.match(result.stdout, /\/ship/);
    assert.ok(fs.existsSync(wtPath), "worktree should still exist");
  } finally {
    cleanup(dir);
  }
});

test("dirty worktree (uncommitted changes) — prints /ship suggestion, keeps worktree", () => {
  const dir = makeTempRepo();
  try {
    const wtPath = makeWorktree(dir);
    fs.writeFileSync(path.join(wtPath, "dirty.txt"), "not staged");
    const result = runHook(wtPath);
    assert.strictEqual(result.status, 0, result.stderr);
    assert.match(result.stdout, /\/ship/);
    assert.ok(fs.existsSync(wtPath), "worktree should still exist");
  } finally {
    cleanup(dir);
  }
});
```

- [ ] **Step 2: Run tests — confirm they fail**

```bash
node --test tests/hooks/test-worktree-close.js
```

Expected: 4 tests fail because `hooks/tonone-worktree-close.js` does not exist yet.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/hooks/test-worktree-close.js
git commit -m "test(worktree): failing tests for tonone-worktree-close"
```

---

## Task 4: Implement tonone-worktree-close.js

**Files:**

- Create: `hooks/tonone-worktree-close.js`

- [ ] **Step 1: Create the hook**

```js
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

    if (isClean) {
      // Auto-remove the worktree (run from main repo to avoid self-removal issues)
      execSync(
        `git -C "${mainRepoPath}" worktree remove --force "${worktreePath}"`,
        { encoding: "utf8" },
      );
      try {
        execSync(`git -C "${mainRepoPath}" branch -d ${branch}`, {
          encoding: "utf8",
        });
      } catch {}
      console.log(`Session branch ${branch} was clean — removed.`);
    } else {
      // Suggest shipping
      console.log(
        `\nWorktree: ${branch}\n` +
          `Changes detected. Run /ship to open a PR.\n` +
          `To discard: git -C "${mainRepoPath}" worktree remove --force "${worktreePath}" ` +
          `&& git -C "${mainRepoPath}" branch -D ${branch}\n`,
      );
    }
  } catch {
    // Silent fail
  }
  process.exit(0);
});
```

- [ ] **Step 2: Run tests — all 4 must pass**

```bash
node --test tests/hooks/test-worktree-close.js
```

Expected: all 4 pass.

- [ ] **Step 3: Run session hook tests too — confirm nothing regressed**

```bash
node --test tests/hooks/test-worktree-session.js
```

Expected: all 4 still pass.

- [ ] **Step 4: Commit**

```bash
git add hooks/tonone-worktree-close.js
git commit -m "feat(worktree): add tonone-worktree-close — Stop hook for session cleanup"
```

---

## Task 5: Wire up plugin.json, delete old hooks, update CLAUDE.md

**Files:**

- Modify: `.claude-plugin/plugin.json`
- Delete: `hooks/tonone-worktree-create.js`
- Delete: `hooks/tonone-worktree-gate.js`
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update plugin.json**

Replace the entire `"hooks"` block in `.claude-plugin/plugin.json` with this (preserving all non-worktree hooks exactly):

```json
{
  "name": "tonone",
  "description": "Engineering + Product team — 23 agents as Claude Code specialists. Infrastructure, DevOps, backend, security, ML/AI, mobile, UX, analytics, growth, strategy, and more.",
  "version": "0.6.10",
  "author": {
    "name": "tonone-ai",
    "url": "https://tonone.ai"
  },
  "repository": "https://github.com/tonone-ai/tonone",
  "license": "MIT",
  "keywords": [
    "agents",
    "engineering-team",
    "infrastructure",
    "devops",
    "backend",
    "security",
    "observability",
    "frontend",
    "ml",
    "mobile",
    "embedded",
    "analytics",
    "testing",
    "platform"
  ],
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "bash \"${CLAUDE_PLUGIN_ROOT}/hooks/install-statusline.sh\""
          },
          {
            "type": "command",
            "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/elephant-recall.js\"",
            "timeout": 5
          },
          {
            "type": "command",
            "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-update-check.js\"",
            "timeout": 8
          },
          {
            "type": "command",
            "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-worktree-session.js\"",
            "timeout": 10
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
          },
          {
            "type": "command",
            "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/elephant-writer.js\"",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/elephant-writer.js\"",
            "timeout": 5
          }
        ]
      },
      {
        "matcher": "Skill",
        "hooks": [
          {
            "type": "command",
            "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/elephant-writer.js\"",
            "timeout": 5
          }
        ]
      }
    ],
    "PreToolUse": [
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
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-notify.js\"",
            "timeout": 5
          },
          {
            "type": "command",
            "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-worktree-close.js\"",
            "timeout": 10
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-notify.js\"",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 2: Delete old hooks**

```bash
git rm hooks/tonone-worktree-create.js hooks/tonone-worktree-gate.js
```

- [ ] **Step 3: Update CLAUDE.md — replace `## Worktree branch naming` section**

Find this section in `CLAUDE.md`:

````markdown
## Worktree branch naming

Before making the first edit in an implementation session, write a short kebab-case description of the task to `.claude/branch-slug`. The worktree hooks read this file to name the branch.

```bash
# Example — do this before any file edit:
echo "fix-auth-bug" > .claude/branch-slug
echo "add-worktree-git-gate" > .claude/branch-slug
```
````

No slashes. Lowercase. Max 50 chars. If omitted, branch falls back to `impl-YYYYMMDD-HHMMSS`.

````

Replace with:

```markdown
## Worktree sessions

Every session starts in an isolated git worktree branch automatically. The SessionStart hook creates a `session-YYYYMMDD-HHMMSS` branch and prints `WORKTREE_READY`. **Call `EnterWorktree("<path>")` immediately — before any other action.**

### Branch rename

Once you understand what the user wants (after the first substantive exchange), rename the branch to a descriptive kebab-case slug:

```bash
git branch -m session-YYYYMMDD-HHMMSS <kebab-slug>
````

Max 50 chars. Lowercase. No slashes. Example: `fix-auth-bug`, `add-stripe-webhooks`.

### Topic drift

If the user shifts to a clearly different task while the current worktree has uncommitted or unpushed changes, say:

> "This looks like a new topic. Want me to open a PR for the current changes first, then start a fresh session for this?"

Do not switch topics silently. Keep sessions focused.

### Session end

When stopping, the hook auto-removes clean worktrees. If changes exist, it prints a `/ship` reminder to the user.

````

- [ ] **Step 4: Commit everything**

```bash
git add .claude-plugin/plugin.json CLAUDE.md
git commit -m "feat(worktree): wire eager session hooks, remove gate, update CLAUDE.md"
````

---

## Self-Review

- **Spec coverage:**
  - ✅ SessionStart creates timestamped worktree → Task 2
  - ✅ Not a git repo → tip message → Task 2
  - ✅ Already in worktree → skip → Task 2
  - ✅ Branch rename hint in output → Task 2 (output) + Task 5 (CLAUDE.md)
  - ✅ Stop hook cleans up clean sessions → Task 4
  - ✅ Stop hook suggests /ship for dirty sessions → Task 4
  - ✅ Default branch detection (not hardcoded to `main`) → Task 4
  - ✅ Old hooks removed → Task 5
  - ✅ plugin.json wired → Task 5
  - ✅ CLAUDE.md updated → Task 5

- **No placeholders:** all steps contain complete code

- **Type consistency:** no shared types across tasks — each hook is a standalone Node.js script
