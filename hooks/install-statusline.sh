#!/usr/bin/env bash
# install-statusline — SessionStart hook
# Points Claude Code's statusLine at tonone-statusline.js.
#
# Opt-in: does nothing unless TONONE_STATUSLINE=1. It edits the user's
# ~/.claude/settings.json, so it never happens by default.
# It also never replaces a statusLine the user already has; it only fills an
# empty slot, or leaves tonone's own entry in place.
set -euo pipefail

[ "${TONONE_STATUSLINE-}" = "1" ] || exit 0
command -v node &>/dev/null || exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

STATUSLINE_SCRIPT="$SCRIPT_DIR/tonone-statusline.js" \
	SETTINGS_FILE="$CLAUDE_DIR/settings.json" \
	node -e '
const fs = require("fs");
const script = process.env.STATUSLINE_SCRIPT;
const file = process.env.SETTINGS_FILE;
const cmd = `node "${script}"`;

let settings = {};
try {
  settings = JSON.parse(fs.readFileSync(file, "utf8"));
} catch (e) {
  if (e.code !== "ENOENT") process.exit(0); // unreadable or invalid JSON: leave it alone
}

const current = settings.statusLine && settings.statusLine.command;
if (current === cmd) process.exit(0);
if (current) {
  console.log("tonone: existing statusLine left unchanged");
  process.exit(0);
}

settings.statusLine = { type: "command", command: cmd };
fs.mkdirSync(require("path").dirname(file), { recursive: true });
fs.writeFileSync(file, JSON.stringify(settings, null, 2) + "\n");
console.log("tonone: statusline installed");
'
