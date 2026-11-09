#!/usr/bin/env python3
"""Estimate the startup context cost of the tonone skill/agent listing.

Claude Code lists every skill and agent (name + description) at session start.
This script estimates that cost from root skills/*/SKILL.md and agents/*.md.

Method: cost per entry = len(name) + len(description) + ENTRY_OVERHEAD chars.
Tokens are ESTIMATED as chars / 4 (not a real tokenizer).

Usage: measure-context.py [--top N] [--json] [--max-desc N]
"""

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRY_OVERHEAD = 8  # chars per entry for list punctuation ("- name: " + newline)
CHARS_PER_TOKEN = 4

# web-app preset from team/apex/skills/apex-profile/SKILL.md
WEB_APP_PRESET = ["apex", "spine", "flux", "prism", "proof", "warden", "crest"]


def parse_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"---\s*\n(.*?)\n---", text, re.S)
    out = {}
    if not m:
        return out
    for line in m.group(1).splitlines():
        km = re.match(r"^(name|description):\s*(.*)$", line)
        if km:
            v = km.group(2).strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            out[km.group(1)] = v
    return out


def load(pattern):
    entries = []
    for p in sorted(ROOT.glob(pattern)):
        fm = parse_frontmatter(p)
        name = fm.get("name") or (p.parent.name if p.name == "SKILL.md" else p.stem)
        desc = fm.get("description", "")
        entries.append(
            {
                "name": name,
                "description_len": len(desc),
                "chars": len(name) + len(desc) + ENTRY_OVERHEAD,
            }
        )
    return entries


def totals(entries):
    chars = sum(e["chars"] for e in entries)
    return {
        "entries": len(entries),
        "chars": chars,
        "est_tokens": round(chars / CHARS_PER_TOKEN),
    }


def in_preset(kind, e, preset):
    if kind == "agent":
        return e["name"] in preset
    return any(e["name"].startswith(a + "-") for a in preset)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--max-desc",
        type=int,
        default=None,
        help="exit 1 if any description exceeds N chars",
    )
    a = ap.parse_args()

    skills = load("skills/*/SKILL.md")
    agents = load("agents/*.md")
    for e in skills:
        e["kind"] = "skill"
    for e in agents:
        e["kind"] = "agent"
    allents = skills + agents

    prof_s = [e for e in skills if in_preset("skill", e, WEB_APP_PRESET)]
    prof_a = [e for e in agents if in_preset("agent", e, WEB_APP_PRESET)]
    top = sorted(allents, key=lambda e: -e["description_len"])[: a.top]
    lens = sorted(e["description_len"] for e in allents)
    median = lens[len(lens) // 2] if lens else 0

    res = {
        "method": "est_tokens = chars/4; chars = len(name)+len(description)+%d per entry"
        % ENTRY_OVERHEAD,
        "skills": totals(skills),
        "agents": totals(agents),
        "combined": totals(allents),
        "web_app_profile": {
            "agents": WEB_APP_PRESET,
            "skills": totals(prof_s),
            "agent_entries": totals(prof_a),
            "combined": totals(prof_s + prof_a),
        },
        "median_description_len": median,
        "top_descriptions": [
            {"kind": e["kind"], "name": e["name"], "len": e["description_len"]}
            for e in top
        ],
    }
    over = [
        e
        for e in allents
        if a.max_desc is not None and e["description_len"] > a.max_desc
    ]

    if a.json:
        if a.max_desc is not None:
            res["over_max_desc"] = [
                {"kind": e["kind"], "name": e["name"], "len": e["description_len"]}
                for e in over
            ]
        print(json.dumps(res, indent=2))
    else:
        print("Method: " + res["method"])
        for k in ("skills", "agents", "combined"):
            t = res[k]
            print(
                "%-9s entries=%-4d chars=%-7d est_tokens=%d"
                % (k, t["entries"], t["chars"], t["est_tokens"])
            )
        w = res["web_app_profile"]
        print(
            "web-app profile (%s): entries=%d chars=%d est_tokens=%d"
            % (
                ",".join(WEB_APP_PRESET),
                w["combined"]["entries"],
                w["combined"]["chars"],
                w["combined"]["est_tokens"],
            )
        )
        print("median description len: %d" % median)
        print("Top %d longest descriptions:" % a.top)
        for e in top:
            print("  %4d  %-6s %s" % (e["description_len"], e["kind"], e["name"]))
        if over:
            print("OVER --max-desc %d: %d entries" % (a.max_desc, len(over)))
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
