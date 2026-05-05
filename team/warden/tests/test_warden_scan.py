"""Tests for warden-scan: semgrep_scanner + pip_auditor + report_schema."""

import json
import os
import sys
import pytest

# path to lib/shared and team/warden/scripts
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, ROOT)

from lib.shared.report_schema import AgentReport, Finding, ReportMetadata
from team.warden.scripts.warden_agent.semgrep_scanner import run_semgrep, check_semgrep
from team.warden.scripts.warden_agent.pip_auditor import run_pip_audit

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestReportSchema:
    def test_finding_valid(self):
        f = Finding(
            severity="HIGH",
            title="SQL Injection",
            detail="User input in query",
            location="app.py:42",
            recommendation="Use parameterized queries",
            effort="S",
            id="CWE-89",
        )
        assert f.severity == "HIGH"

    def test_finding_invalid_severity(self):
        with pytest.raises(ValueError):
            Finding(severity="UNKNOWN", title="x", detail="x", location="x", recommendation="x", effort="S")

    def test_report_summary(self):
        report = AgentReport(agent="warden", skill="warden-scan", target=".")
        report.findings = [
            Finding(severity="CRITICAL", title="a", detail="a", location="a", recommendation="a", effort="S"),
            Finding(severity="HIGH", title="b", detail="b", location="b", recommendation="b", effort="S"),
            Finding(severity="HIGH", title="c", detail="c", location="c", recommendation="c", effort="S"),
        ]
        s = report.summary
        assert s.critical == 1
        assert s.high == 2
        assert s.total == 3

    def test_report_to_json_roundtrip(self):
        report = AgentReport(
            agent="warden",
            skill="warden-scan",
            target="/some/path",
            metadata=ReportMetadata(tool_version="semgrep 1.0", duration_s=5.2),
        )
        report.findings = [
            Finding(severity="LOW", title="t", detail="d", location="f.py:1", recommendation="r", effort="S", id="CVE-1"),
        ]
        restored = AgentReport.from_dict(json.loads(report.to_json()))
        assert restored.agent == "warden"
        assert len(restored.findings) == 1
        assert restored.findings[0].id == "CVE-1"


class TestSemgrepScanner:
    def test_semgrep_available(self):
        available, version = check_semgrep()
        assert available, "semgrep must be installed for these tests (pip install semgrep)"

    def test_fixture_has_findings(self):
        """Semgrep must find ≥1 issue in vulnerable_sample.py."""
        available, _ = check_semgrep()
        if not available:
            pytest.skip("semgrep not installed")
        findings = run_semgrep(FIXTURE_DIR)
        assert len(findings) >= 1, (
            f"Expected ≥1 Semgrep finding in fixtures/, got 0. "
            f"Check that vulnerable_sample.py contains detectable patterns."
        )

    def test_findings_have_required_fields(self):
        available, _ = check_semgrep()
        if not available:
            pytest.skip("semgrep not installed")
        findings = run_semgrep(FIXTURE_DIR)
        for f in findings:
            assert f.severity in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
            assert f.location
            assert f.title
            assert f.recommendation


class TestPipAuditor:
    def test_returns_list(self):
        # audit current env — may find 0 vulns, that's fine
        findings = run_pip_audit(os.getcwd())
        assert isinstance(findings, list)

    def test_finding_structure(self):
        findings = run_pip_audit(os.getcwd())
        for f in findings:
            assert f.severity in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
            assert f.location
            assert "==" in f.location or "→" in f.location


