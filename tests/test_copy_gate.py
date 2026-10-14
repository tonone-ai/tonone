"""
Tests for lib/copy-gate — deterministic checks on outbound copy.

Risk map:
- A banned phrase or placeholder slips through → HIGH: "[Customer X]" or
  "I hope this finds you well" lands in a real prospect's inbox, which is the
  one thing the gate exists to stop.
- Clean copy fails → MEDIUM: skills loop on rewrites of copy that was fine,
  and users learn to ignore the gate.
- Exit code or JSON shape drifts → MEDIUM: the skills branch on both.

Offline and dependency-free.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
GATE = REPO / "lib" / "copy-gate" / "gate.py"

spec = importlib.util.spec_from_file_location("copy_gate", GATE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

CLEAN = """=== touch-1 email
Subject: inventory report
---
{{first_name}}, most ops teams your size rebuild the same inventory report by hand every Monday.

We generate it from the systems {{company}} already runs. Is this on your radar at all?

{{sender_name}}
---
"""


def codes(result, label=None):
    found = []
    for r in result["results"]:
        if label is None or r["label"] == label:
            found += [f["code"] for f in r["findings"] if f["severity"] == "FAIL"]
    return set(found)


def test_clean_cold_email_passes_with_tokens_allowed():
    result = gate.run(CLEAN, "cold-email", allow_tokens=True)
    assert result["verdict"] == "PASS", result


def test_tokens_fail_when_not_allowed():
    result = gate.run(CLEAN, "cold-email", allow_tokens=False)
    assert "MERGE_TAG" in codes(result)


def test_bad_cold_email_trips_every_check():
    bad = """=== bad
Subject: Re: quick question
I hope this finds you well! We built a game-changer — see https://a.com and https://b.com for [Customer X]. TODO add stat
[Name]
"""
    found = codes(gate.run(bad, "cold-email", allow_tokens=True))
    assert {
        "PLACEHOLDER",
        "BANNED_PHRASE",
        "HYPE",
        "EM_DASH",
        "EXCLAIM",
        "LINKS",
        "SUBJECT",
    } <= found


def test_markdown_links_and_tokens_are_not_placeholders():
    text = "See the [changelog](https://x.dev/c) and [[first_name]]."
    result = gate.run(text, "marketing-copy", allow_tokens=True)
    assert "PLACEHOLDER" not in codes(result)


def test_single_brace_tag_is_caught():
    result = gate.run("Hi {first_name}, thanks.", "marketing-copy", allow_tokens=True)
    assert "MERGE_TAG" in codes(result)


def test_cold_email_word_ceiling():
    long_body = "Subject: hi there\n" + " ".join(["word"] * 130)
    assert "TOO_LONG" in codes(gate.run(long_body, "cold-email", allow_tokens=False))


def test_hype_warns_in_marketing_but_fails_in_pitch():
    text = "Subject: new release\nOur seamless platform for teams."
    marketing = gate.run(text, "marketing-copy", allow_tokens=False)
    pitch = gate.run(text, "press-pitch", allow_tokens=False)
    assert marketing["verdict"] == "WARN"
    assert "HYPE" in codes(pitch)


def test_hn_title_rules():
    text = "Title: Show HN: The best revolutionary tool for the ultimate developer experience ever made by us\nBody."
    found = codes(gate.run(text, "hn", allow_tokens=False))
    assert {"TITLE", "HYPE"} <= found
    assert codes(gate.run("Body only.", "hn", allow_tokens=False)) >= {"TITLE"}


def test_per_message_profile_override():
    text = CLEAN + "=== touch-2 [profile=linkedin-note]\n" + ("x" * 310) + "\n"
    result = gate.run(text, "cold-email", allow_tokens=True)
    by_label = {r["label"]: r for r in result["results"]}
    assert by_label["touch-2"]["profile"] == "linkedin-note"
    assert "TOO_LONG" in codes(result, "touch-2")


def test_phrase_matching_respects_word_boundaries():
    # "easy" is a soft microcopy word; "easyjet" must not match it.
    result = gate.run("Book your easyjet flight.", "microcopy", allow_tokens=False)
    assert result["verdict"] == "PASS", result


def _cli(*args, stdin=None):
    proc = subprocess.run(
        [sys.executable, "-I", str(GATE), *args],
        input=stdin,
        capture_output=True,
        text=True,
    )
    return proc.returncode, json.loads(proc.stdout)


def test_cli_exit_codes():
    rc, out = _cli("--profile", "cold-email", "--allow-tokens", "-", stdin=CLEAN)
    assert rc == 0 and out["verdict"] == "PASS"
    rc, out = _cli("--profile", "cold-email", "-", stdin=CLEAN)
    assert rc == 1 and out["verdict"] == "FAIL"
    rc, out = _cli("--profile", "nope", "-", stdin=CLEAN)
    assert rc == 2 and out["ok"] is False


def test_cli_lists_profiles():
    rc, out = _cli("--list-profiles")
    assert rc == 0
    assert {
        "cold-email",
        "reply",
        "linkedin-note",
        "press-pitch",
        "press-release",
        "hn",
        "marketing-copy",
        "microcopy",
    } <= set(out["profiles"])


def test_curly_quotes_line_breaks_and_dash_standins_are_caught():
    text = "Subject: hi\nI hope you\u2019re doing\nwell. It\u2019s not just data \u2013 it is -- more."
    found = codes(gate.run(text, "cold-email", allow_tokens=False))
    assert {"BANNED_PHRASE", "HYPE", "EM_DASH"} <= found


def test_wider_token_and_slot_shapes():
    text = "Subject: hi\nHi {{first name}}, {{ company | default }} *|FNAME|* at <Company>."
    result = gate.run(text, "cold-email", allow_tokens=False)
    msg = " ".join(f["message"] for r in result["results"] for f in r["findings"])
    assert "{{first name}}" in msg and "*|FNAME|*" in msg and "<Company>" in msg


def test_not_slots_and_markdown_headers_pass():
    text = "**Subject:** inventory\nTeams your size [sic] rebuild the report, see [docs][1]. Is this on your radar?"
    assert gate.run(text, "cold-email", allow_tokens=False)["verdict"] == "PASS"


def test_reply_profile_accepts_threads():
    assert (
        gate.run(
            "Subject: Re: pricing\nThat makes sense. Who owns this on your side?",
            "reply",
            allow_tokens=False,
        )["verdict"]
        == "PASS"
    )
    assert (
        gate.run(
            "That makes sense. Who owns this on your side?", "reply", allow_tokens=False
        )["verdict"]
        == "PASS"
    )


def test_hn_allows_normal_technical_words():
    text = "Title: Show HN: The best way I found to diff SQLite schemas\nI'd love to hear feedback."
    assert gate.run(text, "hn", allow_tokens=False)["verdict"] == "PASS"


def test_microcopy_allows_i18n_tokens():
    assert (
        gate.run("Welcome back, {name}.", "microcopy", allow_tokens=True)["verdict"]
        == "PASS"
    )
