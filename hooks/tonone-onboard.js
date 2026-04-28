#!/usr/bin/env node
"use strict";

// tonone-onboard — SessionStart hook
// Fires exactly once after install. Writes a marker to ~/.config/tonone/onboarded.
// On subsequent sessions exits silently. Never blocks the session on any error.

const fs = require("fs");
const os = require("os");
const path = require("path");

// ── Config ────────────────────────────────────────────────────────────────────

const PLUGIN_ROOT =
  process.env.CLAUDE_PLUGIN_ROOT || path.join(__dirname, "..");
const PLUGIN_JSON = path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json");
const MARKER_DIR = path.join(os.homedir(), ".config", "tonone");
const MARKER_FILE = path.join(MARKER_DIR, "onboarded");

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

function writeMarker(version) {
  try {
    fs.mkdirSync(MARKER_DIR, { recursive: true });
    fs.writeFileSync(
      MARKER_FILE,
      JSON.stringify({ version, ts: new Date().toISOString() }),
    );
  } catch {
    // If write fails, hook exits 0 and retries next session — correct behavior.
  }
}

// ── Main ──────────────────────────────────────────────────────────────────────

if (isOnboarded()) process.exit(0);

const version = currentVersion();
writeMarker(version);

const pad = (s, w) => s + " ".repeat(Math.max(0, w - s.length));
const W = 54;
const inner = W - 2; // chars between ║ and ║

function row(text) {
  return "║ " + pad(text, inner - 1) + "║";
}

const banner = [
  "╔" + "═".repeat(W) + "╗",
  row(`tonone v${version} installed!`),
  "╠" + "═".repeat(W) + "╣",
  row("You have 23 agents and 100+ skills."),
  row(""),
  row("Run /tonone-onboard for a guided tour."),
  row("Takes ~90 sec (expert) or ~8 min (newcomer)."),
  "╚" + "═".repeat(W) + "╝",
].join("\n");

process.stdout.write("\n" + banner + "\n\n");
