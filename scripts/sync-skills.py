#!/usr/bin/env python3
"""
Mirror team/<agent>/skills/<skill>/SKILL.md into the repo-root skills/ directory.

team/<agent>/skills/ is the source of truth (see docs/skill-guide.md). Root
skills/ is the distribution copy: the bundle plugin declared in
.claude-plugin/marketplace.json has source "./", so Claude Code discovers its
skills from root skills/ and *only* from there. Any skill missing from the
mirror is invisible to everyone who installs the bundle, even though the agent
that owns it installs fine.

Root skills/<skill>/ may also hold a generated .claude-plugin/plugin.json (see
gen-skill-plugins.py) that turns the directory into a standalone per-skill
plugin. That file has no counterpart under team/, so this script syncs SKILL.md
only and never removes anything.

A handful of root skills are root-only by design — the per-agent hub skills
(skills/apex, skills/form, ...) and tonone-onboard. They have no team/
counterpart and are left alone.

Usage:
    python scripts/sync-skills.py            # write the mirror
    python scripts/sync-skills.py --check    # report drift, exit 1 if any
"""

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
TEAM_DIR = REPO_ROOT / "team"
SKILLS_DIR = REPO_ROOT / "skills"


def find_team_skills():
    """Map skill name -> canonical SKILL.md path.

    Uses an exact (case-sensitive) filename check rather than glob: macOS's
    default case-insensitive filesystem makes Path.glob("SKILL.md") also match
    a stray "skill.md", which then 404s on any case-sensitive target (Linux CI,
    Docker, raw GitHub serving). Same guard as gen-skill-index.py.
    """
    skills, wrong_case, collisions = {}, [], []
    for root, _dirs, files in os.walk(TEAM_DIR):
        root_path = Path(root)
        if root_path.parent.name != "skills":
            continue
        if "SKILL.md" not in files:
            if any(f.lower() == "skill.md" for f in files):
                wrong_case.append(root_path)
            continue
        name = root_path.name
        if name in skills:
            collisions.append(name)
        skills[name] = root_path / "SKILL.md"
    return skills, wrong_case, collisions


def sync(check_only: bool) -> int:
    skills, wrong_case, collisions = find_team_skills()

    if wrong_case:
        for p in sorted(wrong_case):
            print(f"ERROR  lowercase skill.md (invisible on case-sensitive FS): {p}")
        return 1

    if collisions:
        # Root skills/ is a flat namespace, so two agents owning the same skill
        # name would silently clobber each other in the mirror.
        for name in sorted(set(collisions)):
            print(f"ERROR  duplicate skill name across agents: {name}")
        return 1

    created, updated, unchanged = [], [], 0

    for name in sorted(skills):
        src = skills[name]
        dest = SKILLS_DIR / name / "SKILL.md"
        content = src.read_text()

        if not dest.exists():
            created.append(name)
            if not check_only:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content)
        elif dest.read_text() != content:
            updated.append(name)
            if not check_only:
                dest.write_text(content)
        else:
            unchanged += 1

    orphans = sorted(
        d.name
        for d in SKILLS_DIR.iterdir()
        if d.is_dir() and d.name not in skills and (d / "SKILL.md").exists()
    )

    verb = "would create" if check_only else "created"
    print(f"team skills:  {len(skills)}")
    print(f"{verb}:      {len(created)}")
    print(f"{'would update' if check_only else 'updated'}:      {len(updated)}")
    print(f"unchanged:    {unchanged}")
    print(f"root-only:    {len(orphans)}  (agent hub skills + tonone-onboard)")

    if created:
        print("\n" + verb + ":")
        for n in created:
            print(f"  + {n}")
    if updated:
        print("\n" + ("would update" if check_only else "updated") + ":")
        for n in updated:
            print(f"  ~ {n}")

    if check_only and (created or updated):
        print(
            f"\nFAIL  root skills/ is out of sync with team/ "
            f"({len(created)} missing, {len(updated)} drifted). "
            f"Run: python scripts/sync-skills.py"
        )
        return 1

    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift without writing; exit 1 if the mirror is stale",
    )
    args = parser.parse_args()
    sys.exit(sync(args.check))


if __name__ == "__main__":
    main()
