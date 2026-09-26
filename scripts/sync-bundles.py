#!/usr/bin/env python3
"""
Refresh the agent and skill copies inside bundle/<team>/ from the repo root.

A team bundle (engineering-team, product-team, full-team, ...) is its own
plugin in .claude-plugin/marketplace.json with source "./bundle/<team>", so it
must carry real copies of the agents and skills it installs. These used to be
symlinks into ../../../agents and ../../../skills. The Anthropic plugin
directory rejects repositories with that many symlinks, so the bundles now hold
plain copies and this script keeps them in step with the root.

Membership is whatever is already in the bundle: bundle/<team>/agents/<name>.md
is refreshed from agents/<name>.md, and bundle/<team>/skills/<name>/ from
skills/<name>/. Add or remove a member by adding or removing it in the bundle,
then run this script. Any symlink still in a bundle is replaced by a copy.

Usage:
    python scripts/sync-bundles.py            # write the copies
    python scripts/sync-bundles.py --check    # report drift, exit 1 if any
"""

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_DIR = REPO_ROOT / "bundle"


def members(bundle):
    """Yield (bundle_path, source_path) for every agent and skill in a bundle."""
    for entry in sorted((bundle / "agents").glob("*.md")):
        yield entry, REPO_ROOT / "agents" / entry.name
    skills = bundle / "skills"
    if skills.is_dir():
        for entry in sorted(skills.iterdir()):
            yield entry, REPO_ROOT / "skills" / entry.name


def same_tree(a, b):
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    return all(same_tree(a / d, b / d) for d in cmp.common_dirs)


def in_sync(dest, src):
    if dest.is_symlink():
        return False
    if src.is_dir():
        return dest.is_dir() and same_tree(dest, src)
    return dest.is_file() and filecmp.cmp(dest, src, shallow=False)


def copy(dest, src):
    if dest.is_symlink() or dest.is_file():
        dest.unlink()
    elif dest.is_dir():
        shutil.rmtree(dest)
    if src.is_dir():
        shutil.copytree(src, dest)
    else:
        shutil.copy2(src, dest)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="report drift only")
    args = parser.parse_args()

    missing, drift = [], []
    for bundle in sorted(p for p in BUNDLE_DIR.iterdir() if p.is_dir()):
        for dest, src in members(bundle):
            rel = dest.relative_to(REPO_ROOT)
            if not src.exists():
                missing.append(f"{rel} (no {src.relative_to(REPO_ROOT)})")
                continue
            if in_sync(dest, src):
                continue
            drift.append(str(rel))
            if not args.check:
                copy(dest, src)

    for line in missing:
        print(f"missing source: {line}")
    if args.check:
        for line in drift:
            print(f"out of sync: {line}")
        if drift or missing:
            print("Run: python scripts/sync-bundles.py")
            return 1
        print("Bundles in sync.")
        return 0

    print(f"Refreshed {len(drift)} bundle entries.")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
