#!/usr/bin/env python3
"""copy-gate — deterministic checks on outbound copy before a human sends it.

Prompts tell a writer what not to do; this script checks that it didn't.
Every skill that produces copy someone will send or publish (cold email,
press pitch, Hacker News post, landing copy, UI strings) writes its drafts to
a file and runs this gate as its last step. A FAIL finding means the draft
goes back for a rewrite; a WARN means a human should look.

No model, no network, no dependencies. Pattern adapted from Harvey's pre-send
gate (MIT, see NOTICE.md): constraints in the prompt, verification in code.

Input format — one or more messages, each starting with a `=== <label>` line
(text before the first marker is one unlabeled message). Optional header
lines directly under the marker:

    === touch-1 email
    Subject: inventory report
    {{first_name}}, most ops teams your size ...

    === hn-post
    Title: Show HN: A 400-line SQLite migration tool
    Body text ...

A marker may override the profile for that one message:
`=== touch-2 linkedin [profile=linkedin-note]`.

Usage:
    python3 gate.py --profile cold-email drafts.md
    python3 gate.py --profile marketing-copy --allow-tokens - < drafts.md
    python3 gate.py --profile marketing-copy --slop drafts.md
    python3 gate.py --profile slop --waive seamless drafts.md
    python3 gate.py --list-profiles

`--slop` (or the `slop` profile) adds the copy-slop floor: AI-tell words and
stock phrases, residue, and capped devices (em dashes, "Fast. Simple.",
"not X, but Y", trailing -ing riders, rule-of-three, rhetorical openers) with
a per-message score budget. Client-supplied words go in `--waive` or
`.tonone/copy-waivers.json`; each needs a reason. See README.md.

Prints exactly one JSON object. Exit 0 = no FAIL findings, 1 = at least one
FAIL, 2 = usage error (bad profile, unreadable file).
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

# ── phrase lists ─────────────────────────────────────────────────────────
# HARD: fail in every profile. Spam triggers and the tells that mark text as
# machine-written or templated no matter the channel.
HARD_PHRASES = (
    "i hope this finds you well",
    "hope this email finds you",
    "hope this message finds you",
    "i hope you're doing well",
    "i wanted to reach out",
    "just wanted to reach out",
    "reaching out because",
    "circling back",
    "just following up",
    "just checking in",
    "picture this",
    "what if i told you",
    "imagine a world",
    "in today's fast-paced",
    "in today's digital",
    "in today's competitive",
    "in the ever-evolving",
    "let that sink in",
    "as an ai",
    "as a language model",
    "i'm an ai",
    "i am an ai",
    "act now",
    "buy now",
    "click here",
    "click below",
    "limited time offer",
    "risk-free",
    "100% free",
    "make money",
    "double your",
    "guaranteed results",
    "congratulations, you",
    "exclusive deal",
    "special offer",
)

# SOFT: hype and filler. Fail where every word is scrutinised (cold email,
# pitches, HN), warn in long-form marketing and UI copy where a human editor
# makes the call.
SOFT_PHRASES = (
    "game-changer",
    "game changer",
    "game-changing",
    "revolutionize",
    "revolutionary",
    "cutting-edge",
    "cutting edge",
    "next-generation",
    "best-in-class",
    "world-class",
    "state-of-the-art",
    "supercharge",
    "unlock your",
    "unlock the power",
    "elevate your",
    "take it to the next level",
    "seamless",
    "seamlessly",
    "synergy",
    "delve",
    "harness the power",
    "empower your",
    "robust solution",
    "it's not just",
    "here's the thing",
    "quick question",
    "worth a quick",
    "i'd love to",
    "no pressure",
    "no obligation",
    "touch base",
    "hop on a call",
)

# Words that announce marketing on Hacker News; HN readers flag them on sight.
HN_HYPE = (
    "revolutionary",
    "game-changing",
    "disrupt",
    "disruptive",
    "amazing",
    "incredible",
    "ultimate",
    "blazing fast",
    "#1",
    "effortless",
)

MICROCOPY_SOFT = (
    "oops",
    "uh oh",
    "whoops",
    "something went wrong",
    "an error occurred",
    "simply",
    "just click",
    "easy",
    "obviously",
    "please note",
)

# ── regexes ──────────────────────────────────────────────────────────────
# {{first_name}}, {{ company | default }}, [[first_name]], Mailchimp *|FNAME|*
TOKEN_RE = re.compile(
    r"\{\{[^{}\n]{1,60}\}\}|\[\[[^\[\]\n]{1,60}\]\]|\*\|[A-Z0-9_:]{1,30}\|\*"
)
SINGLE_BRACE_RE = re.compile(r"(?<!\{)\{\s*[A-Za-z_][\w.\-]*\s*\}(?!\})")
# <Company>, <First Name>: angle-bracket slots. HTML tags are lowercase and
# caught separately by HTML_RE.
ANGLE_SLOT_RE = re.compile(r"<[A-Z][A-Za-z ]{1,30}>")
# Bracketed text that is not a template slot: checkboxes, [sic], editorial marks.
NOT_A_SLOT = {"x", "sic", "sp", "citation needed", "emphasis added", "sic!"}
# [Name], [subject line], [Customer X] — template slots the writer never
# filled. Markdown links "[text](url)" and [[tokens]] are excluded.
BRACKET_SLOT_RE = re.compile(r"(?<!\[)\[(?!\[)([A-Za-z][^\[\]\n]{0,48})\](?![\]\(\[:])")
TODO_RE = re.compile(r"\b(TODO|TBD|FIXME|XXX|lorem ipsum)\b|<insert\b", re.I)
URL_RE = re.compile(r"https?://[^\s)>\]]+|\bwww\.[^\s)>\]]+", re.I)
HTML_RE = re.compile(r"<\s*(html|body|div|span|table|img|a|p|br|style)\b", re.I)
CAPS_RE = re.compile(r"\b[A-Z]{6,}\b")
FAKE_THREAD_RE = re.compile(r"^\s*(re|fwd?|fw)\s*:", re.I)
# Dashes used as em dashes: the em dash itself, a spaced en dash, a spaced "--".
DASH_RE = re.compile("\u2014|\\s\u2013\\s|\\s--\\s")
HEADER_RE = re.compile(r"^\**\s*(subject|title)\s*:\s*\**\s*(.*?)\s*\**$", re.I)

# ── profiles ─────────────────────────────────────────────────────────────
# Limits are ceilings that block, not targets. Skills state their own
# (lower) targets in prose; the gate catches what slipped past them.
PROFILES = {
    "cold-email": {
        "about": "Cold outbound email (deal-outreach). Short, plain text, one link max.",
        "max_words": 125,
        "max_subject_chars": 60,
        "max_subject_words": 6,
        "max_links": 1,
        "em_dash": "FAIL",
        "max_exclaim": 0,
        "max_questions": 1,
        "soft": "FAIL",
        "extra": (),
        "require_subject": True,
        "subject_no_name": True,
        "no_i_we_opener": True,
    },
    "reply": {
        "about": "Reply in an existing email thread (deal-close objection replies). Re: subjects are fine.",
        "max_words": 150,
        "max_subject_chars": 80,
        "max_links": 1,
        "em_dash": "FAIL",
        "max_exclaim": 0,
        "max_questions": 2,
        "soft": "FAIL",
        "extra": (),
        "reply_thread": True,
    },
    "linkedin-note": {
        "about": "LinkedIn connection note or DM. 300 characters, no links.",
        "max_chars": 300,
        "max_links": 0,
        "em_dash": "FAIL",
        "max_exclaim": 0,
        "max_questions": 1,
        "soft": "FAIL",
        "extra": (),
    },
    "press-pitch": {
        "about": "Journalist, podcast or newsletter pitch email (buzz-pitch, buzz-outreach).",
        "max_words": 200,
        "max_subject_chars": 80,
        "max_links": 2,
        "em_dash": "WARN",
        "max_exclaim": 0,
        "max_questions": 2,
        "soft": "FAIL",
        "extra": (),
        "require_subject": True,
    },
    "press-release": {
        "about": "Press release body (buzz-pitch). Longer, but still no hype.",
        "max_words": 600,
        "max_links": 3,
        "em_dash": "WARN",
        "max_exclaim": 0,
        "soft": "FAIL",
        "extra": (),
    },
    "hn": {
        "about": "Hacker News submission (buzz-hn). Title <=80 chars, no hype, no links in body.",
        "max_title_chars": 80,
        "max_links": 0,
        "em_dash": "WARN",
        "max_exclaim": 0,
        "soft": "FAIL",
        "extra": HN_HYPE,
        "require_title": True,
        "soft_ignore": ("i'd love to",),  # "I'd love to hear feedback" is normal on HN
    },
    "marketing-copy": {
        "about": "Landing page and marketing copy (pitch-copy). Hype warns, placeholders fail.",
        "em_dash": "WARN",
        "max_exclaim": 1,
        "soft": "WARN",
        "extra": (),
    },
    "slop": {
        "about": "Slop floor only (copy-slop): AI-tell words, residue, capped devices, score budget.",
        "slop": True,
        "soft": "WARN",
        "extra": (),
    },
    "microcopy": {
        "about": "UI strings (copy-write): buttons, errors, empty states. Each block is one string.",
        "max_chars": 160,
        "em_dash": "WARN",
        "max_exclaim": 0,
        "soft": "WARN",
        "extra": MICROCOPY_SOFT,
        "single_brace_tokens": True,  # i18n: "Welcome back, {name}"
    },
}


# ── slop lists (copy-slop floor) ─────────────────────────────────────────
# Only words NOT already in HARD_PHRASES / SOFT_PHRASES live here; the slop
# score reuses those lists, so nothing is counted twice. Stems match any
# suffix: "leverag" covers leverage, leverages, leveraging.
SLOP_STEMS = (
    "tapestry",
    "leverag",
    "robust",
    "elevat",
    "unlock",
    "empower",
    "testament",
    "multifaceted",
    "pivotal",
    "embark",
    "foster",
    "bolster",
    "underscor",
    "paradigm",
    "transformative",
    "groundbreaking",
    "meticulous",
    "vibrant",
    "myriad",
    "plethora",
    "unparalleled",
    "unwavering",
    "holistic",
    "spearhead",
    "unleash",
    "realm of",
)

STOCK_PHRASES = (
    "look no further",
    "in the world of",
    "in the realm of",
    "when it comes to",
    "at the end of the day",
    "navigate the complexities",
    "a testament to",
    "plays a crucial role",
    "plays a vital role",
    "it's important to note",
    "it is important to note",
    "it's worth noting",
    "it is worth noting",
    "ever-changing landscape",
    "digital landscape",
    "rapidly evolving",
    "dive into",
    "dive deep into",
    "whether you're a",
    "the power of",
    "your one-stop",
    "tailored to your needs",
    "take your",
)

# Residue: text that proves a model or a template wrote it and nobody read it.
# Always FAIL under slop. Merge tokens stay legal under --allow-tokens unless
# the token name itself is a placeholder.
RESIDUE_PHRASES = (
    "i hope this helps",
    "hope that helps",
    "let me know if you'd like me to",
    "let me know if you need any further",
    "great question",
    "knowledge cutoff",
    "i cannot assist",
    "i can't assist with",
    "here's a draft",
    "here is a draft",
    "here's the revised",
    "dolor sit amet",
)
RESIDUE_OPENER_RE = re.compile(
    r"^\W*(certainly|absolutely|of course|sure thing|sure)\s*!", re.I
)
RESIDUE_SLOT_RE = re.compile(
    r"(?:\{\{|\[\[|\[|<)\s*(?:[\w ]*(?:placeholder|insert|your[ _]name|your[ _]company"
    r"|company[ _]name here|name here)[\w ]*)\s*(?:\}\}|\]\]|\]|>)",
    re.I,
)

# device -> (warn, fail). em_dash is a rate per 100 words; the rest are counts
# per message. Ceilings, like profile limits: they block, they are not targets.
DEVICES = {
    "em_dash": (1.0, 2.0),
    "fragment_heading": (1, 3),
    "contrast": (2, 4),
    "ing_rider": (2, 4),
    "triad": (3, 5),
    "rhetorical_opener": (1, 3),
}
DEVICE_ABOUT = {
    "em_dash": "em dashes per 100 words",
    "fragment_heading": 'two-fragment lines ("Fast. Simple.")',
    "contrast": 'contrast frames ("not X, but Y"; "It\'s not X. It\'s Y." counts double)',
    "ing_rider": 'trailing -ing riders (", making it easier")',
    "triad": "rule-of-three lists (A, B, and C)",
    "rhetorical_opener": "paragraphs opening on a rhetorical question",
}
DEFAULT_BUDGET = {"warn": 3, "fail": 6}  # slop points per message

FRAG_LINE_RE = re.compile(r"^(?:[A-Z][\w'-]*(?:\s+[\w'-]+){0,2}[.!]\s*){2,}$")
_SEP = r"(?:[.;:]|,|\s*[—–]|\s-{1,2}\s)\s*"
STRONG_CONTRAST_RE = re.compile(
    r"\b(?:it'?s\s+not|it\s+is\s+not|it\s+isn'?t|this\s+is\s+not|this\s+isn'?t"
    r"|that'?s\s+not|that\s+isn'?t)\s+(?:just\s+|only\s+|merely\s+|simply\s+|about\s+)?"
    r"[^.!?;\n]{1,60}?" + _SEP + r"(?:it'?s|it\s+is|this\s+is|that'?s|but)\b",
    re.I,
)
# "not X, but Y". "not only ... but also" is ordinary prose and exempt.
WEAK_CONTRAST_RE = re.compile(
    r"\bnot\s+(?!only\b)(?:just\s+|merely\s+|simply\s+)?[^.!?;,\n]{1,40}?,\s*but\s+(?!also\b)",
    re.I,
)
ING_RIDER_RE = re.compile(
    r",\s+(?:making|ensuring|enabling|allowing|empowering|providing|delivering|creating"
    r"|driving|fostering|streamlining|unlocking|giving|offering|boosting|elevating|enhancing)"
    r"\s+(?:it|that|this|you|your|teams?|users?|them|everyone|sure|a|an|the|more|better"
    r"|businesses|organizations|customers)\b",
    re.I,
)
_TRIAD_STOP = {
    "the",
    "a",
    "an",
    "we",
    "you",
    "i",
    "it",
    "they",
    "he",
    "she",
    "this",
    "that",
    "so",
    "but",
    "and",
    "or",
    "if",
    "as",
    "then",
    "when",
    "yes",
    "no",
    "hi",
    "hello",
}
TRIAD_RE = re.compile(
    r"\b([A-Za-z][A-Za-z'-]*),\s+([A-Za-z][A-Za-z'-]*),\s+(?:and|or)\s+([A-Za-z][A-Za-z'-]*)\b"
)
RHETORICAL_RE = re.compile(
    r"^(?:what if|ever wonder|have you ever|are you tired|are you still|tired of|sick of"
    r"|why settle|what would you|what's stopping|isn't it time|wouldn't it be|do you ever"
    r"|struggling with|looking for a|imagine)\b[^?\n]*\?",
    re.I,
)


def load_waivers(path) -> list[dict]:
    """Read a waiver file: {"waive": [{"term": "...", "reason": "..."}]}.
    Raises ValueError when the file is malformed or an entry has no reason."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"cannot read waivers {path}: {e}")
    items = data.get("waive") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise ValueError(f'{path}: expected {{"waive": [{{"term", "reason"}}]}}')
    out = []
    for i, item in enumerate(items):
        term = str(item.get("term", "")).strip() if isinstance(item, dict) else ""
        reason = str(item.get("reason", "")).strip() if isinstance(item, dict) else ""
        if not term or not reason:
            raise ValueError(f"{path}: waive[{i}] needs both a term and a reason")
        out.append({"term": term, "reason": reason, "source": str(path)})
    return out


