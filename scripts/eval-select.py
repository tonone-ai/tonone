#!/usr/bin/env python3
"""Select (and optionally run) evals whose touchfiles match changed files.

    python3 scripts/eval-select.py                     # git diff <base>...HEAD
    python3 scripts/eval-select.py --base origin/main
    python3 scripts/eval-select.py --files a.py b.js
    python3 scripts/eval-select.py --all
    python3 scripts/eval-select.py --run               # pytest the selection

Evals live in tests/evals/<name>/eval.json with {"name","description","touchfiles"}.
Globs are repo-relative: `**` crosses directories, `*` and `?` do not.
Changing a GLOBAL_TOUCHFILES path selects every eval. Stdlib only.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS = REPO / "tests" / "evals"

GLOBAL_TOUCHFILES = [
    "scripts/eval-select.py",
    "tests/evals/conftest.py",
    "tests/evals/README.md",
]


def glob_to_re(glob: str) -> "re.Pattern[str]":
    g = glob.replace("\\", "/")
    if g.startswith("./"):
        g = g[2:]
    out, i = "", 0
    while i < len(g):
        c = g[i]
        if c == "*":
            if g[i + 1 : i + 2] == "*":
                i += 1
                if g[i + 1 : i + 2] == "/":
                    i += 1
                    out += "(?:.*/)?"
                else:
                    out += ".*"
            else:
                out += "[^/]*"
        elif c == "?":
            out += "[^/]"
        else:
            out += re.escape(c)
        i += 1
    return re.compile("^" + out + "$")


def matches(path: str, globs) -> bool:
    p = path.replace("\\", "/")
    if p.startswith("./"):
        p = p[2:]
    return any(glob_to_re(g).match(p) for g in globs)


def load_evals(root: Path = EVALS) -> list[dict]:
    evals = []
    for f in sorted(root.glob("*/eval.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            raise SystemExit(f"eval-select: bad {f}: {e}")
        tf = d.get("touchfiles")
        if not d.get("name") or not isinstance(tf, list) or not tf:
            raise SystemExit(f"eval-select: {f} needs name and non-empty touchfiles")
        evals.append({**d, "dir": f.parent})
    return evals


def select(changed, evals, select_all=False, global_files=GLOBAL_TOUCHFILES):
    """Return the evals to run, in name order."""
    if select_all or any(matches(c, global_files) for c in changed):
        return list(evals)
    return [e for e in evals if any(matches(c, e["touchfiles"]) for c in changed)]


def git_changed(base):
    cands = [base] if base else ["origin/main", "main"]
    for b in cands:
        r = subprocess.run(
            ["git", "diff", "--name-only", f"{b}...HEAD"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        if r.returncode == 0:
            return [l for l in r.stdout.splitlines() if l.strip()]
    raise SystemExit(
        f"eval-select: cannot diff against {' or '.join(cands)}; use --base or --files"
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--files", nargs="+", metavar="PATH")
    ap.add_argument("--base", help="git base ref (default origin/main, then main)")
    ap.add_argument("--all", action="store_true", help="select every eval")
    ap.add_argument("--run", action="store_true", help="run pytest on selected evals")
    args = ap.parse_args(argv)

    evals = load_evals()
    changed = [] if args.all else (args.files or git_changed(args.base))
    chosen = select(changed, evals, args.all)

    if not args.run:
        for e in chosen:
            print(e["name"])
        return 0
    if not chosen:
        print("eval-select: no evals selected", file=sys.stderr)
        return 0
    dirs = [str(e["dir"]) for e in chosen]
    return subprocess.call([sys.executable, "-m", "pytest", "-q", *dirs], cwd=REPO)


if __name__ == "__main__":
    sys.exit(main())
