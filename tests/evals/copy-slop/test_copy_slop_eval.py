"""Eval: lib/copy-gate/gate.py --slop as a CLI."""

import json

from conftest import PY, REPO, run, stage

GATE = REPO / "lib/copy-gate/gate.py"
FIX = REPO / "tests/evals/copy-slop/fixtures"


def gate(workdir, name, *extra):
    (path,) = stage(FIX, workdir, name)
    r = run([PY, GATE, "--slop", path.name, *extra], cwd=workdir)
    assert r.stdout, r.stderr
    return r.returncode, json.loads(r.stdout)


def codes(rep, sev=None):
    return {
        f["code"]
        for res in rep["results"]
        for f in res["findings"]
        if sev is None or f["severity"] == sev
    }


def test_residue_fails(workdir):
    code, rep = gate(workdir, "residue.txt")
    assert rep["verdict"] == "FAIL" and code == 1
    assert "FAIL" in {f["severity"] for r in rep["results"] for f in r["findings"]}


def test_device_overuse_warns_not_fails(workdir):
    code, rep = gate(workdir, "devices.txt")
    assert rep["verdict"] == "WARN", rep
    assert "SLOP_EM_DASH" in codes(rep, "WARN") and rep["fails"] == 0
    assert code == 0  # warnings never fail the run


def test_clean_paragraph_passes(workdir):
    code, rep = gate(workdir, "clean.txt")
    assert rep["verdict"] == "PASS" and code == 0
    assert codes(rep) == set()


def test_cli_waiver_is_honored_and_reported(workdir):
    _, plain = gate(workdir, "waiver.txt")
    assert plain["verdict"] == "WARN" and "HYPE" in codes(plain)
    code, rep = gate(workdir, "waiver.txt", "--waive", "Seamless")
    assert rep["verdict"] == "PASS" and code == 0
    assert rep["results"][0]["waived"][0]["count"] == 1


def test_waiver_file_requires_reason(workdir):
    (workdir / ".tonone").mkdir()
    wf = workdir / ".tonone" / "copy-waivers.json"
    wf.write_text(
        json.dumps({"waive": [{"term": "Seamless", "reason": "client brand"}]})
    )
    _, rep = gate(workdir, "waiver.txt")
    assert rep["verdict"] == "PASS"
    assert rep["waivers"] == [{"term": "Seamless", "reason": "client brand"}]
    wf.write_text(json.dumps({"waive": [{"term": "Seamless"}]}))
    code, bad = gate(workdir, "waiver.txt")
    assert code == 2 and bad["ok"] is False
