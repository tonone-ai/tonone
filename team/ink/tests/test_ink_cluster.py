"""Tests for ink topic cluster scanner: topic_cluster (scan_content_coverage, scan_seo_signals)."""

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, ROOT)

from team.ink.scripts.ink_agent.topic_cluster import (
    _severity_for_content_gap,
    scan_content_coverage,
    scan_seo_signals,
)
from team.shared.report_schema import Finding

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}


class TestSeverityMapping:
    def test_no_content_is_critical(self):
        assert _severity_for_content_gap("no_content") == "CRITICAL"

    def test_few_posts_is_high(self):
        assert _severity_for_content_gap("few_posts") == "HIGH"

    def test_no_keyword_strategy_is_high(self):
        assert _severity_for_content_gap("no_keyword_strategy") == "HIGH"

    def test_no_pillar_page_is_medium(self):
        assert _severity_for_content_gap("no_pillar_page") == "MEDIUM"

    def test_no_internal_linking_is_medium(self):
        assert _severity_for_content_gap("no_internal_linking") == "MEDIUM"

    def test_no_sitemap_is_medium(self):
        assert _severity_for_content_gap("no_sitemap") == "MEDIUM"

    def test_unknown_gap_defaults_to_medium(self):
        assert _severity_for_content_gap("completely_unknown_gap") == "MEDIUM"

    def test_all_known_gap_types_return_valid_severity(self):
        known_gaps = [
            "no_content",
            "few_posts",
            "no_pillar_page",
            "no_internal_linking",
            "no_keyword_strategy",
            "no_sitemap",
        ]
        for gap in known_gaps:
            result = _severity_for_content_gap(gap)
            assert (
                result in VALID_SEVERITIES
            ), f"gap '{gap}' returned invalid severity '{result}'"


