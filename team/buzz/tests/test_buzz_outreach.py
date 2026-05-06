"""Tests for buzz outreach tracker: outreach_tracker (scan_press_assets, scan_community_health)."""

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, ROOT)

from team.buzz.scripts.buzz_agent.outreach_tracker import (
    _severity_for_pr_gap,
    scan_community_health,
    scan_press_assets,
)
from team.shared.report_schema import Finding

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}


class TestSeverityMapping:
    def test_no_press_kit_is_high(self):
        assert _severity_for_pr_gap("no_press_kit") == "HIGH"

    def test_no_community_platform_is_high(self):
        assert _severity_for_pr_gap("no_community_platform") == "HIGH"

    def test_no_media_list_is_medium(self):
        assert _severity_for_pr_gap("no_media_list") == "MEDIUM"

    def test_no_pitch_template_is_medium(self):
        assert _severity_for_pr_gap("no_pitch_template") == "MEDIUM"

    def test_no_contributor_guide_is_medium(self):
        assert _severity_for_pr_gap("no_contributor_guide") == "MEDIUM"

    def test_no_community_docs_is_medium(self):
        assert _severity_for_pr_gap("no_community_docs") == "MEDIUM"

    def test_unknown_gap_defaults_to_medium(self):
        assert _severity_for_pr_gap("completely_unknown_gap") == "MEDIUM"

    def test_all_known_gap_types_return_valid_severity(self):
        known_gaps = [
            "no_press_kit",
            "no_media_list",
            "no_pitch_template",
            "no_contributor_guide",
            "no_community_platform",
            "no_community_docs",
        ]
        for gap in known_gaps:
            result = _severity_for_pr_gap(gap)
            assert (
                result in VALID_SEVERITIES
            ), f"gap '{gap}' returned invalid severity '{result}'"