def discover_waivers(start=None):
    """Walk up from `start` (default cwd) to the first .tonone/copy-waivers.json."""
    from pathlib import Path

    here = Path(start or ".").resolve()
    for d in (here, *here.parents):
        cand = d / ".tonone" / "copy-waivers.json"
        if cand.is_file():
            return cand
    return None


def _waiver_re(term: str):
    parts = [re.escape(t).replace("'", "['’]") for t in term.split()]
    body = r"\s+".join(parts)
    # a single word also covers its inflections: seamless -> seamlessly
    return re.compile(
        r"(?<!\w)" + body + (r"\w*" if len(parts) == 1 else r"(?!\w)"), re.I
    )


def apply_waivers(msg: dict, waivers) -> tuple[dict, list[dict]]:
    """Mask waived terms so no check sees them; report what was waived."""
    masked = dict(msg)
    report = []
    for w in waivers:
        rx = _waiver_re(w["term"])
        n = 0
        for key in ("subject", "title", "body"):
            if masked.get(key):
                masked[key], k = rx.subn("waivedterm", masked[key])
                n += k
        if n:
            report.append({"term": w["term"], "reason": w["reason"], "count": n})
    return masked, report


def _stem_hits(low: str) -> list[tuple[str, str]]:
    """(stem, matched word) for each slop stem present."""
    out = []
    for st in SLOP_STEMS:
        m = re.search(r"(?<![\w])" + re.escape(st) + r"\w*", low)
        if m:
            out.append((st, m.group(0)))
    return out


