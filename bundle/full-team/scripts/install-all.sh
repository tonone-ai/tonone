#!/usr/bin/env bash
set -euo pipefail

MARKETPLACE="tonone-ai"

PLUGINS=(
	# Engineering Team (15)
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

	# Product Team (8)
	"tonone-helm"
	"tonone-echo"
	"tonone-lumen"
	"tonone-draft"
	"tonone-form"
	"tonone-crest"
	"tonone-pitch"
	"tonone-surge"
)

echo ""
echo "=== tonone — Installing ${#PLUGINS[@]} agent(s) (Full Team) ==="
echo ""

if command -v claude &>/dev/null; then
	for plugin in "${PLUGINS[@]}"; do
		echo "  Installing ${plugin}..."
		claude plugin install "${plugin}@${MARKETPLACE}" || echo "  WARNING: Failed to install ${plugin}, skipping"
	done
	echo ""
	echo "Done! Full team installed — Engineering + Product."
else
	echo "Run these commands to install each agent:"
	echo ""
	for plugin in "${PLUGINS[@]}"; do
		echo "  /plugin install ${plugin}@${MARKETPLACE}"
	done
	echo ""
fi
