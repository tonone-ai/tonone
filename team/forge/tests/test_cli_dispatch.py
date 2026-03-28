"""Tests for CLI argument parsing and dispatch."""

import json
from unittest.mock import patch

import pytest
from cloudrun_agent import __version__
from cloudrun_agent.cli import main as cli_main
from cloudrun_agent.tools.gcloud import GcloudError, _remediation_hint

# ── cli.py argument parsing ──────────────────────────────────────


class TestCliArgParsing:
    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--version"])
        assert exc_info.value.code == 0
        output = capsys.readouterr().out
        assert __version__ in output

    def test_service_without_region_exits(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--service", "my-api"])
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "--region is required" in err

    @patch("cloudrun_agent.cli.list_snapshots", return_value=[])
    def test_history_no_snapshots(self, mock_list, capsys):
        cli_main(["--history"])
        err = capsys.readouterr().err
        assert "No snapshots yet" in err

    @patch("cloudrun_agent.cli.list_snapshots")
    def test_history_with_snapshots(self, mock_list, capsys):
        mock_list.return_value = [{"file": "snap-1.json", "date": "2026-03-16"}]
        cli_main(["--history"])
        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert len(parsed) == 1

    @patch("cloudrun_agent.cli.discover_services")
    def test_list_services(self, mock_discover, capsys):
        mock_discover.return_value = [{"name": "svc-a", "region": "us-central1"}]
        cli_main(["--list"])
        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert parsed[0]["name"] == "svc-a"

    @patch("cloudrun_agent.cli.discover_services")
    def test_list_with_project_and_region(self, mock_discover, capsys):
        mock_discover.return_value = []
        cli_main(["--list", "--project", "my-proj", "--region", "us-east1"])
        mock_discover.assert_called_once_with(project="my-proj", region="us-east1")


# ── Error handling ───────────────────────────────────────────────


class TestCliErrorHandling:
    @patch("cloudrun_agent.cli.discover_services")
    def test_gcloud_error_shows_message(self, mock_discover, capsys):
        mock_discover.side_effect = GcloudError(
            "gcloud run services list", "not authenticated", 1
        )
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--list"])
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "not authenticated" in err

    @patch("cloudrun_agent.cli.discover_services")
    def test_gcloud_error_verbose_traceback(self, mock_discover, capsys):
        mock_discover.side_effect = GcloudError("cmd", "fail", 1)
        with pytest.raises(SystemExit):
            cli_main(["--list", "--verbose"])
        err = capsys.readouterr().err
        assert "Traceback" in err

    @patch("cloudrun_agent.cli.discover_services")
    def test_file_not_found_suggests_install(self, mock_discover, capsys):
        mock_discover.side_effect = FileNotFoundError("gcloud")
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--list"])
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "gcloud installed" in err

    @patch("cloudrun_agent.cli.discover_services")
    def test_generic_error_suggests_verbose(self, mock_discover, capsys):
        mock_discover.side_effect = RuntimeError("something broke")
        with pytest.raises(SystemExit):
            cli_main(["--list"])
        err = capsys.readouterr().err
        assert "--verbose" in err

    @patch("cloudrun_agent.cli.discover_services")
    def test_keyboard_interrupt(self, mock_discover, capsys):
        mock_discover.side_effect = KeyboardInterrupt()
        with pytest.raises(SystemExit) as exc_info:
            cli_main(["--list"])
        assert exc_info.value.code == 130


# ── _remediation_hint ────────────────────────────────────────────


class TestRemediationHint:
    def test_not_authenticated(self):
        hint = _remediation_hint("ERROR: not authenticated")
        assert hint is not None
        assert "gcloud auth login" in hint

    def test_no_project(self):
        hint = _remediation_hint("ERROR: project is not set")
        assert hint is not None
        assert "gcloud config set project" in hint

    def test_permission_denied(self):
        hint = _remediation_hint("ERROR: PERMISSION_DENIED: forbidden")
        assert hint is not None
        assert "IAM roles" in hint

    def test_gcloud_not_found(self):
        hint = _remediation_hint("gcloud: command not found")
        assert hint is not None
        assert "cloud.google.com" in hint

    def test_quota_exceeded(self):
        hint = _remediation_hint("RESOURCE_EXHAUSTED: quota exceeded")
        assert hint is not None
        assert "rate limit" in hint.lower() or "quota" in hint.lower()

    def test_unknown_error_returns_none(self):
        assert _remediation_hint("some random error") is None

    def test_empty_string(self):
        assert _remediation_hint("") is None

    def test_service_not_found(self):
        hint = _remediation_hint("could not find service my-api")
        assert hint is not None
        assert "gcloud run services list" in hint


# ── GcloudError with hints ───────────────────────────────────────


class TestGcloudErrorWithHint:
    def test_includes_hint_in_message(self):
        err = GcloudError("cmd", "not authenticated", 1)
        assert "Fix:" in str(err)
        assert "gcloud auth login" in str(err)

    def test_no_hint_for_unknown_error(self):
        err = GcloudError("cmd", "something weird", 1)
        assert "Fix:" not in str(err)

    def test_preserves_command_and_stderr(self):
        err = GcloudError("gcloud run list", "fail", 2)
        assert err.command == "gcloud run list"
        assert err.stderr == "fail"
        assert err.returncode == 2
