"""Install the cloudrun-analyzer agent and skills into Claude Code."""

import shutil
import sys
from pathlib import Path


AGENT_FILENAME = "cloudrun-analyzer.md"

SKILL_FILES = [
    "cloudrun-dashboard.md",
    "cloudrun-check.md",
    "cloudrun-inspect.md",
    "cloudrun-history.md",
]


def _find_source_dir(subdir: str, filename: str) -> Path | None:
    """Locate a bundled file in the package or repo checkout."""
    pkg_dir = Path(__file__).parent

    # Package install
    bundled = pkg_dir / subdir / filename
    if bundled.exists():
        return bundled

    # Repo checkout
    repo_root = pkg_dir.parent.parent
    repo_file = repo_root / ".claude" / subdir.replace("agent_def", "agents") / filename
    if repo_file.exists():
        return repo_file

    # Skills live under .claude/skills/ in repo
    repo_file = repo_root / ".claude" / "skills" / filename
    if repo_file.exists():
        return repo_file

    return None


def _backup_if_exists(target: Path) -> None:
    """Create a .bak backup if the target file already exists."""
    if target.exists():
        backup = target.with_suffix(target.suffix + ".bak")
        shutil.copy2(target, backup)
        print(f"  Backed up existing {target.name} → {backup.name}")


def install_agent() -> None:
    """Copy agent definition and skills to ~/.claude/."""
    # Install agent
    agent_src = _find_source_dir("agent_def", AGENT_FILENAME)
    if not agent_src:
        print(f"Error: could not find {AGENT_FILENAME}", file=sys.stderr)
        sys.exit(1)

    agent_dir = Path.home() / ".claude" / "agents"
    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_target = agent_dir / AGENT_FILENAME

    action = "Updating" if agent_target.exists() else "Installing"
    _backup_if_exists(agent_target)
    shutil.copy2(agent_src, agent_target)
    print(f"{action} agent: {agent_target}")

    # Install skills
    skills_dir = Path.home() / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    for skill_file in SKILL_FILES:
        skill_src = _find_source_dir("skills", skill_file)
        if skill_src:
            skill_target = skills_dir / skill_file
            _backup_if_exists(skill_target)
            shutil.copy2(skill_src, skill_target)
            print(f"  + skill: /cloudrun-{skill_file.replace('cloudrun-', '').replace('.md', '')}")
        else:
            print(f"  Warning: could not find {skill_file} — skill not installed", file=sys.stderr)

    print()
    print("Done! Engineering Team Cloud Run Specialist is ready.")
    print()
    print("  /cloudrun-dashboard  — visual fleet report in browser")
    print("  /cloudrun-check      — quick health check in terminal")
    print("  /cloudrun-inspect    — deep dive into a specific service")
    print("  /cloudrun-history    — compare changes over time")
    print()
    print("Or just ask: 'analyze my cloud run services'")
    print()
    print("Prerequisites:")
    print("  gcloud auth login && gcloud config set project YOUR_PROJECT")


def uninstall_agent() -> None:
    """Remove agent and skills from ~/.claude/."""
    agent_target = Path.home() / ".claude" / "agents" / AGENT_FILENAME
    if agent_target.exists():
        agent_target.unlink()
        print(f"Removed {agent_target}")

    # Also clean up backups
    backup = agent_target.with_suffix(agent_target.suffix + ".bak")
    if backup.exists():
        backup.unlink()

    for skill_file in SKILL_FILES:
        skill_target = Path.home() / ".claude" / "skills" / skill_file
        if skill_target.exists():
            skill_target.unlink()
            print(f"Removed {skill_target}")
        skill_backup = skill_target.with_suffix(skill_target.suffix + ".bak")
        if skill_backup.exists():
            skill_backup.unlink()

    print("Uninstalled.")


def main() -> None:
    """Entry point for cloudrun-agent CLI."""
    import argparse

    from cloudrun_agent import __version__

    parser = argparse.ArgumentParser(
        prog="cloudrun-agent",
        description="Engineering Team — Cloud Run Specialist",
    )
    parser.add_argument("--version", action="version", version=f"cloudrun-agent {__version__}")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("install", help="Install agent + skills to ~/.claude/")
    sub.add_parser("uninstall", help="Remove agent and skills")
    sub.add_parser("analyze", help="Run fleet analysis (pass flags after 'analyze')")

    args, remaining = parser.parse_known_args()

    if args.command == "install":
        install_agent()
    elif args.command == "uninstall":
        uninstall_agent()
    elif args.command == "analyze":
        from cloudrun_agent.cli import main as cli_main
        cli_main(remaining)
    else:
        parser.print_help()
