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
from the same path at the root. bundle/<team>/scripts/<file> is refreshed from
scripts/<file> (a script a skill runs from ${CLAUDE_PLUGIN_ROOT}/scripts, such
as tonone-doctor.py), except the bundle-owned installers in BUNDLE_OWNED_SCRIPTS.
Add or remove a member by adding or removing it in the bundle, then run this
script. Any symlink still in a bundle is replaced by a copy.

Every root skill must be in at least one bundle or be listed in
bundle/UNBUNDLED.txt (see below). --check reports "skill X is in no bundle"
for any that is neither, so a new skill cannot silently ship to nobody who
installs a bundle.

bundle/CORE_EXCLUDED.txt records what the lean tonone-core plugin leaves out on
purpose. --check also fails when an engineering-team skill is in neither core nor
that list, when core ships hooks/ or lib/, or when a core skill cites a repo path
(team/<a>/reference|scripts|hooks|skills/..., docs/<x>.md, lib/<x>) core lacks.

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

# bundle/<team>/scripts/ files that belong to the bundle and have no root twin.
BUNDLE_OWNED_SCRIPTS = {"install-all.sh"}

# Skills deliberately in no bundle. Two sections, one name per line, '#' comments:
#   [ROOT_ONLY]         skills that only make sense in the full `tonone` root plugin
#   [LEGACY_UNBUNDLED]  skills that predate the guard, grandfathered (sorted)
# New skills must join a bundle (create bundle/<team>/skills/<name>/ and run this
# script) or, with a stated reason, be added here.
UNBUNDLED_FILE = BUNDLE_DIR / "UNBUNDLED.txt"
SECTIONS = ("ROOT_ONLY", "LEGACY_UNBUNDLED")

# What the lean tonone-core plugin deliberately leaves out, same file style:
#   [SKILLS]  engineering-team skills not in tonone-core (one-line reason each)
#   [REFS]    repo paths tonone-core skills mention that core does not ship
CORE = "tonone-core"
CORE_EXCLUDED_FILE = BUNDLE_DIR / "CORE_EXCLUDED.txt"
CORE_SECTIONS = ("SKILLS", "REFS")


def load_sections(path, sections):
    """Return {section: [names in file order]} from a [SECTION] list file."""
    out = {name: [] for name in sections}
    section = None
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            if section not in out:
                raise ValueError(f"{path.name}: unknown section [{section}]")
        elif section is None:
            raise ValueError(f"{path.name}: '{line}' before any [SECTION]")
        else:
            out[section].append(line)
    return out


def load_unbundled(path=None):
    """Return {section: [names in file order]} from bundle/UNBUNDLED.txt."""
    return load_sections(path or UNBUNDLED_FILE, SECTIONS)


def load_core_excluded(path=None):
    """Return {section: [names]} from bundle/CORE_EXCLUDED.txt."""
    return load_sections(path or CORE_EXCLUDED_FILE, CORE_SECTIONS)


def root_skills():
    return {
        p.name
        for p in (REPO_ROOT / "skills").iterdir()
        if p.is_dir() and not p.name.startswith("_")
    }


def bundled_skills():
    names = set()
    for bundle in BUNDLE_DIR.iterdir():
        if (bundle / "skills").is_dir():
            names |= {p.name for p in (bundle / "skills").iterdir() if p.is_dir()}
    return names


def coverage_problems():
    """Lines describing skills in no bundle and an exemption list out of step."""
    listed = load_unbundled()
    exempt = set(listed["ROOT_ONLY"]) | set(listed["LEGACY_UNBUNDLED"])
    roots, bundled = root_skills(), bundled_skills()
    out = [
        f"skill {n} is in no bundle (add bundle/<team>/skills/{n}/ and run "
        f"sync-bundles.py, or list it in bundle/UNBUNDLED.txt)"
        for n in sorted(roots - bundled - exempt)
    ]
    out += [
        f"UNBUNDLED.txt lists {n}, which is bundled: remove it from the list"
        for n in sorted(exempt & bundled)
    ]
    out += [
        f"UNBUNDLED.txt lists {n}, which is not a root skill: remove it"
        for n in sorted(exempt - roots)
    ]
    return out


# Repo paths a skill can cite that a bundle must also ship (when they exist at
# the repo root). Placeholders (<agent>, *) are ignored.
REF_RE = re.compile(
    r"(?<![\w./-])("
    r"team/[a-z0-9_-]+/(?:reference|scripts|hooks|skills)/[A-Za-z0-9_./-]*[A-Za-z0-9_]"
    r"|docs/[A-Za-z0-9_-]+\.md"
    r"|lib/[A-Za-z0-9_-][A-Za-z0-9_./-]*[A-Za-z0-9_]"
    r")(?![\w<*])"
)


def skill_refs(bundle, repo_root=None):
    """Return {repo path: [skills]} for existing root paths a bundle's skills cite."""
    repo_root = repo_root or REPO_ROOT
    out = {}
    for skill_md in sorted((bundle / "skills").glob("*/SKILL.md")):
        for m in REF_RE.finditer(skill_md.read_text()):
            ref = m.group(1)
            if (repo_root / ref).exists():
                out.setdefault(ref, []).append(skill_md.parent.name)
    return out


