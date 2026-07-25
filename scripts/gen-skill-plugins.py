#!/usr/bin/env python3
"""
Backfill .claude-plugin/plugin.json for any skill in skills/ that's missing one,
and add matching entries to .claude-plugin/marketplace.json.

Idempotent: skills that already have a plugin.json are left untouched (no
reformatting), and existing marketplace.json entries are preserved as-is —
only missing skill entries get added. Run with --force to regenerate every
plugin.json from scratch instead (only use this deliberately; it reformats
every skill's plugin.json).
"""

import json
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
MARKETPLACE_FILE = REPO_ROOT / ".claude-plugin" / "marketplace.json"
ROOT_PLUGIN = REPO_ROOT / ".claude-plugin" / "plugin.json"

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


def read_root_version() -> str:
    return json.loads(ROOT_PLUGIN.read_text())["version"]


def make_plugin_json(name: str, description: str, version: str) -> dict:
    prefix = agent_prefix(name)
    return {
        "name": name,
        "version": version,
        "description": description,
        "author": AUTHOR,
        "repository": REPOSITORY,
        "license": "MIT",
        "type": "skill",
        "keywords": [prefix, "skill"],
    }


def make_marketplace_entry(name: str, description: str, version: str) -> dict:
    prefix = agent_prefix(name)
    return {
        "name": name,
        "description": description,
        "version": version,
        "source": f"./skills/{name}",
        "author": AUTHOR,
        "type": "skill",
        "category": CATEGORY_MAP.get(prefix, prefix),
        "tags": [prefix, "skill"],
    }


def render_marketplace_entry(entry: dict) -> str:
    """Hand-format to match the existing file's style exactly (4-space indent,
    inline tags array) — json.dumps(indent=2) would reflow tags to multi-line
    and doesn't match how every other skill entry in the file is written."""
    return (
        "    {\n"
        f'      "name": "{entry["name"]}",\n'
        f'      "description": {json.dumps(entry["description"])},\n'
        f'      "version": "{entry["version"]}",\n'
        f'      "source": "{entry["source"]}",\n'
        '      "author": {\n'
        f'        "name": "{entry["author"]["name"]}",\n'
        f'        "url": "{entry["author"]["url"]}"\n'
        "      },\n"
        f'      "type": "{entry["type"]}",\n'
        f'      "category": "{entry["category"]}",\n'
        f'      "tags": {json.dumps(entry["tags"])}\n'
        "    }"
    )


def append_marketplace_entries(entries: list, dry_run: bool) -> None:
    """Insert new entries at the end of the plugins array via text splice —
    never json.load/dump the whole file (see update_marketplace_json in
    bump-version.py for why: it reformats every untouched entry)."""
    if not entries:
        return
    text = MARKETPLACE_FILE.read_text()
    match = re.search(r"\n(  \]\n\}\n?)$", text)
    if not match:
        raise RuntimeError(
            "marketplace.json: could not find closing ']}' to splice before"
        )
    blocks = ",\n".join(render_marketplace_entry(e) for e in entries)
    new_text = text[: match.start()] + ",\n" + blocks + "\n" + match.group(1)
    if not dry_run:
        MARKETPLACE_FILE.write_text(new_text)


def main():
    import sys

    force = "--force" in sys.argv
    version = read_root_version()
    print(f"Using version {version} from root plugin.json\n")

    skill_dirs = sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir())
    backfilled_entries = []
    skipped = 0

    marketplace = json.loads(MARKETPLACE_FILE.read_text())
    existing_names = {p["name"] for p in marketplace["plugins"]}

    for skill_dir in skill_dirs:
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        fm = parse_frontmatter(skill_md)
        name = fm.get("name", skill_dir.name)
        description = fm.get("description", "")

        plugin_dir = skill_dir / ".claude-plugin"
        plugin_json = plugin_dir / "plugin.json"

        if plugin_json.exists() and not force:
            skipped += 1
            continue

        plugin_dir.mkdir(exist_ok=True)
        plugin_json.write_text(
            json.dumps(make_plugin_json(name, description, version), indent=2) + "\n"
        )
        print(f"  wrote {plugin_json.relative_to(REPO_ROOT)}")

        if name not in existing_names:
            backfilled_entries.append(
                make_marketplace_entry(name, description, version)
            )

    append_marketplace_entries(backfilled_entries, dry_run=False)

    print(
        f"\n{len(backfilled_entries)} plugin.json backfilled, {len(backfilled_entries)} marketplace entries added"
    )
    print(f"{skipped} skills already had a plugin.json — left untouched")


if __name__ == "__main__":
    main()
