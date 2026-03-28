"""Tests for the tonone agent registry."""

from tonone.registry import (
    AGENTS,
    TEAMS,
    AgentEntry,
    get_agent,
    get_agents_by_team,
    get_all_teams,
)

# ── AgentEntry dataclass ────────────────────────────────────────


class TestAgentEntry:
    def test_frozen(self):
        entry = AgentEntry(
            name="test",
            team="t",
            pypi_package="p",
            plugin_name="test-plugin",
            marketplace="test/repo",
            description="d",
            skills=(),
        )
        try:
            entry.name = "changed"
            raise AssertionError("Should be frozen")
        except AttributeError:
            pass

    def test_default_status(self):
        entry = AgentEntry(
            name="test",
            team="t",
            pypi_package="p",
            plugin_name="test-plugin",
            marketplace="test/repo",
            description="d",
            skills=(),
        )
        assert entry.status == "available"

    def test_custom_status(self):
        entry = AgentEntry(
            name="test",
            team="t",
            pypi_package="p",
            plugin_name="test-plugin",
            marketplace="test/repo",
            description="d",
            skills=(),
            status="coming-soon",
        )
        assert entry.status == "coming-soon"

    def test_skills_is_tuple(self):
        entry = AgentEntry(
            name="test",
            team="t",
            pypi_package="p",
            plugin_name="test-plugin",
            marketplace="test/repo",
            description="d",
            skills=("/a", "/b"),
        )
        assert isinstance(entry.skills, tuple)
        assert len(entry.skills) == 2


# ── AGENTS registry ─────────────────────────────────────────────


class TestAgentsRegistry:
    def test_agents_is_tuple(self):
        assert isinstance(AGENTS, tuple)

    def test_has_at_least_one_agent(self):
        assert len(AGENTS) >= 1

    def test_cloud_run_specialist_exists(self):
        names = [a.name for a in AGENTS]
        assert "cloud-run-specialist" in names

    def test_cloud_run_specialist_fields(self):
        agent = next(a for a in AGENTS if a.name == "cloud-run-specialist")
        assert agent.team == "cloud-architecture"
        assert agent.pypi_package == "cloudrun-agent"
        assert agent.status == "available"
        assert len(agent.skills) >= 1

    def test_all_agents_have_required_fields(self):
        for agent in AGENTS:
            assert agent.name
            assert agent.team
            assert agent.pypi_package
            assert agent.description
            assert isinstance(agent.skills, tuple)
            assert agent.status in ("available", "coming-soon")

    def test_no_duplicate_names(self):
        names = [a.name for a in AGENTS]
        assert len(names) == len(set(names))

    def test_no_duplicate_pypi_packages(self):
        packages = [a.pypi_package for a in AGENTS]
        assert len(packages) == len(set(packages))


# ── TEAMS dict ───────────────────────────────────────────────────


class TestTeams:
    def test_teams_is_dict(self):
        assert isinstance(TEAMS, dict)

    def test_has_cloud_architecture(self):
        assert "cloud-architecture" in TEAMS

    def test_all_agent_teams_in_teams_dict(self):
        for agent in AGENTS:
            assert (
                agent.team in TEAMS
            ), f"Agent '{agent.name}' has team '{agent.team}' not in TEAMS"


# ── get_agent ────────────────────────────────────────────────────


class TestGetAgent:
    def test_found(self):
        agent = get_agent("cloud-run-specialist")
        assert agent is not None
        assert agent.name == "cloud-run-specialist"

    def test_not_found(self):
        assert get_agent("nonexistent") is None

    def test_empty_string(self):
        assert get_agent("") is None

    def test_partial_match_not_found(self):
        assert get_agent("cloud-run") is None


# ── get_agents_by_team ───────────────────────────────────────────


class TestGetAgentsByTeam:
    def test_cloud_architecture(self):
        agents = get_agents_by_team("cloud-architecture")
        assert isinstance(agents, tuple)
        assert len(agents) >= 1
        assert all(a.team == "cloud-architecture" for a in agents)

    def test_empty_team(self):
        agents = get_agents_by_team("security")
        assert isinstance(agents, tuple)
        assert len(agents) == 0

    def test_nonexistent_team(self):
        agents = get_agents_by_team("nonexistent")
        assert isinstance(agents, tuple)
        assert len(agents) == 0


# ── get_all_teams ────────────────────────────────────────────────


class TestGetAllTeams:
    def test_returns_tuple(self):
        teams = get_all_teams()
        assert isinstance(teams, tuple)

    def test_includes_cloud_architecture(self):
        teams = get_all_teams()
        assert "cloud-architecture" in teams

    def test_no_duplicates(self):
        teams = get_all_teams()
        assert len(teams) == len(set(teams))

    def test_only_teams_with_agents(self):
        teams = get_all_teams()
        for team in teams:
            agents = get_agents_by_team(team)
            assert len(agents) > 0, f"Team '{team}' has no agents"


def test_agent_entry_has_plugin_fields():
    """AgentEntry includes plugin_name and marketplace fields."""
    from tonone.registry import AGENTS

    agent = AGENTS[0]
    assert hasattr(agent, "plugin_name")
    assert hasattr(agent, "marketplace")
    assert agent.plugin_name == "cloud-run-specialist"
    assert agent.marketplace == "tonone-ai/tonone"
