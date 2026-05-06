"""Tests for keep health scorer: health_scorer (scan_onboarding_coverage, scan_churn_signals)."""

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, ROOT)

from team.keep.scripts.keep_agent.health_scorer import (
    _severity_for_cs_gap,
    scan_churn_signals,
    scan_onboarding_coverage,
)
from team.shared.report_schema import Finding

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}


class TestSeverityMapping:
    def test_no_onboarding_sequence_is_high(self):
        assert _severity_for_cs_gap("no_onboarding_sequence") == "HIGH"

    def test_no_health_score_is_high(self):
        assert _severity_for_cs_gap("no_health_score") == "HIGH"

    def test_no_churn_playbook_is_high(self):
        assert _severity_for_cs_gap("no_churn_playbook") == "HIGH"

    def test_no_ttv_definition_is_medium(self):
        assert _severity_for_cs_gap("no_ttv_definition") == "MEDIUM"

    def test_no_lifecycle_emails_is_medium(self):
        assert _severity_for_cs_gap("no_lifecycle_emails") == "MEDIUM"

    def test_unknown_gap_defaults_to_medium(self):
        assert _severity_for_cs_gap("completely_unknown_gap") == "MEDIUM"

    def test_all_known_gap_types_return_valid_severity(self):
        known_gaps = [
            "no_onboarding_sequence",
            "no_ttv_definition",
            "no_health_score",
            "no_churn_playbook",
            "no_lifecycle_emails",
        ]
        for gap in known_gaps:
            result = _severity_for_cs_gap(gap)
            assert (
                result in VALID_SEVERITIES
            ), f"gap '{gap}' returned invalid severity '{result}'"


