#!/usr/bin/env python3
"""
Generate docs/agent-index.json — one compact line per agent (name, hat, team,
owns, agent_path) parsed from CLAUDE.md's team tables.

Used by the apex-route skill: instead of every agent's full persona being
registered as an installed Claude Code plugin (the cost the lazy-load router
exists to avoid), apex reads this small index to find the right specialist,
then reads that one agent's full markdown file on demand.
"""

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
AGENTS_DIR = REPO_ROOT / "agents"
OUT_FILE = REPO_ROOT / "docs" / "agent-index.json"

TEAM_HEADER = re.compile(r"^## (.+?) Team — \d+ agents?$")
TABLE_ROW = re.compile(r"^\|\s*\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|$")


def parse():
    entries = []
    team = None
    for line in CLAUDE_MD.read_text().splitlines():
        header_match = TEAM_HEADER.match(line.strip())
        if header_match:
            team = header_match.group(1)
            continue
        row_match = TABLE_ROW.match(line.strip())
        if row_match and team:
            name, hat, owns = row_match.groups()
            slug = name.lower()
            agent_path = f"agents/{slug}.md"
            if not (REPO_ROOT / agent_path).exists():
                continue
            entries.append(
                {
                    "name": slug,
                    "hat": hat,
                    "team": team,
                    "owns": owns,
                    "agent_path": agent_path,
                }
            )
    return entries


def main():
    entries = parse()
    OUT_FILE.parent.mkdir(exist_ok=True)
    OUT_FILE.write_text(json.dumps(entries, indent=2) + "\n")
    print(f"wrote {OUT_FILE.relative_to(REPO_ROOT)} — {len(entries)} agents")


if __name__ == "__main__":
    main()
