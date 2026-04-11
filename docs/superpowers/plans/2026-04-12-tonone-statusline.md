# Tonone Statusline Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a single-line statusline for tonone that shows git branch, dirty count, active agent + subagent count, token consumption, session cost, context bar, and rate limit — with progressive disclosure and color coding.

**Architecture:** A Node.js statusline script reads JSON from stdin (piped by Claude Code) and git state via `execSync`. A PostToolUse hook on `Agent` tool writes subagent counts to a bridge file. A post_install hook backs up any existing statusline config and patches `~/.claude/settings.json` to point at the tonone script.

**Tech Stack:** Node.js (no dependencies), `child_process.execSync` for git, ANSI escape codes for color.

---

## File Map

| Action | Path                            | Responsibility                                                            |
| ------ | ------------------------------- | ------------------------------------------------------------------------- |
| Create | `hooks/tonone-statusline.js`    | Main statusline script — reads stdin JSON + git, renders single line      |
| Create | `hooks/tonone-agent-tracker.js` | PostToolUse hook — tracks active subagent count in bridge file            |
| Create | `hooks/install-statusline.sh`   | post_install script — backs up existing statusline, patches settings.json |
| Create | `hooks/hooks.json`              | Root-level hook definitions (Setup + PostToolUse)                         |
| Modify | `.claude-plugin/plugin.json`    | Add `"hooks"` field pointing to `hooks/hooks.json`                        |

## Chunk 1: Statusline Script

### Task 1: Create the statusline script

**Files:**

- Create: `hooks/tonone-statusline.js`

- [ ] **Step 1: Create the script with stdin JSON parsing**

```js
#!/usr/bin/env node
// tonone-statusline — single-line status for Claude Code
// Shows: branch, dirty count, agent+subagents, tokens, cost, context bar, rate limit

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

let input = "";
const stdinTimeout = setTimeout(() => process.exit(0), 3000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  clearTimeout(stdinTimeout);
  try {
    const data = JSON.parse(input);
    process.stdout.write(render(data));
  } catch (e) {
    // Silent fail — never break the statusline
  }
});
```

- [ ] **Step 2: Add ANSI color helpers**

```js
// ANSI helpers
const c = {
  reset: "\x1b[0m",
  dim: "\x1b[2m",
  bold: "\x1b[1m",
  blink: "\x1b[5m",
  cyan: "\x1b[36m",
  yellow: "\x1b[33m",
  green: "\x1b[32m",
  red: "\x1b[31m",
  magenta: "\x1b[35m",
  orange: "\x1b[38;5;208m",
  dimWhite: "\x1b[2;37m",
};
```

- [ ] **Step 3: Add git segment functions**

```js
function gitBranch(cwd) {
  try {
    return execSync("git rev-parse --abbrev-ref HEAD", {
      cwd,
      encoding: "utf8",
      timeout: 1000,
      stdio: ["pipe", "pipe", "pipe"],
    }).trim();
  } catch {
    return "";
  }
}

function gitDirtyCount(cwd) {
  try {
    const out = execSync("git status --porcelain", {
      cwd,
      encoding: "utf8",
      timeout: 2000,
      stdio: ["pipe", "pipe", "pipe"],
    });
    return out.trim() ? out.trim().split("\n").length : 0;
  } catch {
    return 0;
  }
}
```

- [ ] **Step 4: Add token formatting helper**

