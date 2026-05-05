"""Tests for apex-scan: health_aggregator + dependency_graph + apex_scan CLI."""

from __future__ import annotations

import ast
import dataclasses
import json
import os
import subprocess
import sys
import tempfile
import textwrap
from unittest.mock import MagicMock, patch

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, ROOT)

from team.shared.report_schema import AgentReport, Finding, ReportMetadata
from team.apex.scripts.apex_agent.health_aggregator import (
    _run_scan,
    _script_path,
    aggregate_health,
)
from team.apex.scripts.apex_agent.dependency_graph import (
    _collect_modules,
    _detect_cycles,
    _parse_imports,
    analyze_dependencies,
)

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def fixture_dir(tmp_path):
    """Return a temp dir containing a small Python package tree."""
    pkg = tmp_path / "team" / "myagent" / "scripts" / "myagent_agent"
    pkg.mkdir(parents=True)
    (pkg.parent.parent.parent / "__init__.py").write_text("")  # team/__init__
    (pkg.parent.parent / "__init__.py").write_text("")
    (pkg.parent / "__init__.py").write_text("")
    (pkg / "__init__.py").write_text("")

    (pkg / "scanner.py").write_text(
        "from team.myagent.scripts.myagent_agent.util import helper\n"
    )
    (pkg / "util.py").write_text("def helper(): pass\n")
    return tmp_path


@pytest.fixture()
def cyclic_fixture(tmp_path):
    """Two modules that import each other."""
    pkg = tmp_path / "team" / "cyclic" / "scripts" / "cyclic_agent"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "a.py").write_text(
        "from team.cyclic.scripts.cyclic_agent.b import something\n"
    )
    (pkg / "b.py").write_text(
        "from team.cyclic.scripts.cyclic_agent.a import other\n"
    )
    return tmp_path


def _make_report(findings: list[Finding] | None = None) -> str:
    report = AgentReport(
        agent="test",
        skill="test-scan",
        target="/tmp",
        findings=findings or [],
        metadata=ReportMetadata(tool_version="test", duration_s=0.1),
    )
    return report.to_json()


# ---------------------------------------------------------------------------
# ReportSchema round-trip
# ---------------------------------------------------------------------------


class TestReportSchema:
    def test_finding_valid(self):
        f = Finding(
            severity="HIGH",
            title="Test",
            detail="detail",
            location="file.py:1",
            recommendation="fix it",
            effort="S",
        )
        assert f.severity == "HIGH"
        assert f.effort == "S"

    def test_finding_invalid_severity(self):
        with pytest.raises(ValueError):
            Finding(severity="BAD", title="x", detail="x", location="x", recommendation="x", effort="S")

    def test_finding_invalid_effort(self):
        with pytest.raises(ValueError):
            Finding(severity="LOW", title="x", detail="x", location="x", recommendation="x", effort="X")

    def test_agent_report_summary(self):
        findings = [
            Finding("CRITICAL", "A", "d", "l", "r", "S"),
            Finding("HIGH", "B", "d", "l", "r", "M"),
            Finding("MEDIUM", "C", "d", "l", "r", "L"),
            Finding("LOW", "D", "d", "l", "r", "S"),
        ]
        report = AgentReport(agent="apex", skill="apex-review", target=".", findings=findings)
        s = report.summary
        assert s.critical == 1
        assert s.high == 1
        assert s.medium == 1
        assert s.low == 1
        assert s.total == 4

    def test_round_trip(self):
        report = AgentReport(
            agent="apex",
            skill="apex-review",
            target="/tmp",
            findings=[Finding("INFO", "T", "d", "l", "r", "S", id="CVE-0000")],
            metadata=ReportMetadata(tool_version="v1", duration_s=1.5),
        )
        data = json.loads(report.to_json())
        assert data["agent"] == "apex"
        assert data["findings"][0]["id"] == "CVE-0000"
        restored = AgentReport.from_dict(data)
        assert restored.findings[0].severity == "INFO"


# ---------------------------------------------------------------------------
# health_aggregator — _run_scan
# ---------------------------------------------------------------------------


