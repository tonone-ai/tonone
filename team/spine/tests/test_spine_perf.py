"""Tests for spine-perf: N+1 detector + endpoint profiler + perf_scan CLI."""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, ROOT)

from team.shared.report_schema import AgentReport, Finding, ReportMetadata
from team.spine.scripts.spine_agent.endpoint_profiler import (
    THRESHOLD_CRITICAL,
    THRESHOLD_HIGH,
    THRESHOLD_MEDIUM,
    _percentile,
    _severity_for_p50,
    profile_endpoints,
)
from team.spine.scripts.spine_agent.n_plus_one_detector import scan_directory, scan_file

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
FIXTURE_FILE = os.path.join(FIXTURE_DIR, "n_plus_one_sample.py")
PERF_SCAN = os.path.join(ROOT, "team/spine/scripts/spine_agent/perf_scan.py")


# ---------------------------------------------------------------------------
# Severity mapping helpers
# ---------------------------------------------------------------------------


class TestSeverityMapping:
    def test_below_threshold_returns_none(self):
        assert _severity_for_p50(0.100) is None

    def test_medium_threshold(self):
        assert _severity_for_p50(THRESHOLD_MEDIUM) == "MEDIUM"

    def test_high_threshold(self):
        assert _severity_for_p50(THRESHOLD_HIGH) == "HIGH"

    def test_critical_threshold(self):
        assert _severity_for_p50(THRESHOLD_CRITICAL) == "CRITICAL"

    def test_just_below_medium(self):
        assert _severity_for_p50(THRESHOLD_MEDIUM - 0.001) is None

    def test_just_above_medium(self):
        assert _severity_for_p50(THRESHOLD_MEDIUM + 0.001) == "MEDIUM"


# ---------------------------------------------------------------------------
# Percentile helper
# ---------------------------------------------------------------------------


class TestPercentile:
    def test_empty_list(self):
        assert _percentile([], 50) == 0.0

    def test_single_element(self):
        assert _percentile([1.0], 50) == 1.0

    def test_p50_of_sorted(self):
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert _percentile(data, 50) == pytest.approx(3.0, abs=0.01)

    def test_p99_of_single(self):
        assert _percentile([0.5], 99) == 0.5


# ---------------------------------------------------------------------------
# N+1 detector — fixture file
# ---------------------------------------------------------------------------