```js
function fmtTokens(n) {
  if (n == null || n === 0) return null; // Hidden at 0 — progressive disclosure
  if (n < 1000) return `${n} tk`;
  if (n < 1_000_000) return `${(n / 1000).toFixed(1).replace(/\.0$/, "")}k tk`;
  return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, "")}M tk`;
}
```

- [ ] **Step 5: Add cost formatting helper**

```js
function fmtCost(usd) {
  if (usd == null) return "";
  if (usd === 0) return "";
  if (usd < 0.01) return `$${usd.toFixed(3)}`;
  return `$${usd.toFixed(2)}`;
}
```

- [ ] **Step 6: Add relative time helper**

```js
function fmtRelativeTime(isoTimestamp) {
  if (!isoTimestamp) return "";
  const diff = new Date(isoTimestamp).getTime() - Date.now();
  if (diff <= 0) return "now";
  const mins = Math.ceil(diff / 60000);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  const rem = mins % 60;
  return rem > 0 ? `${hrs}h${rem}m` : `${hrs}h`;
}
```

- [ ] **Step 7: Add subagent bridge file reader**

```js
function readSubagentCount(sessionId) {
  if (!sessionId || /[/\\]|\.\./.test(sessionId)) return 0;
  try {
    const bridgePath = path.join(
      os.tmpdir(),
      `tonone-agents-${sessionId}.json`,
    );
    const data = JSON.parse(fs.readFileSync(bridgePath, "utf8"));
    // Only count agents active in the last 5 minutes
    const cutoff = Date.now() - 300_000;
    const active = (data.agents || []).filter(
      (a) => a.started > cutoff && !a.finished,
    );
    return active.length;
  } catch {
    return 0;
  }
}
```

- [ ] **Step 8: Add context bar renderer**

```js
function renderContextBar(remaining) {
  if (remaining == null) return "";

  const AUTO_COMPACT_BUFFER_PCT = 16.5;
  const usableRemaining = Math.max(
    0,
    ((remaining - AUTO_COMPACT_BUFFER_PCT) / (100 - AUTO_COMPACT_BUFFER_PCT)) *
      100,
  );
  const used = Math.max(0, Math.min(100, Math.round(100 - usableRemaining)));
  const pctLeft = 100 - used;

  const filled = Math.floor(used / 10);
  const bar = "\u2588".repeat(filled) + "\u2591".repeat(10 - filled);

  let warning = "";
  let color;
  if (pctLeft > 50) {
    color = c.green;
  } else if (pctLeft > 25) {
    color = c.yellow;
  } else if (pctLeft > 10) {
    color = c.red;
    warning = " \u26a0";
  } else {
    color = `${c.blink}${c.red}`;
    warning = " \u26a0 compact soon";
  }

  return `${color}${bar} ${pctLeft}%${warning}${c.reset}`;
}
```

- [ ] **Step 9: Add rate limit renderer**

```js
function renderRateLimit(rateLimits) {
  if (!rateLimits?.five_hour) return "";
  const used = rateLimits.five_hour.used_percentage;
  if (used == null || used < 50) return "";

  const resetsAt = rateLimits.five_hour.resets_at;
  const rel = fmtRelativeTime(resetsAt);

  let color;
  if (used < 70) color = c.green;
  else if (used < 90) color = c.yellow;
  else color = `${c.blink}${c.red}`;

  // Only show reset time when usage is concerning (>70%)
  const resetStr = used >= 70 && rel ? ` \u21bb${rel}` : "";
  return `${color}\u25ce${Math.round(used)}%${resetStr}${c.reset}`;
}
```

- [ ] **Step 10: Write the main render function**

```js
function render(data) {
  const cwd = data.workspace?.current_dir || process.cwd();
  const session = data.session_id || "";

  const segments = [];

  // 1. Branch (cyan, always shown)
  const branch = gitBranch(cwd);
  if (branch) {
    segments.push(`${c.cyan}\u25c6 ${branch}${c.reset}`);
  }

  // 2. Dirty count (yellow, hidden when clean)
  const dirty = gitDirtyCount(cwd);
  if (dirty > 0) {
    segments.push(`${c.yellow}\u25b2${dirty}${c.reset}`);
  }

  // 3. Agent + subagents (magenta when active)
  // Note: stdin JSON only provides agent.name, not the active skill.
  // Skill suffix (e.g. "spine:perf") deferred to future version if Claude Code adds it.
  const agentName = data.agent?.name;
  if (agentName) {
    let agentStr = `${c.magenta}${c.bold}${agentName}${c.reset}`;
    const subCount = readSubagentCount(session);
    if (subCount > 0) {
      agentStr += ` ${c.magenta}\u2295${subCount}${c.reset}`;
    }
    segments.push(agentStr);
  }

  // 4. Tokens (dim white, hidden when 0 — progressive disclosure)
  const totalTokens =
    (data.total_input_tokens || 0) + (data.total_output_tokens || 0);
  const tokenStr = fmtTokens(totalTokens);
  if (tokenStr) segments.push(`${c.dimWhite}${tokenStr}${c.reset}`);

  // 5. Cost (hidden when $0, yellow >$1, red >$5)
  const cost = fmtCost(data.cost?.total_cost_usd);
  if (cost) {
    const costVal = data.cost.total_cost_usd;
    let costColor = c.dimWhite;
    if (costVal > 5) costColor = c.red;
    else if (costVal > 1) costColor = c.yellow;
    segments.push(`${costColor}${cost}${c.reset}`);
  }

  // 6. Context bar (always shown, color escalates)
  const ctxBar = renderContextBar(data.context_window?.remaining_percentage);
  if (ctxBar) segments.push(ctxBar);

  // 7. Rate limit (hidden when <50%)
  const rateLimit = renderRateLimit(data.rate_limits);
  if (rateLimit) segments.push(rateLimit);

  return segments.join(` ${c.dim}\u2502${c.reset} `);
}
```

- [ ] **Step 11: Run the script manually to verify it doesn't crash**

Run: `echo '{"model":{"display_name":"Opus"},"workspace":{"current_dir":"/tmp"},"context_window":{"remaining_percentage":60},"total_input_tokens":42000,"total_output_tokens":8000,"cost":{"total_cost_usd":0.38}}' | node hooks/tonone-statusline.js`

Expected: Colored single-line output with branch, tokens, cost, context bar.

- [ ] **Step 12: Commit**

```bash
git add hooks/tonone-statusline.js
git commit -m "feat: add tonone statusline script with progressive disclosure"
```

---

### Task 2: Create the subagent tracker hook

**Files:**

- Create: `hooks/tonone-agent-tracker.js`

- [ ] **Step 1: Write the tracker script**

This runs as a PostToolUse hook on the `Agent` tool. It receives tool input/output via stdin JSON and updates a bridge file with active subagent state.

```js
#!/usr/bin/env node
// tonone-agent-tracker — PostToolUse hook for Agent tool
// Tracks active subagents in a bridge file for the statusline to read

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
    const session = data.session_id;
    if (!session || /[/\\]|\.\./.test(session)) process.exit(0);

    const bridgePath = path.join(os.tmpdir(), `tonone-agents-${session}.json`);

    // Read existing state
    let state = { agents: [] };
    try {
      state = JSON.parse(fs.readFileSync(bridgePath, "utf8"));
    } catch {}

    const toolInput = data.tool_input || {};
    const toolOutput = data.tool_output || {};

    // Agent tool was invoked — a subagent started or completed
    const agentDesc =
      toolInput.description || toolInput.prompt?.slice(0, 40) || "agent";
    const agentId = toolOutput.agentId || `anon-${Date.now()}`;

    // Check if this is a completion (output has result) or start (output has agentId only)
    const isCompletion = !toolOutput.agentId || toolOutput.output;

    if (isCompletion) {
      // Mark matching agent as finished
      const match = state.agents.find(
        (a) => a.id === agentId || a.desc === agentDesc,
      );
      if (match) match.finished = Date.now();
    } else {
      // New agent started
      state.agents.push({
        id: agentId,
        desc: agentDesc,
        started: Date.now(),
        finished: null,
      });
    }

    // Prune agents older than 10 minutes
    const cutoff = Date.now() - 600_000;
    state.agents = state.agents.filter((a) => a.started > cutoff);

    // Atomic write — temp file + rename to prevent race conditions
    const tmpPath = bridgePath + ".tmp." + process.pid;
    fs.writeFileSync(tmpPath, JSON.stringify(state));
    fs.renameSync(tmpPath, bridgePath);
  } catch {
    // Silent fail
  }
});
```

- [ ] **Step 2: Verify script doesn't crash on empty input**

Run: `echo '{}' | node hooks/tonone-agent-tracker.js && echo "ok"`

Expected: exits cleanly, prints "ok"

- [ ] **Step 3: Commit**

```bash
git add hooks/tonone-agent-tracker.js
git commit -m "feat: add subagent tracker PostToolUse hook"
```

---

## Chunk 2: Installation Hook + Root Hooks Config

### Task 3: Create the install script

**Files:**

- Create: `hooks/install-statusline.sh`

- [ ] **Step 1: Write the install script**

This runs at post_install. Backs up existing statusline config, installs tonone's.

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STATUSLINE_SCRIPT="$SCRIPT_DIR/tonone-statusline.js"

# Resolve settings.json location
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

# Ensure settings file exists
if [ ! -f "$SETTINGS_FILE" ]; then
  echo "{}" > "$SETTINGS_FILE"
fi

# Read current statusline command (if any)
CURRENT_SL=""
if command -v node &>/dev/null; then
  CURRENT_SL=$(node -e "
    try {
      const s = JSON.parse(require('fs').readFileSync('$SETTINGS_FILE', 'utf8'));
      if (s.statusLine?.command) console.log(s.statusLine.command);
    } catch {}
  " 2>/dev/null || true)
fi

# Backup if different statusline exists
if [ -n "$CURRENT_SL" ] && [ "$CURRENT_SL" != "node \"$STATUSLINE_SCRIPT\"" ]; then
  BACKUP_DIR="$CLAUDE_DIR/statusline-backup"
  mkdir -p "$BACKUP_DIR"
  TIMESTAMP=$(date +%Y%m%d-%H%M%S)

  # Save the old command reference
  echo "$CURRENT_SL" > "$BACKUP_DIR/command-$TIMESTAMP.txt"

  # If it points to a file, copy that too
  OLD_FILE=$(echo "$CURRENT_SL" | sed 's/^node "\{0,1\}//;s/"\{0,1\}$//')
  if [ -f "$OLD_FILE" ]; then
    cp "$OLD_FILE" "$BACKUP_DIR/script-$TIMESTAMP.js"
  fi

  echo "tonone: backed up existing statusline to $BACKUP_DIR/"
fi

# Patch settings.json with tonone statusline
if command -v node &>/dev/null; then
  node -e "
    const fs = require('fs');
    const settings = JSON.parse(fs.readFileSync('$SETTINGS_FILE', 'utf8'));
    settings.statusLine = {
      type: 'command',
      command: 'node \"$STATUSLINE_SCRIPT\"'
    };
    fs.writeFileSync('$SETTINGS_FILE', JSON.stringify(settings, null, 2) + '\n');
  "
  echo "tonone: statusline installed"
else
  echo "tonone: WARNING — node not found, statusline not installed"
fi
```

