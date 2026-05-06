#!/usr/bin/env bash
set -euo pipefail

MARKETPLACE="tonone-ai"

PLUGINS=(
	"tonone-helm"
	"tonone-echo"
	"tonone-lumen"
	"tonone-draft"
	"tonone-form"
	"tonone-crest"
	"tonone-pitch"
	"tonone-surge"
	"tonone-deal"
	"tonone-keep"
	"tonone-ink"
	"tonone-buzz"
)

echo ""
echo "=== tonone — Installing ${#PLUGINS[@]} Product Team agent(s) ==="
echo ""

if command -v claude &>/dev/null; then
	for plugin in "${PLUGINS[@]}"; do
		echo "  Installing ${plugin}..."
		claude plugin install "${plugin}@${MARKETPLACE}" || echo "  WARNING: Failed to install ${plugin}, skipping"
	done
	echo ""
	echo "Done! All Product Team agents installed."
else
	echo "Run these commands to install each agent:"
	echo ""
	for plugin in "${PLUGINS[@]}"; do
		echo "  /plugin install ${plugin}@${MARKETPLACE}"
	done
	echo ""
fi
