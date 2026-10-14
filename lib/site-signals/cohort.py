#!/usr/bin/env python3
"""cohort — turn an observation log into a target list you can explain.

Reads the JSONL log that `profile.py --jsonl` appends to and answers one
question: which companies have every required signal and none of the
excluded ones? Only the latest observation of each (domain, signal) counts,
so re-profiling a company updates its answer, and anything below the
confidence floor is ignored.

A signal is "present" when its latest observation has a non-zero value_num,
or non-empty value_text when value_num is null. A row with value_num 0 is an
explicit absence, and only rows from a company's latest run count, so a fact
the latest run didn't see (gone, or unobservable that time) stops matching. Mind the names:
NO_ONLINE_BOOKING is present when there is no booking, so "has no booking"
is --require NO_ONLINE_BOOKING.
Match a specific value with CODE=text, e.g. TECH_STACK=HubSpot.

Usage:
    python3 cohort.py observations.jsonl \\
        --require RUNNING_GOOGLE_ADS,INCUMBENT_AGENCY,NO_ONLINE_BOOKING --exclude TECH_STACK=Calendly
    python3 cohort.py observations.jsonl --changes      # signals whose value moved

Prints exactly one JSON object. Exit 0, or 2 on a usage error.
"""

from __future__ import annotations

import argparse
import json
import sys

CONFIDENCE_FLOOR = 0.75


def load(path: str) -> list[dict]:
    """Observation rows. Failure rows only mark that a run happened."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if "domain" in row and ("signal" in row or "failure" in row):
                rows.append(row)
    return rows


def history(rows: list[dict]) -> dict:
    """{domain: {signal: [observations oldest..newest]}}; multi-valued
    signals (HIRING_ROLE, DECISION_MAKER) keep every row from the latest run."""
    out: dict = {}
    for r in sorted(rows, key=lambda r: r.get("observed_at", "")):
        if "signal" in r:
            out.setdefault(r["domain"], {}).setdefault(r["signal"], []).append(r)
    return out


def last_runs(rows: list[dict]) -> dict:
    """{domain: timestamp of its newest run}, counting failure-only runs."""
    out: dict = {}
    for r in rows:
        t = r.get("observed_at", "")
        if t > out.get(r["domain"], ""):
            out[r["domain"]] = t
    return out


def latest(obs: list[dict]) -> list[dict]:
    newest = obs[-1].get("observed_at", "")
    return [o for o in obs if o.get("observed_at", "") == newest]


def present(
    obs: list[dict], want_text: str | None, run: str = ""
) -> tuple[bool, list[dict]]:
    """Present in the company's latest run. A fact last seen in an older run
    is stale (the newer run couldn't see it, or it went away) and doesn't count."""
    hits = []
    if run and obs and obs[-1].get("observed_at", "") < run:
        return False, []
    for o in latest(obs):
        if o.get("confidence", 0) < CONFIDENCE_FLOOR:
            continue
        num, text = o.get("value_num"), (o.get("value_text") or "")
        if want_text is not None:
            if want_text.lower() in text.lower():
                hits.append(o)
        elif (num not in (None, 0)) or (num is None and text):
            hits.append(o)
    return bool(hits), hits


def parse_terms(raw: str | None) -> list[tuple[str, str | None]]:
    terms = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        code, _, text = part.partition("=")
        terms.append((code.strip().upper(), text.strip() or None))
    return terms


def cohort(rows, require, exclude) -> dict:
    hist, runs = history(rows), last_runs(rows)
    matches = []
    for domain, signals in sorted(hist.items()):
        run = runs.get(domain, "")
        reasons, ok = [], True
        for code, text in require:
            hit, evidence = (
                present(signals[code], text, run) if code in signals else (False, [])
            )
            if not hit:
                ok = False
                break
            reasons += [
                {
                    "signal": code,
                    "value": e.get("value_text") or e.get("value_num"),
                    "evidence_url": e.get("evidence_url"),
                }
                for e in evidence[:2]
            ]
        if not ok:
            continue
        if any(
            code in signals and present(signals[code], text, run)[0]
            for code, text in exclude
        ):
            continue
        matches.append({"domain": domain, "because": reasons})
    return {"companies_observed": len(hist), "matches": len(matches), "cohort": matches}


def _value_set(obs: list[dict]) -> tuple:
    vals = set()
    for o in obs:
        if o.get("value_num") == 0:
            continue  # an explicit "not observed this run"
        vals.add(o.get("value_text") or o.get("value_num"))
    return tuple(sorted(vals, key=str))


def changes(rows) -> list[dict]:
    """Signals whose value moved between a company's last two runs. Both runs
    must have a row for the signal; an explicit absence row (value_num 0)
    counts, so "stopped running ads" is reported but "couldn't see roles" isn't."""
    out = []
    by_domain: dict = {}
    for r in rows:
        by_domain.setdefault(r["domain"], set()).add(r.get("observed_at", ""))
    for domain, signals in sorted(history(rows).items()):
        domain_runs = sorted(by_domain.get(domain, ()))
        if len(domain_runs) < 2:
            continue
        t0, t1 = domain_runs[-2:]
        for code, obs in sorted(signals.items()):
            a = [o for o in obs if o.get("observed_at", "") == t0]
            b = [o for o in obs if o.get("observed_at", "") == t1]
            if not a or not b:
                continue  # not checked (or unobservable) in one run: unknown, not a change
            was, now = _value_set(a), _value_set(b)
            if was != now:
                out.append(
                    {
                        "domain": domain,
                        "signal": code,
                        "was": list(was) if len(was) != 1 else was[0],
                        "now": list(now) if len(now) != 1 else now[0],
                        "since": t0,
                        "observed_at": t1,
                        "evidence_url": b[0].get("evidence_url"),
                    }
                )
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Cohorts and changes over an observation log."
    )
    ap.add_argument("log")
    ap.add_argument("--require")
    ap.add_argument("--exclude")
    ap.add_argument("--changes", action="store_true")
    ap.add_argument("--pretty", action="store_true")
    args = ap.parse_args(argv)
    indent = 2 if args.pretty else None
    try:
        rows = load(args.log)
    except OSError as e:
        print(
            json.dumps({"ok": False, "error": f"cannot read log: {e}"}, indent=indent)
        )
        return 2
    if args.changes:
        print(
            json.dumps(
                {"ok": True, "changes": changes(rows)},
                indent=indent,
                ensure_ascii=False,
            )
        )
        return 0
    require, exclude = parse_terms(args.require), parse_terms(args.exclude)
    if not require:
        print(
            json.dumps(
                {"ok": False, "error": "pass --require with at least one signal"},
                indent=indent,
            )
        )
        return 2
    result = cohort(rows, require, exclude)
    print(
        json.dumps(
            {
                "ok": True,
                "require": args.require,
                "exclude": args.exclude or "",
                **result,
            },
            indent=indent,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
