#!/usr/bin/env node
"use strict";

// tonone-statusline-setup — SessionStart hook
// Offers the tonone status bar once, and installs it only if the user says yes.
//
// A hook cannot prompt, so the first eligible session shows the user a one-time
// message with two commands to type. Nothing runs until the user does. The
// answer comes back through this script:
//   node tonone-statusline-setup.js --yes     install, remember "on"
//   node tonone-statusline-setup.js --never   remember "never"
//
// State file ~/.config/tonone/statusline holds on | never | asked.
// It never replaces a statusLine the user already has, and it leaves
// unreadable settings untouched. Never blocks the session on any error.
//
// TONONE_STATUSLINE=1 installs without asking; =0 turns the offer off.
// Skipped when CI is set.

const fs = require("fs");
const os = require("os");
const path = require("path");

const STATE_DIR =
  process.env.TONONE_CONFIG_DIR || path.join(os.homedir(), ".config", "tonone");
const STATE_FILE = path.join(STATE_DIR, "statusline");
const SCRIPT = path.join(__dirname, "tonone-statusline.js");
const COMMAND = `node "${SCRIPT}"`;

function settingsPath() {
  const dir =
    process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), ".claude");
  return path.join(dir, "settings.json");
}

function readState() {
  try {
    return fs.readFileSync(STATE_FILE, "utf8").trim();
  } catch {
    return "";
  }
}

function writeState(value) {
  try {
    fs.mkdirSync(STATE_DIR, { recursive: true });
    fs.writeFileSync(STATE_FILE, value + "\n");
  } catch {}
}

// "empty" | "ours" | "foreign" | "unreadable"
function slot() {
  let settings;
  try {
    settings = JSON.parse(fs.readFileSync(settingsPath(), "utf8"));
  } catch (e) {
    return e.code === "ENOENT" ? "empty" : "unreadable";
  }
  const cmd = settings.statusLine && settings.statusLine.command;
  if (!cmd) return "empty";
  return cmd === COMMAND ? "ours" : "foreign";
}

// Returns "installed" | "present" | "foreign" | "unreadable".
function install() {
  const s = slot();
  if (s !== "empty") return s === "ours" ? "present" : s;
  const file = settingsPath();
  let settings = {};
  try {
    settings = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {}
  settings.statusLine = { type: "command", command: COMMAND };
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(settings, null, 2) + "\n");
  return "installed";
}

const ASK =
  "tonone: optional status bar (git branch, active agents, context use). " +
  "To install, type:  ! node " +
  JSON.stringify(__filename) +
  " --yes   To decline:  ! node " +
  JSON.stringify(__filename) +
  " --never   (Shown once. Nothing is changed until you run one.)";

function main(argv, env) {
  if (argv.includes("--never")) {
    writeState("never");
    console.log("tonone: status bar offer turned off");
    return;
  }
  if (argv.includes("--yes")) {
    const r = install();
    if (r === "installed" || r === "present") writeState("on");
    console.log(
      r === "installed"
        ? "tonone: status bar installed (restart Claude Code to see it)"
        : r === "present"
          ? "tonone: status bar already installed"
          : "tonone: you already have a statusLine, left unchanged",
    );
    return;
  }

  if (env.CI || env.TONONE_STATUSLINE === "0") return;
  if (env.TONONE_STATUSLINE === "1") {
    install();
    return;
  }

  const state = readState();
  if (state === "never" || state === "asked") return;
  if (state === "on") {
    install();
    return;
  }

  // Undecided. Offer only into an empty slot; never ask about replacing one.
  if (slot() !== "empty") {
    writeState("never");
    return;
  }
  writeState("asked");
  process.stdout.write(JSON.stringify({ systemMessage: ASK }));
}

if (require.main === module) {
  try {
    main(process.argv.slice(2), process.env);
  } catch {}
  process.exit(0);
}

module.exports = { main, slot, ASK };
