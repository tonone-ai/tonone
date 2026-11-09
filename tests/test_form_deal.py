"""Tests for team/form/scripts/form-deal/deal.py."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "team" / "form" / "scripts" / "form-deal" / "deal.py"
SKILL = ROOT / "team" / "form" / "skills" / "form-deal" / "SKILL.md"


def run(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=cwd
    )


def deal(hist, *extra, seed=None):
    a = ["--trade", "saas", "--page-kind", "landing", "--history", str(hist), "--json"]
    if seed:
        a += ["--seed", seed]
    r = run(*a, *extra)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_check_passes():
    r = run("--check")
    assert r.returncode == 0, r.stdout
    assert r.stdout.startswith("OK")


def test_skill_has_required_lines():
    t = SKILL.read_text()
    assert "Follow the output format defined in docs/output-kit.md" in t
    assert "/atlas-report" in t
    assert "name: form-deal" in t


def test_deterministic(tmp_path):
    h = tmp_path / "none.json"
    a, b = deal(h, seed="fixed"), deal(h, seed="fixed")
    assert a == b


def test_history_avoidance(tmp_path):
    h = tmp_path / "h.json"
    first = deal(h, seed="x")
    h.write_text(
        json.dumps([{"palette": first["palette"]["id"], "type": first["type"]["id"]}])
    )
    second = deal(h, seed="x")
    assert second["palette"]["id"] != first["palette"]["id"]
    assert second["type"]["id"] != first["type"]["id"]


def test_missing_and_corrupt_history_fail_open(tmp_path):
    assert deal(tmp_path / "missing.json")["palette"]
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert deal(bad)["palette"]


def test_record_appends_and_changes_next_deal(tmp_path):
    h = tmp_path / ".tonone" / "design-history.json"
    base = ["--trade", "saas", "--page-kind", "landing", "--history", str(h), "--json"]
    r1 = run(*base, "--record")
    assert r1.returncode == 0
    d1 = json.loads(r1.stdout)
    entries = json.loads(h.read_text())
    assert len(entries) == 1
    assert (
        entries[0]["palette"] == d1["palette"]["id"]
        and entries[0]["type"] == d1["type"]["id"]
    )
    d2 = json.loads(run(*base, "--record").stdout)
    assert d2["palette"]["id"] != d1["palette"]["id"]
    assert len(json.loads(h.read_text())) == 2
