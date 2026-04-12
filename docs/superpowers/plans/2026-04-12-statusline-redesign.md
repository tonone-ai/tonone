# Statusline Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the two-line statusline into a three-line design with semantic grouping, micro-labels, static fields, subagent names, model routing display, and pace projection for rate limits.

**Architecture:** Single-file rewrite of `hooks/tonone-statusline.js` (Node.js, reads JSON from stdin, outputs ANSI text). Small addition to `hooks/tonone-agent-tracker.js` to capture subagent model. New pace bridge file created at runtime in `/tmp/`.

**Tech Stack:** Node.js (no dependencies), ANSI escape codes, child_process for git, fs for bridge files.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `hooks/tonone-agent-tracker.js` | Modify | Add `model` field from `tool_input.model` to agent entries |
| `hooks/tonone-statusline.js` | Rewrite | Full rewrite: 3-line render, pace calculation, static fields |
| `hooks/test-statusline.sh` | Create | Test runner — pipes JSON fixtures through statusline |

---

### Task 1: Add model field to agent tracker

**Files:**
- Modify: `hooks/tonone-agent-tracker.js:38-50`

- [ ] **Step 1: Add model capture to agent start block**

In `hooks/tonone-agent-tracker.js`, replace the `isStart` block (lines 38-50):

```javascript
    if (isStart) {
      // New agent started
      state = {
        ...state,
        agents: [
          ...state.agents,
          {
            id: toolOutput.agentId,
            desc: agentDesc,
            started: Date.now(),
            finished: null,
          },
        ],
      };
```

With:

```javascript
    if (isStart) {
      // New agent started
      const agentModel = toolInput.model || null;
      state = {
        ...state,
        agents: [
          ...state.agents,
          {
            id: toolOutput.agentId,
            desc: agentDesc,
            model: agentModel,
            started: Date.now(),
            finished: null,
          },
        ],
      };
```

- [ ] **Step 2: Commit**

```bash
git add hooks/tonone-agent-tracker.js
git commit -m "feat(statusline): track subagent model in bridge file"
```

---

### Task 2: Rewrite statusline — colors, formatters, and git helpers

**Files:**
- Modify: `hooks/tonone-statusline.js:1-104`

- [ ] **Step 1: Replace the entire top section (lines 1-104) with updated helpers**

Replace everything from line 1 through the end of `fmtRelativeTime` (line 104) with:

```javascript
#!/usr/bin/env node
"use strict";

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

// ── ANSI helpers ─────────────────────────────────────────────────────────────

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
  dimWhite: "\x1b[2;37m",
};

const SEP = ` ${c.dim}\u2502${c.reset} `;

// ── Git helpers ──────────────────────────────────────────────────────────────

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

function gitAhead(cwd) {
  try {
    const out = execSync("git rev-list --count @{u}..HEAD", {
      cwd,
      encoding: "utf8",
      timeout: 1000,
      stdio: ["pipe", "pipe", "pipe"],
    });
    return parseInt(out.trim(), 10) || 0;
  } catch {
    return 0;
  }
}

// ── Formatters ───────────────────────────────────────────────────────────────

function fmtDir(dir) {
  const home = os.homedir();
  let d = dir.startsWith(home) ? "~" + dir.slice(home.length) : dir;
  if (d.length > 40) {
    const parts = d.split("/");
    while (d.length > 40 && parts.length > 2) {
      parts.shift();
      d = "\u2026/" + parts.join("/");
    }
  }
  return d;
}

function fmtCost(usd) {
  if (usd == null || usd === 0) return "$0.00";
  if (usd < 0.01) return `$${usd.toFixed(3)}`;
  return `$${usd.toFixed(2)}`;
}

function fmtDuration(ms) {
  if (ms == null || ms <= 0) return "0m";
  const totalSec = Math.floor(ms / 1000);
  if (totalSec < 60) return `${totalSec}s`;
  const mins = Math.floor(totalSec / 60);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  const rem = mins % 60;
  return rem > 0 ? `${hrs}h${rem}m` : `${hrs}h`;
}
```

- [ ] **Step 2: Verify syntax**

```bash
node -c hooks/tonone-statusline.js
```

Expected: no output (syntax ok) — this will fail because the bottom half still references removed functions. That's fine, we're replacing it in the next tasks.

- [ ] **Step 3: Commit**

```bash
git add hooks/tonone-statusline.js
git commit -m "feat(statusline): rewrite helpers — fmtDir, static fmtCost/fmtDuration, drop tokens formatter"
```