- [ ] **Step 2: Make it executable**

Run: `chmod +x hooks/install-statusline.sh`

- [ ] **Step 3: Commit**

```bash
git add hooks/install-statusline.sh
git commit -m "feat: add statusline install script with backup"
```

---

### Task 4: Create root hooks.json

**Files:**

- Create: `hooks/hooks.json`

- [ ] **Step 1: Write the hooks configuration**

```json
{
  "hooks": {
    "Setup": [
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
      }
    ]
  }
}
```

- [ ] **Step 2: Verify JSON is valid**

Run: `node -e "JSON.parse(require('fs').readFileSync('hooks/hooks.json','utf8')); console.log('valid')"`

Expected: `valid`

- [ ] **Step 3: Wire hooks.json into plugin.json**

Modify `.claude-plugin/plugin.json` to add the hooks reference:

```json
{
  "name": "tonone",
  "description": "Engineering + Product team — 23 agents as Claude Code specialists. Infrastructure, DevOps, backend, security, ML/AI, mobile, UX, analytics, growth, strategy, and more.",
  "version": "0.6.4",
  "author": { "name": "tonone-ai", "url": "https://tonone.ai" },
  "repository": "https://github.com/tonone-ai/tonone",
  "license": "MIT",
  "hooks": "hooks/hooks.json",
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
  ]
}
```