def slop_scan(whole, hard, soft, legacy_dash, budget, limits):
    """Return (findings, info). `hard`/`soft` are the existing list hits."""
    findings = []
    text = normalize(whole)
    low = text.lower()
    words = max(len(whole.split()), 1)
    points = 0.0
    scored: list[str] = []

    # residue: always FAIL, never scored
    residue = [p for p in RESIDUE_PHRASES if re.search(r"(?<!\w)" + re.escape(p), low)]
    first = whole.strip()
    if RESIDUE_OPENER_RE.match(first):
        residue.append(first.split("!")[0].strip() + "!")
    residue += sorted({m.group(0) for m in RESIDUE_SLOT_RE.finditer(whole)})
    if residue:
        findings.append(
            {
                "severity": "FAIL",
                "code": "RESIDUE",
                "message": f"model or template residue: {residue[:4]}",
            }
        )

    # words and stock phrases (existing list hits count once, here)
    existing = list(hard) + list(soft)
    new_words = [
        word for st, word in _stem_hits(low) if not any(st in p for p in existing)
    ]
    stock = _phrase_hits(whole, STOCK_PHRASES)
    stock = [p for p in stock if p not in existing]
    points += 2 * len(hard) + len(soft) + len(new_words) + 2 * len(stock)
    scored = [*hard, *soft, *new_words, *stock]
    if new_words:
        findings.append(
            {
                "severity": "WARN",
                "code": "SLOP_WORD",
                "message": f"AI-tell words: {new_words[:6]}",
            }
        )
    if stock:
        findings.append(
            {
                "severity": "WARN",
                "code": "SLOP_PHRASE",
                "message": f"stock phrases: {stock[:4]}",
            }
        )

    # devices
    counts = {}
    counts["em_dash"] = len(DASH_RE.findall(whole))
    counts["fragment_heading"] = sum(
        1
        for ln in whole.splitlines()
        if FRAG_LINE_RE.match(ln.strip().lstrip("#").strip().strip("*_ "))
        and len(ln.split()) <= 9
    )
    strong = list(STRONG_CONTRAST_RE.finditer(text))
    rest = STRONG_CONTRAST_RE.sub(" ", text)
    counts["contrast"] = 2 * len(strong) + len(WEAK_CONTRAST_RE.findall(rest))
    counts["ing_rider"] = len(ING_RIDER_RE.findall(text))
    counts["triad"] = sum(
        1
        for m in TRIAD_RE.finditer(text)
        if not any(g.lower() in _TRIAD_STOP for g in m.groups())
    )
    counts["rhetorical_opener"] = sum(
        1
        for para in re.split(r"\n\s*\n", normalize_keep(whole))
        if RHETORICAL_RE.match(
            re.sub(r"^(?:\{\{[^}]*\}\}\s*,?\s*)", "", para.strip().lstrip("#*_- "))
        )
    )

    devices = {}
    for name, count in counts.items():
        warn, fail = limits[name]
        if name == "em_dash":
            value = round(count * 100 / max(words, 50), 2)
            level = (
                "FAIL"
                if count >= 2 and value > fail
                else "WARN" if value > warn else None
            )
            shown = f"{count} em dash(es), {value} per 100 words (warn >{warn}, fail >{fail})"
            if legacy_dash:  # profile already bans them outright; do not double up
                level = None
        else:
            value = count
            level = "FAIL" if count >= fail else "WARN" if count >= warn else None
            shown = f"{count} {DEVICE_ABOUT[name]} (warn {warn}, fail {fail})"
        devices[name] = {
            "count": count,
            "value": value,
            "warn": warn,
            "fail": fail,
            "level": level,
        }
        if level:
            points += count
            findings.append(
                {"severity": level, "code": "SLOP_" + name.upper(), "message": shown}
            )

    score = round(points, 1)
    level = (
        "FAIL"
        if score >= budget["fail"]
        else "WARN" if score >= budget["warn"] else None
    )
    if level:
        findings.append(
            {
                "severity": level,
                "code": "SLOP_BUDGET",
                "message": f"slop score {score} (warn {budget['warn']}, fail {budget['fail']}): {scored[:6]}",
            }
        )
    info = {
        "score": score,
        "warn": budget["warn"],
        "fail": budget["fail"],
        "devices": devices,
    }
    return findings, info


