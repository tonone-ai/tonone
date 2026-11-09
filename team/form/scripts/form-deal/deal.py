#!/usr/bin/env python3
"""form-deal: deterministic palette + type-pairing picker. Stdlib only, Python 3.9+.

  deal.py --trade saas --page-kind landing [--form-kind software] [--seed S]
          [--history PATH] [--avoid-last N] [--json] [--record] [--check]

Data lives in ../../skills/form-deal/{palettes,type}.json relative to this file.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent.parent / "skills" / "form-deal"
DEFAULT_HISTORY = ".tonone/design-history.json"
PAL_ROLES = ["bg", "surface", "text", "muted", "accent", "on-accent", "border"]
PAL_FIELDS = ["id", "name", "tags", "mode", "roles", "contrast"]
TYPE_FIELDS = ["id", "display", "body", "tags", "rationale", "source", "license"]
OVERUSED = {"inter", "roboto", "arial", "open sans", "poppins", "montserrat", "lato"}


# ---------- color math ----------
def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def lum(h):
    def ch(v):
        v /= 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (ch(v) for v in rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


def hsl(h):
    import colorsys

    r, g, b = (v / 255.0 for v in rgb(h))
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    return hh * 360, ss, ll


def basin_problems(roles):
    out = []
    bg, acc = roles["bg"], roles["accent"]
    r1, r2 = rgb(bg), rgb("#F4F1EA")
    dist = sum((a - b) ** 2 for a, b in zip(r1, r2)) ** 0.5
    if dist < 25 and r1[0] - r1[2] >= 8:  # warm cream only; cool grays are fine
        out.append("bg within cream basin (#F4F1EA)")
    if lum(bg) < 0.02:
        h, s, l = hsl(acc)
        if 70 <= h <= 150 and s > 0.6 and l > 0.4:
            out.append("near-black bg + acid-green accent")
        if (h <= 22 or h >= 352) and s > 0.7 and l > 0.4:
            out.append("near-black bg + vermilion accent")
    return out


# ---------- io ----------
def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def read_history(path):
    """Fail open: missing/corrupt -> []."""
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(d, dict):
        d = d.get("entries", [])
    return [e for e in d if isinstance(e, dict)] if isinstance(d, list) else []


def write_history(path, entry):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    entries = read_history(p)
    entries.append(entry)
    p.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")


# ---------- deal ----------
def candidates(items, wanted):
    wanted = {w.lower() for w in wanted if w}
    scored = [(len(wanted & {t.lower() for t in i["tags"]}), i) for i in items]
    hit = [i for s, i in scored if s > 0]
    return sorted(hit or items, key=lambda i: i["id"])


def pick(cands, used, seed, salt):
    pool = [c for c in cands if c["id"] not in used] or cands
    n = int(hashlib.sha256(f"{seed}|{salt}".encode()).hexdigest(), 16)
    return pool[n % len(pool)]


def deal(args):
    hist = read_history(args.history)
    recent = hist[-args.avoid_last :] if args.avoid_last > 0 else []
    seed = args.seed or f"{args.trade}|{args.page_kind}|{len(hist)}"
    wanted = [args.trade, args.page_kind, args.form_kind]
    pal = pick(
        candidates(load("palettes.json"), wanted),
        {e.get("palette") for e in recent},
        seed,
        "palette",
    )
    typ = pick(
        candidates(load("type.json"), wanted),
        {e.get("type") for e in recent},
        seed,
        "type",
    )
    return {
        "trade": args.trade,
        "page_kind": args.page_kind,
        "seed": seed,
        "palette": pal,
        "type": typ,
    }


def render(d):
    p, t = d["palette"], d["type"]
    r, c = p["roles"], p["contrast"]
    lines = [
        f"FORM ── form-deal  {d['trade']} / {d['page_kind']}  (seed {d['seed']})",
        f"Palette  {p['id']} — {p['name']} [{p['mode']}]",
        "  " + "  ".join(f"{k} {v}" for k, v in r.items() if isinstance(v, str)),
        f"  text/bg {c['text-bg']}:1  muted/bg {c['muted-bg']}:1  on-accent/accent {c['on-accent-accent']}:1",
        f"Type     {t['id']} — {t['display']} / {t['body']}"
        + (f" / {t['mono']}" if t.get("mono") else ""),
        f"  {t['rationale']}  ({t['license']})",
        "Starting deal, not a verdict. Re-deal with --seed or accept with --record.",
    ]
    return "\n".join(lines)


# ---------- check ----------
def check():
    errs = []
    try:
        pals, types = load("palettes.json"), load("type.json")
    except Exception as e:
        print(f"FAIL cannot load data: {e}")
        return 1
    seen = set()
    for p in pals:
        pid = p.get("id", "?")
        for f in PAL_FIELDS:
            if f not in p:
                errs.append(f"palette {pid}: missing {f}")
        if pid in seen:
            errs.append(f"palette {pid}: duplicate id")
        seen.add(pid)
        r = p.get("roles", {})
        miss = [k for k in PAL_ROLES if k not in r]
        if miss:
            errs.append(f"palette {pid}: missing roles {miss}")
            continue
        if p.get("mode") not in ("light", "dark"):
            errs.append(f"palette {pid}: bad mode")
        got = {
            "text-bg": ratio(r["text"], r["bg"]),
            "muted-bg": ratio(r["muted"], r["bg"]),
            "on-accent-accent": ratio(r["on-accent"], r["accent"]),
        }
        stated = p.get("contrast", {})
        for k, v in got.items():
            if abs(stated.get(k, -1) - v) > 0.01:
                errs.append(
                    f"palette {pid}: stated {k} {stated.get(k)} != computed {v}"
                )
        if got["text-bg"] < 4.5:
            errs.append(f"palette {pid}: text/bg {got['text-bg']} < 4.5")
        if got["on-accent-accent"] < 4.5:
            errs.append(
                f"palette {pid}: on-accent/accent {got['on-accent-accent']} < 4.5"
            )
        if got["muted-bg"] < 4.5 and not (
            p.get("muted_large_only") and got["muted-bg"] >= 3
        ):
            errs.append(f"palette {pid}: muted/bg {got['muted-bg']} < 4.5")
        errs += [f"palette {pid}: {b}" for b in basin_problems(r)]
    seen = set()
    for t in types:
        tid = t.get("id", "?")
        for f in TYPE_FIELDS:
            if f not in t:
                errs.append(f"type {tid}: missing {f}")
        if tid in seen:
            errs.append(f"type {tid}: duplicate id")
        seen.add(tid)
        if str(t.get("display", "")).lower() in OVERUSED:
            errs.append(f"type {tid}: overused display face {t['display']}")
        if (
            str(t.get("display", "")).lower() == str(t.get("body", "")).lower()
            and str(t.get("display", "")).lower() in OVERUSED
        ):
            errs.append(f"type {tid}: single overused face")
    if errs:
        print(f"FAIL {len(errs)} problem(s)")
        for e in errs:
            print("  ■ " + e)
        return 1
    print(
        f"OK {len(pals)} palettes, {len(types)} pairings: schema, WCAG AA, basin checks pass"
    )
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="form-deal palette + type picker")
    ap.add_argument("--trade", default="")
    ap.add_argument("--page-kind", default="")
    ap.add_argument("--form-kind", default="")
    ap.add_argument("--seed")
    ap.add_argument("--history", default=DEFAULT_HISTORY)
    ap.add_argument("--avoid-last", type=int, default=3)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    if a.check:
        return check()
    d = deal(a)
    if a.record:
        write_history(
            a.history,
            {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "trade": a.trade,
                "page_kind": a.page_kind,
                "palette": d["palette"]["id"],
                "type": d["type"]["id"],
            },
        )
    print(json.dumps(d, indent=2) if a.json else render(d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