---

### Task 3: Rewrite statusline — subagent reader, pace bridge, and pace computation

**Files:**
- Modify: `hooks/tonone-statusline.js:106-172` (replace old subagent reader, context bar, and rate limit renderer)

- [ ] **Step 1: Replace lines 106-172 (old subagent reader, context bar, rate limit) with new sections**

Replace everything from the `// ── Subagent bridge` comment through the end of `renderRateLimit` with:

```javascript
// ── Subagent bridge ──────────────────────────────────────────────────────────

function readSubagents(sessionId) {
  if (!sessionId || /[/\\]|\.\./.test(sessionId)) return [];
  try {
    const bridgePath = path.join(
      os.tmpdir(),
      `tonone-agents-${sessionId}.json`,
    );
    const data = JSON.parse(fs.readFileSync(bridgePath, "utf8"));
    const cutoff = Date.now() - 300_000;
    return (data.agents || []).filter((a) => a.started > cutoff && !a.finished);
  } catch {
    return [];
  }
}

// ── Pace bridge ──────────────────────────────────────────────────────────────

function readOrCreatePaceBridge(sessionId, fiveHourPct, sevenDayPct) {
  if (!sessionId || /[/\\]|\.\./.test(sessionId)) return null;
  const bridgePath = path.join(os.tmpdir(), `tonone-pace-${sessionId}.json`);
  try {
    const data = JSON.parse(fs.readFileSync(bridgePath, "utf8"));
    if (data.session_id === sessionId) {
      // Window reset during session — burn went negative, re-initialize
      const fiveReset =
        fiveHourPct != null && fiveHourPct < data.start_5h_pct;
      const sevenReset =
        sevenDayPct != null && sevenDayPct < data.start_7d_pct;
      if (!fiveReset && !sevenReset) return data;
    }
  } catch {}
  // Create fresh bridge file
  const bridge = {
    session_id: sessionId,
    start_time: Date.now(),
    start_5h_pct: fiveHourPct || 0,
    start_7d_pct: sevenDayPct || 0,
  };
  try {
    const tmpPath = bridgePath + ".tmp." + process.pid;
    fs.writeFileSync(tmpPath, JSON.stringify(bridge));
    fs.renameSync(tmpPath, bridgePath);
  } catch {}
  return bridge;
}

// ── Pace computation ─────────────────────────────────────────────────────────

function computePace(currentPct, startPct, startTime, resetsAt) {
  const now = Date.now();
  const sessionElapsedHours = (now - startTime) / 3_600_000;

  // Not enough data yet (< 2 minutes)
  if (sessionElapsedHours < 2 / 60) {
    return { verdict: "--", color: c.dim, multiplier: null };
  }

  // Missing or past reset time
  if (!resetsAt) {
    return { verdict: "--", color: c.dim, multiplier: null };
  }
  const resetsAtMs = new Date(resetsAt).getTime();
  const timeRemainingHours = (resetsAtMs - now) / 3_600_000;
  if (timeRemainingHours <= 0) {
    return { verdict: "--", color: c.dim, multiplier: null };
  }

  const sessionBurn = Math.max(0, currentPct - startPct);
  const burnRate = sessionBurn / sessionElapsedHours;

  // Zero burn — session hasn't consumed any of this window
  if (burnRate === 0) {
    return { verdict: "ok", color: c.green, multiplier: 0.0 };
  }

  const projectedAdditional = burnRate * timeRemainingHours;
  const projectedTotal = currentPct + projectedAdditional;

  const safeRate = (100 - currentPct) / timeRemainingHours;
  const multiplier = safeRate > 0 ? burnRate / safeRate : 99.9;

  if (projectedTotal <= 80) {
    return { verdict: "ok", color: c.green, multiplier };
  }
  if (projectedTotal <= 100) {
    return { verdict: "tight", color: c.yellow, multiplier };
  }

  // Will overshoot — show time to impact
  const hoursToImpact = (100 - currentPct) / burnRate;
  const minsToImpact = Math.round(hoursToImpact * 60);
  const timeStr =
    minsToImpact >= 60
      ? `~${Math.floor(minsToImpact / 60)}h`
      : `~${minsToImpact}m`;
  return { verdict: timeStr, color: c.red, multiplier };
}

function renderPace(label, currentPct, startPct, startTime, resetsAt) {
  if (currentPct == null) {
    return `${c.dim}${label}: 0% --${c.reset}`;
  }
  const pct = Math.round(currentPct);
  const pace = computePace(currentPct, startPct, startTime, resetsAt);
  if (pace.multiplier == null) {
    return `${c.dim}${label}: ${pct}% --${c.reset}`;
  }
  const mulStr = `${pace.multiplier.toFixed(1)}\u00d7`;
  return `${pace.color}${label}: ${pct}% ${pace.verdict} ${mulStr}${c.reset}`;
}

// ── Context bar ──────────────────────────────────────────────────────────────

function renderContextBar(remaining) {
  const EMPTY_BAR = "\u2591".repeat(10);
  if (remaining == null) {
    return `${c.dim}${EMPTY_BAR} 100%${c.reset}`;
  }
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
  } else {
    color = `${c.blink}${c.red}`;
    warning = " compact soon";
  }
  return `${color}${bar} ${pctLeft}%${warning}${c.reset}`;
}

// ── Model display ────────────────────────────────────────────────────────────

function renderModel(mainDisplayName, activeSubagents) {
  const name = mainDisplayName || "unknown";
  const mainLower = name.toLowerCase();

  // Collect unique sub models that differ from the main model
  const subModels = [
    ...new Set(
      activeSubagents
        .map((a) => a.model)
        .filter((m) => m && !mainLower.includes(m.toLowerCase())),
    ),
  ];

  if (subModels.length === 0) {
    return `${c.dimWhite}${name}${c.reset}`;
  }

  // Capitalize sub model names, e.g. "sonnet" → "Sonnet"
  const subStr = subModels
    .map((m) => m.charAt(0).toUpperCase() + m.slice(1))
    .join(", ");
  // Shorten main to first word, e.g. "Opus 4.6" → "Opus"
  const mainShort = name.split(" ")[0];
  return `${c.dimWhite}${mainShort} ${c.dim}\u2192${c.reset} ${c.dimWhite}${subStr}${c.reset}`;
}
```

