"""Tests for mint financial scanner: financial_scanner (scan_financial_artifacts, scan_unit_economics)."""

import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, ROOT)

from team.mint.scripts.mint_agent.financial_scanner import (
    _severity_for_gap,
    scan_financial_artifacts,
    scan_unit_economics,
)
from team.shared.report_schema import Finding

VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}


class TestSeverityMapping:
    def test_no_pl_document_is_critical(self):
        assert _severity_for_gap("no_pl_document") == "CRITICAL"

    def test_no_budget_document_is_high(self):
        assert _severity_for_gap("no_budget_document") == "HIGH"

    def test_no_cash_flow_doc_is_high(self):
        assert _severity_for_gap("no_cash_flow_doc") == "HIGH"

    def test_no_revenue_forecast_is_medium(self):
        assert _severity_for_gap("no_revenue_forecast") == "MEDIUM"

    def test_no_ltv_cac_is_high(self):
        assert _severity_for_gap("no_ltv_cac") == "HIGH"

    def test_no_gross_margin_is_high(self):
        assert _severity_for_gap("no_gross_margin") == "HIGH"

    def test_no_churn_tracking_is_medium(self):
        assert _severity_for_gap("no_churn_tracking") == "MEDIUM"

    def test_unknown_gap_defaults_to_medium(self):
        assert _severity_for_gap("completely_unknown_gap_type") == "MEDIUM"

    def test_all_known_gap_types_return_valid_severity(self):
        known_gaps = [
            "no_pl_document",
            "no_budget_document",
            "no_cash_flow_doc",
            "no_revenue_forecast",
            "no_ltv_cac",
            "no_gross_margin",
            "no_churn_tracking",
        ]
        for gap in known_gaps:
            result = _severity_for_gap(gap)
            assert (
                result in VALID_SEVERITIES
            ), f"gap '{gap}' returned invalid severity '{result}'"


class TestFinancialArtifactsScanner:
    def test_scan_financial_artifacts_returns_list(self):
        findings = scan_financial_artifacts(ROOT)
        assert isinstance(findings, list)

    def test_scan_financial_artifacts_findings_are_finding_instances(self):
        findings = scan_financial_artifacts(ROOT)
        for f in findings:
            assert isinstance(f, Finding)

    def test_scan_financial_artifacts_valid_severity(self):
        findings = scan_financial_artifacts(ROOT)
        for f in findings:
            assert (
                f.severity in VALID_SEVERITIES
            ), f"Finding '{f.title}' has invalid severity '{f.severity}'"

    def test_scan_financial_artifacts_nonempty_title(self):
        findings = scan_financial_artifacts(ROOT)
        for f in findings:
            assert f.title, f"Finding has empty title: {f}"

    def test_scan_financial_artifacts_nonempty_detail(self):
        findings = scan_financial_artifacts(ROOT)
        for f in findings:
            assert f.detail, f"Finding '{f.title}' has empty detail"

    def test_scan_financial_artifacts_nonempty_recommendation(self):
        findings = scan_financial_artifacts(ROOT)
        for f in findings:
            assert f.recommendation, f"Finding '{f.title}' has empty recommendation"

    def test_scan_financial_artifacts_nonempty_location(self):
        findings = scan_financial_artifacts(ROOT)
        for f in findings:
            assert f.location, f"Finding '{f.title}' has empty location"

    def test_scan_financial_artifacts_valid_effort(self):
        findings = scan_financial_artifacts(ROOT)
        for f in findings:
            assert f.effort in {
                "S",
                "M",
                "L",
            }, f"Finding '{f.title}' has invalid effort '{f.effort}'"

    def test_scan_financial_artifacts_empty_dir(self, tmp_path):
        findings = scan_financial_artifacts(str(tmp_path))
        assert isinstance(findings, list)
        # Empty directory should flag CRITICAL for no P&L document
        severities = {f.severity for f in findings}
        assert "CRITICAL" in severities

    def test_scan_financial_artifacts_at_most_four_findings(self, tmp_path):
        # Maximum possible: no_pl + no_budget + no_cash_flow + no_revenue_forecast = 4
        findings = scan_financial_artifacts(str(tmp_path))
        assert len(findings) <= 4

    def test_scan_financial_artifacts_pl_finding_id(self, tmp_path):
        findings = scan_financial_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "MINT-001" in ids

    def test_scan_financial_artifacts_budget_finding_id(self, tmp_path):
        findings = scan_financial_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "MINT-002" in ids

    def test_scan_financial_artifacts_cash_flow_finding_id(self, tmp_path):
        findings = scan_financial_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "MINT-003" in ids

    def test_scan_financial_artifacts_forecast_finding_id(self, tmp_path):
        findings = scan_financial_artifacts(str(tmp_path))
        ids = [f.id for f in findings]
        assert "MINT-004" in ids

    def test_scan_with_pl_content(self, tmp_path):
        pl_doc = tmp_path / "financials.md"
        pl_doc.write_text(
            "# P&L Statement\n\nRevenue: $500K\nCOGS: $100K\nGross Margin: 80%\nOpex: $300K\n"
        )
        findings = scan_financial_artifacts(str(tmp_path))
        pl_finding = [f for f in findings if "MINT-001" == f.id]
        assert len(pl_finding) == 0

    def test_scan_with_budget_content(self, tmp_path):
        budget_doc = tmp_path / "budget.md"
        budget_doc.write_text(
            "# Annual Budget\n\nHeadcount plan: 5 engineers, 2 sales.\nSpending plan: $1.2M.\n"
        )
        findings = scan_financial_artifacts(str(tmp_path))
        budget_finding = [f for f in findings if "MINT-002" == f.id]
        assert len(budget_finding) == 0

    def test_scan_with_cash_flow_content(self, tmp_path):
        runway_doc = tmp_path / "runway.md"
        runway_doc.write_text(
            "# Runway\n\nCash position: $2M\nBurn rate: $150K/month\nRunway: 13 months\n"
        )
        findings = scan_financial_artifacts(str(tmp_path))
        cash_finding = [f for f in findings if "MINT-003" == f.id]
        assert len(cash_finding) == 0

    def test_scan_with_forecast_content(self, tmp_path):
        forecast_doc = tmp_path / "model.md"
        forecast_doc.write_text(
            "# Financial Model\n\nARR forecast: $2M by Q4.\nRevenue projection: 3x growth.\n"
        )
        findings = scan_financial_artifacts(str(tmp_path))
        forecast_finding = [f for f in findings if "MINT-004" == f.id]
        assert len(forecast_finding) == 0


