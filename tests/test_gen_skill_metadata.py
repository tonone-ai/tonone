"""
Tests for scripts/gen-skill-metadata.py — the tags/compatibility frontmatter
backfill. Covers the idempotency guarantee (safe to re-run for new skills),
the tag-building logic (dedup, truncation, unmapped-agent hard-fail, special-
skill fallback), and the atomic-write path.
"""

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent

_spec = importlib.util.spec_from_file_location(
    "gen_skill_metadata", REPO / "scripts" / "gen-skill-metadata.py"
)
gsm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gsm)


def test_process_skips_file_that_already_has_tags(tmp_path):
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "---\nname: forge-recon\ndescription: x\nlicense: MIT\ntags: [existing]\n---\nbody\n"
    )
    before = skill.read_text()
    reason, result = gsm.process(skill, dry_run=False)
    assert reason == "already_tagged"
    assert result is None
    assert skill.read_text() == before


def test_process_skips_file_that_already_has_compatibility(tmp_path):
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "---\nname: forge-recon\ndescription: x\nlicense: MIT\n"
        "compatibility: Designed for Claude Code\n---\nbody\n"
    )
    before = skill.read_text()
    reason, result = gsm.process(skill, dry_run=False)
    assert reason == "already_tagged"
    assert result is None
    assert skill.read_text() == before


def test_process_reports_no_frontmatter(tmp_path):
    f = tmp_path / "SKILL.md"
    f.write_text("just a body, no frontmatter\n")
    reason, result = gsm.process(f, dry_run=True)
    assert reason == "no_frontmatter"
    assert result is None


def test_process_reports_no_name_field(tmp_path):
    f = tmp_path / "SKILL.md"
    f.write_text("---\ndescription: x\nlicense: MIT\n---\nbody\n")
    reason, result = gsm.process(f, dry_run=True)
    assert reason == "no_name_field"
    assert result is None


def test_process_adds_both_fields(tmp_path):
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "---\nname: forge-recon\ndescription: x\nlicense: MIT\n---\nbody\n"
    )
    reason, result = gsm.process(skill, dry_run=False)
    assert reason == "ok"
    assert result is not None
    text = skill.read_text()
    assert "compatibility: Designed for Claude Code" in text
    assert "tags: [" in text


def test_process_write_is_atomic_no_tmp_file_left_behind(tmp_path):
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        "---\nname: forge-recon\ndescription: x\nlicense: MIT\n---\nbody\n"
    )
    gsm.process(skill, dry_run=False)
    assert not skill.with_suffix(skill.suffix + ".tmp").exists()


def test_process_writes_lf_only_even_with_crlf_input(tmp_path):
    skill = tmp_path / "SKILL.md"
    skill.write_bytes(
        b"---\r\nname: forge-recon\r\ndescription: x\r\nlicense: MIT\r\n---\r\nbody\r\n"
    )
    gsm.process(skill, dry_run=False)
    raw = skill.read_bytes()
    assert b"\r\n" not in raw


def test_build_tags_dedupes_suffix_matching_base_tag(monkeypatch):
    monkeypatch.setitem(gsm.AGENT_TAGS, "cache", ["infrastructure", "caching"])
    tags = gsm.build_tags("cache-caching")
    assert tags == ["infrastructure", "caching"]


def test_build_tags_truncates_to_max(monkeypatch):
    monkeypatch.setitem(gsm.AGENT_TAGS, "foo", ["a", "b", "c", "d", "e"])
    tags = gsm.build_tags("foo-extra")
    assert len(tags) == gsm.MAX_TAGS


def test_build_tags_raises_on_unmapped_agent(monkeypatch):
    monkeypatch.delitem(gsm.AGENT_TAGS, "forge", raising=False)
    with pytest.raises(ValueError, match="forge"):
        gsm.build_tags("forge-recon")


def test_build_tags_uses_special_skill_fallback():
    tags = gsm.build_tags("tonone-onboard")
    assert tags == gsm.SPECIAL_SKILL_TAGS["tonone-onboard"]


def test_find_skill_files_excludes_noise_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(gsm, "REPO_ROOT", tmp_path)
    real = tmp_path / "team" / "forge" / "skills" / "forge-recon"
    real.mkdir(parents=True)
    (real / "SKILL.md").write_text("---\nname: forge-recon\n---\nbody\n")
    noise = tmp_path / "team" / "forge" / "scripts" / ".venv" / "lib" / "SKILL.md"
    noise.parent.mkdir(parents=True)
    noise.write_text("not a real skill")
    found = list(gsm.find_skill_files())
    assert real / "SKILL.md" in found
    assert noise not in found
