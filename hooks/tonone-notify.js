#!/usr/bin/env node
"use strict";

// tonone-notify — Stop + Notification hook
// Fires a macOS notification when Claude finishes a turn or needs attention.
//
// Config: ~/.config/tonone/config.json
// {
//   "notify": {
//     "sound": true,
//     "soundFile": "/System/Library/Sounds/Glass.aiff"
//   }
// }

const { spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

// ── Config ────────────────────────────────────────────────────────────────────

const CONFIG_PATH = path.join(os.homedir(), ".config", "tonone", "config.json");

const DEFAULTS = {
  sound: true,
  soundFile: "/System/Library/Sounds/Glass.aiff",
};

function loadConfig() {
  try {
    const raw = JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
    return { ...DEFAULTS, ...(raw.notify || {}) };
  } catch {
    return { ...DEFAULTS };
  }
}

// ── Notification ──────────────────────────────────────────────────────────────

// Escape a string for use inside an AppleScript double-quoted string literal.
function escapeAS(s) {
  return String(s)
    .replace(/\\/g, "\\\\")
    .replace(/"/g, '\\"');
}

function sendNotification(title, subtitle, body) {
  const parts = [`display notification "${escapeAS(body)}"`, `with title "${escapeAS(title)}"`];
  if (subtitle) parts.push(`subtitle "${escapeAS(subtitle)}"`);
  spawnSync("osascript", ["-e", parts.join(" ")], { timeout: 3000 });
}

function playSound(file) {
  if (!file) return;
  spawnSync("afplay", [file], { timeout: 5000 });
}

// ── Main ──────────────────────────────────────────────────────────────────────

let input = "";
const stdinTimeout = setTimeout(() => process.exit(0), 3000);
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => (input += chunk));
process.stdin.on("end", () => {
  clearTimeout(stdinTimeout);

  let data;
  try {
    data = JSON.parse(input);
  } catch {
    process.exit(0);
  }

  // Detect event type: prefer explicit field, fall back to payload shape.
  const event = data.hook_event_name || (data.message != null ? "Notification" : "Stop");

  if (event !== "Stop" && event !== "Notification") process.exit(0);

  const cwd = data.cwd || data.workspace?.current_dir || "";
  const folder = cwd ? path.basename(cwd) : "";

  let body;
  if (event === "Stop") {
    body = "Done \u2014 your turn";
  } else {
    body = data.message || "Needs your attention";
  }

  const cfg = loadConfig();
  sendNotification("Claude Code", folder || null, body);
  if (cfg.sound) playSound(cfg.soundFile);
});
