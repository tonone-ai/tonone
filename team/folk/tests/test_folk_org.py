"""Tests for folk org scanner: org_scanner (scan_people_artifacts, scan_performance_culture)."""

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, ROOT)

from team.folk.scripts.folk_agent.org_scanner import (
    _severity_for_gap,
    scan_people_artifacts,
    scan_performance_culture,
)
from team.shared.report_schema import Finding

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}


class TestSeverityMapping:
    def test_no_people_artifacts_is_critical(self):
        assert _severity_for_gap("no_people_artifacts") == "CRITICAL"

    def test_no_org_chart_is_high(self):
        assert _severity_for_gap("no_org_chart") == "HIGH"

    def test_no_jds_is_high(self):
        assert _severity_for_gap("no_jds") == "HIGH"

    def test_no_comp_bands_is_high(self):
        assert _severity_for_gap("no_comp_bands") == "HIGH"

    def test_no_onboarding_is_medium(self):
        assert _severity_for_gap("no_onboarding") == "MEDIUM"

    def test_no_performance_review_is_high(self):
        assert _severity_for_gap("no_performance_review") == "HIGH"

    def test_no_career_ladder_is_medium(self):
        assert _severity_for_gap("no_career_ladder") == "MEDIUM"

    def test_no_culture_doc_is_low(self):
        assert _severity_for_gap("no_culture_doc") == "LOW"

    def test_unknown_gap_defaults_to_medium(self):
        assert _severity_for_gap("completely_unknown_gap_type") == "MEDIUM"

    def test_all_known_gap_types_return_valid_severity(self):
        known_gaps = [
            "no_people_artifacts",
            "no_org_chart",
            "no_jds",
            "no_comp_bands",
            "no_onboarding",
            "no_performance_review",
            "no_career_ladder",
            "no_culture_doc",
        ]
        for gap in known_gaps:
            result = _severity_for_gap(gap)
            assert (
                result in VALID_SEVERITIES
            ), f"gap '{gap}' returned invalid severity '{result}'"


