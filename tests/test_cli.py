"""Tests for the engteam CLI."""

import argparse
from unittest.mock import MagicMock, patch

from engteam import __version__
from engteam.cli import _header, cmd_install, cmd_list, cmd_run

# ── _header ──────────────────────────────────────────────────────


class TestHeader:
    def test_returns_string(self):
        assert isinstance(_header(), str)

    def test_contains_name(self):
        assert "Engineering Team" in _header()


# ── cmd_list ─────────────────────────────────────────────────────


class TestCmdList:
    def test_list_all(self, capsys):
        args = argparse.Namespace(team=None, verbose=False)
        cmd_list(args)
        output = capsys.readouterr().out
        assert "CLOUD ARCHITECTURE" in output
        assert "cloud-run-specialist" in output

    def test_list_with_team_filter(self, capsys):
        args = argparse.Namespace(team="cloud-architecture", verbose=False)
        cmd_list(args)
        output = capsys.readouterr().out
        assert "CLOUD ARCHITECTURE" in output
        assert "cloud-run-specialist" in output

    def test_list_empty_team(self, capsys):
        args = argparse.Namespace(team="security", verbose=False)
        cmd_list(args)
        output = capsys.readouterr().out
        assert "no agents yet" in output

    def test_list_verbose(self, capsys):
        args = argparse.Namespace(team=None, verbose=True)
        cmd_list(args)
        output = capsys.readouterr().out
        assert "package:" in output
        assert "cloudrun-agent" in output
        assert "skill:" in output

    def test_list_nonexistent_team(self, capsys):
        args = argparse.Namespace(team="nonexistent", verbose=False)
        cmd_list(args)
        output = capsys.readouterr().out
        assert "no agents yet" in output


# ── cmd_install ──────────────────────────────────────────────────


class TestCmdInstall:
    def test_unknown_agent_exits(self):
        args = argparse.Namespace(target="nonexistent-agent")
        try:
            cmd_install(args)
            assert False, "Should have called sys.exit"
        except SystemExit as e:
            assert e.code == 1

    def test_coming_soon_agent_exits(self):
        """Coming-soon agents should not be installable."""
        from engteam.registry import AGENTS

        coming_soon = [a for a in AGENTS if a.status == "coming-soon"]
        if not coming_soon:
            return  # No coming-soon agents to test
        args = argparse.Namespace(target=coming_soon[0].name)
        try:
            cmd_install(args)
            assert False, "Should have called sys.exit"
        except SystemExit as e:
            assert e.code == 1

    @patch("engteam.cli._run")
    def test_install_specific_agent(self, mock_run, capsys):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Installed OK\n", stderr=""
        )
        args = argparse.Namespace(target="cloud-run-specialist")
        cmd_install(args)
        output = capsys.readouterr().out
        assert "Installing" in output

    @patch("engteam.cli._run")
    def test_install_team(self, mock_run, capsys):
        mock_run.return_value = MagicMock(returncode=0, stdout="OK\n", stderr="")
        args = argparse.Namespace(target="cloud-architecture")
        cmd_install(args)
        output = capsys.readouterr().out
        assert "Installing" in output
        assert "agent(s)" in output

    @patch("engteam.cli._run")
    def test_install_all(self, mock_run, capsys):
        mock_run.return_value = MagicMock(returncode=0, stdout="OK\n", stderr="")
        args = argparse.Namespace(target="--all")
        cmd_install(args)
        output = capsys.readouterr().out
        assert "Installing all" in output

    def test_install_empty_team(self, capsys):
        args = argparse.Namespace(target="security")
        cmd_install(args)
        output = capsys.readouterr().out
        assert "No available agents" in output

    @patch("engteam.cli._run")
    def test_install_fallback_to_pip(self, mock_run, capsys):
        """When uvx fails, should try pip."""
        fail = MagicMock(returncode=1, stdout="", stderr="not found")
        success = MagicMock(returncode=0, stdout="Installed\n", stderr="")
        mock_run.side_effect = [
            fail,
            success,
            success,
        ]  # uvx fails, pip install, pip run
        args = argparse.Namespace(target="cloud-run-specialist")
        cmd_install(args)
        assert mock_run.call_count >= 2


# ── cmd_run ──────────────────────────────────────────────────────


class TestCmdRun:
    def test_unknown_agent_exits(self):
        args = argparse.Namespace(agent="nonexistent", agent_args=[])
        try:
            cmd_run(args)
            assert False, "Should have called sys.exit"
        except SystemExit as e:
            assert e.code == 1

    @patch("engteam.cli._run")
    def test_run_known_agent(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        args = argparse.Namespace(agent="cloud-run-specialist", agent_args=["--html"])
        cmd_run(args)
        cmd = mock_run.call_args[0][0]
        assert "cloudrun-agent" in cmd
        assert "--html" in cmd


# ── version ──────────────────────────────────────────────────────


class TestVersion:
    def test_version_string(self):
        assert isinstance(__version__, str)
        assert "." in __version__
