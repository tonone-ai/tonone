#!/usr/bin/env bash
set -euo pipefail

MARKETPLACE="tonone-ai"

PLUGINS=(
	"apex-lead"
	"forge-infra"
	"relay-devops"
	"spine-backend"
	"flux-data"
	"warden-security"
	"vigil-sre"
	"prism-frontend"
	"cortex-ml"
	"touch-mobile"
	"volt-embedded"
	"atlas-docs"
	"lens-analytics"
)

echo ""
echo "=== tonone — Installing ${#PLUGINS[@]} agent(s) ==="
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