def normalize_keep(text: str) -> str:
    """Quote normalisation only; keeps line breaks for paragraph checks."""
    for curly, straight in (("’", "'"), ("‘", "'")):
        text = text.replace(curly, straight)
    return text


MARKER_RE = re.compile(r"^===\s*(.*?)\s*(?:\[profile=([\w\-]+)\])?\s*$")


def parse_messages(text: str) -> list[dict]:
    """Split input into messages on `=== label` lines."""
    messages: list[dict] = []
    current = {"label": "message-1", "profile": None, "lines": []}
    seen_marker = False
    for line in text.splitlines():
        m = MARKER_RE.match(line)
        if m:
            if seen_marker or any(l.strip() for l in current["lines"]):
                messages.append(current)
            seen_marker = True
            current = {
                "label": m.group(1) or f"message-{len(messages) + 1}",
                "profile": m.group(2),
                "lines": [],
            }
        else:
            current["lines"].append(line)
    if seen_marker or any(l.strip() for l in current["lines"]):
        messages.append(current)

    out = []
    for msg in messages:
        subject = title = None
        body_lines = []
        header_open = True
        for line in msg["lines"]:
            stripped = line.strip()
            if header_open and not stripped:
                continue
            h = HEADER_RE.match(stripped) if header_open else None
            if h:
                if h.group(1).lower() == "subject":
                    subject = h.group(2)
                else:
                    title = h.group(2)
                continue
            header_open = False
            if stripped == "---":  # template separators, not content
                continue
            body_lines.append(line)
        out.append(
            {
                "label": msg["label"],
                "profile": msg["profile"],
                "subject": subject,
                "title": title,
                "body": "\n".join(body_lines).strip(),
            }
        )
    return out


