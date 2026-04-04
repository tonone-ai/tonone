#!/usr/bin/env bash
set -euo pipefail

MARKETPLACE="tonone-ai"

PLUGINS=(
	# Engineering Team (15)
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
	"proof-qa"
	"pave-platform"

	# Product Team (8)
	"helm-product"
	"echo-research"
	"lumen-analytics"
	"draft-ux"
	"form-design"
	"crest-strategy"
	"pitch-marketing"
	"surge-growth"
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
