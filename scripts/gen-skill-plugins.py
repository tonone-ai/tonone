#!/usr/bin/env python3
"""
Generate .claude-plugin/plugin.json for every skill in skills/
and update .claude-plugin/marketplace.json with individual skill entries.
"""

import json
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
MARKETPLACE_FILE = REPO_ROOT / ".claude-plugin" / "marketplace.json"

AUTHOR = {"name": "tonone-ai", "url": "https://tonone.ai"}
REPOSITORY = "https://github.com/tonone-ai/tonone"

# Agent-prefix → marketplace category
CATEGORY_MAP = {
    "apex": "lead",
    "forge": "infrastructure",
    "relay": "devops",
    "spine": "backend",
    "flux": "data",
    "warden": "security",
    "vigil": "observability",
    "prism": "frontend",
    "cortex": "ml",
    "touch": "mobile",
    "volt": "embedded",
    "atlas": "knowledge",
    "lens": "analytics",
    "proof": "testing",
    "pave": "platform",
    "helm": "product",
    "draft": "ux",
    "form": "design",
    "echo": "research",
    "lumen": "product-analytics",
    "crest": "strategy",
    "pitch": "marketing",
    "surge": "growth",
}


def parse_frontmatter(skill_md: Path) -> dict:
    text = skill_md.read_text()
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        if ": " in line:
            key, _, val = line.partition(": ")
            fm[key.strip()] = val.strip()
    return fm


def agent_prefix(skill_name: str) -> str:
    return skill_name.split("-")[0]


def make_plugin_json(name: str, description: str) -> dict:
    prefix = agent_prefix(name)
    return {
        "name": name,
        "version": "0.1.0",
        "description": description,
        "author": AUTHOR,
        "repository": REPOSITORY,
        "license": "MIT",
        "type": "skill",
        "keywords": [prefix, "skill"],
    }


def make_marketplace_entry(name: str, description: str) -> dict:
    prefix = agent_prefix(name)
    return {
        "name": name,
        "description": description,
        "version": "0.1.0",
        "source": f"./skills/{name}",
        "author": AUTHOR,
        "type": "skill",
        "category": CATEGORY_MAP.get(prefix, prefix),
        "tags": [prefix, "skill"],
    }


def main():
    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())
    new_marketplace_entries = []

    for skill_dir in skill_dirs:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        fm = parse_frontmatter(skill_md)
        name = fm.get("name", skill_dir.name)
        description = fm.get("description", "")

        # Write .claude-plugin/plugin.json
        plugin_dir = skill_dir / ".claude-plugin"
        plugin_dir.mkdir(exist_ok=True)
        plugin_json = plugin_dir / "plugin.json"
        plugin_json.write_text(
            json.dumps(make_plugin_json(name, description), indent=2) + "\n"
        )
        print(f"  wrote {plugin_json.relative_to(REPO_ROOT)}")

        new_marketplace_entries.append(make_marketplace_entry(name, description))

    # Update marketplace.json — replace any existing skill entries, keep agent/bundle entries
    marketplace = json.loads(MARKETPLACE_FILE.read_text())
    non_skill = [p for p in marketplace["plugins"] if p.get("type") != "skill"]
    marketplace["plugins"] = non_skill + new_marketplace_entries
    MARKETPLACE_FILE.write_text(json.dumps(marketplace, indent=2) + "\n")
    print(f"\nUpdated {MARKETPLACE_FILE.relative_to(REPO_ROOT)}")
    print(f"  {len(non_skill)} agent/bundle entries kept")
    print(f"  {len(new_marketplace_entries)} skill entries added")


if __name__ == "__main__":
    main()