def normalize(text: str) -> str:
    """Straight quotes and single spaces, so a curly apostrophe or a phrase
    split across a line break still matches the lists."""
    for curly, straight in (
        ("\u2019", "'"),
        ("\u2018", "'"),
        ("\u201c", '"'),
        ("\u201d", '"'),
    ):
        text = text.replace(curly, straight)
    return re.sub(r"\s+", " ", text)


def _phrase_hits(text: str, phrases) -> list[str]:
    low = normalize(text).lower()
    hits = []
    for p in phrases:
        if re.search(r"(?<![\w])" + re.escape(p) + r"(?![\w])", low):
            hits.append(p)
    return hits


def check_message(
    msg: dict,
    profile: dict,
    allow_tokens: bool,
    slop: bool = False,
    waivers=(),
    budget=None,
    limits=None,
    report=None,
) -> list[dict]:
    findings: list[dict] = []
    slop_on = bool(slop or profile.get("slop"))
    if waivers:
        msg, waived = apply_waivers(msg, waivers)
        if report is not None:
            report["waived"] = waived

    def add(sev, code, message):
        findings.append({"severity": sev, "code": code, "message": message})

    subject = msg["subject"] or ""
    title = msg["title"] or ""
    body = msg["body"]
    whole = "\n".join(x for x in (subject, title, body) if x)

    if not body and not title:
        add("FAIL", "EMPTY", "message has no body")

    # Unfilled slots and leftover tokens
    slots = sorted(
        {
            m.group(0)
            for m in BRACKET_SLOT_RE.finditer(whole)
            if m.group(1).strip().lower() not in NOT_A_SLOT
        }
        | {m.group(0) for m in ANGLE_SLOT_RE.finditer(whole)}
    )
    if slots:
        add("FAIL", "PLACEHOLDER", f"unfilled template slots: {slots[:4]}")
    todos = sorted({m.group(0) for m in TODO_RE.finditer(whole)})
    if todos:
        add("FAIL", "PLACEHOLDER", f"draft markers left in copy: {todos[:4]}")
    tokens = sorted({m.group(0) for m in TOKEN_RE.finditer(whole)})
    if tokens and not allow_tokens:
        add("FAIL", "MERGE_TAG", f"unrendered merge tags: {tokens[:4]}")
    single = sorted({m.group(0) for m in SINGLE_BRACE_RE.finditer(whole)})
    if single and not (profile.get("single_brace_tokens") and allow_tokens):
        add("FAIL", "MERGE_TAG", f"single-brace merge tags: {single[:4]}")

    # Phrases
    hard = _phrase_hits(whole, HARD_PHRASES)
    if hard:
        add("FAIL", "BANNED_PHRASE", f"spam trigger or AI tell: {hard[:4]}")
    ignore = set(profile.get("soft_ignore", ()))
    soft = [
        p
        for p in _phrase_hits(whole, SOFT_PHRASES + tuple(profile.get("extra", ())))
        if p not in ignore
    ]
    if soft:
        add(profile.get("soft", "WARN"), "HYPE", f"hype or filler: {soft[:5]}")

    # Punctuation tells
    dashes = DASH_RE.findall(whole)
    # Under slop, a WARN-level em-dash profile defers to the per-100-word budget.
    legacy_dash = profile.get("em_dash") == "FAIL" or (
        profile.get("em_dash") and not slop_on
    )
    if dashes and legacy_dash:
        add(
            profile["em_dash"],
            "EM_DASH",
            f"{len(dashes)} em dash(es) or dash stand-ins; rewrite with a period or comma",
        )
    if "max_exclaim" in profile:
        n = whole.count("!")
        if n > profile["max_exclaim"]:
            add(
                "FAIL" if profile["max_exclaim"] == 0 else "WARN",
                "EXCLAIM",
                f"{n} exclamation mark(s) (max {profile['max_exclaim']})",
            )
    if "max_questions" in profile:
        n = body.count("?")
        if n > profile["max_questions"]:
            add(
                "WARN",
                "QUESTIONS",
                f"{n} questions; one clear question gets more replies (max {profile['max_questions']})",
            )
    caps = sorted(set(CAPS_RE.findall(whole)))
    if caps:
        add("WARN", "ALL_CAPS", f"shouting words: {caps[:4]}")

    # Length
    words = len(body.split())
    if "max_words" in profile and words > profile["max_words"]:
        add("FAIL", "TOO_LONG", f"body is {words} words (max {profile['max_words']})")
    if "max_chars" in profile and len(body) > profile["max_chars"]:
        add(
            "FAIL",
            "TOO_LONG",
            f"body is {len(body)} chars (max {profile['max_chars']})",
        )

    # Links and markup
    if "max_links" in profile:
        links = URL_RE.findall(body)
        if len(links) > profile["max_links"]:
            add("FAIL", "LINKS", f"{len(links)} link(s) (max {profile['max_links']})")
    if HTML_RE.search(body):
        add("FAIL", "HTML", "HTML markup in body; send plain text")

    # Subject line
    if profile.get("require_subject") and not subject:
        add("FAIL", "SUBJECT", "missing 'Subject:' line")
    if subject:
        if FAKE_THREAD_RE.match(subject) and not profile.get("reply_thread"):
            add(
                "FAIL",
                "SUBJECT",
                "subject fakes a reply or forward (Re:/Fwd:) on a new thread",
            )
        if (
            "max_subject_chars" in profile
            and len(subject) > profile["max_subject_chars"]
        ):
            add(
                "FAIL",
                "SUBJECT",
                f"subject is {len(subject)} chars (max {profile['max_subject_chars']})",
            )
        if (
            "max_subject_words" in profile
            and len(subject.split()) > profile["max_subject_words"]
        ):
            add(
                "WARN",
                "SUBJECT",
                f"subject is {len(subject.split())} words (target {profile['max_subject_words']} or fewer)",
            )
        if profile.get("subject_no_name") and re.search(r"first_?name", subject, re.I):
            add("WARN", "SUBJECT", "prospect's name in the subject reads as automated")

    # Title (HN)
    if profile.get("require_title") and not title:
        add("FAIL", "TITLE", "missing 'Title:' line")
    if (
        title
        and "max_title_chars" in profile
        and len(title) > profile["max_title_chars"]
    ):
        add(
            "FAIL",
            "TITLE",
            f"title is {len(title)} chars (max {profile['max_title_chars']})",
        )

    # Opener
    if profile.get("no_i_we_opener"):
        first = re.sub(r"^(\{\{\s*\w+\s*\}\}|\[\[\s*\w+\s*\]\])\s*,?\s*", "", body)
        if re.match(r"(?i)^(i|we|i'm|we're|my name)\b", first):
            add("WARN", "OPENER", "opens with I/We; lead with them, not you")

    if slop_on:
        extra, info = slop_scan(
            whole,
            hard,
            soft,
            legacy_dash,
            {**DEFAULT_BUDGET, **(budget or {})},
            {**DEVICES, **(limits or {})},
        )
        findings.extend(extra)
        if report is not None:
            report["slop"] = info

    return findings