class TestPeopleArtifactsScanner:
    def test_scan_people_artifacts_returns_list(self):
        findings = scan_people_artifacts(ROOT)
        assert isinstance(findings, list)

    def test_scan_people_artifacts_findings_are_finding_instances(self):
        findings = scan_people_artifacts(ROOT)
        for f in findings:
            assert isinstance(f, Finding)

    def test_scan_people_artifacts_valid_severity(self):
        findings = scan_people_artifacts(ROOT)
        for f in findings:
            assert (
                f.severity in VALID_SEVERITIES
            ), f"Finding '{f.title}' has invalid severity '{f.severity}'"

    def test_scan_people_artifacts_nonempty_title(self):
        findings = scan_people_artifacts(ROOT)
        for f in findings:
            assert f.title, f"Finding has empty title: {f}"

    def test_scan_people_artifacts_nonempty_detail(self):
        findings = scan_people_artifacts(ROOT)
        for f in findings:
            assert f.detail, f"Finding '{f.title}' has empty detail"

    def test_scan_people_artifacts_nonempty_recommendation(self):
        findings = scan_people_artifacts(ROOT)
        for f in findings:
            assert f.recommendation, f"Finding '{f.title}' has empty recommendation"

    def test_scan_people_artifacts_nonempty_location(self):
        findings = scan_people_artifacts(ROOT)
        for f in findings:
            assert f.location, f"Finding '{f.title}' has empty location"

    def test_scan_people_artifacts_valid_effort(self):
        findings = scan_people_artifacts(ROOT)
        for f in findings:
            assert f.effort in {
                "S",
                "M",
                "L",
            }, f"Finding '{f.title}' has invalid effort '{f.effort}'"

    def test_scan_people_artifacts_empty_dir(self, tmp_path):
        findings = scan_people_artifacts(str(tmp_path))
        assert isinstance(findings, list)
        # Empty directory should flag CRITICAL for no people artifacts
        severities = {f.severity for f in findings}
        assert "CRITICAL" in severities

    def test_scan_people_artifacts_at_most_five_findings(self, tmp_path):
        # Maximum possible: FOLK-001 + FOLK-002 + FOLK-003 + FOLK-004 + FOLK-005 = 5
        findings = scan_people_artifacts(str(tmp_path))
        assert len(findings) <= 5

    def test_scan_people_artifacts_empty_dir_folk001(self, tmp_path):
        findings = scan_people_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "FOLK-001" in ids

    def test_scan_people_artifacts_empty_dir_folk002(self, tmp_path):
        findings = scan_people_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "FOLK-002" in ids

    def test_scan_people_artifacts_empty_dir_folk003(self, tmp_path):
        findings = scan_people_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "FOLK-003" in ids

    def test_scan_people_artifacts_empty_dir_folk004(self, tmp_path):
        findings = scan_people_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "FOLK-004" in ids

    def test_scan_people_artifacts_empty_dir_folk005(self, tmp_path):
        findings = scan_people_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "FOLK-005" in ids

    def test_scan_with_people_content_no_folk001(self, tmp_path):
        people_doc = tmp_path / "hiring.md"
        people_doc.write_text(
            "# Hiring\n\nWe are recruiting a new engineer. Interview process starts with a recruiter screen.\n"
        )
        findings = scan_people_artifacts(str(tmp_path))
        folk001 = [f for f in findings if f.id == "FOLK-001"]
        assert len(folk001) == 0

    def test_scan_with_org_content_no_folk002(self, tmp_path):
        org_doc = tmp_path / "org-chart.md"
        org_doc.write_text(
            "# Org Chart\n\nThis document describes our reporting structure and team structure.\n"
        )
        findings = scan_people_artifacts(str(tmp_path))
        folk002 = [f for f in findings if f.id == "FOLK-002"]
        assert len(folk002) == 0

    def test_scan_with_jd_content_no_folk003(self, tmp_path):
        jd_doc = tmp_path / "senior-engineer.md"
        jd_doc.write_text(
            "# Senior Engineer\n\n## Responsibilities\n\nLead backend systems.\n\n## Requirements\n\n5+ years experience.\n"
        )
        findings = scan_people_artifacts(str(tmp_path))
        folk003 = [f for f in findings if f.id == "FOLK-003"]
        assert len(folk003) == 0

    def test_scan_with_comp_content_no_folk004(self, tmp_path):
        comp_doc = tmp_path / "comp-bands.md"
        comp_doc.write_text(
            "# Compensation\n\nSalary band for IC2: $150K-$180K base salary. Equity: 0.1-0.2%.\n"
        )
        findings = scan_people_artifacts(str(tmp_path))
        folk004 = [f for f in findings if f.id == "FOLK-004"]
        assert len(folk004) == 0

    def test_scan_with_onboarding_content_no_folk005(self, tmp_path):
        onboard_doc = tmp_path / "onboarding.md"
        onboard_doc.write_text(
            "# Onboarding\n\nWelcome! This is your first day guide for new hire setup.\n"
        )
        findings = scan_people_artifacts(str(tmp_path))
        folk005 = [f for f in findings if f.id == "FOLK-005"]
        assert len(folk005) == 0

    def test_scan_people_artifacts_finding_ids_are_unique(self, tmp_path):
        findings = scan_people_artifacts(str(tmp_path))
        ids = [f.id for f in findings if f.id is not None]
        assert len(ids) == len(set(ids)), "Duplicate finding IDs found"