- [ ] **Step 2: Verify syntax**

```bash
node -c hooks/tonone-statusline.js
```

Expected: still fails (render function not yet replaced). That's expected.

- [ ] **Step 3: Commit**

```bash
git add hooks/tonone-statusline.js
git commit -m "feat(statusline): add pace bridge, pace computation, model display, rewrite subagent reader"
```

---

### Task 4: Rewrite statusline — render function and stdin reader

**Files:**
- Modify: `hooks/tonone-statusline.js:174-311` (replace old render function and stdin reader)

- [ ] **Step 1: Replace everything from `// ── Main render` to end of file with new render function**

Replace from line 174 (`// ── Main render`) through line 311 (end of file) with:

```javascript
// ── Main render ──────────────────────────────────────────────────────────────

function render(data) {
  const cwd = data.workspace?.current_dir || process.cwd();
  const session = data.session_id || "";

  // ── Line 1: Location & Git ──────────────────────────────────────────────
  const dir = fmtDir(cwd);
  const branch = gitBranch(cwd);
  const ahead = gitAhead(cwd);
  const dirty = gitDirtyCount(cwd);
  const added = data.cost?.total_lines_added || 0;
  const removed = data.cost?.total_lines_removed || 0;

  const dirStr = `${c.dimWhite}${dir}${c.reset}`;

  let branchStr = branch
    ? `${c.cyan}${branch}${c.reset}`
    : `${c.dim}no branch${c.reset}`;
  if (branch && ahead > 0) {
    branchStr += ` ${c.green}\u2191${ahead}${c.reset}`;
  }

  const dirtyStr =
    dirty > 0
      ? `${c.yellow}${dirty} dirty${c.reset}`
      : `${c.dim}clean${c.reset}`;

  const linesStr =
    added > 0 || removed > 0
      ? `${c.green}+${added}${c.reset} ${c.red}-${removed}${c.reset} ${c.dim}lines${c.reset}`
      : `${c.dim}+0 -0 lines${c.reset}`;

  const line1 = [dirStr, branchStr, dirtyStr, linesStr].join(SEP);

  // ── Line 2: Session Activity ────────────────────────────────────────────
  const agentName = data.agent?.name;
  const subagents = readSubagents(session);

  const agentStr = agentName
    ? `${c.magenta}${c.bold}${agentName}${c.reset}`
    : `${c.dim}idle${c.reset}`;

  let subsStr;
  if (subagents.length === 0) {
    subsStr = `${c.dim}no subs${c.reset}`;
  } else if (subagents.length <= 3) {
    const names = subagents
      .map((a) => (a.desc || "agent").slice(0, 20))
      .join(", ");
    subsStr = `${c.magenta}subs: ${names}${c.reset}`;
  } else {
    const names = subagents
      .slice(0, 2)
      .map((a) => (a.desc || "agent").slice(0, 20))
      .join(", ");
    subsStr = `${c.magenta}subs: ${names}, +${subagents.length - 2} more${c.reset}`;
  }

  const costVal = data.cost?.total_cost_usd || 0;
  let costColor = c.dimWhite;
  if (costVal > 5) costColor = c.red;
  else if (costVal > 1) costColor = c.yellow;
  const costStr = `${costColor}${fmtCost(costVal)}${c.reset}`;

  const durStr = `${c.dimWhite}${fmtDuration(data.cost?.total_duration_ms)}${c.reset}`;

  const line2 = [agentStr, subsStr, costStr, durStr].join(SEP);

  // ── Line 3: Model & Runway ──────────────────────────────────────────────
  const modelStr = renderModel(data.model?.display_name, subagents);
  const ctxBar = renderContextBar(data.context_window?.remaining_percentage);

  const fiveH = data.rate_limits?.five_hour;
  const sevenD = data.rate_limits?.seven_day;
  const paceBridge = readOrCreatePaceBridge(
    session,
    fiveH?.used_percentage,
    sevenD?.used_percentage,
  );
  const startTime = paceBridge?.start_time || Date.now();

  const fiveHStr = renderPace(
    "5h",
    fiveH?.used_percentage,
    paceBridge?.start_5h_pct || 0,
    startTime,
    fiveH?.resets_at,
  );

  const sevenDStr = renderPace(
    "7d",
    sevenD?.used_percentage,
    paceBridge?.start_7d_pct || 0,
    startTime,
    sevenD?.resets_at,
  );

  const line3 = [modelStr, ctxBar, fiveHStr, sevenDStr].join(SEP);

  return `${line1}\n${line2}\n${line3}`;
}

// ── Stdin reader with 3s timeout guard ───────────────────────────────────────

let input = "";
const stdinTimeout = setTimeout(() => process.exit(0), 3000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  input += chunk;
});
process.stdin.on("end", () => {
  clearTimeout(stdinTimeout);
  try {
    const data = JSON.parse(input);
    process.stdout.write(render(data));
  } catch (e) {}
});
```