class TestRunScan:
    def test_missing_script(self):
        result = _run_scan("fake", "/nonexistent/scan.py", "/tmp", [])
        assert result.error is not None
        assert "not found" in result.error

    def test_success_parses_findings(self, tmp_path):
        script = tmp_path / "scan.py"
        report_json = _make_report([
            Finding("HIGH", "Vuln", "detail", "file.py:1", "fix", "S")
        ])
        # write a script that outputs the report JSON to the --out file
        script.write_text(textwrap.dedent(f"""\
            import sys, json, pathlib
            args = sys.argv[1:]
            out_idx = args.index("--out") + 1
            out_path = args[out_idx]
            pathlib.Path(out_path).write_text({repr(report_json)})
            sys.exit(0)
        """))
        result = _run_scan("test", str(script), "/tmp", [])
        assert result.error is None
        assert len(result.findings) == 1
        assert result.findings[0].severity == "HIGH"

    def test_exit_2_treated_as_findings(self, tmp_path):
        script = tmp_path / "scan.py"
        report_json = _make_report([
            Finding("CRITICAL", "X", "d", "l", "r", "S")
        ])
        script.write_text(textwrap.dedent(f"""\
            import sys, pathlib
            args = sys.argv[1:]
            out_idx = args.index("--out") + 1
            pathlib.Path(args[out_idx]).write_text({repr(report_json)})
            sys.exit(2)
        """))
        result = _run_scan("test", str(script), "/tmp", [])
        assert result.error is None
        assert result.findings[0].severity == "CRITICAL"

    def test_nonzero_non2_exit_is_error(self, tmp_path):
        script = tmp_path / "scan.py"
        script.write_text("import sys; sys.exit(1)\n")
        result = _run_scan("test", str(script), "/tmp", [])
        assert result.error is not None

    def test_no_output_file_is_error(self, tmp_path):
        script = tmp_path / "scan.py"
        script.write_text("import sys; sys.exit(0)\n")
        result = _run_scan("test", str(script), "/tmp", [])
        assert result.error is not None

    def test_timeout_returns_error(self, tmp_path):
        script = tmp_path / "scan.py"
        script.write_text("import time; time.sleep(999)\n")
        with patch(
            "team.apex.scripts.apex_agent.health_aggregator.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="", timeout=1),
        ):
            result = _run_scan("test", str(script), "/tmp", [])
        assert result.error is not None
        assert "timeout" in result.error


# ---------------------------------------------------------------------------
# health_aggregator — aggregate_health
# ---------------------------------------------------------------------------


class TestAggregateHealth:
    def test_all_missing_scripts_returns_empty_findings(self):
        with patch(
            "team.apex.scripts.apex_agent.health_aggregator._script_path",
            return_value="/nonexistent/scan.py",
        ):
            findings, errors = aggregate_health("/tmp")
        assert findings == []
        assert len(errors) == 4

    def test_merges_findings_from_all_agents(self, tmp_path):
        def fake_run_scan(agent, script, target, extra):
            from team.apex.scripts.apex_agent.health_aggregator import SubScanResult
            return SubScanResult(
                agent=agent,
                findings=[Finding("LOW", f"{agent}-finding", "d", "l", "r", "S")],
                error=None,
            )

        with patch(
            "team.apex.scripts.apex_agent.health_aggregator._run_scan",
            side_effect=fake_run_scan,
        ):
            findings, errors = aggregate_health(str(tmp_path))

        assert len(findings) == 4
        assert errors == []
        agents = {f.title.split("-")[0] for f in findings}
        assert "warden" in agents
        assert "forge" in agents


# ---------------------------------------------------------------------------
# dependency_graph
# ---------------------------------------------------------------------------


