#!/usr/bin/env python3
"""Render team/<agent>/skills/<skill>/SKILL.md.tmpl -> sibling SKILL.md.

Include syntax: a line containing only `{{> section-name}}` is replaced by
the contents of skills/_sections/<section-name>.md (one trailing newline
trimmed). Anything else, including other `{{...}}`, is left verbatim.

The generated SKILL.md carries a one-line HTML comment right after the
frontmatter naming its source. Edit the .tmpl or the section, never the
generated file. Run sync-skills.py afterwards to mirror into skills/.

Usage:
  gen-skill-docs.py          write all outputs
  gen-skill-docs.py --check  exit 1 if any output is stale/missing or a
                             section is unknown (read-only)
"""

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TEAM_DIR = REPO_ROOT / "team"
SECTIONS_DIR = REPO_ROOT / "skills" / "_sections"

INCLUDE_RE = re.compile(r"^\{\{> ([a-z0-9][a-z0-9-]*)\}\}$")
FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.S)
MARKER = "<!-- GENERATED from SKILL.md.tmpl by scripts/gen-skill-docs.py — edit the .tmpl or skills/_sections/*.md, not this file -->\n"


def find_templates(team_dir):
    out = []
    for root, _dirs, files in os.walk(team_dir):
        p = Path(root)
        if p.parent.name == "skills" and "SKILL.md.tmpl" in files:
            out.append(p / "SKILL.md.tmpl")
    return sorted(out)


def render(tmpl_text, sections_dir):
    """Return (rendered, errors)."""
    errors = []
    lines = []
    for i, line in enumerate(tmpl_text.split("\n")):
        m = INCLUDE_RE.match(line)
        if m:
            sec = sections_dir / f"{m.group(1)}.md"
            if not sec.is_file():
                errors.append(f"line {i + 1}: unknown section '{m.group(1)}'")
                lines.append(line)
                continue
            body = sec.read_text()
            lines.append(body[:-1] if body.endswith("\n") else body)
        else:
            lines.append(line)
    text = "\n".join(lines)
    fm = FRONTMATTER_RE.match(text)
    if not fm:
        errors.append("missing frontmatter")
        return text, errors
    return text[: fm.end()] + MARKER + text[fm.end() :], errors


def run(team_dir=TEAM_DIR, sections_dir=SECTIONS_DIR, check=False):
    problems, written, ok = [], 0, 0
    for tmpl in find_templates(team_dir):
        rel = tmpl.relative_to(team_dir)
        out, errs = render(tmpl.read_text(), sections_dir)
        if errs:
            problems += [f"error: {rel}: {e}" for e in errs]
            continue
        dest = tmpl.with_name("SKILL.md")
        cur = dest.read_text() if dest.exists() else None
        if cur == out:
            ok += 1
        elif check:
            problems.append(
                f"{'missing' if cur is None else 'stale'}: {dest.relative_to(team_dir)} (re-run scripts/gen-skill-docs.py)"
            )
        else:
            dest.write_text(out)
            written += 1
    return problems, written, ok


def main(argv):
    check = "--check" in argv
    problems, written, ok = run(check=check)
    for p in problems:
        print(p)
    if check:
        print(f"{ok} up to date, {len(problems)} problem(s)")
    else:
        print(f"{written} written, {ok} unchanged, {len(problems)} error(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
