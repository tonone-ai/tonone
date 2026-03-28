"""Engineering Team CLI - discover, install, and run agents."""

import argparse
import subprocess
import sys

from engteam import __version__
from engteam.registry import (
    AGENTS,
    TEAMS,
    get_agent,
    get_agents_by_team,
    get_all_teams,
)


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, **kwargs)


def _header() -> str:
    return "Engineering Team - your engineering team on call\n"


# ── list ─────────────────────────────────────────────────────────


def cmd_list(args: argparse.Namespace) -> None:
    print(_header())

    teams = [args.team] if args.team else list(get_all_teams())

    for team in teams:
        label = TEAMS.get(team, team.replace("-", " ").title())
        print(f"  {label.upper()}")

        agents = get_agents_by_team(team)
        if not agents:
            print("    (no agents yet)\n")
            continue

        for a in agents:
            status = "" if a.status == "available" else "  (coming soon)"
            print(f"    {a.name:<28} {a.description}{status}")

            if args.verbose:
                print(f"      package: {a.pypi_package}")
                print(
                    f"      plugin:  /plugin install {a.plugin_name}@{a.marketplace.split('/')[0]}"
                )
                for skill in a.skills:
                    print(f"      skill:   {skill}")
        print()


# ── install ──────────────────────────────────────────────────────


def cmd_install(args: argparse.Namespace) -> None:
    target = args.target

    # Install a whole team?
    if target in TEAMS:
        agents = get_agents_by_team(target)
        available = [a for a in agents if a.status == "available"]
        if not available:
            print(f"No available agents in team '{target}' yet.")
            return
        print(f"Installing {len(available)} agent(s) from {TEAMS[target]}...\n")
        for a in available:
            _install_agent(a.pypi_package)
        return

    # Install --all?
    if target == "--all":
        available = [a for a in AGENTS if a.status == "available"]
        print(f"Installing all {len(available)} available agent(s)...\n")
        for a in available:
            _install_agent(a.pypi_package)
        return

    # Install a specific agent
    agent = get_agent(target)
    if not agent:
        print(f"Unknown agent: '{target}'")
        print("Run 'engteam list' to see available agents.")
        sys.exit(1)

    if agent.status != "available":
        print(f"'{agent.name}' is coming soon - not available yet.")
        sys.exit(1)

    _install_agent(agent.pypi_package)


def _install_agent(package: str) -> None:
    """Install an agent package and run its install command."""
    print(f"  Installing {package}...")

    # Try uvx first, fall back to pip
    result = _run(
        ["uvx", package, "install"],
        capture_output=True,
    )

    if result.returncode != 0:
        # Try pip install + direct command
        _run(["pip", "install", "-q", package], capture_output=True)
        result = _run([package, "install"], capture_output=True)

    if result.returncode == 0:
        # Print the output but indent it
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                print(f"  {line}")
        print()
    else:
        print(f"  Failed to install {package}")
        if result.stderr:
            print(f"  {result.stderr.strip()}")
        print()


# ── run ──────────────────────────────────────────────────────────


def cmd_run(args: argparse.Namespace) -> None:
    agent = get_agent(args.agent)
    if not agent:
        print(f"Unknown agent: '{args.agent}'")
        sys.exit(1)

    # Pass remaining args to the agent
    cmd = [agent.pypi_package, *args.agent_args]

    # Try direct command first
    result = _run(cmd)
    if result.returncode != 0:
        # Try uvx
        _run(["uvx", *cmd])


# ── update ───────────────────────────────────────────────────────


def cmd_update(args: argparse.Namespace) -> None:
    available = [a for a in AGENTS if a.status == "available"]
    print(f"Updating {len(available)} agent(s)...\n")
    for a in available:
        print(f"  Updating {a.pypi_package}...")
        _run(
            ["pip", "install", "-q", "--upgrade", a.pypi_package],
            capture_output=True,
        )
        # Re-run install to update agent defs and skills
        _run([a.pypi_package, "install"], capture_output=True)
    print("\nDone.")


# ── main ─────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="engteam",
        description="Engineering Team - your engineering team on call",
    )
    parser.add_argument("--version", action="version", version=f"engteam {__version__}")
    sub = parser.add_subparsers(dest="command")

    # list
    ls = sub.add_parser("list", help="Browse available agents")
    ls.add_argument("--team", help="Filter by team")
    ls.add_argument(
        "-v", "--verbose", action="store_true", help="Show packages and skills"
    )

    # install
    inst = sub.add_parser("install", help="Install an agent or team")
    inst.add_argument("target", help="Agent name, team name, or --all")

    # run
    run = sub.add_parser("run", help="Run an agent directly")
    run.add_argument("agent", help="Agent name")
    run.add_argument("agent_args", nargs="*", help="Arguments to pass to the agent")

    # update
    sub.add_parser("update", help="Update all installed agents")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list(args)
    elif args.command == "install":
        cmd_install(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "update":
        cmd_update(args)
    else:
        print(_header())
        print("Install (plugin - recommended):")
        print("  /plugin marketplace add tonone-ai/tonone")
        print("  /plugin install cloud-run-specialist@tonone-ai")
        print()
        print("Install (pip):")
        print("  engteam list                    Browse available agents")
        print("  engteam install <agent|team>    Install an agent or team")
        print("  engteam run <agent> [args]      Run an agent directly")
        print("  engteam update                  Update all installed agents")
        print()
        print("Get started:")
        print("  engteam list")