class TestSemgrepScannerErrorPaths:
    def test_check_semgrep_file_not_found(self, monkeypatch):
        import subprocess
        def mock_run(*args, **kwargs):
            raise FileNotFoundError("semgrep not found")
        monkeypatch.setattr(subprocess, "run", mock_run)
        available, version = check_semgrep()
        assert not available
        assert version == ""

    def test_check_semgrep_timeout(self, monkeypatch):
        import subprocess
        def mock_run(*args, **kwargs):
            raise subprocess.TimeoutExpired(cmd=["semgrep", "--version"], timeout=30)
        monkeypatch.setattr(subprocess, "run", mock_run)
        available, version = check_semgrep()
        assert not available
        assert version == ""

    def test_run_semgrep_not_available(self, monkeypatch, tmp_path):
        import subprocess
        def mock_run(*args, **kwargs):
            raise FileNotFoundError("semgrep not found")
        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = run_semgrep(str(tmp_path))
        assert findings == []

    def test_run_semgrep_timeout(self, monkeypatch, tmp_path):
        import subprocess
        call_count = {"n": 0}
        def mock_run(cmd, *args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                # first call is check_semgrep — succeed
                class R:
                    returncode = 0
                    stdout = "semgrep 1.0\n"
                return R()
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=120)
        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = run_semgrep(str(tmp_path))
        assert findings == []

    def test_run_semgrep_invalid_json(self, monkeypatch, tmp_path):
        import subprocess
        call_count = {"n": 0}
        def mock_run(cmd, *args, **kwargs):
            call_count["n"] += 1
            class R:
                returncode = 0
                stdout = "semgrep 1.0\n" if call_count["n"] == 1 else "not-json{"
                stderr = ""
            return R()
        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = run_semgrep(str(tmp_path))
        assert findings == []

    def test_run_semgrep_nonzero_exit(self, monkeypatch, tmp_path):
        import subprocess
        call_count = {"n": 0}
        def mock_run(cmd, *args, **kwargs):
            call_count["n"] += 1
            class R:
                returncode = 0 if call_count["n"] == 1 else 2
                stdout = "semgrep 1.0\n"
                stderr = "fatal error"
            return R()
        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = run_semgrep(str(tmp_path))
        assert findings == []


class TestPipAuditorErrorPaths:
    def test_not_installed(self, monkeypatch):
        import subprocess
        def mock_run(*args, **kwargs):
            raise FileNotFoundError("pip-audit not found")
        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = run_pip_audit(os.getcwd())
        assert findings == []

    def test_empty_stdout(self, monkeypatch, tmp_path):
        import subprocess
        call_count = {"n": 0}
        def mock_run(cmd, *args, **kwargs):
            call_count["n"] += 1
            class R:
                returncode = 0
                stdout = "" if call_count["n"] > 1 else "pip-audit 2.0\n"
                stderr = ""
            return R()
        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = run_pip_audit(os.getcwd())
        assert findings == []

    def test_invalid_json(self, monkeypatch, tmp_path):
        import subprocess
        call_count = {"n": 0}
        def mock_run(cmd, *args, **kwargs):
            call_count["n"] += 1
            class R:
                returncode = 0
                stdout = "pip-audit 2.0\n" if call_count["n"] == 1 else "not-json{"
                stderr = ""
            return R()
        monkeypatch.setattr(subprocess, "run", mock_run)
        findings = run_pip_audit(os.getcwd())
        assert findings == []


class TestReportSchemaCoverage:
    def test_summary_medium_low_info(self):
        report = AgentReport(agent="warden", skill="warden-scan", target=".")
        report.findings = [
            Finding(severity="MEDIUM", title="m", detail="d", location="l", recommendation="r", effort="M"),
            Finding(severity="LOW", title="l", detail="d", location="l", recommendation="r", effort="L"),
            Finding(severity="INFO", title="i", detail="d", location="l", recommendation="r", effort="S"),
        ]
        s = report.summary
        assert s.medium == 1
        assert s.low == 1
        assert s.info == 1
        assert s.total == 3

    def test_from_dict_no_metadata(self):
        report = AgentReport(agent="warden", skill="warden-scan", target=".")
        d = json.loads(report.to_json())
        d["metadata"] = None
        restored = AgentReport.from_dict(d)
        assert restored.metadata is None

    def test_finding_invalid_effort(self):
        with pytest.raises(ValueError):
            Finding(severity="HIGH", title="x", detail="x", location="x", recommendation="x", effort="INVALID")


class TestScanCLI:
    def test_nonexistent_target_exits(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(ROOT, "team/warden/scripts/warden_agent/scan.py"),
             "/nonexistent/path/that/does/not/exist"],
            capture_output=True, text=True
        )
        assert result.returncode == 1
        assert "does not exist" in result.stderr