class TestHealthScorer:
    def test_scan_onboarding_coverage_returns_list(self):
        findings = scan_onboarding_coverage(ROOT)
        assert isinstance(findings, list)

    def test_scan_onboarding_coverage_findings_are_finding_instances(self):
        findings = scan_onboarding_coverage(ROOT)
        for f in findings:
            assert isinstance(f, Finding)

    def test_scan_onboarding_coverage_valid_severity(self):
        findings = scan_onboarding_coverage(ROOT)
        for f in findings:
            assert (
                f.severity in VALID_SEVERITIES
            ), f"Finding '{f.title}' has invalid severity '{f.severity}'"

    def test_scan_onboarding_coverage_nonempty_title(self):
        findings = scan_onboarding_coverage(ROOT)
        for f in findings:
            assert f.title, f"Finding has empty title: {f}"

    def test_scan_onboarding_coverage_nonempty_detail(self):
        findings = scan_onboarding_coverage(ROOT)
        for f in findings:
            assert f.detail, f"Finding '{f.title}' has empty detail"

    def test_scan_onboarding_coverage_nonempty_recommendation(self):
        findings = scan_onboarding_coverage(ROOT)
        for f in findings:
            assert f.recommendation, f"Finding '{f.title}' has empty recommendation"

    def test_scan_onboarding_coverage_nonempty_location(self):
        findings = scan_onboarding_coverage(ROOT)
        for f in findings:
            assert f.location, f"Finding '{f.title}' has empty location"

    def test_scan_onboarding_coverage_valid_effort(self):
        findings = scan_onboarding_coverage(ROOT)
        for f in findings:
            assert f.effort in {
                "S",
                "M",
                "L",
            }, f"Finding '{f.title}' has invalid effort '{f.effort}'"

    def test_scan_onboarding_coverage_empty_dir(self, tmp_path):
        findings = scan_onboarding_coverage(str(tmp_path))
        assert isinstance(findings, list)
        # Empty dir: no_onboarding_sequence (HIGH) + no_ttv_definition (MEDIUM) = 2
        assert len(findings) == 2

    def test_scan_onboarding_coverage_empty_dir_has_high(self, tmp_path):
        findings = scan_onboarding_coverage(str(tmp_path))
        severities = {f.severity for f in findings}
        assert "HIGH" in severities

    def test_scan_onboarding_finding_ids_empty_dir(self, tmp_path):
        findings = scan_onboarding_coverage(str(tmp_path))
        ids = [f.id for f in findings]
        assert "KEEP-001" in ids
        assert "KEEP-002" in ids

    def test_scan_onboarding_with_onboarding_content(self, tmp_path):
        doc = tmp_path / "onboarding.md"
        doc.write_text(
            "# Onboarding Guide\nWelcome! This is your getting started guide for activation.\n"
        )
        findings = scan_onboarding_coverage(str(tmp_path))
        onboarding_findings = [f for f in findings if f.id == "KEEP-001"]
        assert len(onboarding_findings) == 0

    def test_scan_onboarding_with_ttv_content(self, tmp_path):
        doc = tmp_path / "metrics.md"
        doc.write_text(
            "# Metrics\nWe track time-to-value (TTV) and the aha moment for new users.\n"
        )
        findings = scan_onboarding_coverage(str(tmp_path))
        ttv_findings = [f for f in findings if f.id == "KEEP-002"]
        assert len(ttv_findings) == 0

    def test_scan_churn_signals_returns_list(self):
        findings = scan_churn_signals(ROOT)
        assert isinstance(findings, list)

    def test_scan_churn_signals_findings_are_finding_instances(self):
        findings = scan_churn_signals(ROOT)
        for f in findings:
            assert isinstance(f, Finding)

    def test_scan_churn_signals_valid_severity(self):
        findings = scan_churn_signals(ROOT)
        for f in findings:
            assert (
                f.severity in VALID_SEVERITIES
            ), f"Finding '{f.title}' has invalid severity '{f.severity}'"

    def test_scan_churn_signals_nonempty_title(self):
        findings = scan_churn_signals(ROOT)
        for f in findings:
            assert f.title, f"Finding has empty title: {f}"

    def test_scan_churn_signals_nonempty_detail(self):
        findings = scan_churn_signals(ROOT)
        for f in findings:
            assert f.detail, f"Finding '{f.title}' has empty detail"

    def test_scan_churn_signals_nonempty_recommendation(self):
        findings = scan_churn_signals(ROOT)
        for f in findings:
            assert f.recommendation, f"Finding '{f.title}' has empty recommendation"

    def test_scan_churn_signals_nonempty_location(self):
        findings = scan_churn_signals(ROOT)
        for f in findings:
            assert f.location, f"Finding '{f.title}' has empty location"

    def test_scan_churn_signals_valid_effort(self):
        findings = scan_churn_signals(ROOT)
        for f in findings:
            assert f.effort in {
                "S",
                "M",
                "L",
            }, f"Finding '{f.title}' has invalid effort '{f.effort}'"

    def test_scan_churn_signals_empty_dir(self, tmp_path):
        findings = scan_churn_signals(str(tmp_path))
        assert isinstance(findings, list)
        # Empty dir: no_health_score (HIGH) + no_churn_playbook (HIGH) + no_lifecycle_emails (MEDIUM) = 3
        assert len(findings) == 3

    def test_scan_churn_signals_empty_dir_finding_ids(self, tmp_path):
        findings = scan_churn_signals(str(tmp_path))
        ids = [f.id for f in findings]
        assert "KEEP-003" in ids
        assert "KEEP-004" in ids
        assert "KEEP-005" in ids

    def test_scan_churn_signals_with_health_score_content(self, tmp_path):
        doc = tmp_path / "health.md"
        doc.write_text(
            "# Account Health\nWe define account health score using usage score and NPS.\n"
        )
        findings = scan_churn_signals(str(tmp_path))
        health_findings = [f for f in findings if f.id == "KEEP-003"]
        assert len(health_findings) == 0

    def test_scan_churn_signals_with_churn_content(self, tmp_path):
        doc = tmp_path / "churn-playbook.md"
        doc.write_text(
            "# Churn Playbook\nAt-risk accounts trigger a save playbook and win-back sequence.\n"
        )
        findings = scan_churn_signals(str(tmp_path))
        churn_findings = [f for f in findings if f.id == "KEEP-004"]
        assert len(churn_findings) == 0
