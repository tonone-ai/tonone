"""Tests for brace support scanner: support_scanner (scan_support_artifacts, scan_support_metrics)."""

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, ROOT)

from team.brace.scripts.brace_agent.support_scanner import (
    _severity_for_gap,
    scan_support_artifacts,
    scan_support_metrics,
)
from team.shared.report_schema import Finding

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}


class TestSeverityMapping:
    def test_no_support_artifacts_is_critical(self):
        assert _severity_for_gap("no_support_artifacts") == "CRITICAL"

    def test_no_sla_is_high(self):
        assert _severity_for_gap("no_sla") == "HIGH"

    def test_no_kb_is_high(self):
        assert _severity_for_gap("no_kb") == "HIGH"

    def test_no_escalation_path_is_medium(self):
        assert _severity_for_gap("no_escalation_path") == "MEDIUM"

    def test_no_csat_is_high(self):
        assert _severity_for_gap("no_csat") == "HIGH"

    def test_no_bug_triage_is_medium(self):
        assert _severity_for_gap("no_bug_triage") == "MEDIUM"

    def test_no_support_playbook_is_medium(self):
        assert _severity_for_gap("no_support_playbook") == "MEDIUM"

    def test_unknown_gap_defaults_to_medium(self):
        assert _severity_for_gap("completely_unknown_gap_type") == "MEDIUM"

    def test_all_known_gap_types_return_valid_severity(self):
        known_gaps = [
            "no_support_artifacts",
            "no_sla",
            "no_kb",
            "no_escalation_path",
            "no_csat",
            "no_bug_triage",
            "no_support_playbook",
        ]
        for gap in known_gaps:
            result = _severity_for_gap(gap)
            assert (
                result in VALID_SEVERITIES
            ), f"gap '{gap}' returned invalid severity '{result}'"


