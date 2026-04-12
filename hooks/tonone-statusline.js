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
