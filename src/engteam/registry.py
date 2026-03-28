"""Agent registry - the catalog of all Engineering Team agents."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentEntry:
    name: str
    team: str
    pypi_package: str
    plugin_name: str
    marketplace: str
    description: str
    skills: tuple[str, ...]
    status: str = "available"  # available, coming-soon


AGENTS: tuple[AgentEntry, ...] = (
    AgentEntry(
        name="cloud-run-specialist",
        team="cloud-architecture",
        pypi_package="cloudrun-agent",
        plugin_name="cloud-run-specialist",
        marketplace="tonone-ai/tonone",
        description="Audit Cloud Run fleet: resource waste, performance, pricing, traffic, security",
        skills=(
            "/cloudrun-dashboard",
            "/cloudrun-check",
            "/cloudrun-inspect",
            "/cloudrun-history",
        ),
    ),
    # Future agents - add entries here as they're built
    # AgentEntry(
    #     name="gke-specialist",
    #     team="cloud-architecture",
    #     pypi_package="gke-agent",
    #     description="Audit GKE clusters: node pools, workload sizing, networking, security",
    #     skills=("/gke-dashboard", "/gke-check"),
    #     status="coming-soon",
    # ),
)

TEAMS: dict[str, str] = {
    "cloud-architecture": "Cloud Architecture",
    "security": "Security",
    "devops": "DevOps",
    "data": "Data Engineering",
}


def get_agent(name: str) -> AgentEntry | None:
    """Look up an agent by name."""
    for agent in AGENTS:
        if agent.name == name:
            return agent
    return None


def get_agents_by_team(team: str) -> tuple[AgentEntry, ...]:
    """Get all agents in a team."""
    return tuple(a for a in AGENTS if a.team == team)


def get_all_teams() -> tuple[str, ...]:
    """Get all team names that have at least one agent."""
    return tuple(dict.fromkeys(a.team for a in AGENTS))
