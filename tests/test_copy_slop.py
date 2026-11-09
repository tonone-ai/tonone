"""
Tests for the copy-slop checks in lib/copy-gate/gate.py.

Risk map:
- Slop ships (AI-tell words, residue, stacked devices) -> HIGH: the check
  exists to stop it.
- Good human copy fails -> HIGH: writers learn to ignore or bypass the gate.
- Waiver path leaks or silently accepts reasonless waivers -> MEDIUM.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
GATE = REPO / "lib" / "copy-gate" / "gate.py"
spec = importlib.util.spec_from_file_location("copy_gate_slop", GATE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def slop(text, profile="slop", **kw):
    return gate.run(text, profile, kw.pop("allow_tokens", False), **kw)


def findings(result, sev=None):
    return {
        f["code"]
        for r in result["results"]
        for f in r["findings"]
        if sev is None or f["severity"] == sev
    }


# Good human copy. Must produce zero FAILs under every profile with --slop.
GOOD = [
    "We moved invoices to a nightly job. Finance sees yesterday's totals by 7am, "
    "and nothing runs during the working day. If the job fails, you get an email "
    "with the failing account and the retry time.",
    # one em dash in a long paragraph: under budget
    "The export keeps your column order — we tested it against the three "
    "spreadsheet apps most customers use. Open the file, check the totals, and "
    "send it on. If a row looks wrong, the log shows which import step touched it, "
    "so you can fix the source instead of the copy. Most teams are done in ten minutes. "
    "If your sheet has merged cells, unmerge them first; the importer reads one value "
    "per cell and will skip the rest. Dates must use the year-month-day order. "
    "Support can run the import for you if the file is larger than fifty megabytes.",
    # "not only ... but also" is ordinary prose
    "The rule applies not only to new accounts but also to accounts created before March.",
    "Payment failed. Check the card number and try again, or use a different card.",
    "No projects yet. Create one to start tracking work.",
    # client term, waived below
    "Seamless Pay settles within two business days.",
]


def test_clean_corpus_has_no_fails_in_any_profile():
    for profile in ("slop", "marketing-copy", "press-release", "microcopy"):
        # microcopy has a 160-char ceiling; use the short UI strings there
        for text in (GOOD[3:5] if profile == "microcopy" else GOOD[:5]):
            res = slop(text, profile, slop=True)
            assert res["fails"] == 0, (profile, text, res)
    res = slop(GOOD[1])
    assert findings(res) == set(), res  # under-budget em dash is silent


def test_not_only_but_also_is_exempt():
    res = slop(GOOD[2])
    assert "SLOP_CONTRAST" not in findings(res)
    assert res["results"][0]["slop"]["devices"]["contrast"]["count"] == 0


def test_banned_words_and_stock_phrases_score():
    res = slop("We leverage a robust tapestry of tools. Look no further.")
    r = res["results"][0]
    assert {"SLOP_WORD", "SLOP_PHRASE"} <= findings(res)
    assert r["slop"]["score"] >= 5
    # existing lists are reused: seamless/delve come from SOFT_PHRASES, not a copy
    assert "seamless" in gate.SOFT_PHRASES and "seamless" not in gate.SLOP_STEMS
    res = slop("Delve into our seamless platform.")
    assert "HYPE" in findings(res)  # existing finding still fires, scored once
    assert res["results"][0]["slop"]["score"] == 2


def test_residue_always_fails():
    for text in (
        "Certainly! Here is the email you asked for.",
        "Thanks for reading. I hope this helps.",
        "Lorem ipsum dolor sit amet.",
        "Dear [Your Name], welcome.",
        "TODO write the intro",
        "As an AI, I cannot say.",
        "Hi {{placeholder}}, welcome.",
    ):
        res = slop(text, allow_tokens=True)
        assert res["verdict"] == "FAIL", text
    # a normal merge token survives --allow-tokens
    assert (
        slop("Hi {{first_name}}, welcome back.", allow_tokens=True)["verdict"] == "PASS"
    )
    assert (
        slop("Hi {{first_name}}, welcome back.")["verdict"] == "FAIL"
    )  # existing semantics


def test_em_dash_budget():
    words = " ".join(["word"] * 150)
    assert findings(slop(f"{words} a — b")) == set()  # 0.67 per 100
    assert "SLOP_EM_DASH" in findings(slop(f"{words} a — b — c"), "WARN")
    dense = "Fast — simple — safe, " + " ".join(["word"] * 40)
    assert "SLOP_EM_DASH" in findings(slop(dense), "FAIL")
    # zero-tolerance profiles keep their flat ban and do not double count
    cold = slop("Subject: hi\nOne — two.", "cold-email", slop=True)
    assert "EM_DASH" in findings(cold, "FAIL") and "SLOP_EM_DASH" not in findings(cold)
    # WARN-level profile defers to the budget when slop is on
    assert "EM_DASH" not in findings(
        slop(f"{words} a — b", "marketing-copy", slop=True)
    )
    assert "EM_DASH" in findings(slop(f"{words} a — b", "marketing-copy"))


def test_fragment_headings():
    assert "SLOP_FRAGMENT_HEADING" in findings(
        slop("# Fast. Simple.\nBody text here."), "WARN"
    )
    three = "Fast. Simple.\n\nSecure. Quick.\n\nSmart. Easy.\n\nBody."
    assert "SLOP_FRAGMENT_HEADING" in findings(slop(three), "FAIL")
    assert "SLOP_FRAGMENT_HEADING" not in findings(
        slop("# Pricing\nPlans start at $9.")
    )


def test_contrast_frames():
    strong = "It's not a dashboard. It's a command center."
    assert "SLOP_CONTRAST" in findings(slop(strong), "WARN")
    two = strong + " It's not just email, it's your whole inbox."
    assert "SLOP_CONTRAST" in findings(slop(two), "FAIL")
    weak = "Not today, but soon. Not you, but your team."
    assert "SLOP_CONTRAST" in findings(slop(weak), "WARN")
    assert "SLOP_CONTRAST" not in findings(slop("Not today, but soon."))


def test_ing_riders():
    one = "We sync your files, making it easier to share."
    assert "SLOP_ING_RIDER" not in findings(slop(one))
    two = one + " We back them up, ensuring that nothing is lost."
    assert "SLOP_ING_RIDER" in findings(slop(two), "WARN")
    four = (
        two
        + " We encrypt them, enabling you to relax. We alert you, giving teams time."
    )
    assert "SLOP_ING_RIDER" in findings(slop(four), "FAIL")


def test_rule_of_three():
    t = "We are fast, reliable, and cheap. Clear, calm, or quick. Plan, build, and ship."
    assert "SLOP_TRIAD" in findings(slop(t), "WARN")
    assert "SLOP_TRIAD" not in findings(slop("We are fast, reliable, and cheap."))
    assert "SLOP_TRIAD" in findings(
        slop(t + " Read, write, and share. Try, test, and learn."), "FAIL"
    )


def test_rhetorical_openers():
    t = "Tired of messy spreadsheets?\n\nOur tool helps."
    assert "SLOP_RHETORICAL_OPENER" in findings(slop(t), "WARN")
    assert "SLOP_RHETORICAL_OPENER" not in findings(
        slop("Need a hand?\n\nOur tool helps.")
    )


def test_budget_warn_fail_and_overrides():
    text = "We leverage robust tools to elevate and empower teams."
    base = slop(text)
    score = base["results"][0]["slop"]["score"]
    assert score >= 4 and "SLOP_BUDGET" in findings(base, "WARN")
    assert "SLOP_BUDGET" in findings(slop(text, budget={"warn": 2, "fail": 4}), "FAIL")
    assert "SLOP_BUDGET" not in findings(slop(text, budget={"warn": 50, "fail": 60}))


def test_slop_is_opt_in_for_other_profiles():
    text = "We leverage tools."
    assert "slop" not in gate.run(text, "marketing-copy", False)["results"][0]
    assert "slop" in gate.run(text, "marketing-copy", False, slop=True)["results"][0]


def test_waivers_mask_and_report():
    w = [{"term": "seamless", "reason": "client product name"}]
    plain = slop(GOOD[5], "marketing-copy", slop=True)
    assert "HYPE" in findings(plain)
    res = slop(GOOD[5], "marketing-copy", slop=True, waivers=w)
    assert "HYPE" not in findings(res)
    waived = res["results"][0]["waived"]
    assert waived == [{"term": "seamless", "reason": "client product name", "count": 1}]
    assert res["results"][0]["slop"]["score"] == 0
    assert res["waivers"][0]["reason"] == "client product name"
    # only the waived term is exempt
    res = slop("Seamless Pay is a game-changer.", waivers=w)
    assert "game-changer" in " ".join(
        f["message"] for f in res["results"][0]["findings"]
    )


def test_waiver_file_requires_reason(tmp_path):
    bad = tmp_path / "w.json"
    bad.write_text(json.dumps({"waive": [{"term": "seamless"}]}))
    try:
        gate.load_waivers(bad)
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "reason" in str(e)
    ok = tmp_path / "ok.json"
    ok.write_text(json.dumps({"waive": [{"term": "seamless", "reason": "client"}]}))
    assert gate.load_waivers(ok)[0]["term"] == "seamless"


def _cli(*args, stdin=None, cwd=None):
    proc = subprocess.run(
        [sys.executable, "-I", str(GATE), *args],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return proc.returncode, json.loads(proc.stdout)


def test_cli_flags_exit_codes_and_waivers(tmp_path):
    rc, out = _cli(
        "--profile", "marketing-copy", "--slop", "-", stdin="We leverage tools."
    )
    assert rc == 0 and out["verdict"] in ("WARN", "PASS")
    rc, out = _cli("--profile", "slop", "-", stdin="Certainly! Here you go.")
    assert rc == 1 and "RESIDUE" in findings(out)
    rc, out = _cli(
        "--profile", "slop", "--slop-warn", "5", "--slop-fail", "2", "-", stdin="x"
    )
    assert rc == 2 and out["ok"] is False
    rc, out = _cli("--profile", "slop", "--device", "bogus=1:2", "-", stdin="x")
    assert rc == 2
    rc, out = _cli(
        "--profile", "slop", "--waive", "tapestry", "-", stdin="A rich tapestry."
    )
    assert out["results"][0]["waived"][0]["term"] == "tapestry"
    # auto-discovery walks up from cwd
    (tmp_path / ".tonone").mkdir()
    (tmp_path / ".tonone" / "copy-waivers.json").write_text(
        json.dumps({"waive": [{"term": "robust", "reason": "client term"}]})
    )
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    rc, out = _cli("--profile", "slop", "-", stdin="Our Robust plan.", cwd=sub)
    assert out["results"][0]["waived"][0]["reason"] == "client term"
    (tmp_path / ".tonone" / "copy-waivers.json").write_text('{"waive":[{"term":"x"}]}')
    rc, out = _cli("--profile", "slop", "-", stdin="hi", cwd=sub)
    assert rc == 2 and "reason" in out["error"]
