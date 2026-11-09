"""Unit tests for scripts/eval-select.py selection logic."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
SCRIPT = REPO / "scripts" / "eval-select.py"
spec = importlib.util.spec_from_file_location("eval_select", SCRIPT)
es = importlib.util.module_from_spec(spec)
spec.loader.exec_module(es)

EVALS = [
    {"name": "a", "touchfiles": ["lib/a/**", "tests/evals/a/**"]},
    {"name": "b", "touchfiles": ["tools/*.py"]},
]


def names(changed, **kw):
    return [e["name"] for e in es.select(changed, EVALS, **kw)]


def test_glob_semantics():
    assert es.matches("lib/a/x/y.py", ["lib/a/**"])
    assert es.matches("lib/a/x.py", ["lib/a/**"])
    assert es.matches("tools/x.py", ["tools/*.py"])
    assert not es.matches("tools/sub/x.py", ["tools/*.py"])  # * stops at /
    assert es.matches("a/b/c.js", ["**/c.js"]) and es.matches("c.js", ["**/c.js"])
    assert not es.matches("lib/ab/x.py", ["lib/a/**"])
    assert es.matches("./lib/a/x.py", ["lib/a/**"])
    assert not es.matches("tools/xpy", ["tools/*.py"])  # dot is literal


def test_selects_only_matching():
    assert names(["lib/a/gate.py"]) == ["a"]
    assert names(["tools/z.py", "README.md"]) == ["b"]
    assert names(["lib/a/g.py", "tools/z.py"]) == ["a", "b"]


def test_nothing_matches_selects_nothing():
    assert names(["docs/x.md"]) == []
    assert names([]) == []


def test_global_touchfiles_select_all():
    assert names(["scripts/eval-select.py"]) == ["a", "b"]
    assert names(["tests/evals/conftest.py"]) == ["a", "b"]


def test_all_flag():
    assert names([], select_all=True) == ["a", "b"]


def test_real_evals_load_and_are_self_selecting():
    evals = es.load_evals()
    assert {"form-lint", "copy-slop"} <= {e["name"] for e in evals}
    for e in evals:
        assert e["description"]
        assert es.matches(f"tests/evals/{e['name']}/test_x.py", e["touchfiles"]), e[
            "name"
        ]
    picked = [e["name"] for e in es.select(["lib/copy-gate/gate.py"], evals)]
    assert picked == ["copy-slop"]


def test_cli_files_prints_names():
    r = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--files",
            "team/form/scripts/design-lint/rules.js",
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0 and r.stdout.split() == ["form-lint"]


def test_bad_eval_json_exits(tmp_path):
    d = tmp_path / "x"
    d.mkdir()
    (d / "eval.json").write_text(json.dumps({"name": "x"}))
    try:
        es.load_evals(tmp_path)
    except SystemExit as e:
        assert "touchfiles" in str(e)
    else:
        raise AssertionError("expected SystemExit")
