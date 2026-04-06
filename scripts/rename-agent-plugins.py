#!/usr/bin/env python3
"""
Rename agent plugin names from {agent}-{domain} to tonone-{agent}.

Before: forge-infra, relay-devops, apex-lead, ...
After:  tonone-forge, tonone-relay, tonone-apex, ...

Updates:
  - team/{agent}/.claude-plugin/plugin.json
  - .claude-plugin/marketplace.json  (agent entries only)
  - bundle/*/scripts/install-all.sh
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# agent-directory → new plugin name
AGENT_RENAME = {
    "apex": "tonone-apex",
    "forge": "tonone-forge",
    "relay": "tonone-relay",
    "spine": "tonone-spine",
    "flux": "tonone-flux",
    "warden": "tonone-warden",
    "vigil": "tonone-vigil",
    "prism": "tonone-prism",
    "cortex": "tonone-cortex",
    "touch": "tonone-touch",
    "volt": "tonone-volt",
    "atlas": "tonone-atlas",
    "lens": "tonone-lens",
    "proof": "tonone-proof",
    "pave": "tonone-pave",
    "helm": "tonone-helm",
    "draft": "tonone-draft",
    "form": "tonone-form",
    "echo": "tonone-echo",
    "lumen": "tonone-lumen",
    "surge": "tonone-surge",
    "crest": "tonone-crest",
    "pitch": "tonone-pitch",
}

# old plugin name → new plugin name (for install scripts)
OLD_TO_NEW = {
    "apex-lead": "tonone-apex",
    "forge-infra": "tonone-forge",
    "relay-devops": "tonone-relay",
    "spine-backend": "tonone-spine",
    "flux-data": "tonone-flux",
    "warden-security": "tonone-warden",
    "vigil-sre": "tonone-vigil",
    "prism-frontend": "tonone-prism",
    "cortex-ml": "tonone-cortex",
    "touch-mobile": "tonone-touch",
    "volt-embedded": "tonone-volt",
    "atlas-docs": "tonone-atlas",
    "lens-analytics": "tonone-lens",
    "proof-qa": "tonone-proof",
    "pave-platform": "tonone-pave",
    "helm-product": "tonone-helm",
    "draft-ux": "tonone-draft",
    "form-design": "tonone-form",
    "echo-research": "tonone-echo",
    "lumen-analytics": "tonone-lumen",
    "surge-growth": "tonone-surge",
    "crest-strategy": "tonone-crest",
    "pitch-marketing": "tonone-pitch",
}


def update_team_plugin_jsons():
    for agent, new_name in AGENT_RENAME.items():
        path = REPO_ROOT / "team" / agent / ".claude-plugin" / "plugin.json"
        if not path.exists():
            print(f"  SKIP (not found): {path.relative_to(REPO_ROOT)}")
            continue
        data = json.loads(path.read_text())
        old_name = data["name"]
        data["name"] = new_name
        path.write_text(json.dumps(data, indent=2) + "\n")
        print(f"  {path.relative_to(REPO_ROOT)}: {old_name} → {new_name}")


def update_marketplace():
    path = REPO_ROOT / ".claude-plugin" / "marketplace.json"
    market = json.loads(path.read_text())
    for entry in market["plugins"]:
        if entry.get("type") == "skill":
            continue
        old = entry["name"]
        if old in OLD_TO_NEW:
            entry["name"] = OLD_TO_NEW[old]
            print(f"  marketplace: {old} → {entry['name']}")
    path.write_text(json.dumps(market, indent=2) + "\n")


def update_install_scripts():
    for script in REPO_ROOT.glob("bundle/*/scripts/install-all.sh"):
        text = script.read_text()
        changed = False
        for old, new in OLD_TO_NEW.items():
            if f'"{old}"' in text:
                text = text.replace(f'"{old}"', f'"{new}"')
                changed = True
        if changed:
            script.write_text(text)
            print(f"  updated: {script.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    print("Updating team plugin.json names...")
    update_team_plugin_jsons()
    print("\nUpdating marketplace.json agent entries...")
    update_marketplace()
    print("\nUpdating bundle install scripts...")
    update_install_scripts()
    print("\nDone.")