class TestPerformanceCultureScanner:
    def test_scan_performance_culture_returns_list(self):
        findings = scan_performance_culture(ROOT)
        assert isinstance(findings, list)

    def test_scan_performance_culture_findings_are_finding_instances(self):
        findings = scan_performance_culture(ROOT)
        for f in findings:
            assert isinstance(f, Finding)

    def test_scan_performance_culture_valid_severity(self):
        findings = scan_performance_culture(ROOT)
        for f in findings:
            assert (
                f.severity in VALID_SEVERITIES
            ), f"Finding '{f.title}' has invalid severity '{f.severity}'"

    def test_scan_performance_culture_nonempty_title(self):
        findings = scan_performance_culture(ROOT)
        for f in findings:
            assert f.title, f"Finding has empty title: {f}"

    def test_scan_performance_culture_nonempty_detail(self):
        findings = scan_performance_culture(ROOT)
        for f in findings:
            assert f.detail, f"Finding '{f.title}' has empty detail"

    def test_scan_performance_culture_nonempty_recommendation(self):
        findings = scan_performance_culture(ROOT)
        for f in findings:
            assert f.recommendation, f"Finding '{f.title}' has empty recommendation"

    def test_scan_performance_culture_nonempty_location(self):
        findings = scan_performance_culture(ROOT)
        for f in findings:
            assert f.location, f"Finding '{f.title}' has empty location"

    def test_scan_performance_culture_valid_effort(self):
        findings = scan_performance_culture(ROOT)
        for f in findings:
            assert f.effort in {
                "S",
                "M",
                "L",
            }, f"Finding '{f.title}' has invalid effort '{f.effort}'"

    def test_scan_performance_culture_empty_dir(self, tmp_path):
        findings = scan_performance_culture(str(tmp_path))
        assert isinstance(findings, list)
        # Empty dir: no performance review (HIGH) + no career ladder (MEDIUM) + no culture (LOW) = 3
        assert len(findings) == 3

    def test_scan_performance_culture_at_most_three_findings(self, tmp_path):
        findings = scan_performance_culture(str(tmp_path))
        assert len(findings) <= 3

    def test_scan_performance_culture_folk006_in_empty_dir(self, tmp_path):
        findings = scan_performance_culture(str(tmp_path))
        ids = [f.id for f in findings]
        assert "FOLK-006" in ids

    def test_scan_performance_culture_folk007_in_empty_dir(self, tmp_path):
        findings = scan_performance_culture(str(tmp_path))
        ids = [f.id for f in findings]
        assert "FOLK-007" in ids

    def test_scan_performance_culture_folk008_in_empty_dir(self, tmp_path):
        findings = scan_performance_culture(str(tmp_path))
        ids = [f.id for f in findings]
        assert "FOLK-008" in ids

    def test_scan_with_performance_content_no_folk006(self, tmp_path):
        perf_doc = tmp_path / "performance-review.md"
        perf_doc.write_text(
            "# Performance Review\n\nAnnual review cycle. All employees complete a self-review.\n"
        )
        findings = scan_performance_culture(str(tmp_path))
        folk006 = [f for f in findings if f.id == "FOLK-006"]
        assert len(folk006) == 0

    def test_scan_with_career_content_no_folk007(self, tmp_path):
        career_doc = tmp_path / "levels.md"
        career_doc.write_text(
            "# Career Ladder\n\nIC1: entry. IC2: mid. Leveling is based on scope and impact.\n"
        )
        findings = scan_performance_culture(str(tmp_path))
        folk007 = [f for f in findings if f.id == "FOLK-007"]
        assert len(folk007) == 0

    def test_scan_with_culture_content_no_folk008(self, tmp_path):
        culture_doc = tmp_path / "values.md"
        culture_doc.write_text(
            "# Company Values\n\nOur culture is built on transparency and speed.\n"
        )
        findings = scan_performance_culture(str(tmp_path))
        folk008 = [f for f in findings if f.id == "FOLK-008"]
        assert len(folk008) == 0

    def test_scan_performance_culture_finding_ids_are_unique(self, tmp_path):
        findings = scan_performance_culture(str(tmp_path))
        ids = [f.id for f in findings if f.id is not None]
        assert len(ids) == len(set(ids)), "Duplicate finding IDs found"

    def test_folk006_severity_is_high(self, tmp_path):
        findings = scan_performance_culture(str(tmp_path))
        folk006 = [f for f in findings if f.id == "FOLK-006"]
        assert len(folk006) == 1
        assert folk006[0].severity == "HIGH"

    def test_folk007_severity_is_medium(self, tmp_path):
        findings = scan_performance_culture(str(tmp_path))
        folk007 = [f for f in findings if f.id == "FOLK-007"]
        assert len(folk007) == 1
        assert folk007[0].severity == "MEDIUM"

    def test_folk008_severity_is_low(self, tmp_path):
        findings = scan_performance_culture(str(tmp_path))
        folk008 = [f for f in findings if f.id == "FOLK-008"]
        assert len(folk008) == 1
        assert folk008[0].severity == "LOW"
