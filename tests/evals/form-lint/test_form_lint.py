"""Eval: design-lint CLI end to end (node, no deps)."""

import json
import shutil

import pytest
from conftest import REPO, run, stage

CLI = REPO / "team/form/scripts/design-lint/design-lint.js"
FIX = REPO / "tests/evals/form-lint/fixtures"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node required")


def lint(workdir, name, *extra):
    (path,) = stage(FIX, workdir, name)
    r = run(["node", CLI, path.name, "--json", *extra], cwd=workdir)
    assert r.stdout, r.stderr
    return r.returncode, json.loads(r.stdout)


def rules(report):
    return {f["rule"] for f in report["findings"]}


def test_gradient_text_fires(workdir):
    code, rep = lint(workdir, "gradient.jsx")
    assert "gradient-text" in rules(rep)
    assert code == 1  # immediate-tier finding fails the run
    hit = next(f for f in rep["findings"] if f["rule"] == "gradient-text")
    assert hit["tier"] == "immediate" and hit["line"] >= 1 and hit["fix"]


def test_low_contrast_fires_with_ratio(workdir):
    code, rep = lint(workdir, "lowcontrast.css")
    assert "low-contrast" in rules(rep)
    assert "gradient-text" not in rules(rep)
    msg = next(f["message"] for f in rep["findings"] if f["rule"] == "low-contrast")
    assert "4.5:1" in msg and code == 1


def test_clean_file_has_zero_immediate_findings(workdir):
    code, rep = lint(workdir, "clean.css")
    assert [f for f in rep["findings"] if f["tier"] == "immediate"] == []
    assert code == 0 and rep["scanned"] == 1


def test_disable_comment_suppresses_only_named_rule(workdir):
    code, rep = lint(workdir, "suppressed.jsx")
    assert "gradient-text" not in rules(rep)
    assert code == 0


def test_missing_path_is_usage_error_not_crash(workdir):
    r = run(["node", CLI, "nope-does-not-exist.css", "--json"], cwd=workdir)
    assert r.returncode in (0, 2)
    assert "Traceback" not in r.stderr and "at Object" not in r.stderr