def run(
    text: str,
    profile_name: str,
    allow_tokens: bool,
    slop: bool = False,
    waivers=None,
    budget=None,
    limits=None,
) -> dict:
    messages = parse_messages(text)
    results = []
    fails = warns = 0
    for msg in messages:
        name = msg["profile"] or profile_name
        if name not in PROFILES:
            return {"ok": False, "error": f"unknown profile '{name}' on {msg['label']}"}
        extra: dict = {}
        findings = check_message(
            msg,
            PROFILES[name],
            allow_tokens,
            slop,
            waivers or (),
            budget,
            limits,
            extra,
        )
        f = sum(1 for x in findings if x["severity"] == "FAIL")
        w = sum(1 for x in findings if x["severity"] == "WARN")
        fails += f
        warns += w
        results.append(
            {
                "label": msg["label"],
                "profile": name,
                "words": len(msg["body"].split()),
                "verdict": "FAIL" if f else ("WARN" if w else "PASS"),
                "findings": findings,
                **extra,
            }
        )
    out = {
        "ok": True,
        "verdict": "FAIL" if fails else ("WARN" if warns else "PASS"),
        "messages": len(results),
        "fails": fails,
        "warns": warns,
        "results": results,
    }
    if waivers:
        out["waivers"] = [{"term": w["term"], "reason": w["reason"]} for w in waivers]
    return out