class TestOutreachTracker:
    def test_scan_press_assets_returns_list(self):
        findings = scan_press_assets(ROOT)
        assert isinstance(findings, list)

    def test_scan_press_assets_findings_are_finding_instances(self):
        findings = scan_press_assets(ROOT)
        for f in findings:
            assert isinstance(f, Finding)

    def test_scan_press_assets_valid_severity(self):
        findings = scan_press_assets(ROOT)
        for f in findings:
            assert (
                f.severity in VALID_SEVERITIES
            ), f"Finding '{f.title}' has invalid severity '{f.severity}'"

    def test_scan_press_assets_nonempty_title(self):
        findings = scan_press_assets(ROOT)
        for f in findings:
            assert f.title, f"Finding has empty title: {f}"

    def test_scan_press_assets_nonempty_detail(self):
        findings = scan_press_assets(ROOT)
        for f in findings:
            assert f.detail, f"Finding '{f.title}' has empty detail"

    def test_scan_press_assets_nonempty_recommendation(self):
        findings = scan_press_assets(ROOT)
        for f in findings:
            assert f.recommendation, f"Finding '{f.title}' has empty recommendation"

    def test_scan_press_assets_nonempty_location(self):
        findings = scan_press_assets(ROOT)
        for f in findings:
            assert f.location, f"Finding '{f.title}' has empty location"

    def test_scan_press_assets_valid_effort(self):
        findings = scan_press_assets(ROOT)
        for f in findings:
            assert f.effort in {
                "S",
                "M",
                "L",
            }, f"Finding '{f.title}' has invalid effort '{f.effort}'"

    def test_scan_press_assets_empty_dir(self, tmp_path):
        findings = scan_press_assets(str(tmp_path))
        assert isinstance(findings, list)
        # Empty dir: no_press_kit (HIGH) + no_media_list (MEDIUM) + no_pitch_template (MEDIUM) = 3
        assert len(findings) == 3

    def test_scan_press_assets_empty_dir_finding_ids(self, tmp_path):
        findings = scan_press_assets(str(tmp_path))
        ids = [f.id for f in findings]
        assert "BUZZ-001" in ids
        assert "BUZZ-002" in ids
        assert "BUZZ-003" in ids

    def test_scan_press_assets_empty_dir_has_high(self, tmp_path):
        findings = scan_press_assets(str(tmp_path))
        severities = {f.severity for f in findings}
        assert "HIGH" in severities

    def test_scan_press_assets_with_press_kit(self, tmp_path):
        doc = tmp_path / "press-kit.md"
        doc.write_text(
            "# Press Kit\nCompany boilerplate, logos, and media kit assets.\n"
        )
        findings = scan_press_assets(str(tmp_path))
        press_findings = [f for f in findings if f.id == "BUZZ-001"]
        assert len(press_findings) == 0

    def test_scan_press_assets_with_media_list(self, tmp_path):
        doc = tmp_path / "contacts.csv"
        doc.write_text("name,outlet,beat\nJane Doe,TechCrunch,media list\n")
        findings = scan_press_assets(str(tmp_path))
        media_findings = [f for f in findings if f.id == "BUZZ-002"]
        assert len(media_findings) == 0

    def test_scan_press_assets_with_pitch_template(self, tmp_path):
        doc = tmp_path / "pitch.md"
        doc.write_text(
            "# Pitch Template\nUse this pitch email when reaching out to journalists.\n"
        )
        findings = scan_press_assets(str(tmp_path))
        pitch_findings = [f for f in findings if f.id == "BUZZ-003"]
        assert len(pitch_findings) == 0

    def test_scan_community_health_returns_list(self):
        findings = scan_community_health(ROOT)
        assert isinstance(findings, list)

    def test_scan_community_health_findings_are_finding_instances(self):
        findings = scan_community_health(ROOT)
        for f in findings:
            assert isinstance(f, Finding)

    def test_scan_community_health_valid_severity(self):
        findings = scan_community_health(ROOT)
        for f in findings:
            assert (
                f.severity in VALID_SEVERITIES
            ), f"Finding '{f.title}' has invalid severity '{f.severity}'"

    def test_scan_community_health_nonempty_title(self):
        findings = scan_community_health(ROOT)
        for f in findings:
            assert f.title, f"Finding has empty title: {f}"

    def test_scan_community_health_nonempty_detail(self):
        findings = scan_community_health(ROOT)
        for f in findings:
            assert f.detail, f"Finding '{f.title}' has empty detail"

    def test_scan_community_health_nonempty_recommendation(self):
        findings = scan_community_health(ROOT)
        for f in findings:
            assert f.recommendation, f"Finding '{f.title}' has empty recommendation"

    def test_scan_community_health_nonempty_location(self):
        findings = scan_community_health(ROOT)
        for f in findings:
            assert f.location, f"Finding '{f.title}' has empty location"

    def test_scan_community_health_valid_effort(self):
        findings = scan_community_health(ROOT)
        for f in findings:
            assert f.effort in {
                "S",
                "M",
                "L",
            }, f"Finding '{f.title}' has invalid effort '{f.effort}'"

    def test_scan_community_health_empty_dir(self, tmp_path):
        findings = scan_community_health(str(tmp_path))
        assert isinstance(findings, list)
        # Empty dir triggers: no_community_platform (HIGH) + no_contributor_guide (MEDIUM)
        # community_health check may pass if no "community" keyword found -- exactly 2 or 3
        assert len(findings) >= 2

    def test_scan_community_health_empty_dir_finding_ids(self, tmp_path):
        findings = scan_community_health(str(tmp_path))
        ids = [f.id for f in findings]
        assert "BUZZ-004" in ids
        assert "BUZZ-005" in ids

    def test_scan_community_health_with_discord(self, tmp_path):
        doc = tmp_path / "community.md"
        doc.write_text(
            "# Community\nJoin our Discord server for help and discussion.\n"
        )
        findings = scan_community_health(str(tmp_path))
        platform_findings = [f for f in findings if f.id == "BUZZ-004"]
        assert len(platform_findings) == 0

    def test_scan_community_health_with_contributing(self, tmp_path):
        doc = tmp_path / "CONTRIBUTING.md"
        doc.write_text(
            "# Contributing\nThis is the contributor guide. How to contribute to this project.\n"
        )
        findings = scan_community_health(str(tmp_path))
        contrib_findings = [f for f in findings if f.id == "BUZZ-005"]
        assert len(contrib_findings) == 0

    def test_scan_community_health_with_code_of_conduct(self, tmp_path):
        doc = tmp_path / "CODE_OF_CONDUCT.md"
        doc.write_text(
            "# Code of Conduct\nOur community guidelines and moderation rules.\n"
        )
        findings = scan_community_health(str(tmp_path))
        coc_findings = [f for f in findings if f.id == "BUZZ-006"]
        assert len(coc_findings) == 0