- [ ] **Step 2: Verify full file parses**

```bash
node -c hooks/tonone-statusline.js
```

Expected: no output (clean parse).

- [ ] **Step 3: Commit**

```bash
git add hooks/tonone-statusline.js
git commit -m "feat(statusline): 3-line render — location/git, session, model/runway with pace"
```

---

### Task 5: Create test runner and verify all 7 states

**Files:**
- Create: `hooks/test-statusline.sh`

- [ ] **Step 1: Create the test script**

Create `hooks/test-statusline.sh`:

```bash
#!/usr/bin/env bash
# Test statusline rendering with JSON fixtures piped to stdin.
# Usage: bash hooks/test-statusline.sh
set -euo pipefail

SCRIPT="hooks/tonone-statusline.js"
PASS=0
FAIL=0

run_test() {
  local name="$1"
  local json="$2"
  shift 2
  local expected=("$@")

  echo "── $name ──"
  local output
  output=$(echo "$json" | node "$SCRIPT" 2>/dev/null) || true
  echo "$output"
  echo ""

  local ok=true
  for pattern in "${expected[@]}"; do
    # Strip ANSI codes for matching
    local stripped
    stripped=$(echo "$output" | sed 's/\x1b\[[0-9;]*m//g')
    if ! echo "$stripped" | grep -qF "$pattern"; then
      echo "  FAIL: expected '$pattern' not found"
      ok=false
    fi
  done

  if $ok; then
    echo "  PASS"
    ((PASS++))
  else
    ((FAIL++))
  fi
  echo ""
}

# State 1: Fresh session
run_test "Fresh session" '{
  "session_id": "test-fresh",
  "workspace": {"current_dir": "'"$HOME"'/repos/tn/tonone"},
  "model": {"display_name": "Opus 4.6"},
  "cost": {}
}' \
  "~/repos/tn/tonone" \
  "clean" \
  "+0 -0 lines" \
  "idle" \
  "no subs" \
  '$0.00' \
  "0m" \
  "Opus 4.6" \
  "5h: 0% --" \
  "7d: 0% --"

# State 2: Active session with agent (no subs)
run_test "Active session, no subs" '{
  "session_id": "test-active",
  "workspace": {"current_dir": "'"$HOME"'/repos/tn/tonone"},
  "agent": {"name": "spine"},
  "model": {"display_name": "Opus 4.6"},
  "cost": {"total_cost_usd": 0.38, "total_duration_ms": 1380000, "total_lines_added": 156, "total_lines_removed": 23},
  "context_window": {"remaining_percentage": 60},
  "rate_limits": {
    "five_hour": {"used_percentage": 24, "resets_at": "'"$(date -u -v+3H +%Y-%m-%dT%H:%M:%SZ)"'"},
    "seven_day": {"used_percentage": 41, "resets_at": "'"$(date -u -v+4d +%Y-%m-%dT%H:%M:%SZ)"'"}
  }
}' \
  "~/repos/tn/tonone" \
  "spine" \
  "no subs" \
  '$0.38' \
  "23m" \
  "+156" \
  "-23" \
  "lines" \
  "Opus 4.6" \
  "5h: 24%" \
  "7d: 41%"

# State 3: Warning state (high usage)
run_test "Warning state" '{
  "session_id": "test-warn",
  "workspace": {"current_dir": "'"$HOME"'/repos/tn/tonone"},
  "agent": {"name": "spine"},
  "model": {"display_name": "Opus 4.6"},
  "cost": {"total_cost_usd": 6.20, "total_duration_ms": 2880000, "total_lines_added": 420, "total_lines_removed": 87},
  "context_window": {"remaining_percentage": 30},
  "rate_limits": {
    "five_hour": {"used_percentage": 82, "resets_at": "'"$(date -u -v+2H +%Y-%m-%dT%H:%M:%SZ)"'"},
    "seven_day": {"used_percentage": 68, "resets_at": "'"$(date -u -v+3d +%Y-%m-%dT%H:%M:%SZ)"'"}
  }
}' \
  "spine" \
  '$6.20' \
  "48m" \
  "+420" \
  "-87" \
  "5h: 82%" \
  "7d: 68%"

# State 4: Critical state (context almost gone)
run_test "Critical state" '{
  "session_id": "test-critical",
  "workspace": {"current_dir": "'"$HOME"'/repos/tn/tonone"},
  "agent": {"name": "spine"},
  "model": {"display_name": "Opus 4.6"},
  "cost": {"total_cost_usd": 8.40, "total_duration_ms": 4320000, "total_lines_added": 520, "total_lines_removed": 110},
  "context_window": {"remaining_percentage": 18},
  "rate_limits": {
    "five_hour": {"used_percentage": 92, "resets_at": "'"$(date -u -v+1H +%Y-%m-%dT%H:%M:%SZ)"'"},
    "seven_day": {"used_percentage": 78, "resets_at": "'"$(date -u -v+2d +%Y-%m-%dT%H:%M:%SZ)"'"}
  }
}' \
  "spine" \
  '$8.40' \
  "1h12m" \
  "compact soon" \
  "5h: 92%" \
  "7d: 78%"

# State 5: Active session with subs on different model
# Pre-populate the agent bridge file so readSubagents finds active subs
AGENT_BRIDGE="$TMPDIR/tonone-agents-test-subs.json"
NOW_MS=$(node -e "process.stdout.write(String(Date.now()))")
cat > "$AGENT_BRIDGE" <<AGENT_EOF
{"agents":[
  {"id":"a1","desc":"audit pipeline","model":"sonnet","started":${NOW_MS},"finished":null},
  {"id":"a2","desc":"check deps","model":"sonnet","started":${NOW_MS},"finished":null}
]}
AGENT_EOF

run_test "Subs on different model" '{
  "session_id": "test-subs",
  "workspace": {"current_dir": "'"$HOME"'/repos/tn/tonone"},
  "agent": {"name": "apex"},
  "model": {"display_name": "Opus 4.6"},
  "cost": {"total_cost_usd": 1.50, "total_duration_ms": 900000, "total_lines_added": 80, "total_lines_removed": 12},
  "context_window": {"remaining_percentage": 55},
  "rate_limits": {
    "five_hour": {"used_percentage": 35, "resets_at": "'"$(date -u -v+4H +%Y-%m-%dT%H:%M:%SZ)"'"},
    "seven_day": {"used_percentage": 20, "resets_at": "'"$(date -u -v+5d +%Y-%m-%dT%H:%M:%SZ)"'"}
  }
}' \
  "apex" \
  "subs: audit pipeline, check deps" \
  "Opus" \
  "Sonnet" \
  '$1.50' \
  "15m"

rm -f "$AGENT_BRIDGE"

# State 6: Window reset during session (pace bridge re-initialization)
# Pre-populate pace bridge with start_5h_pct HIGHER than current — simulates window reset
PACE_BRIDGE="$TMPDIR/tonone-pace-test-reset.json"
cat > "$PACE_BRIDGE" <<PACE_EOF
{"session_id":"test-reset","start_time":${NOW_MS},"start_5h_pct":60.0,"start_7d_pct":50.0}
PACE_EOF

run_test "Window reset during session" '{
  "session_id": "test-reset",
  "workspace": {"current_dir": "'"$HOME"'/repos/tn/tonone"},
  "model": {"display_name": "Opus 4.6"},
  "cost": {"total_duration_ms": 600000},
  "rate_limits": {
    "five_hour": {"used_percentage": 5, "resets_at": "'"$(date -u -v+5H +%Y-%m-%dT%H:%M:%SZ)"'"},
    "seven_day": {"used_percentage": 10, "resets_at": "'"$(date -u -v+7d +%Y-%m-%dT%H:%M:%SZ)"'"}
  }
}' \
  "5h: 5%" \
  "7d: 10%"

rm -f "$PACE_BRIDGE"

# State 7: Long directory path (truncation)
run_test "Long directory path" '{
  "session_id": "test-longdir",
  "workspace": {"current_dir": "'"$HOME"'/very/deeply/nested/project/directory/structure/src"},
  "model": {"display_name": "Opus 4.6"},
  "cost": {}
}' \
  "idle" \
  "no subs" \
  "Opus 4.6"

# State 8: No rate limit data
run_test "No rate limits" '{
  "session_id": "test-norate",
  "workspace": {"current_dir": "'"$HOME"'/repos/tn/tonone"},
  "model": {"display_name": "Sonnet 4.6"},
  "cost": {"total_cost_usd": 0.05, "total_duration_ms": 120000}
}' \
  "Sonnet 4.6" \
  '$0.05' \
  "5h: 0% --" \
  "7d: 0% --"

echo "═══════════════════════════"
echo "Results: $PASS passed, $FAIL failed"
echo "═══════════════════════════"

[ "$FAIL" -eq 0 ] || exit 1
```

