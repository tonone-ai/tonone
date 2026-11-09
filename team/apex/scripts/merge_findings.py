#!/usr/bin/env python3
"""Merge apex-review lens outputs (stdlib only).

Usage:
  merge_findings.py lens1.json lens2.json ... [--red red.json]

Prints merged JSON: {"findings": [...], "dropped": [...], "verdict": "..."}.
Rules: drop findings without evidence or with bad severity; dedupe on
file + line + normalized title; keep max severity; record agreeing lenses;
red-team disputes (with evidence) mark a finding disputed.
Verdict: undisputed CRITICAL -> BLOCK; undisputed HIGH, or any disputed
CRITICAL -> FIX-FIRST; else SHIP.
"""

import json
import re
import sys

SEV = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
CONF = {"low": 0, "medium": 1, "high": 2}


def normalize_title(title):
    return re.sub(r"[^a-z0-9 ]+", "", str(title).lower()).split()


def _key(f):
    return (
        f.get("file") or "",
        f.get("line"),
        " ".join(normalize_title(f.get("title", ""))),
    )


def _valid(f):
    if f.get("severity") not in SEV:
        return "bad severity"
    if not str(f.get("evidence") or "").strip():
        return "no evidence"
    return None


def merge(docs):
    """docs: list of schema documents. Returns (findings, dropped)."""
    merged, dropped = {}, []
    for doc in docs:
        lens = doc.get("lens", "?")
        for f in doc.get("findings", []):
            why = _valid(f)
            if why:
                dropped.append({"id": f.get("id"), "lens": lens, "reason": why})
                continue
            k = _key(f)
            cur = merged.get(k)
            if cur is None:
                merged[k] = dict(f, lenses=[lens], ids=[f["id"]], disputed=False)
                continue
            if lens not in cur["lenses"]:
                cur["lenses"].append(lens)
            cur["ids"].append(f["id"])
            if SEV[f["severity"]] > SEV[cur["severity"]]:
                for field in ("severity", "evidence", "impact", "fix"):
                    cur[field] = f[field]
            if CONF.get(f.get("confidence"), 0) > CONF.get(cur.get("confidence"), 0):
                cur["confidence"] = f["confidence"]
    out = sorted(
        merged.values(), key=lambda f: (-SEV[f["severity"]], f["file"], f["line"] or 0)
    )
    return out, dropped


def apply_red(findings, red_doc):
    """Merge red's new findings in; mark disputed findings. Returns (findings, dropped)."""
    new, dropped = merge(
        [{"lens": red_doc.get("lens", "red"), "findings": red_doc.get("findings", [])}]
    )
    base = {_key(f): f for f in findings}
    for f in new:
        cur = base.get(_key(f))
        if cur:
            for l in f["lenses"]:
                if l not in cur["lenses"]:
                    cur["lenses"].append(l)
            if SEV[f["severity"]] > SEV[cur["severity"]]:
                cur.update({k: f[k] for k in ("severity", "evidence", "impact", "fix")})
        else:
            base[_key(f)] = f
    out = list(base.values())
    for d in red_doc.get("disputes", []):
        if not str(d.get("evidence") or "").strip():
            dropped.append(
                {"id": d.get("id"), "lens": "red", "reason": "dispute without evidence"}
            )
            continue
        for f in out:
            if d.get("id") in f["ids"]:
                f["disputed"] = True
                f["dispute"] = {"reason": d.get("reason"), "evidence": d["evidence"]}
    out.sort(key=lambda f: (-SEV[f["severity"]], f["file"], f["line"] or 0))
    return out, dropped


def verdict(findings):
    live = [f for f in findings if not f.get("disputed")]
    if any(f["severity"] == "CRITICAL" for f in live):
        return "BLOCK"
    if any(f["severity"] == "HIGH" for f in live) or any(
        f["severity"] == "CRITICAL" for f in findings
    ):
        return "FIX-FIRST"
    return "SHIP"


def main(argv):
    red_path, paths = None, []
    it = iter(argv)
    for a in it:
        if a == "--red":
            red_path = next(it, None)
        else:
            paths.append(a)
    docs = [json.load(open(p)) for p in paths]
    findings, dropped = merge(docs)
    if red_path:
        findings, d2 = apply_red(findings, json.load(open(red_path)))
        dropped += d2
    json.dump(
        {"findings": findings, "dropped": dropped, "verdict": verdict(findings)},
        sys.stdout,
        indent=2,
    )
    print()


if __name__ == "__main__":
    main(sys.argv[1:])
