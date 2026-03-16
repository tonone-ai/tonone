"""Install agent and skills into Claude Code."""

import shutil
import sys
from pathlib import Path


AGENT_FILENAME = "AGENT_SLUG.md"
SKILL_FILES: list[str] = []  # Add skill filenames here


def install_agent() -> None:
    """Copy agent definition and skills to ~/.claude/."""
    pkg_dir = Path(__file__).parent

    # Install agent
    agent_src = pkg_dir / "agent_def" / AGENT_FILENAME
    if not agent_src.exists():
        print(f"Error: could not find {AGENT_FILENAME}", file=sys.stderr)
        sys.exit(1)

    agent_dir = Path.home() / ".claude" / "agents"
    agent_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(agent_src, agent_dir / AGENT_FILENAME)
    print(f"Installed agent: {agent_dir / AGENT_FILENAME}")

    # Install skills
    skills_dir = Path.home() / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    for skill_file in SKILL_FILES:
        skill_src = pkg_dir / "skills" / skill_file
        if skill_src.exists():
            shutil.copy2(skill_src, skills_dir / skill_file)

    print("Done!")


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(prog="AGENT_PYPI_NAME")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("install", help="Install agent to ~/.claude/")
    sub.add_parser("uninstall", help="Remove agent")

    args = parser.parse_args()
    if args.command == "install":
        install_agent()
    else:
        parser.print_help()