def core_problems(bundle_dir=None, excluded=None, repo_root=None):
    """Drift lines for tonone-core vs engineering-team (pure on its inputs)."""
    bundle_dir = bundle_dir or BUNDLE_DIR
    excluded = excluded if excluded is not None else load_core_excluded()
    core, eng = bundle_dir / CORE, bundle_dir / "engineering-team"
    names = lambda b: (
        {p.name for p in (b / "skills").iterdir() if p.is_dir()}
        if (b / "skills").is_dir()
        else set()
    )
    in_core, in_eng = names(core), names(eng)
    skip = set(excluded["SKILLS"])
    out = [
        f"engineering skill {n} is in neither tonone-core nor CORE_EXCLUDED.txt "
        f"[SKILLS]: add bundle/{CORE}/skills/{n}/ or list it with a reason"
        for n in sorted(in_eng - in_core - skip)
    ]
    out += [
        f"CORE_EXCLUDED.txt [SKILLS] lists {n}, which is in tonone-core: remove it"
        for n in sorted(skip & in_core)
    ]
    out += [
        f"CORE_EXCLUDED.txt [SKILLS] lists {n}, which is not an engineering-team skill: remove it"
        for n in sorted(skip - in_eng)
    ]
    out += [
        f"tonone-core must not ship {d}/ (no hooks, no lib)"
        for d in ("hooks", "lib")
        if (core / d).exists()
    ]
    refs = skill_refs(core, repo_root)
    skip_refs = set(excluded["REFS"])
    out += [
        f"tonone-core skill {skills[0]} cites {ref}, which tonone-core does not "
        f"ship: add it to the bundle or list it in CORE_EXCLUDED.txt [REFS]"
        for ref, skills in sorted(refs.items())
        if ref not in skip_refs and not (core / ref).exists()
    ]
    for ref in sorted(skip_refs):
        if ref not in refs:
            out.append(
                f"CORE_EXCLUDED.txt [REFS] lists {ref}, which no tonone-core skill cites: remove it"
            )
        elif (core / ref).exists():
            out.append(
                f"CORE_EXCLUDED.txt [REFS] lists {ref}, which tonone-core ships: remove it"
            )
    return out


def members(bundle):
    """Yield (bundle_path, source_path) for every agent and skill in a bundle."""
    for entry in sorted((bundle / "agents").glob("*.md")):
        yield entry, REPO_ROOT / "agents" / entry.name
    skills = bundle / "skills"
    if skills.is_dir():
        for entry in sorted(skills.iterdir()):
            yield entry, REPO_ROOT / "skills" / entry.name
    # Shared reference files a bundle ships so its skills' repo-relative
    # paths (docs/output-kit.md, team/prism/reference/...) still resolve, and
    # lib/ scripts its skills run (lib/copy-gate, lib/site-signals), which
    # they locate under ${CLAUDE_PLUGIN_ROOT}/lib.
    for sub in ("docs", "team"):
        for entry in sorted((bundle / sub).rglob("*")):
            if entry.is_file():
                yield entry, REPO_ROOT / entry.relative_to(bundle)
    # scripts/ files skills run from ${CLAUDE_PLUGIN_ROOT}/scripts. The
    # bundle-owned installers have no root counterpart and are left alone.
    scripts = bundle / "scripts"
    if scripts.is_dir():
        for entry in sorted(scripts.iterdir()):
            if entry.is_file() and entry.name not in BUNDLE_OWNED_SCRIPTS:
                yield entry, REPO_ROOT / "scripts" / entry.name
    # lib/ membership is by directory: a bundle that ships lib/<name> gets
    # every file in it, so a file added to lib/<name> later is not skipped.
    lib = bundle / "lib"
    if lib.is_dir():
        for pkg in sorted(p for p in lib.iterdir() if p.is_dir()):
            src_pkg = REPO_ROOT / "lib" / pkg.name
            seen = set()
            for src in sorted(src_pkg.rglob("*")):
                if src.is_file() and "__pycache__" not in src.parts:
                    seen.add(src.relative_to(src_pkg))
                    yield lib / pkg.name / src.relative_to(src_pkg), src
            # A file removed from lib/<name> at the root shows up as a
            # missing source instead of lingering in the bundle.
            for dest in sorted(pkg.rglob("*")):
                rel = dest.relative_to(pkg)
                if (
                    dest.is_file()
                    and "__pycache__" not in dest.parts
                    and rel not in seen
                ):
                    yield dest, src_pkg / rel


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
        dest.parent.mkdir(parents=True, exist_ok=True)
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

    uncovered = coverage_problems() + core_problems()
    for line in missing:
        print(f"missing source: {line}")
    for line in uncovered:
        print(line)
    if args.check:
        for line in drift:
            print(f"out of sync: {line}")
        if drift or missing or uncovered:
            print("Run: python scripts/sync-bundles.py")
            return 1
        print("Bundles in sync.")
        return 0

    print(f"Refreshed {len(drift)} bundle entries.")
    return 1 if missing or uncovered else 0


if __name__ == "__main__":
    sys.exit(main())
