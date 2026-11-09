import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import merge_findings as m  # noqa: E402


def F(
    id,
    sev="HIGH",
    title="SQL injection in search",
    file="a.py",
    line=10,
    evidence="q = f'...{x}'",
):
    return {
        "id": id,
        "severity": sev,
        "title": title,
        "file": file,
        "line": line,
        "evidence": evidence,
        "impact": "i",
        "fix": "f",
        "confidence": "medium",
    }


def doc(lens, *fs):
    return {"lens": lens, "findings": list(fs), "checked": [], "skipped": []}


def test_dedupe_keeps_max_severity_and_lenses():
    out, _ = m.merge(
        [
            doc("warden", F("W1", "MEDIUM")),
            doc("spine", F("S1", "CRITICAL", title="SQL Injection in search!")),
        ]
    )
    assert len(out) == 1
    assert out[0]["severity"] == "CRITICAL"
    assert out[0]["lenses"] == ["warden", "spine"]


def test_drops_missing_evidence_and_bad_severity():
    out, dropped = m.merge(
        [doc("proof", F("P1", evidence="  "), F("P2", sev="NOPE"), F("P3", line=3))]
    )
    assert [f["id"] for f in out] == ["P3"]
    assert {d["reason"] for d in dropped} == {"no evidence", "bad severity"}


def test_different_line_not_deduped():
    out, _ = m.merge([doc("warden", F("W1", line=1), F("W2", line=2))])
    assert len(out) == 2


def test_dispute_requires_evidence_and_changes_verdict():
    base, _ = m.merge([doc("warden", F("W1", "CRITICAL"))])
    assert m.verdict(base) == "BLOCK"
    red = {
        "lens": "red",
        "findings": [],
        "checked": [],
        "skipped": [],
        "disputes": [
            {"id": "W1", "reason": "input is sanitized", "evidence": "a.py:8 escape(x)"}
        ],
    }
    out, _ = m.apply_red(base, red)
    assert out[0]["disputed"] and m.verdict(out) == "FIX-FIRST"
    bad = dict(red, disputes=[{"id": "W1", "reason": "r", "evidence": ""}])
    base2, _ = m.merge([doc("warden", F("W1", "CRITICAL"))])
    out2, dropped = m.apply_red(base2, bad)
    assert not out2[0]["disputed"] and dropped


def test_red_adds_new_finding_and_verdict_tiers():
    base, _ = m.merge([doc("spine", F("S1", "LOW"))])
    assert m.verdict(base) == "SHIP"
    out, _ = m.apply_red(base, doc("red", F("R1", "HIGH", title="other", file="b.py")))
    assert len(out) == 2 and m.verdict(out) == "FIX-FIRST"


def test_cli_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "w.json"
        p.write_text(json.dumps(doc("warden", F("W1", "CRITICAL"))))
        r = subprocess.run(
            [sys.executable, str(Path(m.__file__)), str(p)],
            capture_output=True,
            text=True,
            check=True,
        )
        assert json.loads(r.stdout)["verdict"] == "BLOCK"