class TestSupportArtifactsScanner:
    def test_scan_support_artifacts_returns_list(self):
        findings = scan_support_artifacts(ROOT)
        assert isinstance(findings, list)

    def test_scan_support_artifacts_findings_are_finding_instances(self):
        findings = scan_support_artifacts(ROOT)
        for f in findings:
            assert isinstance(f, Finding)

    def test_scan_support_artifacts_valid_severity(self):
        findings = scan_support_artifacts(ROOT)
        for f in findings:
            assert (
                f.severity in VALID_SEVERITIES
            ), f"Finding '{f.title}' has invalid severity '{f.severity}'"

    def test_scan_support_artifacts_nonempty_title(self):
        findings = scan_support_artifacts(ROOT)
        for f in findings:
            assert f.title, f"Finding has empty title: {f}"

    def test_scan_support_artifacts_nonempty_detail(self):
        findings = scan_support_artifacts(ROOT)
        for f in findings:
            assert f.detail, f"Finding '{f.title}' has empty detail"

    def test_scan_support_artifacts_nonempty_recommendation(self):
        findings = scan_support_artifacts(ROOT)
        for f in findings:
            assert f.recommendation, f"Finding '{f.title}' has empty recommendation"

    def test_scan_support_artifacts_nonempty_location(self):
        findings = scan_support_artifacts(ROOT)
        for f in findings:
            assert f.location, f"Finding '{f.title}' has empty location"

    def test_scan_support_artifacts_valid_effort(self):
        findings = scan_support_artifacts(ROOT)
        for f in findings:
            assert f.effort in {
                "S",
                "M",
                "L",
            }, f"Finding '{f.title}' has invalid effort '{f.effort}'"

    def test_scan_support_artifacts_empty_dir(self, tmp_path):
        findings = scan_support_artifacts(str(tmp_path))
        assert isinstance(findings, list)
        # Empty directory should flag CRITICAL for no support artifacts
        severities = {f.severity for f in findings}
        assert "CRITICAL" in severities

    def test_scan_support_artifacts_at_most_four_findings(self, tmp_path):
        # Maximum possible: no_support_artifacts + no_sla + no_kb + no_escalation_path = 4
        findings = scan_support_artifacts(str(tmp_path))
        assert len(findings) <= 4

    def test_scan_support_artifacts_empty_dir_has_brace_001(self, tmp_path):
        findings = scan_support_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "BRACE-001" in ids

    def test_scan_support_artifacts_empty_dir_has_brace_002(self, tmp_path):
        findings = scan_support_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "BRACE-002" in ids

    def test_scan_support_artifacts_empty_dir_has_brace_003(self, tmp_path):
        findings = scan_support_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "BRACE-003" in ids

    def test_scan_support_artifacts_empty_dir_has_brace_004(self, tmp_path):
        findings = scan_support_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "BRACE-004" in ids

    def test_scan_with_support_content_clears_brace_001(self, tmp_path):
        support_doc = tmp_path / "support.md"
        support_doc.write_text(
            "# Support\n\nThis document covers ticket workflow and helpdesk process.\n"
        )
        findings = scan_support_artifacts(str(tmp_path))
        brace_001 = [f for f in findings if f.id == "BRACE-001"]
        assert len(brace_001) == 0

    def test_scan_with_sla_content_clears_brace_002(self, tmp_path):
        sla_doc = tmp_path / "sla.md"
        sla_doc.write_text(
            "# SLA\n\nFirst response time: 4 hours. Resolution time: 24 hours.\n"
        )
        findings = scan_support_artifacts(str(tmp_path))
        brace_002 = [f for f in findings if f.id == "BRACE-002"]
        assert len(brace_002) == 0

    def test_scan_with_kb_content_clears_brace_003(self, tmp_path):
        kb_doc = tmp_path / "faq.md"
        kb_doc.write_text(
            "# FAQ\n\nFrequently asked questions about our product.\n\n## How to get started?\n"
        )
        findings = scan_support_artifacts(str(tmp_path))
        brace_003 = [f for f in findings if f.id == "BRACE-003"]
        assert len(brace_003) == 0

    def test_scan_with_escalation_content_clears_brace_004(self, tmp_path):
        escalation_doc = tmp_path / "escalation.md"
        escalation_doc.write_text(
            "# Escalation Path\n\nTier 1 handles basic questions. Tier 2 handles complex issues.\n"
        )
        findings = scan_support_artifacts(str(tmp_path))
        brace_004 = [f for f in findings if f.id == "BRACE-004"]
        assert len(brace_004) == 0

    def test_scan_with_all_content_returns_no_findings(self, tmp_path):
        (tmp_path / "support.md").write_text(
            "# Support\n\nTicket workflow and helpdesk process.\n"
        )
        (tmp_path / "sla.md").write_text(
            "# SLA\n\nService level: first response time 4h, resolution time 24h.\n"
        )
        (tmp_path / "faq.md").write_text(
            "# FAQ\n\nFrequently asked questions.\n\n## Troubleshooting guide.\n"
        )
        (tmp_path / "escalation.md").write_text(
            "# Escalation\n\nTier 1 to Tier 2 handoff process.\n"
        )
        findings = scan_support_artifacts(str(tmp_path))
        assert len(findings) == 0


