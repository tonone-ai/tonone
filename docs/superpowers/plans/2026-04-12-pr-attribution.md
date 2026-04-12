# PR Attribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Append agent credits + tonone link to every PR created during a tonone session, driving K-factor by making the team visible in the most-read artifact in any repo.

**Architecture:** Two hooks wired into the root plugin.json. Hook 1 (`tonone-session-tracker.js`) fires on every Skill PostToolUse, extracts the tonone agent name from the skill name, and appends it to `.claude/session-agents`. Hook 2 (`tonone-pr-attribution.js`) fires on every Bash PostToolUse, detects `gh pr create`, reads `.claude/session-agents`, and appends a formatted attribution block via `gh pr edit`. Both hooks follow the existing pattern in `hooks/tonone-git-gate.js` and `hooks/elephant-writer.js`.

**Tech Stack:** Node.js (built-in modules only: `fs`, `path`, `child_process`), `node:test` for tests, `gh` CLI (pre-installed wherever Claude Code runs).

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `hooks/tonone-session-tracker.js` | Create | Skill PostToolUse — write agent name to `.claude/session-agents` |
| `hooks/tonone-pr-attribution.js` | Create | Bash PostToolUse — detect `gh pr create`, append attribution to PR |
| `.claude-plugin/plugin.json` | Modify lines 76–83 | Register both new hooks |
| `tests/hooks/test-session-tracker.js` | Create | Unit tests for session tracker |
| `tests/hooks/test-pr-attribution.js` | Create | Unit tests for PR attribution hook |

---

## Task 1: Write failing tests for tonone-session-tracker.js

**Files:**
- Create: `tests/hooks/test-session-tracker.js`

- [ ] **Step 1: Write the test file**

```js
const { test } = require("node:test");
const assert = require("node:assert");
const { spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const HOOK = path.join(__dirname, "../../hooks/tonone-session-tracker.js");

function runHook(input, cwd) {
  return spawnSync("node", [HOOK], {
    input: JSON.stringify(input),
    encoding: "utf8",
    cwd,
    timeout: 5000,
  });
}

function makeTempDir() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "sess-tracker-"));
  fs.mkdirSync(path.join(dir, ".claude"), { recursive: true });
  return dir;
}

function cleanup(dir) {
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
}

test("tonone skill — appends agent name to .claude/session-agents", () => {
  const dir = makeTempDir();
  try {
    const result = runHook(
      { tool_name: "Skill", tool_input: { skill: "spine-api" } },
      dir
    );
    assert.strictEqual(result.status, 0, result.stderr);
    const content = fs.readFileSync(path.join(dir, ".claude", "session-agents"), "utf8");
    assert.ok(content.includes("spine"), `expected 'spine' in: ${content}`);
  } finally {
    cleanup(dir);
  }
});

test("non-tonone skill — ignored, file not written", () => {
  const dir = makeTempDir();
  try {
    const result = runHook(
      { tool_name: "Skill", tool_input: { skill: "superpowers:brainstorming" } },
      dir
    );
    assert.strictEqual(result.status, 0, result.stderr);
    const filePath = path.join(dir, ".claude", "session-agents");
    assert.ok(!fs.existsSync(filePath), "file should not be created for non-tonone skill");
  } finally {
    cleanup(dir);
  }
});

test("same agent invoked twice — deduplication, appears once", () => {
  const dir = makeTempDir();
  try {
    runHook({ tool_name: "Skill", tool_input: { skill: "warden-audit" } }, dir);
    runHook({ tool_name: "Skill", tool_input: { skill: "warden-harden" } }, dir);
    const content = fs.readFileSync(path.join(dir, ".claude", "session-agents"), "utf8");
    const lines = content.trim().split("\n").filter(Boolean);
    const wardenLines = lines.filter(l => l === "warden");
    assert.strictEqual(wardenLines.length, 1, `expected 1 warden line, got: ${content}`);
  } finally {
    cleanup(dir);
  }
});

test("multiple different agents — all appended", () => {
  const dir = makeTempDir();
  try {
    runHook({ tool_name: "Skill", tool_input: { skill: "spine-api" } }, dir);
    runHook({ tool_name: "Skill", tool_input: { skill: "atlas-map" } }, dir);
    runHook({ tool_name: "Skill", tool_input: { skill: "proof-audit" } }, dir);
    const content = fs.readFileSync(path.join(dir, ".claude", "session-agents"), "utf8");
    assert.ok(content.includes("spine"), content);
    assert.ok(content.includes("atlas"), content);
    assert.ok(content.includes("proof"), content);
  } finally {
    cleanup(dir);
  }
});

test("non-Skill tool event — exits 0, no file written", () => {
  const dir = makeTempDir();
  try {
    const result = runHook(
      { tool_name: "Bash", tool_input: { command: "ls" } },
      dir
    );
    assert.strictEqual(result.status, 0, result.stderr);
    assert.ok(!fs.existsSync(path.join(dir, ".claude", "session-agents")));
  } finally {
    cleanup(dir);
  }
});

test("malformed JSON input — exits 0 silently", () => {
  const result = spawnSync("node", [HOOK], {
    input: "not-json",
    encoding: "utf8",
    timeout: 5000,
  });
  assert.strictEqual(result.status, 0);
});
```

