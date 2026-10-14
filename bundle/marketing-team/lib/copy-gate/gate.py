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
    python3 gate.py --list-profiles

Prints exactly one JSON object. Exit 0 = no FAIL findings, 1 = at least one
FAIL, 2 = usage error (bad profile, unreadable file).
"""

from __future__ import annotations

import argparse
import json
import re
import sys

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


def check_message(msg: dict, profile: dict, allow_tokens: bool) -> list[dict]:
    findings: list[dict] = []

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
    if dashes and profile.get("em_dash"):
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

    return findings


def run(text: str, profile_name: str, allow_tokens: bool) -> dict:
    messages = parse_messages(text)
    results = []
    fails = warns = 0
    for msg in messages:
        name = msg["profile"] or profile_name
        if name not in PROFILES:
            return {"ok": False, "error": f"unknown profile '{name}' on {msg['label']}"}
        findings = check_message(msg, PROFILES[name], allow_tokens)
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
            }
        )
    return {
        "ok": True,
        "verdict": "FAIL" if fails else ("WARN" if warns else "PASS"),
        "messages": len(results),
        "fails": fails,
        "warns": warns,
        "results": results,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deterministic checks on outbound copy.")
    ap.add_argument("file", nargs="?", help="drafts file, or - for stdin")
    ap.add_argument("--profile", default="marketing-copy")
    ap.add_argument(
        "--allow-tokens",
        action="store_true",
        help="permit {{token}} / [[token]] merge tags (templates for a sequencer)",
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

    result = run(text, args.profile, args.allow_tokens)
    print(json.dumps(result, indent=indent, ensure_ascii=False))
    if not result["ok"]:
        return 2
    return 1 if result["fails"] else 0


if __name__ == "__main__":
    sys.exit(main())