- [ ] **Step 2: Run the test script**

```bash
bash hooks/test-statusline.sh
```

Expected: All tests pass. Each test prints the rendered statusline (with ANSI colors visible) and checks that key strings appear in the output.

- [ ] **Step 3: Fix any failures**

If any test fails, check the `FAIL: expected '...' not found` output, read the relevant section of `hooks/tonone-statusline.js`, and fix.

- [ ] **Step 4: Verify the 3-line structure**

```bash
echo '{"session_id":"x","workspace":{"current_dir":"'"$HOME"'/repos/tn/tonone"},"model":{"display_name":"Opus 4.6"},"cost":{}}' | node hooks/tonone-statusline.js | wc -l
```

Expected: `3` (three lines of output).

- [ ] **Step 5: Commit**

```bash
git add hooks/test-statusline.sh hooks/tonone-statusline.js
git commit -m "test(statusline): add test runner, verify all 7 states"
```

---

### Task 6: Final cleanup and integration commit

- [ ] **Step 1: Verify the full statusline script parses cleanly**

```bash
node -c hooks/tonone-statusline.js && echo "OK"
```

Expected: `OK`

- [ ] **Step 2: Run tests one final time**

```bash
bash hooks/test-statusline.sh
```

Expected: All pass.

- [ ] **Step 3: Verify no leftover references to removed features**

Check that old symbols (◆, ▲, ⊕, ◎), `fmtTokens`, `renderRateLimit`, and `readSubagentCount` are gone:

```bash
grep -nE '\\u25c6|\\u25b2|\\u2295|\\u25ce|fmtTokens|renderRateLimit|readSubagentCount' hooks/tonone-statusline.js
```

Expected: no output (no matches).

- [ ] **Step 4: Confirm line count is reasonable**

```bash
wc -l hooks/tonone-statusline.js
```

Expected: ~280-320 lines (similar to before, reorganized).

- [ ] **Step 5: Squash into feature commit if desired, or leave as incremental commits**

The incremental commits from Tasks 1-5 tell a clean story. No squash needed unless preferred.
