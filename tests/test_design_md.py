"""DESIGN.md unified format: spec example + fixtures parse in design-lint; skills reference the spec."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "design-md"
LINT = ROOT / "team/form/scripts/design-lint/design-lint.js"
SPEC = ROOT / "docs" / "design-md.md"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None, reason="node not installed"
)


def parse(design_dir: Path):
    code = (
        "const {loadDesignMd}=require(process.argv[1]);"
        "const d=loadDesignMd(process.argv[2]);"
        "console.log(JSON.stringify(d&&{hex:[...d.hex],scale:[...d.scale],format:d.format}))"
    )
    r = subprocess.run(
        ["node", "-e", code, str(LINT), str(design_dir)],
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_unified_fixture_parses():
    d = parse(FIX / "unified")
    assert d["format"] == "unified"
    assert {"faf9f7", "1c1b1a", "2d5be3"} <= set(d["hex"])
    assert "787673" in d["hex"]  # rgb(120,118,115) literal
    assert 16 in d["scale"] and 6 in d["scale"]


def test_legacy_fixture_parses():
    d = parse(FIX / "legacy")
    assert d["format"] == "legacy"
    assert {"faf9f7", "ffffff", "1c1b1a", "2d5be3"} <= set(d["hex"])
    assert 16 in d["scale"]


def test_spec_example_parses(tmp_path):
    blocks = re.findall(r"```markdown\n(.*?)```", SPEC.read_text(), re.S)
    assert blocks, "spec has no markdown example"
    (tmp_path / "DESIGN.md").write_text(blocks[-1])
    d = parse(tmp_path)
    assert d["format"] == "unified"
    assert {"faf9f7", "1c1b1a", "2d5be3"} <= set(d["hex"])
    assert 16 in d["scale"]


def test_drift_uses_both_formats(tmp_path):
    for name in ("unified", "legacy"):
        proj = tmp_path / name
        proj.mkdir()
        shutil.copy(FIX / name / "DESIGN.md", proj / "DESIGN.md")
        (proj / "a.css").write_text(
            ".a{color:#2d5be3;background:#faf9f7}.b{color:#1c1b1a}.c{color:#abcdef}\n"
        )
        r = subprocess.run(
            ["node", str(LINT), str(proj / "a.css"), "--root", str(proj), "--json"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        out = r.stdout
        assert "abcdef" in out.lower(), (name, out, r.stderr)
        assert "2d5be3" not in out.lower()


@pytest.mark.parametrize("skill", ["form-brief", "form-document"])
def test_skills_reference_spec(skill):
    text = (ROOT / "team/form/skills" / skill / "SKILL.md").read_text()
    assert "docs/design-md.md" in text


def test_spec_lists_legacy_headings():
    text = SPEC.read_text()
    for h in ("Visual Theme & Atmosphere", "Color Palette & Roles", "Typography Rules"):
        assert h in text