def _metric(result: dict) -> None:
    """Opt-in counter (TONONE_METRICS=on): counts only, errors swallowed."""
    try:
        if os.environ.get("TONONE_METRICS") != "on":
            return
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path.cwd())
        (root / ".tonone").mkdir(parents=True, exist_ok=True)
        waived = sum(
            w.get("count", 1)
            for r in result.get("results", [])
            for w in r.get("waived", [])
        )
        line = {
            "ts": datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "tool": "copy-slop",
            "event": "run",
            "messages": result.get("messages", 0),
            "warn": result.get("warns", 0),
            "fail": result.get("fails", 0),
            "waived": waived,
        }
        with open(root / ".tonone" / "metrics.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(line) + "\n")
    except Exception:
        pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic checks on outbound copy.")
    ap.add_argument("file", nargs="?", help="drafts file, or - for stdin")
    ap.add_argument("--profile", default="marketing-copy")
    ap.add_argument(
        "--allow-tokens",
        action="store_true",
        help="permit {{token}} / [[token]] merge tags (templates for a sequencer)",
    )
    ap.add_argument(
        "--slop",
        action="store_true",
        help="add the copy-slop floor to any profile (the `slop` profile always has it)",
    )
    ap.add_argument("--slop-warn", type=float, help="slop score that warns (default 3)")
    ap.add_argument("--slop-fail", type=float, help="slop score that fails (default 6)")
    ap.add_argument(
        "--device",
        action="append",
        default=[],
        metavar="NAME=WARN:FAIL",
        help="override one device limit, e.g. em_dash=2:4 or triad=4:8 (repeatable)",
    )
    ap.add_argument(
        "--waive",
        default="",
        help="comma-separated client-supplied terms to leave alone (reported as waived)",
    )
    ap.add_argument(
        "--waivers",
        metavar="PATH",
        help="waiver JSON; default: .tonone/copy-waivers.json found walking up from cwd",
    )
    ap.add_argument("--list-profiles", action="store_true")
    ap.add_argument("--pretty", action="store_true")
    args = ap.parse_args(argv)
    indent = 2 if args.pretty else None

    if args.list_profiles:
        print(
            json.dumps(
                {"ok": True, "profiles": {k: v["about"] for k, v in PROFILES.items()}},
                indent=indent,
            )
        )
        return 0
    if args.profile not in PROFILES:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"unknown profile '{args.profile}'",
                    "profiles": sorted(PROFILES),
                },
                indent=indent,
            )
        )
        return 2
    if not args.file:
        print(
            json.dumps(
                {"ok": False, "error": "no input file (use - for stdin)"}, indent=indent
            )
        )
        return 2
    try:
        text = (
            sys.stdin.read()
            if args.file == "-"
            else open(args.file, encoding="utf-8").read()
        )
    except OSError as e:
        print(
            json.dumps({"ok": False, "error": f"cannot read input: {e}"}, indent=indent)
        )
        return 2

    def usage(msg):
        print(json.dumps({"ok": False, "error": msg}, indent=indent))
        return 2

    waivers: list[dict] = []
    try:
        wpath = args.waivers
        if not wpath and (
            args.slop or args.profile == "slop" or "profile=slop" in text
        ):
            found = discover_waivers()
            wpath = str(found) if found else None
        if wpath:
            waivers += load_waivers(wpath)
    except ValueError as e:
        return usage(str(e))
    for term in (t.strip() for t in args.waive.split(",")):
        if term:
            waivers.append({"term": term, "reason": "--waive flag", "source": "cli"})

    budget = {}
    if args.slop_warn is not None:
        budget["warn"] = args.slop_warn
    if args.slop_fail is not None:
        budget["fail"] = args.slop_fail
    b = {**DEFAULT_BUDGET, **budget}
    if b["warn"] > b["fail"]:
        return usage("--slop-warn must be <= --slop-fail")
    limits = {}
    for spec in args.device:
        m = re.fullmatch(r"(\w+)=([\d.]+):([\d.]+)", spec)
        if not m or m.group(1) not in DEVICES or float(m.group(2)) > float(m.group(3)):
            return usage(
                f"bad --device '{spec}'; use NAME=WARN:FAIL with NAME in {sorted(DEVICES)}"
            )
        limits[m.group(1)] = (float(m.group(2)), float(m.group(3)))

    result = run(
        text, args.profile, args.allow_tokens, args.slop, waivers, budget, limits
    )
    print(json.dumps(result, indent=indent, ensure_ascii=False))
    if result["ok"] and (args.slop or args.profile == "slop" or "profile=slop" in text):
        _metric(result)
    if not result["ok"]:
        return 2
    return 1 if result["fails"] else 0


if __name__ == "__main__":
    sys.exit(main())
