"""Tests for keel ops scanner: ops_scanner (scan_ops_artifacts, scan_compliance_artifacts)."""

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, ROOT)

from team.keel.scripts.keel_agent.ops_scanner import (
    _severity_for_gap,
    scan_compliance_artifacts,
    scan_ops_artifacts,
)
from team.shared.report_schema import Finding

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}


class TestSeverityMapping:
    def test_no_ops_artifacts_is_critical(self):
        assert _severity_for_gap("no_ops_artifacts") == "CRITICAL"

    def test_no_sop_docs_is_high(self):
        assert _severity_for_gap("no_sop_docs") == "HIGH"

    def test_no_vendor_docs_is_medium(self):
        assert _severity_for_gap("no_vendor_docs") == "MEDIUM"

    def test_no_okr_docs_is_medium(self):
        assert _severity_for_gap("no_okr_docs") == "MEDIUM"

    def test_no_compliance_docs_is_high(self):
        assert _severity_for_gap("no_compliance_docs") == "HIGH"

    def test_no_legal_docs_is_high(self):
        assert _severity_for_gap("no_legal_docs") == "HIGH"

    def test_no_bcp_docs_is_low(self):
        assert _severity_for_gap("no_bcp_docs") == "LOW"

    def test_unknown_gap_defaults_to_medium(self):
        assert _severity_for_gap("completely_unknown_gap_type") == "MEDIUM"

    def test_all_known_gap_types_return_valid_severity(self):
        known_gaps = [
            "no_ops_artifacts",
            "no_sop_docs",
            "no_vendor_docs",
            "no_okr_docs",
            "no_compliance_docs",
            "no_legal_docs",
            "no_bcp_docs",
        ]
        for gap in known_gaps:
            result = _severity_for_gap(gap)
            assert (
                result in VALID_SEVERITIES
            ), f"gap '{gap}' returned invalid severity '{result}'"