- [ ] **Step 2: Run tests to verify they fail (hook not yet created)**

```bash
node --test tests/hooks/test-session-tracker.js
```

Expected: all tests fail with `Cannot find module` or `ENOENT`.

---

## Task 2: Implement tonone-session-tracker.js

**Files:**
- Create: `hooks/tonone-session-tracker.js`

- [ ] **Step 1: Write the hook**

```js
#!/usr/bin/env node
// tonone-session-tracker — PostToolUse Skill hook
// Tracks which tonone agents were invoked in this session.
// Appends agent name to .claude/session-agents for PR attribution.

"use strict";

const fs = require("fs");
const path = require("path");

const TONONE_AGENTS = new Set([
  "apex", "forge", "relay", "spine", "flux", "warden", "vigil",
  "prism", "cortex", "touch", "volt", "atlas", "lens", "proof",
  "pave", "helm", "echo", "lumen", "draft", "form", "crest",
  "pitch", "surge",
]);

const SESSION_FILE = path.join(".claude", "session-agents");

function appendAgent(agentName) {
  // Read existing agents
  let existing = new Set();
  try {
    const content = fs.readFileSync(SESSION_FILE, "utf8");
    content.trim().split("\n").filter(Boolean).forEach(l => existing.add(l));
  } catch {}

  if (existing.has(agentName)) return; // Already tracked

  existing.add(agentName);

  // Atomic write
  fs.mkdirSync(path.dirname(SESSION_FILE), { recursive: true });
  const tmp = SESSION_FILE + ".tmp." + process.pid;
  fs.writeFileSync(tmp, [...existing].join("\n") + "\n");
  fs.renameSync(tmp, SESSION_FILE);
}

let input = "";
const timeout = setTimeout(() => process.exit(0), 3000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => (input += chunk));
process.stdin.on("end", () => {
  clearTimeout(timeout);
  try {
    const data = JSON.parse(input);

    if (data.tool_name !== "Skill") process.exit(0);

    const skillName = (data.tool_input && data.tool_input.skill) || "";
    if (!skillName) process.exit(0);

    // Extract agent name: "spine-api" → "spine", "superpowers:brainstorming" → skip
    const base = skillName.includes(":") ? "" : skillName.split("-")[0];
    if (!base || !TONONE_AGENTS.has(base)) process.exit(0);

    appendAgent(base);
  } catch {
    // Silent fail — never block workflow
  }
});
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
node --test tests/hooks/test-session-tracker.js
```

Expected: all 6 tests pass.

- [ ] **Step 3: Commit**

```bash
git add hooks/tonone-session-tracker.js tests/hooks/test-session-tracker.js
git commit -m "feat(growth): add tonone-session-tracker — record active agents to .claude/session-agents"
```

---

## Task 3: Write failing tests for tonone-pr-attribution.js

**Files:**
- Create: `tests/hooks/test-pr-attribution.js`

- [ ] **Step 1: Write the test file**

