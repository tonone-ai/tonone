"""Tests for scripts/gen-skill-docs.py (SKILL.md.tmpl -> SKILL.md)."""

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parent.parent
SCRIPT = REPO / "scripts" / "gen-skill-docs.py"

_spec = importlib.util.spec_from_file_location("gen_skill_docs", SCRIPT)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

FM = "---\nname: x-y\ndescription: d\n---\n"


def _fixture(tmp_path, body):
    team = tmp_path / "team"
    skill = team / "x" / "skills" / "x-y"
    skill.mkdir(parents=True)
    sections = tmp_path / "sections"
    sections.mkdir()
    (sections / "hello.md").write_text("hello section\n")
    (skill / "SKILL.md.tmpl").write_text(FM + body)
    return team, sections, skill


def test_repo_check_passes():
    r = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"], capture_output=True, text=True
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_pilot_templates_exist():
    assert list((REPO / "team").glob("*/skills/*/SKILL.md.tmpl"))


def test_render_and_marker_after_frontmatter(tmp_path):
    team, sections, skill = _fixture(
        tmp_path, "\n{{> hello}}\n\nkeep {{> hello}} inline and {{x}}\n"
    )
    problems, written, _ = gen.run(team, sections, check=False)
    assert not problems and written == 1
    out = (skill / "SKILL.md").read_text()
    assert out.startswith(FM + "\n" + gen.MARKER)
    assert "\nhello section\n" in out
    assert "keep {{> hello}} inline and {{x}}" in out


def test_stale_output_detected(tmp_path):
    team, sections, skill = _fixture(tmp_path, "\n{{> hello}}\n")
    gen.run(team, sections, check=False)
    assert gen.run(team, sections, check=True)[0] == []
    (skill / "SKILL.md").write_text("tampered\n")
    problems, _, _ = gen.run(team, sections, check=True)
    assert any(p.startswith("stale") for p in problems)
    (sections / "hello.md").write_text("changed\n")
    (skill / "SKILL.md").unlink()
    assert any(p.startswith("missing") for p in gen.run(team, sections, check=True)[0])


def test_unknown_section_detected(tmp_path):
    team, sections, skill = _fixture(tmp_path, "\n{{> nope}}\n")
    problems, _, _ = gen.run(team, sections, check=True)
    assert any("unknown section 'nope'" in p for p in problems)
    assert not (skill / "SKILL.md").exists()


def test_sections_dir_not_a_skill():
    sections = REPO / "skills" / "_sections"
    assert sections.is_dir() and not (sections / "SKILL.md").exists()
    import test_skill_compliance as tsc

    assert "_sections" not in {d.name for d in tsc.SKILL_DIRS}


def test_tmpl_not_mirrored():
    assert not list((REPO / "skills").rglob("*.tmpl"))


def test_output_kit_bullet_section_renders():
    sec = REPO / "skills" / "_sections" / "output-kit-bullet.md"
    assert (
        sec.read_text() == "- Follow the output format defined in docs/output-kit.md\n"
    )
    out, errs = gen.render(
        FM + "\n## Rules\n{{> output-kit-bullet}}\n", REPO / "skills" / "_sections"
    )
    assert not errs
    assert "\n- Follow the output format defined in docs/output-kit.md\n" in out
    assert "{{>" not in out
