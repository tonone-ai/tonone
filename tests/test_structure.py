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
AGENTS = sorted(
    [
        d.name
        for d in (REPO / "team").iterdir()
        if d.is_dir() and (d / ".claude-plugin" / "plugin.json").exists()
    ]
)


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


def test_plugin_json_skills_and_agents_are_not_stale_arrays():
    """
    plugin.json must not carry 'skills' or 'agents' as an array of {name, path}
    objects — that shape belongs to the per-skill-plugin generator removed in
    1.13.0 and fails install-time schema validation outright (confirmed via
    `claude plugin install`, not just `claude plugin validate`). The other 89
    agents omit both keys and rely on auto-discovery; that's the only shape
    that installs. 11 agents (budget, deploy, embed, evals, form, guard,
    prompt, proof, rank, token, trace) shipped with the stale array shape in
    1.13.0 and could not be installed standalone — exactly the granularity
    apex-profile depends on.
    """
    for agent in AGENTS:
        p = REPO / "team" / agent / ".claude-plugin" / "plugin.json"
        data = json.loads(p.read_text())
        for key in ("skills", "agents"):
            value = data.get(key)
            assert not isinstance(value, list), (
                f"{agent}/plugin.json: '{key}' is a stale array of "
                f"{{name, path}} objects — this fails `claude plugin install "
                f"{agent}@tonone-ai`. Remove the key; auto-discovery covers it."
            )


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
        if skill_dir.is_dir() and not skill_dir.name.startswith("_"):
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


def test_marketplace_json_lists_all_agents():
    """
    Every agent in team/ must have a matching entry in marketplace.json plugins.
    Adding an agent to team/ without registering it means it won't appear in
    the registry for install by name.
    """
    manifest_path = REPO / ".claude-plugin" / "marketplace.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text())
    listed_names = {p["name"] for p in manifest.get("plugins", [])}
    missing = [a for a in AGENTS if a not in listed_names]
    assert (
        not missing
    ), f"Agents in team/ missing from marketplace.json plugins: {missing}"


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


