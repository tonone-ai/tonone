#!/usr/bin/env python3
"""
Generate docs/skill-index.json — one compact entry per skill (name, agent,
team, description, path) parsed from every team/<agent>/skills/*/SKILL.md
frontmatter.

team/<agent>/skills/ is the source of truth (skills/ at repo root is a
mirror copied from it — see docs/skill-guide.md). This index reads the
source directly, so it stays correct even when the root mirror lags behind.

Companion to docs/agent-index.json (same map-then-detail pattern): consumers
read this small index to find the right skill, then open its SKILL.md path
for the full prompt.
"""

import json
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
TEAM_DIR = REPO_ROOT / "team"
AGENT_INDEX = REPO_ROOT / "docs" / "agent-index.json"
OUT_FILE = REPO_ROOT / "docs" / "skill-index.json"

NAME_RE = re.compile(r"^name:\s*(.+?)\s*$")
DESC_RE = re.compile(r"^description:\s*(.+?)\s*$")


def find_skill_files():
    """os.walk with an exact (case-sensitive) filename check — macOS's
    default case-insensitive filesystem makes Path.glob('SKILL.md') also
    match a stray 'skill.md', which then 404s on any case-sensitive
    deploy target (Linux CI, Docker, raw GitHub/npm serving)."""
    found, wrong_case = [], []
    for root, dirs, files in os.walk(TEAM_DIR):
        root_path = Path(root)
        if root_path.parent.name != "skills":
            continue
        for fn in files:
            if fn == "SKILL.md":
                found.append(Path(root) / fn)
            elif fn.lower() == "skill.md":
                wrong_case.append(Path(root) / fn)
    return found, wrong_case


def load_agent_teams():
    entries = json.loads(AGENT_INDEX.read_text())
    return {e["name"]: e["team"] for e in entries}


def parse_frontmatter(text):
    if not text.startswith("---"):
        return None, None
    end = text.find("\n---", 3)
    if end == -1:
        return None, None
    block = text[3:end]
    name = desc = None
    for line in block.splitlines():
        m = NAME_RE.match(line)
        if m:
            name = m.group(1)
        m = DESC_RE.match(line)
        if m:
            desc = m.group(1)
    return name, desc


def parse():
    agent_teams = load_agent_teams()
    found, wrong_case = find_skill_files()
    entries = []
    no_frontmatter = []
    for skill_md in sorted(found):
        agent = skill_md.parent.parent.name
        name, desc = parse_frontmatter(skill_md.read_text())
        if not name:
            no_frontmatter.append(skill_md.relative_to(REPO_ROOT))
            continue
        entries.append(
            {
                "name": name,
                "agent": agent,
                "team": agent_teams.get(agent, "unknown"),
                "description": desc or "",
                "path": str(skill_md.relative_to(REPO_ROOT)),
            }
        )
    return entries, no_frontmatter, sorted(wrong_case)


def main():
    entries, no_frontmatter, wrong_case = parse()
    OUT_FILE.parent.mkdir(exist_ok=True)
    OUT_FILE.write_text(json.dumps(entries, indent=2) + "\n")
    print(f"wrote {OUT_FILE.relative_to(REPO_ROOT)} — {len(entries)} skills")
    if no_frontmatter:
        print(f"\n{len(no_frontmatter)} SKILL.md with no frontmatter (excluded):")
        for p in no_frontmatter:
            print(f"  {p}")
    if wrong_case:
        print(
            f"\n{len(wrong_case)} skill.md with wrong case, breaks on case-sensitive fs (excluded):"
        )
        for p in wrong_case:
            print(f"  {p.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
