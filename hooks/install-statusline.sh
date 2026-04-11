#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STATUSLINE_SCRIPT="$SCRIPT_DIR/tonone-statusline.js"

# Resolve settings.json location
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

# Ensure settings file exists
if [ ! -f "$SETTINGS_FILE" ]; then
	echo "{}" >"$SETTINGS_FILE"
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
	echo "$CURRENT_SL" >"$BACKUP_DIR/command-$TIMESTAMP.txt"

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