def _team_skills():
    """Map skill name -> canonical team/<agent>/skills/<name>/SKILL.md.

    Walks the tree instead of deriving the agent from the skill-name prefix:
    the prefix split is wrong for any skill whose name isn't <agent>-<verb>
    (tonone-onboard, the per-agent hub skills), which silently skipped those
    from the comparison.
    """
    skills = {}
    for agent in sorted((REPO / "team").iterdir()):
        skills_dir = agent / "skills"
        if not skills_dir.is_dir():
            continue  # e.g. team/shared holds no skills
        for d in sorted(skills_dir.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                skills[d.name] = d / "SKILL.md"
    return skills


def test_root_skills_mirror_is_complete():
    """
    Every team/<agent>/skills/<name> must have a root skills/<name> mirror.

    The bundle plugin ("tonone", source "./" in marketplace.json) discovers its
    skills from root skills/ and only from there, so a skill missing from the
    mirror is invisible to everyone who installs the bundle — the owning agent
    installs, its skills don't. This is exactly how 257 skills across 73 agents
    went missing while every per-agent plugin kept working.

    Fix drift with: python scripts/sync-skills.py
    """
    missing = sorted(
        name
        for name in _team_skills()
        if not (REPO / "skills" / name / "SKILL.md").exists()
    )
    assert not missing, (
        f"{len(missing)} team skill(s) missing from the root skills/ mirror — "
        f"they will not ship in the bundle plugin. "
        f"Run: python scripts/sync-skills.py\n  " + "\n  ".join(missing)
    )


def test_root_skills_match_team_skills():
    """
    Every root skills/<name>/SKILL.md must be identical to its canonical copy in
    team/<agent>/skills/<name>/SKILL.md.  Drift means the root copy is missing
    features that the team copy gained (or vice versa).
    """
    team = _team_skills()
    drifted = []
    for name, team_file in sorted(team.items()):
        root_file = REPO / "skills" / name / "SKILL.md"
        if not root_file.exists():
            continue  # completeness is test_root_skills_mirror_is_complete's job
        if root_file.read_text() != team_file.read_text():
            drifted.append(name)
    assert not drifted, (
        f"{len(drifted)} root skill(s) drifted from team/ canonical copy — "
        f"run: python scripts/sync-skills.py\n  " + "\n  ".join(drifted)
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


def test_agent_definitions_mirror_team_copies():
    """
    agents/<name>.md and team/<name>/agents/<name>.md must be byte-identical.

    Both copies ship — the bundle plugin reads agents/, the per-agent plugin
    reads team/<name>/agents/ — so drift means two installs of the same agent
    behave differently. Found in September 2026: Form's anti-pattern list had
    been edited only in agents/, Draft's skills table only in team/.
    """
    drifted = []
    for agent_file in sorted((REPO / "agents").glob("*.md")):
        team_copy = REPO / "team" / agent_file.stem / "agents" / agent_file.name
        if not team_copy.exists():
            continue
        if agent_file.read_text() != team_copy.read_text():
            drifted.append(agent_file.stem)
    assert not drifted, (
        f"agent definitions drifted between agents/ and team/*/agents/: {drifted}. "
        f"Reconcile by hand — whichever copy is newer wins — then copy it to the other."
    )


def test_root_hooks_declared_once():
    """Root plugin hooks live only in hooks/hooks.json.

    Claude Code loads hooks/hooks.json AND an inline "hooks" key in
    plugin.json together, so any hook listed in both runs twice.
    """
    root_manifest = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text())
    assert "hooks" not in root_manifest, (
        "declare root hooks in hooks/hooks.json only; an inline 'hooks' key in "
        ".claude-plugin/plugin.json makes shared hooks run twice"
    )


def test_no_symlinks_and_bundles_in_sync():
    """Bundles hold real copies, not symlinks, and match the root sources.

    The Anthropic plugin directory rejects repositories with symlinks.
    """
    import subprocess

    staged = subprocess.run(
        ["git", "ls-files", "-s"], cwd=REPO, capture_output=True, text=True
    ).stdout
    links = [
        line.split("\t", 1)[1]
        for line in staged.splitlines()
        if line.startswith("120000")
    ]
    assert not links, f"symlinks tracked: {links[:5]}"
    check = subprocess.run(
        ["python3", "scripts/sync-bundles.py", "--check"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0, check.stdout


def _sync_bundles_module():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "sync_bundles", REPO / "scripts" / "sync-bundles.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_every_root_skill_is_bundled_or_exempt():
    """A root skill in no bundle ships to nobody who installs a bundle.

    New skills must get a bundle/<team>/skills/<name>/ entry (then run
    scripts/sync-bundles.py) or, with a reason, a line in bundle/UNBUNDLED.txt.
    """
    mod = _sync_bundles_module()
    listed = mod.load_unbundled()
    exempt = set(listed["ROOT_ONLY"]) | set(listed["LEGACY_UNBUNDLED"])
    orphans = sorted(mod.root_skills() - mod.bundled_skills() - exempt)
    assert not orphans, (
        "skills in no bundle (add bundle/<team>/skills/<name>/ and run "
        "python3 scripts/sync-bundles.py, or list in bundle/UNBUNDLED.txt): "
        f"{orphans}"
    )


def test_unbundled_list_is_honest():
    """The exemption list names no bundled skill, no missing skill, no repeats."""
    mod = _sync_bundles_module()
    listed = mod.load_unbundled()
    names = listed["ROOT_ONLY"] + listed["LEGACY_UNBUNDLED"]
    dupes = sorted({n for n in names if names.count(n) > 1})
    assert not dupes, f"listed twice in bundle/UNBUNDLED.txt: {dupes}"
    stale = sorted(set(names) & mod.bundled_skills())
    assert not stale, f"bundled now, remove from bundle/UNBUNDLED.txt: {stale}"
    gone = sorted(set(names) - mod.root_skills())
    assert not gone, f"no such root skill, remove from bundle/UNBUNDLED.txt: {gone}"
    legacy = listed["LEGACY_UNBUNDLED"]
    assert legacy == sorted(legacy), "LEGACY_UNBUNDLED must stay sorted"
    assert listed["ROOT_ONLY"] == sorted(listed["ROOT_ONLY"])


def test_core_excluded_list_is_honest_and_core_is_complete():
    """tonone-core vs engineering-team drift guard (mirrors sync-bundles --check).

    Every engineering skill is in core or in CORE_EXCLUDED [SKILLS]; core ships
    no hooks/ or lib/; every repo path a core skill cites that exists at the
    root is shipped by core or listed in [REFS], and [REFS] cannot go stale.
    """
    mod = _sync_bundles_module()
    listed = mod.load_core_excluded()
    for sec in ("SKILLS", "REFS"):
        assert listed[sec] == sorted(set(listed[sec])), f"[{sec}] sorted, no repeats"
    problems = mod.core_problems()
    assert not problems, "\n".join(problems)
    assert not (REPO / "bundle" / "tonone-core" / "hooks").exists()
    assert not (REPO / "bundle" / "tonone-core" / "lib").exists()


def test_core_drift_guard_reports_missing_skill(tmp_path):
    """A new engineering skill absent from core and the exclusion list is reported."""
    mod = _sync_bundles_module()
    for team, skills in (
        ("engineering-team", ["a-one", "a-new"]),
        ("tonone-core", ["a-one"]),
    ):
        for name in skills:
            d = tmp_path / team / "skills" / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(
                "see team/apex/reference/x.md and docs/gone.md\n"
            )
    root = tmp_path / "root"
    (root / "docs").mkdir(parents=True)
    (root / "docs" / "gone.md").write_text("x")
    excl = {"SKILLS": [], "REFS": []}
    out = mod.core_problems(tmp_path, excl, root)
    assert any("a-new" in line for line in out)
    assert any("docs/gone.md" in line for line in out)  # exists at root, not shipped
    assert not any("team/apex/reference/x.md" in line for line in out)  # not at root
    # Listing the skill and the ref, and shipping hooks/, changes the report.
    excl = {"SKILLS": ["a-new"], "REFS": ["docs/gone.md"]}
    (tmp_path / "tonone-core" / "hooks").mkdir()
    out = mod.core_problems(tmp_path, excl, root)
    assert not any("a-new" in line for line in out)
    assert any("hooks/" in line for line in out)
    # A stale [REFS] entry (shipped now) and a stale [SKILLS] entry are reported.
    (tmp_path / "tonone-core" / "docs").mkdir()
    (tmp_path / "tonone-core" / "docs" / "gone.md").write_text("x")
    excl = {"SKILLS": ["a-one"], "REFS": ["docs/gone.md"]}
    out = mod.core_problems(tmp_path, excl, root)
    assert any("a-one" in line and "remove" in line for line in out)
    assert any("docs/gone.md" in line and "ships" in line for line in out)


def test_bundle_hooks_reference_shipped_files():
    """Every hook a bundle registers points at a file that bundle ships."""
    import re

    for hooks in sorted((REPO / "bundle").glob("*/hooks/hooks.json")):
        bundle = hooks.parent.parent
        for rel in re.findall(
            r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\"\s]+)",
            json.dumps(json.loads(hooks.read_text())).replace('\\"', " "),
        ):
            assert (
                bundle / rel
            ).is_file(), f"{hooks.relative_to(REPO)}: {rel} not shipped"


def test_bundle_omit_blocks():
    """<!-- bundle:omit X --> blocks drop for bundle X and unwrap elsewhere."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "sync_bundles", REPO / "scripts" / "sync-bundles.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    text = "a\n<!-- bundle:omit tonone-core -->\nb\n<!-- /bundle:omit -->\nc\n"
    assert mod.omit_blocks("tonone-core", text) == "a\nc\n"
    assert mod.omit_blocks("engineering-team", text) == "a\nb\nc\n"


def test_headline_counts_match_tree():
    """Agent and skill totals quoted in public copy match the tree.

    README, CLAUDE.md and the plugin manifests hardcode the totals, and
    directories, plugin browsers and awesome lists copy them verbatim. They
    drifted before (marketplace.json said 23 agents at 100). Only totals are
    checked: per-team counts are below 50 agents, and the skill total is the
    only three-digit skill count outside the per-team
    "(N agents, M skills)" headers, so those are ignored.
    """
    import re

    agents = len(AGENTS)
    skills = len(_team_skills())
    files = [
        "README.md",
        "CLAUDE.md",
        ".claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
    ]
    wrong = []
    for rel in files:
        text = (REPO / rel).read_text()
        for m in re.finditer(r"\b(\d+) (?:agents|specialists)\b", text, re.I):
            if int(m.group(1)) >= 50 and int(m.group(1)) != agents:
                wrong.append(f"{rel}: '{m.group(0)}' (tree has {agents} agents)")
        # "(15 agents, 105 skills)" per-team headers in the README list are
        # subtotals, not the headline total.
        for m in re.finditer(r"(?<!agents, )\b(\d{3}) skills\b", text, re.I):
            if int(m.group(1)) != skills:
                wrong.append(f"{rel}: '{m.group(0)}' (tree has {skills} skills)")
    assert not wrong, "\n".join(wrong)