```js
const { test } = require("node:test");
const assert = require("node:assert");
const { spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const HOOK = path.join(__dirname, "../../hooks/tonone-pr-attribution.js");

// Import the formatting helper directly for unit testing
// We'll test formatAttribution by requiring it after it exports
function runHook(input, cwd) {
  return spawnSync("node", [HOOK], {
    input: JSON.stringify(input),
    encoding: "utf8",
    cwd,
    timeout: 5000,
  });
}

function makeTempDir(agents) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "pr-attr-"));
  fs.mkdirSync(path.join(dir, ".claude"), { recursive: true });
  if (agents && agents.length > 0) {
    fs.writeFileSync(path.join(dir, ".claude", "session-agents"), agents.join("\n") + "\n");
  }
  return dir;
}

function cleanup(dir) {
  try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
}

// --- Unit tests for attribution formatting (tested via hook output on non-gh-create commands)
// We test formatting by exporting a pure function from the hook.
// The hook exports { formatAttribution } when required (not run as main).

const hook = require(HOOK);

test("formatAttribution — single agent, title-cased", () => {
  const line = hook.formatAttribution(["spine"]);
  assert.ok(line.includes("Spine"), line);
  assert.ok(line.includes("https://second.tonone.ai"), line);
  assert.ok(line.includes("[tonone]"), line);
});

test("formatAttribution — multiple agents, alphabetical, title-cased", () => {
  const line = hook.formatAttribution(["warden", "spine", "proof"]);
  assert.ok(line.includes("Proof · Spine · Warden"), line);
});

test("formatAttribution — more than 5 agents, truncated", () => {
  const line = hook.formatAttribution(["apex", "atlas", "forge", "lens", "proof", "spine", "warden"]);
  assert.ok(line.includes("and 2 more"), line);
});

test("formatAttribution — empty agents list, minimal attribution", () => {
  const line = hook.formatAttribution([]);
  assert.ok(line.includes("[tonone]"), line);
  assert.ok(line.includes("https://second.tonone.ai"), line);
});

// --- Integration: non-gh-create command is ignored
test("non gh-pr-create command — exits 0, no side effects", () => {
  const dir = makeTempDir(["spine"]);
  try {
    const result = runHook(
      { tool_name: "Bash", tool_input: { command: "git status" }, tool_output: {} },
      dir
    );
    assert.strictEqual(result.status, 0, result.stderr);
    // session-agents file should still exist (not cleared)
    assert.ok(fs.existsSync(path.join(dir, ".claude", "session-agents")));
  } finally {
    cleanup(dir);
  }
});

test("gh pr create — session-agents cleared after run", () => {
  const dir = makeTempDir(["spine", "warden"]);
  try {
    // Hook will try gh pr edit — it will fail (no real repo) but session-agents should clear
    runHook(
      {
        tool_name: "Bash",
        tool_input: { command: "gh pr create --title test --body test" },
        tool_output: { output: "https://github.com/owner/repo/pull/1" },
      },
      dir
    );
    // session-agents should be cleared regardless of gh success/failure
    const content = fs.existsSync(path.join(dir, ".claude", "session-agents"))
      ? fs.readFileSync(path.join(dir, ".claude", "session-agents"), "utf8")
      : "";
    assert.strictEqual(content.trim(), "", `expected empty session-agents, got: ${content}`);
  } finally {
    cleanup(dir);
  }
});

test("malformed JSON input — exits 0 silently", () => {
  const result = spawnSync("node", [HOOK], {
    input: "not-json",
    encoding: "utf8",
    timeout: 5000,
  });
  assert.strictEqual(result.status, 0);
});
```

- [ ] **Step 2: Run tests to verify they fail (hook not yet created)**

```bash
node --test tests/hooks/test-pr-attribution.js
```

Expected: fail with `Cannot find module` or `ENOENT`.

---

## Task 4: Implement tonone-pr-attribution.js

**Files:**
- Create: `hooks/tonone-pr-attribution.js`

- [ ] **Step 1: Write the hook**

```js
#!/usr/bin/env node
// tonone-pr-attribution — PostToolUse Bash hook
// Detects `gh pr create`, appends agent credits to the PR description.

"use strict";

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const SESSION_FILE = path.join(".claude", "session-agents");
const TONONE_URL = "https://second.tonone.ai";
const MAX_AGENTS = 5;

function titleCase(s) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function formatAttribution(agents) {
  if (!agents || agents.length === 0) {
    return `*— [tonone](${TONONE_URL})*`;
  }
  const sorted = [...agents].sort();
  let names;
  if (sorted.length <= MAX_AGENTS) {
    names = sorted.map(titleCase).join(" · ");
  } else {
    const shown = sorted.slice(0, MAX_AGENTS).map(titleCase).join(" · ");
    const remaining = sorted.length - MAX_AGENTS;
    names = `${shown} and ${remaining} more`;
  }
  return `*${names} — [tonone](${TONONE_URL})*`;
}

function readAgents() {
  try {
    const content = fs.readFileSync(SESSION_FILE, "utf8");
    return [...new Set(content.trim().split("\n").filter(Boolean))];
  } catch {
    return [];
  }
}

function clearAgents() {
  try { fs.writeFileSync(SESSION_FILE, ""); } catch {}
}

function getPrUrl(toolOutput) {
  // Try tool_output.output first (stdout of gh pr create)
  const raw = (toolOutput && (toolOutput.output || toolOutput)) || "";
  const urlMatch = String(raw).match(/https:\/\/github\.com\/[^\s]+\/pull\/\d+/);
  if (urlMatch) return urlMatch[0];

  // Fallback: ask gh for the current branch's PR
  try {
    const url = execSync("gh pr view --json url -q .url", { encoding: "utf8", timeout: 5000 }).trim();
    if (url.startsWith("http")) return url;
  } catch {}

  return null;
}

function appendAttribution(prUrl, attributionLine) {
  const tmpFile = path.join(require("os").tmpdir(), `tonone-pr-body-${process.pid}.md`);
  try {
    const currentBody = execSync(`gh pr view "${prUrl}" --json body -q .body`, {
      encoding: "utf8",
      timeout: 5000,
    }).trim();
    const newBody = `${currentBody}\n\n---\n${attributionLine}`;
    fs.writeFileSync(tmpFile, newBody);
    execSync(`gh pr edit "${prUrl}" --body-file "${tmpFile}"`, { timeout: 10000 });
  } finally {
    try { fs.unlinkSync(tmpFile); } catch {}
  }
}

// Export for unit testing
if (require.main !== module) {
  module.exports = { formatAttribution };
  return;
}

let input = "";
const timeout = setTimeout(() => process.exit(0), 3000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", chunk => (input += chunk));
process.stdin.on("end", () => {
  clearTimeout(timeout);
  try {
    const data = JSON.parse(input);

    if (data.tool_name !== "Bash") process.exit(0);

    const command = (data.tool_input && data.tool_input.command) || "";
    if (!/\bgh\s+pr\s+create\b/.test(command)) process.exit(0);

    const agents = readAgents();
    const attributionLine = formatAttribution(agents);

    // Clear agents before any network calls — even if edit fails, don't double-attribute
    clearAgents();

    const prUrl = getPrUrl(data.tool_output);
    if (!prUrl) process.exit(0);

    appendAttribution(prUrl, attributionLine);
  } catch {
    // Silent fail — never block workflow
  }
});
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
node --test tests/hooks/test-pr-attribution.js
```