class TestTopicCluster:
    def test_scan_content_coverage_returns_list(self):
        findings = scan_content_coverage(ROOT)
        assert isinstance(findings, list)

    def test_scan_content_coverage_findings_are_finding_instances(self):
        findings = scan_content_coverage(ROOT)
        for f in findings:
            assert isinstance(f, Finding)

    def test_scan_content_coverage_valid_severity(self):
        findings = scan_content_coverage(ROOT)
        for f in findings:
            assert (
                f.severity in VALID_SEVERITIES
            ), f"Finding '{f.title}' has invalid severity '{f.severity}'"

    def test_scan_content_coverage_nonempty_title(self):
        findings = scan_content_coverage(ROOT)
        for f in findings:
            assert f.title, f"Finding has empty title: {f}"

    def test_scan_content_coverage_nonempty_detail(self):
        findings = scan_content_coverage(ROOT)
        for f in findings:
            assert f.detail, f"Finding '{f.title}' has empty detail"

    def test_scan_content_coverage_nonempty_recommendation(self):
        findings = scan_content_coverage(ROOT)
        for f in findings:
            assert f.recommendation, f"Finding '{f.title}' has empty recommendation"

    def test_scan_content_coverage_nonempty_location(self):
        findings = scan_content_coverage(ROOT)
        for f in findings:
            assert f.location, f"Finding '{f.title}' has empty location"

    def test_scan_content_coverage_valid_effort(self):
        findings = scan_content_coverage(ROOT)
        for f in findings:
            assert f.effort in {
                "S",
                "M",
                "L",
            }, f"Finding '{f.title}' has invalid effort '{f.effort}'"

    def test_scan_content_coverage_empty_dir_is_critical(self, tmp_path):
        findings = scan_content_coverage(str(tmp_path))
        assert isinstance(findings, list)
        severities = {f.severity for f in findings}
        assert "CRITICAL" in severities

    def test_scan_content_coverage_empty_dir_no_content_id(self, tmp_path):
        findings = scan_content_coverage(str(tmp_path))
        ids = [f.id for f in findings]
        assert "INK-001" in ids

    def test_scan_content_coverage_thin_library(self, tmp_path):
        # Create 3 markdown files -- below the 5-post threshold
        for i in range(3):
            (tmp_path / f"post-{i}.md").write_text(f"# Post {i}\nSome content here.\n")
        findings = scan_content_coverage(str(tmp_path))
        thin_findings = [f for f in findings if f.id == "INK-002"]
        assert len(thin_findings) == 1
        assert thin_findings[0].severity == "HIGH"

    def test_scan_content_coverage_thin_library_no_critical(self, tmp_path):
        # 3 posts: should get "few_posts" (HIGH) not "no_content" (CRITICAL)
        for i in range(3):
            (tmp_path / f"post-{i}.md").write_text(f"# Post {i}\nSome content here.\n")
        findings = scan_content_coverage(str(tmp_path))
        # INK-001 (no_content) should NOT appear
        no_content_findings = [f for f in findings if f.id == "INK-001"]
        assert len(no_content_findings) == 0

    def test_scan_content_coverage_five_posts_no_count_finding(self, tmp_path):
        # 5 posts: neither CRITICAL (no_content) nor HIGH (few_posts) for count
        for i in range(5):
            (tmp_path / f"post-{i}.md").write_text(f"# Post {i}\nSome content here.\n")
        findings = scan_content_coverage(str(tmp_path))
        count_findings = [f for f in findings if f.id in {"INK-001", "INK-002"}]
        assert len(count_findings) == 0

    def test_scan_content_coverage_with_pillar_content(self, tmp_path):
        doc = tmp_path / "guide.md"
        doc.write_text("# Ultimate Guide to Topic X\nThis is the definitive guide.\n")
        findings = scan_content_coverage(str(tmp_path))
        pillar_findings = [f for f in findings if f.id == "INK-003"]
        assert len(pillar_findings) == 0

    def test_scan_content_coverage_with_internal_linking(self, tmp_path):
        doc = tmp_path / "strategy.md"
        doc.write_text(
            "# Content Strategy\nWe use a topic cluster and internal linking approach.\n"
        )
        findings = scan_content_coverage(str(tmp_path))
        link_findings = [f for f in findings if f.id == "INK-004"]
        assert len(link_findings) == 0

    def test_scan_seo_signals_returns_list(self):
        findings = scan_seo_signals(ROOT)
        assert isinstance(findings, list)

    def test_scan_seo_signals_findings_are_finding_instances(self):
        findings = scan_seo_signals(ROOT)
        for f in findings:
            assert isinstance(f, Finding)

    def test_scan_seo_signals_valid_severity(self):
        findings = scan_seo_signals(ROOT)
        for f in findings:
            assert (
                f.severity in VALID_SEVERITIES
            ), f"Finding '{f.title}' has invalid severity '{f.severity}'"

    def test_scan_seo_signals_nonempty_title(self):
        findings = scan_seo_signals(ROOT)
        for f in findings:
            assert f.title, f"Finding has empty title: {f}"

    def test_scan_seo_signals_nonempty_detail(self):
        findings = scan_seo_signals(ROOT)
        for f in findings:
            assert f.detail, f"Finding '{f.title}' has empty detail"

    def test_scan_seo_signals_nonempty_recommendation(self):
        findings = scan_seo_signals(ROOT)
        for f in findings:
            assert f.recommendation, f"Finding '{f.title}' has empty recommendation"

    def test_scan_seo_signals_nonempty_location(self):
        findings = scan_seo_signals(ROOT)
        for f in findings:
            assert f.location, f"Finding '{f.title}' has empty location"

    def test_scan_seo_signals_valid_effort(self):
        findings = scan_seo_signals(ROOT)
        for f in findings:
            assert f.effort in {
                "S",
                "M",
                "L",
            }, f"Finding '{f.title}' has invalid effort '{f.effort}'"

    def test_scan_seo_signals_empty_dir_finding_ids(self, tmp_path):
        findings = scan_seo_signals(str(tmp_path))
        ids = [f.id for f in findings]
        assert "INK-005" in ids
        assert "INK-006" in ids

    def test_scan_seo_signals_with_keyword_strategy(self, tmp_path):
        doc = tmp_path / "seo.md"
        doc.write_text(
            "# SEO Strategy\nThis doc covers keyword research, target keyword clusters, "
            "and search intent.\n"
        )
        findings = scan_seo_signals(str(tmp_path))
        kw_findings = [f for f in findings if f.id == "INK-005"]
        assert len(kw_findings) == 0

    def test_scan_seo_signals_with_sitemap(self, tmp_path):
        sitemap = tmp_path / "sitemap.xml"
        sitemap.write_text("<?xml version='1.0'?><urlset></urlset>")
        findings = scan_seo_signals(str(tmp_path))
        sitemap_findings = [f for f in findings if f.id == "INK-006"]
        assert len(sitemap_findings) == 0

    def test_scan_seo_signals_empty_dir_max_two_findings(self, tmp_path):
        findings = scan_seo_signals(str(tmp_path))
        assert len(findings) <= 2