class TestN1DetectorFixture:
    def test_fixture_file_exists(self):
        assert os.path.isfile(FIXTURE_FILE), f"Fixture not found: {FIXTURE_FILE}"

    def test_detects_findings_in_fixture(self):
        findings = scan_file(FIXTURE_FILE)
        assert len(findings) >= 1, "Expected >=1 N+1 finding in fixture file"

    def test_detects_orm_query_in_loop(self):
        findings = scan_file(FIXTURE_FILE)
        ids = [f.id for f in findings]
        assert (
            "SPINE-N1-ORM" in ids
        ), "Expected SPINE-N1-ORM finding (ORM call inside loop)"

    def test_detects_raw_sql_in_loop(self):
        findings = scan_file(FIXTURE_FILE)
        ids = [f.id for f in findings]
        assert (
            "SPINE-N1-SQL" in ids
        ), "Expected SPINE-N1-SQL finding (cursor.execute in loop)"

    def test_detects_formatted_sql_in_loop(self):
        findings = scan_file(FIXTURE_FILE)
        ids = [f.id for f in findings]
        assert (
            "SPINE-N1-FMTSQL" in ids
        ), "Expected SPINE-N1-FMTSQL finding (string-formatted SQL in loop)"

    def test_findings_have_required_fields(self):
        findings = scan_file(FIXTURE_FILE)
        for f in findings:
            assert f.severity in {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
            assert f.location
            assert f.title
            assert f.recommendation
            assert f.effort in {"S", "M", "L"}

    def test_findings_have_location_with_line(self):
        findings = scan_file(FIXTURE_FILE)
        for f in findings:
            assert (
                ":" in f.location
            ), f"location should include line number, got: {f.location}"

    def test_scan_directory_includes_fixture(self):
        findings = scan_directory(FIXTURE_DIR)
        assert len(findings) >= 1


class TestN1DetectorEdgeCases:
    def test_empty_file(self, tmp_path):
        empty = tmp_path / "empty.py"
        empty.write_text("")
        findings = scan_file(str(empty))
        assert findings == []

    def test_syntax_error_file(self, tmp_path):
        bad = tmp_path / "bad.py"
        bad.write_text("def foo(: bad syntax")
        findings = scan_file(str(bad))
        assert findings == []

    def test_nonexistent_file(self):
        findings = scan_file("/nonexistent/path/no_file.py")
        assert findings == []

    def test_clean_file_no_findings(self, tmp_path):
        clean = tmp_path / "clean.py"
        clean.write_text(
            "def good():\n"
            "    items = get_queryset().select_related('author').all()\n"
            "    return list(items)\n"
        )
        findings = scan_file(str(clean))
        # Should have no HIGH ORM-in-loop findings (select_related call, not in a loop)
        high_findings = [f for f in findings if f.severity == "HIGH"]
        assert len(high_findings) == 0

    def test_skips_venv_directory(self, tmp_path):
        venv_dir = tmp_path / ".venv" / "lib"
        venv_dir.mkdir(parents=True)
        bad = venv_dir / "bad.py"
        bad.write_text("for x in items:\n" "    obj = Model.objects.get(id=x)\n")
        findings = scan_directory(str(tmp_path))
        assert findings == []


# ---------------------------------------------------------------------------
# Endpoint profiler — error paths
# ---------------------------------------------------------------------------


class TestEndpointProfilerErrors:
    def test_httpx_not_installed(self, monkeypatch):
        """If httpx is not importable, return [] and print install message."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "httpx":
                raise ImportError("No module named 'httpx'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        findings = profile_endpoints("http://localhost:9999", ["/api/test"])
        assert findings == []

    def test_connection_refused(self):
        """Connection refused on a port nothing is listening on returns []."""
        # Port 19999 is almost certainly not in use
        findings = profile_endpoints("http://127.0.0.1:19999", ["/ping"], timeout=2.0)
        assert findings == []

    def test_empty_paths(self):
        """No paths to test returns empty list without error."""
        findings = profile_endpoints("http://localhost:8000", [], timeout=1.0)
        assert findings == []

    def test_timeout_per_request(self, monkeypatch):
        """Timeout per request is handled gracefully — returns a finding (slow)."""
        import httpx

        class FakeTimeoutClient:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def get(self, url, **kwargs):
                raise httpx.TimeoutException("timed out", request=None)

        monkeypatch.setattr(httpx, "Client", FakeTimeoutClient)
        findings = profile_endpoints(
            "http://localhost:8000",
            ["/slow"],
            timeout=5.0,
            warmup=1,
            measured=3,
        )
        # all requests timed out at 5s — p50 = 5.0 >= THRESHOLD_CRITICAL
        assert len(findings) == 1
        assert findings[0].severity == "CRITICAL"


# ---------------------------------------------------------------------------
# perf_scan CLI
# ---------------------------------------------------------------------------


class TestPerfScanCLI:
    def test_nonexistent_target_exits_1(self):
        result = subprocess.run(
            [sys.executable, PERF_SCAN, "/nonexistent/path/that/does/not/exist"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "does not exist" in result.stderr

    def test_valid_target_exits_0_or_2(self, tmp_path):
        """A scan on a clean temp dir should exit 0 (no HIGH/CRITICAL)."""
        result = subprocess.run(
            [sys.executable, PERF_SCAN, str(tmp_path), "--skip-endpoints"],
            capture_output=True,
            text=True,
        )
        assert result.returncode in (0, 2)

    def test_writes_report_json(self, tmp_path):
        out = str(tmp_path / "report.json")
        result = subprocess.run(
            [
                sys.executable,
                PERF_SCAN,
                str(tmp_path),
                "--skip-endpoints",
                "--out",
                out,
            ],
            capture_output=True,
            text=True,
        )
        assert os.path.isfile(out), "Report file should be written"
        with open(out) as fh:
            data = json.load(fh)
        assert data["agent"] == "spine"
        assert data["skill"] == "spine-perf"

    def test_fixture_scan_exits_nonzero(self):
        """Fixture directory has HIGH findings so exit should be 2."""
        result = subprocess.run(
            [sys.executable, PERF_SCAN, FIXTURE_DIR, "--skip-endpoints"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 2, (
            f"Expected exit 2 (HIGH findings) but got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )


# ---------------------------------------------------------------------------
# Report schema round-trip (spine context)
# ---------------------------------------------------------------------------


class TestReportSchema:
    def test_finding_valid_spine(self):
        f = Finding(
            id="SPINE-N1-ORM",
            severity="HIGH",
            title="N+1 ORM query inside loop",
            detail="ORM .filter() in loop",
            location="app/views.py:42",
            recommendation="Use select_related()",
            effort="S",
        )
        assert f.severity == "HIGH"

    def test_report_summary_counts(self):
        report = AgentReport(agent="spine", skill="spine-perf", target=".")
        report.findings = [
            Finding(
                severity="CRITICAL",
                title="a",
                detail="a",
                location="a",
                recommendation="a",
                effort="S",
            ),
            Finding(
                severity="HIGH",
                title="b",
                detail="b",
                location="b",
                recommendation="b",
                effort="S",
            ),
            Finding(
                severity="MEDIUM",
                title="c",
                detail="c",
                location="c",
                recommendation="c",
                effort="M",
            ),
        ]
        s = report.summary
        assert s.critical == 1
        assert s.high == 1
        assert s.medium == 1
        assert s.total == 3

    def test_report_json_roundtrip(self):
        report = AgentReport(
            agent="spine",
            skill="spine-perf",
            target="/some/path",
            metadata=ReportMetadata(tool_version="spine-perf 0.9.8", duration_s=1.5),
        )
        report.findings = [
            Finding(
                id="SPINE-N1-SQL",
                severity="HIGH",
                title="Raw SQL in loop",
                detail="cursor.execute in for-loop",
                location="app.py:100",
                recommendation="Batch query",
                effort="S",
            )
        ]
        restored = AgentReport.from_dict(json.loads(report.to_json()))
        assert restored.agent == "spine"
        assert len(restored.findings) == 1
        assert restored.findings[0].id == "SPINE-N1-SQL"
