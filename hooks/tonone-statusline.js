#!/usr/bin/env node
"use strict";

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const os = require("os");

// ── ANSI color helpers ────────────────────────────────────────────────────────

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

// ── Git helpers ───────────────────────────────────────────────────────────────

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

// ── Formatters ────────────────────────────────────────────────────────────────

function fmtTokens(n) {
  if (n == null || n === 0) return null;
  if (n < 1000) return `${n} tk`;
  if (n < 1_000_000) return `${(n / 1000).toFixed(1).replace(/\.0$/, "")}k tk`;
  return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, "")}M tk`;
}

function fmtCost(usd) {
  if (usd == null) return null;
  if (usd === 0) return null;
  if (usd < 0.01) return `$${usd.toFixed(3)}`;
  return `$${usd.toFixed(2)}`;
}

function fmtDuration(ms) {
  if (ms == null || ms <= 0) return null;
  const totalSec = Math.floor(ms / 1000);
  if (totalSec < 60) return `${totalSec}s`;
  const mins = Math.floor(totalSec / 60);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  const rem = mins % 60;
  return rem > 0 ? `${hrs}h${rem}m` : `${hrs}h`;
}

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

// ── Subagent bridge ───────────────────────────────────────────────────────────

function readSubagentCount(sessionId) {
  if (!sessionId || /[/\\]|\.\./.test(sessionId)) return 0;
  try {
    const bridgePath = path.join(
      os.tmpdir(),
      `tonone-agents-${sessionId}.json`,
    );
    const data = JSON.parse(fs.readFileSync(bridgePath, "utf8"));
    const cutoff = Date.now() - 300_000;
    const active = (data.agents || []).filter(
      (a) => a.started > cutoff && !a.finished,
    );
    return active.length;
  } catch {
    return 0;
  }
}

// ── Context bar ───────────────────────────────────────────────────────────────

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

// ── Rate limit ────────────────────────────────────────────────────────────────

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
  const resetStr = used >= 70 && rel ? ` \u21bb${rel}` : "";
  return `${color}\u25ce${Math.round(used)}%${resetStr}${c.reset}`;
}

// ── Main render ───────────────────────────────────────────────────────────────

function render(data) {
  const cwd = data.workspace?.current_dir || process.cwd();
  const session = data.session_id || "";
  const segments = [];

  // 1. Branch + ahead count (cyan, always shown)
  const branch = gitBranch(cwd);
  if (branch) {
    const ahead = gitAhead(cwd);
    const aheadStr = ahead > 0 ? ` ${c.green}\u2191${ahead}${c.reset}` : "";
    segments.push(`${c.cyan}\u25c6 ${branch}${c.reset}${aheadStr}`);
  }

  // 2. Dirty count (yellow, hidden when clean)
  const dirty = gitDirtyCount(cwd);
  if (dirty > 0) segments.push(`${c.yellow}\u25b2${dirty}${c.reset}`);

  // 3. Agent name (magenta, hidden when no agent active)
  const agentName = data.agent?.name;
  if (agentName) {
    segments.push(`${c.magenta}${c.bold}${agentName}${c.reset}`);
  }

  // 4. Subagent count (hidden when 0, independent of agent name)
  const subCount = readSubagentCount(session);
  if (subCount > 0) {
    const label = agentName ? `\u2295${subCount}` : `\u2295${subCount} agents`;
    segments.push(`${c.magenta}${label}${c.reset}`);
  }

  // 5. Tokens (hidden when 0)
  const totalTokens =
    (data.total_input_tokens || 0) + (data.total_output_tokens || 0);
  const tokenStr = fmtTokens(totalTokens);
  if (tokenStr) segments.push(`${c.dimWhite}${tokenStr}${c.reset}`);

  // 6. Cost (hidden when $0, yellow >$1, red >$5)
  const cost = fmtCost(data.cost?.total_cost_usd);
  if (cost) {
    const costVal = data.cost.total_cost_usd;
    let costColor = c.dimWhite;
    if (costVal > 5) costColor = c.red;
    else if (costVal > 1) costColor = c.yellow;
    segments.push(`${costColor}${cost}${c.reset}`);
  }

  // 7. Context bar (always shown)
  const ctxBar = renderContextBar(data.context_window?.remaining_percentage);
  if (ctxBar) segments.push(ctxBar);

  // 8. Rate limit (hidden when <50%)
  const rateLimit = renderRateLimit(data.rate_limits);
  if (rateLimit) segments.push(rateLimit);

  const line1 = segments.join(` ${c.dim}\u2502${c.reset} `);

  // ── Line 2: model + usage windows ──────────────────────────────────────────
  const line2Parts = [];

  // Model name (always shown when available)
  const modelName = data.model?.display_name;
  if (modelName) {
    line2Parts.push(`${c.dimWhite}${modelName}${c.reset}`);
  }

  // Session duration
  const duration = fmtDuration(data.cost?.total_duration_ms);
  if (duration) {
    line2Parts.push(`${c.dimWhite}${duration}${c.reset}`);
  }

  // Lines changed (+N -N)
  const added = data.cost?.total_lines_added || 0;
  const removed = data.cost?.total_lines_removed || 0;
  if (added > 0 || removed > 0) {
    let linesStr = "";
    if (added > 0) linesStr += `${c.green}+${added}${c.reset}`;
    if (added > 0 && removed > 0) linesStr += " ";
    if (removed > 0) linesStr += `${c.red}-${removed}${c.reset}`;
    line2Parts.push(linesStr);
  }

  // Cost per line (wow metric — hidden when no lines or no cost)
  const totalLines = added + removed;
  const totalCost = data.cost?.total_cost_usd || 0;
  if (totalLines > 0 && totalCost > 0) {
    const cpl = totalCost / totalLines;
    const cplStr =
      cpl < 0.001
        ? `$${(cpl * 1000).toFixed(1)}\u00d710\u207b\u00b3`
        : `$${cpl.toFixed(3)}`;
    line2Parts.push(`${c.dimWhite}${cplStr}/line${c.reset}`);
  }

  // 5-hour usage
  const fiveH = data.rate_limits?.five_hour;
  if (fiveH?.used_percentage != null) {
    const pct = Math.round(fiveH.used_percentage);
    let col = c.dimWhite;
    if (pct >= 90) col = `${c.blink}${c.red}`;
    else if (pct >= 70) col = c.yellow;
    line2Parts.push(`${col}5h: ${pct}%${c.reset}`);
  }

  // 7-day (weekly) usage
  const sevenD = data.rate_limits?.seven_day;
  if (sevenD?.used_percentage != null) {
    const pct = Math.round(sevenD.used_percentage);
    let col = c.dimWhite;
    if (pct >= 90) col = `${c.blink}${c.red}`;
    else if (pct >= 70) col = c.yellow;
    line2Parts.push(`${col}7d: ${pct}%${c.reset}`);
  }

  if (line2Parts.length === 0) return line1;

  const line2 = line2Parts.join(` ${c.dim}\u2502${c.reset} `);
  return `${line1}\n${line2}`;
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