The key change: add `"hooks": "hooks/hooks.json"` field.

- [ ] **Step 4: Commit**

```bash
git add hooks/hooks.json .claude-plugin/plugin.json
git commit -m "feat: add root hooks.json with statusline install + agent tracker"
```

---

### Task 5: Smoke test the full flow

> **Note:** Run Step 1 (bridge file) first so Step 2 (statusline with agent) can read the subagent count.

- [ ] **Step 1: Create bridge file for subagent test**

Run:

```bash
echo '{"session_id":"smoke-test","tool_input":{"description":"Research task"},"tool_output":{"agentId":"abc123"}}' | node hooks/tonone-agent-tracker.js
cat /tmp/tonone-agents-smoke-test.json
```

Expected: JSON with one agent entry, `finished: null`.

- [ ] **Step 2: Test statusline with realistic JSON (reads bridge file)**

Run: `echo '{"model":{"display_name":"Opus 4.6"},"workspace":{"current_dir":"'$(pwd)'"},"session_id":"smoke-test","context_window":{"remaining_percentage":45},"total_input_tokens":142000,"total_output_tokens":38000,"cost":{"total_cost_usd":1.72},"rate_limits":{"five_hour":{"used_percentage":65,"resets_at":"'$(date -u -v+90M +%Y-%m-%dT%H:%M:%SZ)'"}},"agent":{"name":"spine"}}' | node hooks/tonone-statusline.js`

Expected: `◆ main ▲N │ spine ⊕1 │ 180k tk │ $1.72 │ ██████░░░░ 34% │ ◎65%`

- [ ] **Step 3: Test with minimal JSON (progressive disclosure)**

Run: `echo '{"model":{"display_name":"Sonnet"},"workspace":{"current_dir":"/tmp"}}' | node hooks/tonone-statusline.js`

Expected: Minimal output — just branch and context bar. No tokens, no cost, no agent, no rate limit.

- [ ] **Step 4: Test install script in dry-run mode (inspect output)**

Run: `bash -x hooks/install-statusline.sh 2>&1 | head -20`

Expected: Shows backup detection, settings.json patching steps.

- [ ] **Step 5: Clean up smoke test artifacts**

Run: `rm -f /tmp/tonone-agents-smoke-test.json`

- [ ] **Step 6: Final commit if any fixes needed**

```bash
git add -A hooks/
git commit -m "fix: statusline smoke test fixes"
```
