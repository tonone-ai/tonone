#!/usr/bin/env bash
set -euo pipefail

MARKETPLACE="tonone-ai"

PLUGINS=(
	"tonone-apex"
	"tonone-forge"
	"tonone-relay"
	"tonone-spine"
	"tonone-flux"
	"tonone-warden"
	"tonone-vigil"
	"tonone-prism"
	"tonone-cortex"
	"tonone-touch"
	"tonone-volt"
	"tonone-atlas"
	"tonone-lens"
	"tonone-proof"
	"tonone-pave"
)

echo ""
echo "=== tonone — Installing ${#PLUGINS[@]} Engineering Team agent(s) ==="
echo ""

if command -v claude &>/dev/null; then
	for plugin in "${PLUGINS[@]}"; do
		echo "  Installing ${plugin}..."
		claude plugin install "${plugin}@${MARKETPLACE}" || echo "  WARNING: Failed to install ${plugin}, skipping"
	done
	echo ""
	echo "Done! All agents installed."
else
	echo "Run these commands to install each agent:"
	echo ""
	for plugin in "${PLUGINS[@]}"; do
		echo "  /plugin install ${plugin}@${MARKETPLACE}"
	done
	echo ""
fi
