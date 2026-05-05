"""Tests for forge-cost: infracost_analyzer + cloud_cost_fetcher + report_schema."""

import json
import os
import sys
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, ROOT)

from team.shared.report_schema import AgentReport, Finding, ReportMetadata
from team.forge.scripts.forge_agent.infracost_analyzer import run_infracost, check_infracost, check_infracost_api_key, _severity_for_cost
from team.forge.scripts.forge_agent.cloud_cost_fetcher import run_cloud_cost_fetch, _severity_for_spend

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures/terraform_sample")


class TestSeverityMapping:
    def test_infracost_critical(self):
        assert _severity_for_cost(1500.0) == "CRITICAL"

    def test_infracost_high(self):
        assert _severity_for_cost(200.0) == "HIGH"

    def test_infracost_medium(self):
        assert _severity_for_cost(25.0) == "MEDIUM"

    def test_infracost_low(self):
        assert _severity_for_cost(5.0) == "LOW"

    def test_infracost_info(self):
        assert _severity_for_cost(0.0) == "INFO"

    def test_spend_critical(self):
        assert _severity_for_spend(6000.0) == "CRITICAL"

    def test_spend_high(self):
        assert _severity_for_spend(1500.0) == "HIGH"

    def test_spend_medium(self):
        assert _severity_for_spend(300.0) == "MEDIUM"


_infracost_ready = pytest.mark.skipif(
    not check_infracost()[0] or not check_infracost_api_key(),
    reason="infracost not installed or API key not configured (https://dashboard.infracost.io)",
)


class TestInfracostAnalyzer:
    def test_infracost_available(self):
        available, version = check_infracost()
        assert available, "infracost must be installed (https://www.infracost.io/docs/)"

    @_infracost_ready
    def test_fixture_has_findings(self):
        findings = run_infracost(FIXTURE_DIR)
        assert len(findings) >= 1, (
            f"Expected ≥1 cost finding in fixtures/terraform_sample/, got 0. "
            f"Check that main.tf contains detectable resources."
        )

    @_infracost_ready
    def test_findings_have_required_fields(self):
        findings = run_infracost(FIXTURE_DIR)
        for f in findings:
            assert f.severity in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
            assert f.title
            assert f.recommendation
            assert "$" in f.detail

    @_infracost_ready
    def test_empty_dir_returns_empty(self, tmp_path):
        findings = run_infracost(str(tmp_path))
        assert isinstance(findings, list)


class TestInfracostErrorPaths:
    def test_not_installed(self, monkeypatch):
        import subprocess
        def mock_run(*args, **kwargs):
            raise FileNotFoundError("infracost not found")
        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = run_infracost("/tmp")
        assert findings == []

    def test_timeout(self, monkeypatch):
        import subprocess
        call_count = {"n": 0}
        def mock_run(cmd, *args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                class R:
                    returncode = 0
                    stdout = "infracost v0.10.0"
                return R()
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=180)
        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = run_infracost("/tmp")
        assert findings == []

    def test_invalid_json(self, monkeypatch):
        import subprocess
        call_count = {"n": 0}
        def mock_run(cmd, *args, **kwargs):
            call_count["n"] += 1
            class R:
                returncode = 0
                stdout = "infracost v0.10.0" if call_count["n"] == 1 else "not-json{"
                stderr = ""
            return R()
        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = run_infracost("/tmp")
        assert findings == []

    def test_nonzero_exit_no_terraform(self, monkeypatch):
        import subprocess
        call_count = {"n": 0}
        def mock_run(cmd, *args, **kwargs):
            call_count["n"] += 1
            class R:
                returncode = 0 if call_count["n"] == 1 else 1
                stdout = "infracost v0.10.0" if call_count["n"] == 1 else ""
                stderr = "No Terraform files found"
            return R()
        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = run_infracost("/tmp")
        assert findings == []


class TestCloudCostFetcher:
    def test_returns_list(self):
        # may return [] if no cloud CLIs configured — that's fine
        findings = run_cloud_cost_fetch(os.getcwd())
        assert isinstance(findings, list)

    def test_finding_structure(self):
        findings = run_cloud_cost_fetch(os.getcwd())
        for f in findings:
            assert f.severity in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
            assert f.title
            assert f.location

    def test_aws_not_installed(self, monkeypatch):
        import subprocess
        def mock_run(cmd, *args, **kwargs):
            raise FileNotFoundError("aws not found")
        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = run_cloud_cost_fetch("/tmp")
        assert findings == []

    def test_aws_no_credentials(self, monkeypatch):
        import subprocess
        call_count = {"n": 0}
        def mock_run(cmd, *args, **kwargs):
            call_count["n"] += 1
            class R:
                returncode = 0 if "version" in cmd else 254
                stdout = "aws-cli/2.0" if "version" in cmd else ""
                stderr = "" if "version" in cmd else "Unable to locate credentials"
            return R()
        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = run_cloud_cost_fetch("/tmp")
        assert isinstance(findings, list)

    def test_aws_invalid_json(self, monkeypatch):
        import subprocess
        def mock_run(cmd, *args, **kwargs):
            class R:
                returncode = 0
                stdout = "aws-cli/2.0" if "--version" in cmd else "not-json{"
                stderr = ""
            return R()
        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = run_cloud_cost_fetch("/tmp")
        assert isinstance(findings, list)


class TestCostScanCLI:
    def test_nonexistent_target_exits(self):
        import subprocess
        result = subprocess.run(
            [sys.executable,
             os.path.join(ROOT, "team/forge/scripts/forge_agent/cost_scan.py"),
             "/nonexistent/path/does/not/exist"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1
        assert "does not exist" in result.stderr