class TestOpsScanner:
    def test_scan_ops_artifacts_returns_list(self):
        findings = scan_ops_artifacts(ROOT)
        assert isinstance(findings, list)

    def test_scan_ops_artifacts_findings_are_finding_instances(self):
        findings = scan_ops_artifacts(ROOT)
        for f in findings:
            assert isinstance(f, Finding)

    def test_scan_ops_artifacts_valid_severity(self):
        findings = scan_ops_artifacts(ROOT)
        for f in findings:
            assert (
                f.severity in VALID_SEVERITIES
            ), f"Finding '{f.title}' has invalid severity '{f.severity}'"

    def test_scan_ops_artifacts_nonempty_title(self):
        findings = scan_ops_artifacts(ROOT)
        for f in findings:
            assert f.title, f"Finding has empty title: {f}"

    def test_scan_ops_artifacts_nonempty_detail(self):
        findings = scan_ops_artifacts(ROOT)
        for f in findings:
            assert f.detail, f"Finding '{f.title}' has empty detail"

    def test_scan_ops_artifacts_nonempty_recommendation(self):
        findings = scan_ops_artifacts(ROOT)
        for f in findings:
            assert f.recommendation, f"Finding '{f.title}' has empty recommendation"

    def test_scan_ops_artifacts_nonempty_location(self):
        findings = scan_ops_artifacts(ROOT)
        for f in findings:
            assert f.location, f"Finding '{f.title}' has empty location"

    def test_scan_ops_artifacts_valid_effort(self):
        findings = scan_ops_artifacts(ROOT)
        for f in findings:
            assert f.effort in {
                "S",
                "M",
                "L",
            }, f"Finding '{f.title}' has invalid effort '{f.effort}'"

    def test_scan_ops_artifacts_empty_dir(self, tmp_path):
        findings = scan_ops_artifacts(str(tmp_path))
        assert isinstance(findings, list)
        # Empty directory should flag CRITICAL for no ops artifacts
        severities = {f.severity for f in findings}
        assert "CRITICAL" in severities

    def test_scan_ops_artifacts_at_most_four_findings(self, tmp_path):
        # Maximum possible: no_ops_artifacts + no_sop_docs + no_vendor_docs + no_okr_docs = 4
        findings = scan_ops_artifacts(str(tmp_path))
        assert len(findings) <= 4

    def test_scan_ops_artifacts_empty_dir_has_keel001(self, tmp_path):
        findings = scan_ops_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "KEEL-001" in ids

    def test_scan_ops_artifacts_empty_dir_has_keel002(self, tmp_path):
        findings = scan_ops_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "KEEL-002" in ids

    def test_scan_ops_artifacts_empty_dir_has_keel003(self, tmp_path):
        findings = scan_ops_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "KEEL-003" in ids

    def test_scan_ops_artifacts_empty_dir_has_keel004(self, tmp_path):
        findings = scan_ops_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "KEEL-004" in ids

    def test_scan_ops_with_sop_content(self, tmp_path):
        sop_doc = tmp_path / "sop-onboarding.md"
        sop_doc.write_text(
            "# Onboarding SOP\n\nThis is a standard operating procedure for new hires.\n"
            "## Steps\n1. Set up accounts\n2. Complete checklist\n"
        )
        findings = scan_ops_artifacts(str(tmp_path))
        # SOP found -- no HIGH for sop_missing
        sop_finding = [f for f in findings if f.id == "KEEL-002"]
        assert len(sop_finding) == 0

    def test_scan_ops_with_vendor_content(self, tmp_path):
        vendor_doc = tmp_path / "vendors.md"
        vendor_doc.write_text(
            "# Vendor Registry\n\nList of vendors and contracts.\n"
            "| Vendor | Contract | Renewal |\n| AWS | MSA | 2025-01 |\n"
        )
        findings = scan_ops_artifacts(str(tmp_path))
        vendor_finding = [f for f in findings if f.id == "KEEL-003"]
        assert len(vendor_finding) == 0

    def test_scan_ops_with_okr_content(self, tmp_path):
        okr_doc = tmp_path / "okrs.md"
        okr_doc.write_text(
            "# Q2 OKRs\n\n## Objective: Reach product-market fit\n"
            "Key Result 1: 10 paying customers by June 30\n"
        )
        findings = scan_ops_artifacts(str(tmp_path))
        okr_finding = [f for f in findings if f.id == "KEEL-004"]
        assert len(okr_finding) == 0

    def test_scan_ops_with_full_ops_content(self, tmp_path):
        ops_doc = tmp_path / "operations.md"
        ops_doc.write_text(
            "# Operations\n\nThis covers our process, sop, vendor, okr, and workflow.\n"
        )
        findings = scan_ops_artifacts(str(tmp_path))
        # Broad ops artifact found -- KEEL-001 should not appear
        broad_finding = [f for f in findings if f.id == "KEEL-001"]
        assert len(broad_finding) == 0