class TestUnitEconomicsScanner:
    def test_scan_unit_economics_returns_list(self):
        findings = scan_unit_economics(ROOT)
        assert isinstance(findings, list)

    def test_scan_unit_economics_findings_are_finding_instances(self):
        findings = scan_unit_economics(ROOT)
        for f in findings:
            assert isinstance(f, Finding)

    def test_scan_unit_economics_valid_severity(self):
        findings = scan_unit_economics(ROOT)
        for f in findings:
            assert (
                f.severity in VALID_SEVERITIES
            ), f"Finding '{f.title}' has invalid severity '{f.severity}'"

    def test_scan_unit_economics_nonempty_title(self):
        findings = scan_unit_economics(ROOT)
        for f in findings:
            assert f.title, f"Finding has empty title: {f}"

    def test_scan_unit_economics_nonempty_detail(self):
        findings = scan_unit_economics(ROOT)
        for f in findings:
            assert f.detail, f"Finding '{f.title}' has empty detail"

    def test_scan_unit_economics_nonempty_recommendation(self):
        findings = scan_unit_economics(ROOT)
        for f in findings:
            assert f.recommendation, f"Finding '{f.title}' has empty recommendation"

    def test_scan_unit_economics_nonempty_location(self):
        findings = scan_unit_economics(ROOT)
        for f in findings:
            assert f.location, f"Finding '{f.title}' has empty location"

    def test_scan_unit_economics_valid_effort(self):
        findings = scan_unit_economics(ROOT)
        for f in findings:
            assert f.effort in {
                "S",
                "M",
                "L",
            }, f"Finding '{f.title}' has invalid effort '{f.effort}'"

    def test_scan_unit_economics_empty_dir(self, tmp_path):
        findings = scan_unit_economics(str(tmp_path))
        assert isinstance(findings, list)
        # Empty directory: no LTV/CAC (HIGH) + no gross margin (HIGH) + no churn (MEDIUM) = 3
        assert len(findings) == 3

    def test_scan_unit_economics_at_most_three_findings(self, tmp_path):
        findings = scan_unit_economics(str(tmp_path))
        assert len(findings) <= 3

    def test_scan_unit_economics_ltv_cac_finding_id(self, tmp_path):
        findings = scan_unit_economics(str(tmp_path))
        ids = [f.id for f in findings]
        assert "MINT-005" in ids

    def test_scan_unit_economics_gross_margin_finding_id(self, tmp_path):
        findings = scan_unit_economics(str(tmp_path))
        ids = [f.id for f in findings]
        assert "MINT-006" in ids

    def test_scan_unit_economics_churn_finding_id(self, tmp_path):
        findings = scan_unit_economics(str(tmp_path))
        ids = [f.id for f in findings]
        assert "MINT-007" in ids

    def test_scan_with_ltv_cac_content(self, tmp_path):
        unit_doc = tmp_path / "unit-economics.md"
        unit_doc.write_text(
            "# Unit Economics\n\nCAC: $1,200\nLTV: $4,800\nPayback period: 8 months.\n"
        )
        findings = scan_unit_economics(str(tmp_path))
        ltv_finding = [f for f in findings if "MINT-005" == f.id]
        assert len(ltv_finding) == 0

    def test_scan_with_gross_margin_content(self, tmp_path):
        gm_doc = tmp_path / "gross-margin.md"
        gm_doc.write_text(
            "# Gross Margin Analysis\n\nCOGS: $80K\nRevenue: $500K\nGross margin: 84%.\n"
        )
        findings = scan_unit_economics(str(tmp_path))
        gm_finding = [f for f in findings if "MINT-006" == f.id]
        assert len(gm_finding) == 0

    def test_scan_with_churn_content(self, tmp_path):
        churn_doc = tmp_path / "retention.md"
        churn_doc.write_text(
            "# Retention Metrics\n\nLogo churn: 2%/month\nNRR: 118%\nRevenue churn: 1.5%.\n"
        )
        findings = scan_unit_economics(str(tmp_path))
        churn_finding = [f for f in findings if "MINT-007" == f.id]
        assert len(churn_finding) == 0
