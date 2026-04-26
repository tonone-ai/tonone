#!/usr/bin/env python3
"""
Bump version across all plugin.json and pyproject.toml files.

Single source of truth: .claude-plugin/plugin.json

Usage:
    python scripts/bump-version.py 0.7.0          # explicit version
    python scripts/bump-version.py patch           # 0.6.6 → 0.6.7
    python scripts/bump-version.py minor           # 0.6.6 → 0.7.0
    python scripts/bump-version.py major           # 0.6.6 → 1.0.0
    python scripts/bump-version.py --dry-run 0.7.0 # preview without writing
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = str(REPO_ROOT / "templates")


def read_current_version() -> str:
    root_plugin = REPO_ROOT / ".claude-plugin" / "plugin.json"
    return json.loads(root_plugin.read_text())["version"]


def bump(current: str, part: str) -> str:
    major, minor, patch = (int(x) for x in current.split("."))
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "major":
        return f"{major + 1}.0.0"
    raise ValueError(f"Unknown bump type: {part}")


def resolve_version(arg: str, current: str) -> str:
    if arg in ("patch", "minor", "major"):
        return bump(current, arg)
    if re.match(r"^\d+\.\d+\.\d+$", arg):
        return arg
    print(
        f"Error: invalid version '{arg}'. Use patch/minor/major or X.Y.Z",
        file=sys.stderr,
    )
    sys.exit(1)


def update_plugin_json(path: Path, new_version: str, dry_run: bool) -> str | None:
    """Returns old version if updated, None if already current."""
    data = json.loads(path.read_text())
    old = data.get("version", "")
    if old == new_version:
        return None
    data["version"] = new_version
    if not dry_run:
        path.write_text(json.dumps(data, indent=2) + "\n")
    return old


def update_pyproject_toml(path: Path, new_version: str, dry_run: bool) -> str | None:
    """Returns old version if updated, None if already current."""
    text = path.read_text()
    match = re.search(r'^version\s*=\s*"([^"]*)"', text, re.MULTILINE)
    if not match or match.group(1) == new_version:
        return None
    old = match.group(1)
    new_text = text[: match.start(1)] + new_version + text[match.end(1) :]
    if not dry_run:
        path.write_text(new_text)
    return old


def find_files():
    plugin_files = sorted(REPO_ROOT.glob("**/.claude-plugin/plugin.json"))
    pyproject_files = sorted(REPO_ROOT.glob("**/pyproject.toml"))

    WORKTREES_DIR = str(REPO_ROOT / ".claude" / "worktrees")

    # Exclude templates, venvs, and git worktrees
    plugin_files = [
        p for p in plugin_files
        if not str(p).startswith(TEMPLATE_DIR) and not str(p).startswith(WORKTREES_DIR)
    ]
    pyproject_files = [
        p
        for p in pyproject_files
        if not str(p).startswith(TEMPLATE_DIR)
        and ".venv" not in str(p)
        and not str(p).startswith(WORKTREES_DIR)
    ]

    return plugin_files, pyproject_files


def main():
    parser = argparse.ArgumentParser(description="Bump version across all manifests")
    parser.add_argument(
        "version", help="New version (X.Y.Z) or bump type (patch/minor/major)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without writing"
    )
    args = parser.parse_args()

    current = read_current_version()
    new_version = resolve_version(args.version, current)
    prefix = "[DRY RUN] " if args.dry_run else ""

    print(f"{prefix}{current} → {new_version}\n")

    plugin_files, pyproject_files = find_files()

    updated = 0
    for pf in plugin_files:
        rel = pf.relative_to(REPO_ROOT)
        old = update_plugin_json(pf, new_version, args.dry_run)
        if old is not None:
            print(f"  {old} → {new_version}  {rel}")
            updated += 1

    for pf in pyproject_files:
        rel = pf.relative_to(REPO_ROOT)
        old = update_pyproject_toml(pf, new_version, args.dry_run)
        if old is not None:
            print(f"  {old} → {new_version}  {rel}")
            updated += 1

    total = len(plugin_files) + len(pyproject_files)
    at_target = total - updated
    print(f"\n{prefix}Updated: {updated} files")
    if at_target:
        print(f"Already at {new_version}: {at_target} files")


if __name__ == "__main__":
    main()
