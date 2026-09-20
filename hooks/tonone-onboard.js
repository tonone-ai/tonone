#!/usr/bin/env node
"use strict";

// tonone-onboard — SessionStart hook
// Fires exactly once after install. Writes a marker to ~/.config/tonone/onboarded.
// On subsequent sessions exits silently. Never blocks the session on any error.
//
// The banner proposes a ROSTER, not the whole catalog. Project shape detection
// lives in lib/signals/project-shape.js and is shared with the skill gate, so
// both halves of onboarding read the same signals. If that module cannot be
// loaded, or its recommendation does not arrive in time, the original banner
// prints unchanged — the recommendation is an enhancement, never a dependency.

const fs = require("fs");
const os = require("os");
const path = require("path");

// ── Config ────────────────────────────────────────────────────────────────────

const PLUGIN_ROOT =
  process.env.CLAUDE_PLUGIN_ROOT || path.join(__dirname, "..");
const PLUGIN_JSON = path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json");
const MARKER_DIR = path.join(os.homedir(), ".config", "tonone");
const MARKER_FILE = path.join(MARKER_DIR, "onboarded");

// Hard ceiling on the recommendation. Past this the banner prints without it.
const SHAPE_BUDGET_MS = 2000;

// ── Helpers ───────────────────────────────────────────────────────────────────

function currentVersion() {
  try {
    return (
      JSON.parse(fs.readFileSync(PLUGIN_JSON, "utf8")).version || "unknown"
    );
  } catch {
    return "unknown";
  }
}

function isOnboarded() {
  try {
    return fs.existsSync(MARKER_FILE);
  } catch {
    return true; // fail-safe: don't re-show if we can't check
  }
}

function writeMarker(version, rosterId) {
  try {
    fs.mkdirSync(MARKER_DIR, { recursive: true });
    fs.writeFileSync(
      MARKER_FILE,
      JSON.stringify({
        version,
        ts: new Date().toISOString(),
        roster: rosterId || null,
      }),
    );
  } catch {
    // If write fails, hook exits 0 and retries next session — correct behavior.
  }
}

// Count what actually ships rather than hard-coding a number that goes stale.
function countDir(dir, predicate) {
  try {
    return fs.readdirSync(dir, { withFileTypes: true }).filter(predicate)
      .length;
  } catch {
    return 0;
  }
}

function inventory() {
  const agents = countDir(
    path.join(PLUGIN_ROOT, "agents"),
    (e) => e.isFile() && e.name.endsWith(".md"),
  );
  const skills = countDir(path.join(PLUGIN_ROOT, "skills"), (e) =>
    e.isDirectory(),
  );
  if (!agents || !skills) return "A full team of agents and skills.";
  return `${agents} agents, ${skills} skills. You need a handful:`;
}

// Resolve the roster recommendation, or null. Never throws, never outlives the
// budget, and never needs credentials: lib/signals scores deterministically and
// only consults lib/jev to break a near-tie.
function recommendation() {
  let shape;
  try {
    shape = require(
      path.join(PLUGIN_ROOT, "lib", "signals", "project-shape.js"),
    );
  } catch {
    return Promise.resolve(null);
  }

  let settled = false;
  return new Promise((resolve) => {
    const finish = (value) => {
      if (settled) return;
      settled = true;
      resolve(value || null);
    };

    const timer = setTimeout(() => finish(null), SHAPE_BUDGET_MS);
    if (typeof timer.unref === "function") timer.unref();

    try {
      Promise.resolve(
        shape.recommend(process.cwd(), { timeoutMs: SHAPE_BUDGET_MS - 250 }),
      )
        .then((rec) => {
          clearTimeout(timer);
          finish({ rec, lines: shape.render(rec) });
        })
        .catch(() => {
          clearTimeout(timer);
          finish(null);
        });
    } catch {
      clearTimeout(timer);
      finish(null);
    }
  });
}

// ── Banner ────────────────────────────────────────────────────────────────────

// W is the run length of the ═ border; a row carries W - 2 characters of text
// between one space of padding on each side, so every line is exactly W + 2
// columns wide. The widest thing a row has to hold is an install one-liner.
const W = 58;
const inner = W - 2;

function row(text) {
  const s = String(text);
  const clipped = s.length > inner ? s.slice(0, inner - 3) + "..." : s;
  return "║ " + clipped + " ".repeat(inner - clipped.length) + " ║";
}

function banner(version, shapeLines) {
  const rows = [
    "╔" + "═".repeat(W) + "╗",
    row(`tonone v${version} installed!`),
    "╠" + "═".repeat(W) + "╣",
    row(inventory()),
  ];

  if (shapeLines && shapeLines.length) {
    rows.push(row(""));
    for (const line of shapeLines) rows.push(row(line));
    rows.push(row(""));
    rows.push(row("Run /tonone-onboard to confirm or change it."));
  } else {
    rows.push(row(""));
    rows.push(row("Run /tonone-onboard to pick your roster."));
  }

  rows.push("╚" + "═".repeat(W) + "╝");
  return rows.join("\n");
}

// ── Main ──────────────────────────────────────────────────────────────────────

if (isOnboarded()) process.exit(0);

const version = currentVersion();

recommendation()
  .then((shape) => {
    writeMarker(version, shape && shape.rec ? shape.rec.roster.id : null);
    process.stdout.write("\n" + banner(version, shape && shape.lines) + "\n\n");
  })
  .catch(() => {
    writeMarker(version, null);
    process.stdout.write("\n" + banner(version, null) + "\n\n");
  });
