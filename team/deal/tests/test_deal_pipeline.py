"""Tests for deal pipeline scanner: pipeline_scanner (scan_crm_artifacts, scan_playbook_coverage)."""

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, ROOT)

from team.deal.scripts.deal_agent.pipeline_scanner import (
    _severity_for_gap,
    scan_crm_artifacts,
    scan_playbook_coverage,
)
from team.shared.report_schema import Finding

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}


class TestSeverityMapping:
    def test_no_crm_artifacts_is_critical(self):
        assert _severity_for_gap("no_crm_artifacts") == "CRITICAL"

    def test_no_icp_is_high(self):
        assert _severity_for_gap("no_icp") == "HIGH"

    def test_no_pricing_is_high(self):
        assert _severity_for_gap("no_pricing") == "HIGH"

    def test_no_discovery_guide_is_high(self):
        assert _severity_for_gap("no_discovery_guide") == "HIGH"

    def test_no_outreach_sequence_is_medium(self):
        assert _severity_for_gap("no_outreach_sequence") == "MEDIUM"

    def test_no_objection_guide_is_medium(self):
        assert _severity_for_gap("no_objection_guide") == "MEDIUM"

    def test_unknown_gap_defaults_to_medium(self):
        assert _severity_for_gap("completely_unknown_gap_type") == "MEDIUM"

    def test_all_known_gap_types_return_valid_severity(self):
        known_gaps = [
            "no_icp",
            "no_pricing",
            "no_outreach_sequence",
            "no_discovery_guide",
            "no_objection_guide",
            "no_crm_artifacts",
        ]
        for gap in known_gaps:
            result = _severity_for_gap(gap)
            assert (
                result in VALID_SEVERITIES
            ), f"gap '{gap}' returned invalid severity '{result}'"


class TestPipelineScanner:
    def test_scan_crm_artifacts_returns_list(self):
        findings = scan_crm_artifacts(ROOT)
        assert isinstance(findings, list)

    def test_scan_crm_artifacts_findings_are_finding_instances(self):
        findings = scan_crm_artifacts(ROOT)
        for f in findings:
            assert isinstance(f, Finding)

    def test_scan_crm_artifacts_valid_severity(self):
        findings = scan_crm_artifacts(ROOT)
        for f in findings:
            assert (
                f.severity in VALID_SEVERITIES
            ), f"Finding '{f.title}' has invalid severity '{f.severity}'"

    def test_scan_crm_artifacts_nonempty_title(self):
        findings = scan_crm_artifacts(ROOT)
        for f in findings:
            assert f.title, f"Finding has empty title: {f}"

    def test_scan_crm_artifacts_nonempty_detail(self):
        findings = scan_crm_artifacts(ROOT)
        for f in findings:
            assert f.detail, f"Finding '{f.title}' has empty detail"

    def test_scan_crm_artifacts_nonempty_recommendation(self):
        findings = scan_crm_artifacts(ROOT)
        for f in findings:
            assert f.recommendation, f"Finding '{f.title}' has empty recommendation"

    def test_scan_crm_artifacts_nonempty_location(self):
        findings = scan_crm_artifacts(ROOT)
        for f in findings:
            assert f.location, f"Finding '{f.title}' has empty location"

    def test_scan_crm_artifacts_valid_effort(self):
        findings = scan_crm_artifacts(ROOT)
        for f in findings:
            assert f.effort in {
                "S",
                "M",
                "L",
            }, f"Finding '{f.title}' has invalid effort '{f.effort}'"

    def test_scan_crm_artifacts_empty_dir(self, tmp_path):
        findings = scan_crm_artifacts(str(tmp_path))
        assert isinstance(findings, list)
        # Empty directory should flag CRITICAL for no CRM artifacts
        severities = {f.severity for f in findings}
        assert "CRITICAL" in severities

    def test_scan_crm_artifacts_at_most_four_findings(self, tmp_path):
        # Maximum possible: no_crm_artifacts + no_icp + no_pricing + no_outreach_sequence = 4
        findings = scan_crm_artifacts(str(tmp_path))
        assert len(findings) <= 4

    def test_scan_playbook_coverage_returns_list(self):
        findings = scan_playbook_coverage(ROOT)
        assert isinstance(findings, list)

    def test_scan_playbook_coverage_findings_are_finding_instances(self):
        findings = scan_playbook_coverage(ROOT)
        for f in findings:
            assert isinstance(f, Finding)

    def test_scan_playbook_coverage_valid_severity(self):
        findings = scan_playbook_coverage(ROOT)
        for f in findings:
            assert (
                f.severity in VALID_SEVERITIES
            ), f"Finding '{f.title}' has invalid severity '{f.severity}'"

    def test_scan_playbook_coverage_nonempty_title(self):
        findings = scan_playbook_coverage(ROOT)
        for f in findings:
            assert f.title, f"Finding has empty title: {f}"

    def test_scan_playbook_coverage_nonempty_detail(self):
        findings = scan_playbook_coverage(ROOT)
        for f in findings:
            assert f.detail, f"Finding '{f.title}' has empty detail"

    def test_scan_playbook_coverage_nonempty_recommendation(self):
        findings = scan_playbook_coverage(ROOT)
        for f in findings:
            assert f.recommendation, f"Finding '{f.title}' has empty recommendation"

    def test_scan_playbook_coverage_nonempty_location(self):
        findings = scan_playbook_coverage(ROOT)
        for f in findings:
            assert f.location, f"Finding '{f.title}' has empty location"

    def test_scan_playbook_coverage_valid_effort(self):
        findings = scan_playbook_coverage(ROOT)
        for f in findings:
            assert f.effort in {
                "S",
                "M",
                "L",
            }, f"Finding '{f.title}' has invalid effort '{f.effort}'"

    def test_scan_playbook_coverage_empty_dir(self, tmp_path):
        findings = scan_playbook_coverage(str(tmp_path))
        assert isinstance(findings, list)
        # Empty directory: no discovery guide (HIGH) + no objection guide (MEDIUM) = 2
        assert len(findings) == 2

    def test_scan_playbook_coverage_at_most_two_findings(self, tmp_path):
        findings = scan_playbook_coverage(str(tmp_path))
        assert len(findings) <= 2

    def test_scan_playbook_coverage_discovery_finding_id(self, tmp_path):
        findings = scan_playbook_coverage(str(tmp_path))
        ids = [f.id for f in findings]
        assert "DEAL-005" in ids

    def test_scan_playbook_coverage_objection_finding_id(self, tmp_path):
        findings = scan_playbook_coverage(str(tmp_path))
        ids = [f.id for f in findings]
        assert "DEAL-006" in ids

    def test_scan_crm_with_crm_content(self, tmp_path):
        crm_doc = tmp_path / "pipeline.md"
        crm_doc.write_text(
            "# Pipeline\n\nThis document covers ARR, MRR, deals, and prospect tracking.\n"
        )
        findings = scan_crm_artifacts(str(tmp_path))
        # CRM artifact found -- no CRITICAL for crm_missing
        crm_finding = [f for f in findings if "DEAL-001" == f.id]
        assert len(crm_finding) == 0

    def test_scan_crm_with_icp_content(self, tmp_path):
        icp_doc = tmp_path / "icp.md"
        icp_doc.write_text(
            "# Ideal Customer Profile\nTarget customer: mid-market SaaS.\n"
        )
        findings = scan_crm_artifacts(str(tmp_path))
        icp_finding = [f for f in findings if "DEAL-002" == f.id]
        assert len(icp_finding) == 0