class TestSupportMetricsScanner:
    def test_scan_support_metrics_returns_list(self):
        findings = scan_support_metrics(ROOT)
        assert isinstance(findings, list)

    def test_scan_support_metrics_findings_are_finding_instances(self):
        findings = scan_support_metrics(ROOT)
        for f in findings:
            assert isinstance(f, Finding)

    def test_scan_support_metrics_valid_severity(self):
        findings = scan_support_metrics(ROOT)
        for f in findings:
            assert (
                f.severity in VALID_SEVERITIES
            ), f"Finding '{f.title}' has invalid severity '{f.severity}'"

    def test_scan_support_metrics_nonempty_title(self):
        findings = scan_support_metrics(ROOT)
        for f in findings:
            assert f.title, f"Finding has empty title: {f}"

    def test_scan_support_metrics_nonempty_detail(self):
        findings = scan_support_metrics(ROOT)
        for f in findings:
            assert f.detail, f"Finding '{f.title}' has empty detail"

    def test_scan_support_metrics_nonempty_recommendation(self):
        findings = scan_support_metrics(ROOT)
        for f in findings:
            assert f.recommendation, f"Finding '{f.title}' has empty recommendation"

    def test_scan_support_metrics_nonempty_location(self):
        findings = scan_support_metrics(ROOT)
        for f in findings:
            assert f.location, f"Finding '{f.title}' has empty location"

    def test_scan_support_metrics_valid_effort(self):
        findings = scan_support_metrics(ROOT)
        for f in findings:
            assert f.effort in {
                "S",
                "M",
                "L",
            }, f"Finding '{f.title}' has invalid effort '{f.effort}'"

    def test_scan_support_metrics_empty_dir(self, tmp_path):
        findings = scan_support_metrics(str(tmp_path))
        assert isinstance(findings, list)
        # Empty directory: no csat (HIGH) + no bug triage (MEDIUM) + no playbook (MEDIUM) = 3
        assert len(findings) == 3

    def test_scan_support_metrics_at_most_three_findings(self, tmp_path):
        findings = scan_support_metrics(str(tmp_path))
        assert len(findings) <= 3

    def test_scan_support_metrics_empty_dir_has_brace_005(self, tmp_path):
        findings = scan_support_metrics(str(tmp_path))
        ids = [f.id for f in findings]
        assert "BRACE-005" in ids

    def test_scan_support_metrics_empty_dir_has_brace_006(self, tmp_path):
        findings = scan_support_metrics(str(tmp_path))
        ids = [f.id for f in findings]
        assert "BRACE-006" in ids

    def test_scan_support_metrics_empty_dir_has_brace_007(self, tmp_path):
        findings = scan_support_metrics(str(tmp_path))
        ids = [f.id for f in findings]
        assert "BRACE-007" in ids

    def test_scan_with_csat_content_clears_brace_005(self, tmp_path):
        csat_doc = tmp_path / "csat.md"
        csat_doc.write_text(
            "# Customer Satisfaction\n\nCSAT score target: 4.2/5.0. Survey sent after each resolution.\n"
        )
        findings = scan_support_metrics(str(tmp_path))
        brace_005 = [f for f in findings if f.id == "BRACE-005"]
        assert len(brace_005) == 0

    def test_scan_with_bug_triage_content_clears_brace_006(self, tmp_path):
        bug_doc = tmp_path / "bug-triage.md"
        bug_doc.write_text(
            "# Bug Triage\n\nEngineering handoff template. Bug report format: reproduction steps, environment, impact.\n"
        )
        findings = scan_support_metrics(str(tmp_path))
        brace_006 = [f for f in findings if f.id == "BRACE-006"]
        assert len(brace_006) == 0

    def test_scan_with_playbook_content_clears_brace_007(self, tmp_path):
        playbook_doc = tmp_path / "playbook.md"
        playbook_doc.write_text(
            "# Support Playbook\n\nResponse templates and runbook for common issues.\n"
        )
        findings = scan_support_metrics(str(tmp_path))
        brace_007 = [f for f in findings if f.id == "BRACE-007"]
        assert len(brace_007) == 0

    def test_scan_with_all_metrics_content_returns_no_findings(self, tmp_path):
        (tmp_path / "csat.md").write_text(
            "# CSAT\n\nCustomer satisfaction score measurement process.\n"
        )
        (tmp_path / "bug-triage.md").write_text(
            "# Bug Triage\n\nBug report and engineering handoff process.\n"
        )
        (tmp_path / "playbook.md").write_text(
            "# Support Playbook\n\nResponse templates and agent guide.\n"
        )
        findings = scan_support_metrics(str(tmp_path))
        assert len(findings) == 0

    def test_brace_005_severity_is_high(self, tmp_path):
        findings = scan_support_metrics(str(tmp_path))
        brace_005 = [f for f in findings if f.id == "BRACE-005"]
        assert len(brace_005) == 1
        assert brace_005[0].severity == "HIGH"

    def test_brace_006_severity_is_medium(self, tmp_path):
        findings = scan_support_metrics(str(tmp_path))
        brace_006 = [f for f in findings if f.id == "BRACE-006"]
        assert len(brace_006) == 1
        assert brace_006[0].severity == "MEDIUM"

    def test_brace_007_severity_is_medium(self, tmp_path):
        findings = scan_support_metrics(str(tmp_path))
        brace_007 = [f for f in findings if f.id == "BRACE-007"]
        assert len(brace_007) == 1
        assert brace_007[0].severity == "MEDIUM"
