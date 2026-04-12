"""
Structure tests for the tonone repo.

Risk map:
- Agent definitions missing → HIGH impact (broken install, silent gaps at public release)
- plugin.json schema violations → HIGH impact (plugin registry won't parse)
- setup.sh missing → MEDIUM impact (agent unusable without manual workaround)
- Skill SKILL.md missing/thin → HIGH impact (skill won't load in Claude)
- marketplace.json out of sync → MEDIUM impact (wrong install count in registry)

These are integration-level structure tests — they exercise the real filesystem,
not mocked paths, so they catch renames, deletions, and partial scaffolds.
"""

import json
from pathlib import Path

REPO = Path(__file__).parent.parent
AGENTS = sorted([d.name for d in (REPO / "team").iterdir() if d.is_dir()])


# ---------------------------------------------------------------------------
# Agent structure
# ---------------------------------------------------------------------------


def test_all_agents_have_plugin_json():
    """Every agent must have a .claude-plugin/plugin.json for the plugin registry."""
    for agent in AGENTS:
        p = REPO / "team" / agent / ".claude-plugin" / "plugin.json"
        assert p.exists(), f"{agent}: missing .claude-plugin/plugin.json"


def test_all_agents_have_agent_definition():
    """Every agent must have a canonical definition in agents/<agent>.md."""
    for agent in AGENTS:
        p = REPO / "agents" / f"{agent}.md"
        assert p.exists(), f"{agent}: missing agents/{agent}.md"


def test_all_agents_have_setup_script():
    """Every agent must have a scripts/setup.sh for local environment setup."""
    for agent in AGENTS:
        p = REPO / "team" / agent / "scripts" / "setup.sh"
        assert p.exists(), f"{agent}: missing scripts/setup.sh"


def test_plugin_json_required_fields():
    """plugin.json must contain name, version, and description — registry parses these."""
    for agent in AGENTS:
        p = REPO / "team" / agent / ".claude-plugin" / "plugin.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        for field in ["name", "version", "description"]:
            assert field in data, f"{agent}/plugin.json: missing '{field}'"


def test_agent_definitions_not_empty():
    """Agent definitions must be substantive (>= 50 lines) — not placeholder stubs."""
    for agent_file in sorted((REPO / "agents").glob("*.md")):
        lines = len(agent_file.read_text().splitlines())
        assert (
            lines >= 50
        ), f"agents/{agent_file.name}: only {lines} lines (suspiciously thin)"


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


def test_all_skills_have_skill_md():
    """Every skill directory must contain a SKILL.md — without it the skill won't load."""
    skills_dir = REPO / "skills"
    for skill_dir in sorted(skills_dir.iterdir()):
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            assert skill_file.exists(), f"skills/{skill_dir.name}: missing SKILL.md"


def test_skills_have_minimum_content():
    """SKILL.md files must have at least 10 lines — catches empty scaffolded stubs."""
    skills_dir = REPO / "skills"
    for skill_dir in sorted(skills_dir.iterdir()):
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            lines = len(skill_file.read_text().splitlines())
            assert (
                lines >= 10
            ), f"skills/{skill_dir.name}/SKILL.md: only {lines} lines (suspiciously thin)"


# ---------------------------------------------------------------------------
# Marketplace manifest
# ---------------------------------------------------------------------------


def test_marketplace_json_skill_count():
    """
    If marketplace.json has a 'skills' array, it must match the actual count of
    skill directories. A mismatch means the manifest was not updated after adding
    or removing skills.

    Note: the current marketplace.json uses a 'plugins' array (bundle registry),
    not a 'skills' array — so this test is a no-op today and activates automatically
    if a skills index is added later.
    """
    manifest_path = REPO / ".claude-plugin" / "marketplace.json"
    if not manifest_path.exists():
        return  # no manifest at all — skip
    manifest = json.loads(manifest_path.read_text())
    if "skills" not in manifest:
        return  # manifest exists but has no skills index — skip
    actual_skills = len([d for d in (REPO / "skills").iterdir() if d.is_dir()])
    listed_skills = len(manifest["skills"])
    assert (
        listed_skills == actual_skills
    ), f"marketplace.json lists {listed_skills} skills but skills/ has {actual_skills} dirs"


# ---------------------------------------------------------------------------
# Internal consistency
# ---------------------------------------------------------------------------


def test_team_agents_match_agents_directory():
    """
    Every agent in team/ must have a matching file in agents/, and vice versa.
    This catches the case where an agent is added to one location but not the other.
    """
    team_agents = set(AGENTS)
    agents_dir_names = {f.stem for f in (REPO / "agents").glob("*.md")}
    only_in_team = team_agents - agents_dir_names
    only_in_agents_dir = agents_dir_names - team_agents
    assert not only_in_team, f"In team/ but missing agents/*.md: {sorted(only_in_team)}"
    assert (
        not only_in_agents_dir
    ), f"In agents/ but missing team/ dir: {sorted(only_in_agents_dir)}"


def test_root_skills_match_team_skills():
    """
    Every root skills/<name>/SKILL.md must be identical to its canonical copy in
    team/<agent>/skills/<name>/SKILL.md.  Drift means the root copy is missing
    features that the team copy gained (or vice versa).
    """
    skills_dir = REPO / "skills"
    drifted = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        root_file = skill_dir / "SKILL.md"
        if not root_file.exists():
            continue
        agent = skill_dir.name.split("-")[0]
        team_file = REPO / "team" / agent / "skills" / skill_dir.name / "SKILL.md"
        if not team_file.exists():
            continue  # team-only or root-only mismatches caught elsewhere
        if root_file.read_text() != team_file.read_text():
            drifted.append(skill_dir.name)
    assert (
        not drifted
    ), f"{len(drifted)} root skill(s) drifted from team/ canonical copy: " + ", ".join(
        drifted
    )


def test_skill_output_kit_contract():
    """
    Every skill SKILL.md must contain the output-kit contract line.
    Without it, the skill's output is not guaranteed to follow the team standard
    (40-line CLI max, box-drawing skeleton, severity indicators, compressed prose).
    """
    contract = "Follow the output format defined in docs/output-kit.md"
    missing = []
    for agent in AGENTS:
        skills_dir = REPO / "team" / agent / "skills"
        if not skills_dir.exists():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            if contract not in skill_file.read_text():
                missing.append(skill_dir.name)
    assert (
        not missing
    ), f"{len(missing)} skill(s) missing output-kit contract line: " + ", ".join(
        missing
    )


def test_plugin_json_name_matches_agent_directory():
    """
    plugin.json 'name' must match the agent directory name (bare, no prefix).
    Mismatches break the registry lookup by name.
    """
    for agent in AGENTS:
        p = REPO / "team" / agent / ".claude-plugin" / "plugin.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        if "name" not in data:
            continue
        expected = agent
        assert (
            data["name"] == expected
        ), f"{agent}/plugin.json: 'name' is '{data['name']}', expected '{expected}'"
