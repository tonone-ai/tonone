#!/usr/bin/env python3
"""
Check the upstream plugins tonone borrows from for newer releases.

tonone's agents, skills, and the lib/uiux corpus carry patterns absorbed from a
handful of public Claude Code plugins. Those plugins keep shipping. This script
answers one question: which of them moved since we last read their diff?

Pinned versions live in docs/upstream.json; the narrative of what was taken from
each one lives in docs/upstream.md.

Usage:
    python scripts/check-upstream.py           # report drift, exit 1 if any
    python scripts/check-upstream.py --json    # machine-readable
    python scripts/check-upstream.py --quiet   # exit code only

Network access is required. On failure the script says so and exits 2 — an
unreachable API is not the same as "no drift".
"""

import argparse
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PINS = REPO / "docs" / "upstream.json"
API = "https://api.github.com/repos/{repo}/releases"
TIMEOUT = 15


def _releases(repo: str) -> list[dict]:
    """Fetch the release list for a repo.

    Prefers the `gh` CLI when it is installed and authenticated — the anonymous
    GitHub API allows 60 requests an hour, which one impatient afternoon burns
    through. Falls back to a plain HTTPS request otherwise.
    """
    if shutil.which("gh"):
        result = subprocess.run(
            ["gh", "api", f"repos/{repo}/releases", "--paginate=false"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )
        if result.returncode == 0:
            return json.loads(result.stdout)

    req = urllib.request.Request(
        API.format(repo=repo),
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "tonone-check-upstream",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def _fetch_latest_tag(repo: str, prefix: str | None) -> tuple[str | None, str | None]:
    """Return (tag, published_at) for the newest release matching prefix."""
    releases = _releases(repo)

    for release in releases:
        if release.get("draft") or release.get("prerelease"):
            continue
        tag = release.get("tag_name", "")
        if prefix and not tag.startswith(prefix):
            continue
        return tag, release.get("published_at", "")[:10]
    return None, None


def check() -> tuple[list[dict], list[str]]:
    """Return (rows, errors). Each row carries pinned vs latest for one upstream."""
    data = json.loads(PINS.read_text())
    rows, errors = [], []

    for entry in data["upstreams"]:
        row = {
            "name": entry["name"],
            "repo": entry["repo"],
            "pinned": entry["version"],
            "checked": entry["checked"],
            "latest": None,
            "published": None,
            "drift": False,
        }
        if entry.get("release_prefix") is None:
            row["latest"] = entry["version"]
            row["note"] = entry.get("note", "manual version tracking")
            rows.append(row)
            continue
        try:
            tag, published = _fetch_latest_tag(entry["repo"], entry["release_prefix"])
        except (
            urllib.error.URLError,
            TimeoutError,
            subprocess.SubprocessError,
            json.JSONDecodeError,
        ) as exc:
            errors.append(f"{entry['name']}: {exc}")
            rows.append(row)
            continue
        row["latest"] = tag
        row["published"] = published
        row["drift"] = bool(tag) and tag != entry["version"]
        rows.append(row)

    return rows, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--quiet", action="store_true", help="exit code only")
    args = parser.parse_args()

    rows, errors = check()
    drifted = [r for r in rows if r["drift"]]

    if args.json:
        print(json.dumps({"rows": rows, "errors": errors}, indent=2))
    elif not args.quiet:
        print("╭─ UPSTREAM CHECK ────────────────────────────────────────────╮")
        for r in rows:
            marker = "▲" if r["drift"] else "●"
            latest = r["latest"] or "unreachable"
            tail = (
                f" (published {r['published']})"
                if r["drift"] and r["published"]
                else ""
            )
            print(
                f"  {marker} {r['name']:<16} pinned {r['pinned']:<22} latest {latest}{tail}"
            )
        print("╰─────────────────────────────────────────────────────────────╯")
        if drifted:
            names = ", ".join(r["name"] for r in drifted)
            print(f"\n{len(drifted)} upstream(s) moved: {names}")
            print("Read the release notes, absorb what applies, then update")
            print("docs/upstream.json and the ledger in docs/upstream.md.")
        elif errors:
            print(f"\n{len(errors)} upstream(s) could not be checked — drift unknown.")
        else:
            print("\nAll pinned upstreams are current.")
        for err in errors:
            print(f"  ! could not check {err}", file=sys.stderr)

    if errors:
        return 2
    return 1 if drifted else 0


if __name__ == "__main__":
    sys.exit(main())
