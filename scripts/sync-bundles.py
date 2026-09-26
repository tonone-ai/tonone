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
is refreshed from agents/<name>.md, bundle/<team>/skills/<name>/ from
skills/<name>/, and any file under bundle/<team>/docs/ or bundle/<team>/team/
from the same path at the root. Add or remove a member by adding or removing it in the bundle,
then run this script. Any symlink still in a bundle is replaced by a copy.

Usage:
    python scripts/sync-bundles.py            # write the copies
    python scripts/sync-bundles.py --check    # report drift, exit 1 if any
"""

import argparse
import filecmp
import re
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_DIR = REPO_ROOT / "bundle"

# Frontmatter keys dropped from SKILL.md when copying into a bundle.
# tonone-core is the plugin submitted to the Anthropic plugin directory, which
# holds any skill whose allowed-tools pre-approves unscoped Bash, Write or
# WebFetch. Without the key the tools still work; Claude Code simply asks.
STRIP_FRONTMATTER = {"tonone-core": ("allowed-tools",)}


def members(bundle):
    """Yield (bundle_path, source_path) for every agent and skill in a bundle."""
    for entry in sorted((bundle / "agents").glob("*.md")):
        yield entry, REPO_ROOT / "agents" / entry.name
    skills = bundle / "skills"
    if skills.is_dir():
        for entry in sorted(skills.iterdir()):
            yield entry, REPO_ROOT / "skills" / entry.name
    # Shared reference files a bundle ships so its skills' repo-relative
    # paths (docs/output-kit.md, team/prism/reference/...) still resolve.
    for sub in ("docs", "team"):
        for entry in sorted((bundle / sub).rglob("*")):
            if entry.is_file():
                yield entry, REPO_ROOT / entry.relative_to(bundle)


OMIT_BLOCK = re.compile(
    r"<!-- bundle:omit ([^>]*?) -->\n(.*?)<!-- /bundle:omit -->\n", re.S
)


def omit_blocks(bundle_name, text):
    """Resolve <!-- bundle:omit NAME ... --> ... <!-- /bundle:omit --> blocks.

    Lets a root skill carry a section a slim bundle cannot use, such as the
    optional decision-layer step whose code tonone-core does not ship. The
    block is dropped for the bundles it names and kept, without its markers,
    everywhere else.
    """

    def repl(m):
        return "" if bundle_name in m.group(1).split() else m.group(2)

    return OMIT_BLOCK.sub(repl, text)


def transformed(bundle, src):
    """Bytes a bundle should hold for SKILL.md src, or None to copy verbatim."""
    if src.name != "SKILL.md":
        return None
    text = src.read_text()
    out = omit_blocks(bundle.name, text)
    keys = STRIP_FRONTMATTER.get(bundle.name)
    m = re.match(r"---\n(.*?\n)---\n", out, re.S) if keys else None
    if m:
        kept = [
            line
            for line in m.group(1).splitlines(keepends=True)
            if not any(line.startswith(k + ":") for k in keys)
        ]
        out = "---\n" + "".join(kept) + "---\n" + out[m.end() :]
    return None if out == text else out.encode()


def same_file(bundle, dest, src):
    want = transformed(bundle, src)
    if want is None:
        return filecmp.cmp(dest, src, shallow=False)
    return dest.read_bytes() == want


def same_tree(bundle, a, b):
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.funny_files:
        return False
    if not all(same_file(bundle, a / f, b / f) for f in cmp.common_files):
        return False
    return all(same_tree(bundle, a / d, b / d) for d in cmp.common_dirs)


def in_sync(bundle, dest, src):
    if dest.is_symlink():
        return False
    if src.is_dir():
        return dest.is_dir() and same_tree(bundle, dest, src)
    return dest.is_file() and same_file(bundle, dest, src)


def copy(bundle, dest, src):
    if dest.is_symlink() or dest.is_file():
        dest.unlink()
    elif dest.is_dir():
        shutil.rmtree(dest)
    if src.is_dir():
        shutil.copytree(src, dest)
        for f in dest.rglob("SKILL.md"):
            want = transformed(bundle, src / f.relative_to(dest))
            if want is not None:
                f.write_bytes(want)
    else:
        shutil.copy2(src, dest)
        want = transformed(bundle, src)
        if want is not None:
            dest.write_bytes(want)


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
            if in_sync(bundle, dest, src):
                continue
            drift.append(str(rel))
            if not args.check:
                copy(bundle, dest, src)

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