class TestComplianceScanner:
    def test_scan_compliance_artifacts_returns_list(self):
        findings = scan_compliance_artifacts(ROOT)
        assert isinstance(findings, list)

    def test_scan_compliance_artifacts_findings_are_finding_instances(self):
        findings = scan_compliance_artifacts(ROOT)
        for f in findings:
            assert isinstance(f, Finding)

    def test_scan_compliance_artifacts_valid_severity(self):
        findings = scan_compliance_artifacts(ROOT)
        for f in findings:
            assert (
                f.severity in VALID_SEVERITIES
            ), f"Finding '{f.title}' has invalid severity '{f.severity}'"

    def test_scan_compliance_artifacts_nonempty_title(self):
        findings = scan_compliance_artifacts(ROOT)
        for f in findings:
            assert f.title, f"Finding has empty title: {f}"

    def test_scan_compliance_artifacts_nonempty_detail(self):
        findings = scan_compliance_artifacts(ROOT)
        for f in findings:
            assert f.detail, f"Finding '{f.title}' has empty detail"

    def test_scan_compliance_artifacts_nonempty_recommendation(self):
        findings = scan_compliance_artifacts(ROOT)
        for f in findings:
            assert f.recommendation, f"Finding '{f.title}' has empty recommendation"

    def test_scan_compliance_artifacts_nonempty_location(self):
        findings = scan_compliance_artifacts(ROOT)
        for f in findings:
            assert f.location, f"Finding '{f.title}' has empty location"

    def test_scan_compliance_artifacts_valid_effort(self):
        findings = scan_compliance_artifacts(ROOT)
        for f in findings:
            assert f.effort in {
                "S",
                "M",
                "L",
            }, f"Finding '{f.title}' has invalid effort '{f.effort}'"

    def test_scan_compliance_empty_dir(self, tmp_path):
        findings = scan_compliance_artifacts(str(tmp_path))
        assert isinstance(findings, list)
        # Empty directory: no compliance (HIGH) + no legal (HIGH) + no bcp (LOW) = 3
        assert len(findings) == 3

    def test_scan_compliance_at_most_three_findings(self, tmp_path):
        findings = scan_compliance_artifacts(str(tmp_path))
        assert len(findings) <= 3

    def test_scan_compliance_empty_dir_has_keel005(self, tmp_path):
        findings = scan_compliance_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "KEEL-005" in ids

    def test_scan_compliance_empty_dir_has_keel006(self, tmp_path):
        findings = scan_compliance_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "KEEL-006" in ids

    def test_scan_compliance_empty_dir_has_keel007(self, tmp_path):
        findings = scan_compliance_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "KEEL-007" in ids

    def test_scan_compliance_with_soc2_content(self, tmp_path):
        compliance_doc = tmp_path / "security-policy.md"
        compliance_doc.write_text(
            "# Information Security Policy\n\nSOC2 compliance requirements.\n"
            "This security policy covers our data privacy and compliance program.\n"
        )
        findings = scan_compliance_artifacts(str(tmp_path))
        compliance_finding = [f for f in findings if f.id == "KEEL-005"]
        assert len(compliance_finding) == 0

    def test_scan_compliance_with_gdpr_content(self, tmp_path):
        compliance_doc = tmp_path / "gdpr.md"
        compliance_doc.write_text(
            "# GDPR Compliance\n\nData privacy requirements for EU customers.\n"
        )
        findings = scan_compliance_artifacts(str(tmp_path))
        compliance_finding = [f for f in findings if f.id == "KEEL-005"]
        assert len(compliance_finding) == 0

    def test_scan_compliance_with_legal_content(self, tmp_path):
        legal_doc = tmp_path / "terms.md"
        legal_doc.write_text(
            "# Terms of Service\n\nThese terms and conditions govern use of the service.\n"
            "Liability limitations apply.\n"
        )
        findings = scan_compliance_artifacts(str(tmp_path))
        legal_finding = [f for f in findings if f.id == "KEEL-006"]
        assert len(legal_finding) == 0

    def test_scan_compliance_with_privacy_policy(self, tmp_path):
        privacy_doc = tmp_path / "privacy.md"
        privacy_doc.write_text(
            "# Privacy Policy\n\nThis privacy policy describes how we collect and use data.\n"
        )
        findings = scan_compliance_artifacts(str(tmp_path))
        legal_finding = [f for f in findings if f.id == "KEEL-006"]
        assert len(legal_finding) == 0

    def test_scan_compliance_with_bcp_content(self, tmp_path):
        bcp_doc = tmp_path / "bcp.md"
        bcp_doc.write_text(
            "# Business Continuity Plan\n\nDisaster recovery procedures and failover steps.\n"
            "RTO: 4 hours. RPO: 1 hour.\n"
        )
        findings = scan_compliance_artifacts(str(tmp_path))
        bcp_finding = [f for f in findings if f.id == "KEEL-007"]
        assert len(bcp_finding) == 0

    def test_scan_compliance_keel005_is_high_severity(self, tmp_path):
        findings = scan_compliance_artifacts(str(tmp_path))
        keel005 = [f for f in findings if f.id == "KEEL-005"]
        assert len(keel005) == 1
        assert keel005[0].severity == "HIGH"

    def test_scan_compliance_keel006_is_high_severity(self, tmp_path):
        findings = scan_compliance_artifacts(str(tmp_path))
        keel006 = [f for f in findings if f.id == "KEEL-006"]
        assert len(keel006) == 1
        assert keel006[0].severity == "HIGH"

    def test_scan_compliance_keel007_is_low_severity(self, tmp_path):
        findings = scan_compliance_artifacts(str(tmp_path))
        keel007 = [f for f in findings if f.id == "KEEL-007"]
        assert len(keel007) == 1
        assert keel007[0].severity == "LOW"