Expected: all tests pass. The `gh pr edit` call in the integration test will fail (no real repo) but `clearAgents` happens before the network call, so the session-agents clearing test passes.

- [ ] **Step 3: Commit**

```bash
git add hooks/tonone-pr-attribution.js tests/hooks/test-pr-attribution.js
git commit -m "feat(growth): add tonone-pr-attribution — append team credits to PRs"
```

---

## Task 5: Register both hooks in plugin.json

**Files:**
- Modify: `.claude-plugin/plugin.json`

- [ ] **Step 1: Read current plugin.json to confirm exact line positions**

Read `.claude-plugin/plugin.json` lines 70–90 (the PostToolUse Bash and Skill matchers).

- [ ] **Step 2: Add session-tracker to Skill PostToolUse matcher**

Current Skill matcher block (lines ~75–83):
```json
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
```

Replace with:
```json
{
  "matcher": "Skill",
  "hooks": [
    {
      "type": "command",
      "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/elephant-writer.js\"",
      "timeout": 5
    },
    {
      "type": "command",
      "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-session-tracker.js\"",
      "timeout": 5
    }
  ]
}
```

- [ ] **Step 3: Add PR attribution to Bash PostToolUse matcher**

Current Bash matcher block (lines ~49–56):
```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/elephant-writer.js\"",
      "timeout": 5
    }
  ]
}
```

Replace with:
```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/elephant-writer.js\"",
      "timeout": 5
    },
    {
      "type": "command",
      "command": "node \"${CLAUDE_PLUGIN_ROOT}/hooks/tonone-pr-attribution.js\"",
      "timeout": 10
    }
  ]
}
```

Note: PR attribution gets `timeout: 10` (not 5) because it makes two `gh` network calls.

- [ ] **Step 4: Validate plugin.json is valid JSON**

```bash
node -e "JSON.parse(require('fs').readFileSync('.claude-plugin/plugin.json','utf8')); console.log('valid')"
```

Expected: `valid`

- [ ] **Step 5: Run all hook tests to confirm nothing broke**

```bash
node --test tests/hooks/test-session-tracker.js && node --test tests/hooks/test-pr-attribution.js
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add .claude-plugin/plugin.json
git commit -m "feat(growth): register session-tracker and pr-attribution hooks in plugin.json"
```

---

## Task 6: Manual integration smoke test

**No code changes — verification only.**

- [ ] **Step 1: Start a new Claude Code session**

Open Claude Code in this repo. The session-tracker hook will now fire on every tonone skill invocation.

- [ ] **Step 2: Invoke any tonone skill** (e.g., `/relay-recon` or `/atlas-map`)

Expected: `.claude/session-agents` now contains the agent name:
```bash
cat .claude/session-agents
# → relay
```

- [ ] **Step 3: Create a test PR**

In a feature branch with a harmless change, run `gh pr create` (or `/relay-ship`).

Expected: PR description contains attribution block at the bottom:
```
---
*Relay — [tonone](https://second.tonone.ai)*
```

- [ ] **Step 4: Verify session-agents cleared**

```bash
cat .claude/session-agents
# → (empty)
```

- [ ] **Step 5: Close the test PR**

```bash
gh pr close <url> --delete-branch
```