class TestParseImports:
    def test_basic_import(self, tmp_path):
        f = tmp_path / "mod.py"
        f.write_text("import os\nimport sys\n")
        imports = _parse_imports(str(f))
        assert "os" in imports
        assert "sys" in imports

    def test_from_import(self, tmp_path):
        f = tmp_path / "mod.py"
        f.write_text("from team.shared.report_schema import Finding\n")
        imports = _parse_imports(str(f))
        assert "team.shared.report_schema" in imports

    def test_syntax_error_returns_empty(self, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def broken(\n")
        assert _parse_imports(str(f)) == []


class TestDetectCycles:
    def test_no_cycles(self):
        graph = {"a": {"b"}, "b": {"c"}, "c": set()}
        assert _detect_cycles(graph) == []

    def test_simple_cycle(self):
        graph = {"a": {"b"}, "b": {"a"}}
        cycles = _detect_cycles(graph)
        assert len(cycles) >= 1
        names = set()
        for c in cycles:
            names.update(c)
        assert "a" in names and "b" in names

    def test_self_loop(self):
        graph = {"a": {"a"}}
        cycles = _detect_cycles(graph)
        assert len(cycles) >= 1


class TestAnalyzeDependencies:
    def test_no_team_dir(self, tmp_path):
        findings = analyze_dependencies(str(tmp_path))
        assert findings == []

    def test_detects_cycle(self, cyclic_fixture):
        findings = analyze_dependencies(str(cyclic_fixture))
        cycle_findings = [f for f in findings if f.id == "apex-dep-cycle"]
        assert len(cycle_findings) >= 1
        assert cycle_findings[0].severity == "HIGH"

    def test_detects_unused(self, fixture_dir):
        findings = analyze_dependencies(str(fixture_dir))
        # util.py is imported by scanner.py — should not be flagged unused
        unused = [f for f in findings if f.id == "apex-dep-unused"]
        titles = [f.detail for f in unused]
        assert not any("util" in t for t in titles)

    def test_normal_tree_no_cycles(self, fixture_dir):
        findings = analyze_dependencies(str(fixture_dir))
        cycle_findings = [f for f in findings if f.id == "apex-dep-cycle"]
        assert cycle_findings == []


# ---------------------------------------------------------------------------
# apex_scan CLI
# ---------------------------------------------------------------------------


class TestApexScanCli:
    def _run_cli(self, *args):
        import team.apex.scripts.apex_agent.apex_scan as apex_scan_mod
        with patch.object(sys, "argv", ["apex_scan.py", *args]):
            try:
                apex_scan_mod.main()
                return 0
            except SystemExit as exc:
                return exc.code

    def test_skip_both_tools_writes_empty_report(self, tmp_path):
        out = tmp_path / "report.json"
        code = self._run_cli(str(tmp_path), "--skip-health", "--skip-deps", "--out", str(out))
        assert code in (0, None)
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["agent"] == "apex"
        assert data["findings"] == []

    def test_nonexistent_target_exits_1(self, tmp_path):
        code = self._run_cli("/nonexistent/path/xyz", "--skip-health", "--skip-deps")
        assert code == 1

    def test_critical_finding_exits_2(self, tmp_path):
        out = tmp_path / "report.json"
        with patch(
            "team.apex.scripts.apex_agent.apex_scan.aggregate_health",
            return_value=([Finding("CRITICAL", "X", "d", "l", "r", "S")], []),
        ), patch(
            "team.apex.scripts.apex_agent.apex_scan.analyze_dependencies",
            return_value=[],
        ):
            code = self._run_cli(str(tmp_path), "--out", str(out))
        assert code == 2

    def test_high_finding_exits_2(self, tmp_path):
        out = tmp_path / "report.json"
        with patch(
            "team.apex.scripts.apex_agent.apex_scan.aggregate_health",
            return_value=([Finding("HIGH", "X", "d", "l", "r", "S")], []),
        ), patch(
            "team.apex.scripts.apex_agent.apex_scan.analyze_dependencies",
            return_value=[],
        ):
            code = self._run_cli(str(tmp_path), "--out", str(out))
        assert code == 2

    def test_low_finding_exits_0(self, tmp_path):
        out = tmp_path / "report.json"
        with patch(
            "team.apex.scripts.apex_agent.apex_scan.aggregate_health",
            return_value=([Finding("LOW", "X", "d", "l", "r", "S")], []),
        ), patch(
            "team.apex.scripts.apex_agent.apex_scan.analyze_dependencies",
            return_value=[],
        ):
            code = self._run_cli(str(tmp_path), "--out", str(out))
        assert code in (0, None)

    def test_report_json_structure(self, tmp_path):
        out = tmp_path / "report.json"
        with patch(
            "team.apex.scripts.apex_agent.apex_scan.aggregate_health",
            return_value=([Finding("INFO", "Note", "d", "l", "r", "S")], []),
        ), patch(
            "team.apex.scripts.apex_agent.apex_scan.analyze_dependencies",
            return_value=[],
        ):
            self._run_cli(str(tmp_path), "--out", str(out))
        data = json.loads(out.read_text())
        assert data["skill"] == "apex-review"
        assert data["metadata"]["tool_version"] == "apex-scan 0.9.9"
        assert "summary" in data
