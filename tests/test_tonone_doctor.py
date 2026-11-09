"""tonone-doctor: read-only health report."""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
DOCTOR = REPO / "scripts" / "tonone-doctor.py"


def run(root, *args):
    return subprocess.run(
        [sys.executable, str(DOCTOR), "--root", str(root), *args],
        capture_output=True,
        text=True,
        timeout=300,
    )


def snapshot(root):
    return sorted((str(p), p.stat().st_mtime_ns) for p in Path(root).rglob("*"))


def test_broken_project_has_findings(tmp_path):
    (tmp_path / ".tonone").mkdir()
    (tmp_path / ".tonone" / "design.json").write_text("{not json")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "PostToolUse": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "node .claude/hooks/gone.js",
                                }
                            ]
                        }
                    ]
                }
            }
        )
    )
    before = snapshot(tmp_path)
    r = run(tmp_path, "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["scope"] == "project"
    checks = {(f["check"], f["severity"]) for f in data["findings"]}
    assert ("json-parse", "WARNING") in checks
    assert ("hooks", "WARNING") in checks
    assert snapshot(tmp_path) == before  # read-only


def test_strict_exits_nonzero_on_findings(tmp_path):
    (tmp_path / ".tonone").mkdir()
    (tmp_path / ".tonone" / "x.json").write_text("{")
    assert run(tmp_path).returncode == 0
    assert run(tmp_path, "--strict").returncode == 1


def test_clean_project_no_critical(tmp_path):
    r = run(tmp_path, "--json")
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert not [f for f in data["findings"] if f["severity"] == "CRITICAL"]
    assert run(tmp_path, "--strict").returncode == 0


def test_text_output_is_boxed(tmp_path):
    out = run(tmp_path).stdout
    assert "doctor" in out and "╭" in out and "╯" in out
    assert len(out.splitlines()) <= 40


def test_plugin_repo_smoke():
    r = run(REPO, "--json")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["scope"] == "plugin"
    assert data["findings"]


def test_usage_off_and_summary_tolerates_bad_lines(tmp_path):
    r = run(tmp_path, "--usage")
    assert r.returncode == 0 and "metrics off (set TONONE_METRICS=on)" in r.stdout
    (tmp_path / ".tonone").mkdir()
    (tmp_path / ".tonone" / "metrics.jsonl").write_text(
        '{"ts":"2026-11-08T00:00:00Z","tool":"apex-guard","event":"ask","rules":["x"]}\n'
        "not json\n"
        '{"ts":"2026-11-08T00:00:00Z","tool":"apex-guard","event":"ask"}\n'
        '{"ts":"2020-01-01T00:00:00Z","tool":"copy-slop","event":"run","warn":2}\n'
        '{"tool":"x"}\n'
        "[1]\n"
    )
    r = run(tmp_path, "--usage")
    assert r.returncode == 0 and "apex-guard" in r.stdout and "ask x2" in r.stdout
    assert "malformed" in r.stdout and len(r.stdout.splitlines()) <= 40
    r = run(tmp_path, "--usage", "--since", "7d")
    assert "copy-slop" not in r.stdout and "apex-guard" in r.stdout
    assert run(tmp_path, "--usage", "--since", "bogus").returncode == 2
    assert run(tmp_path, "--usage", "--json").returncode == 0
