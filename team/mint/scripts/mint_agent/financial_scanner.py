"""Financial artifact scanner for the mint agent."""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, ROOT)
from team.shared.report_schema import Finding

# Keywords that indicate P&L / income statement content
_FINANCIAL_KEYWORDS = {
    "p&l",
    "income statement",
    "profit and loss",
    "revenue",
    "expenses",
    "ebitda",
    "gross margin",
    "net income",
    "operating expenses",
    "opex",
    "cogs",
}

_BUDGET_KEYWORDS = {
    "budget",
    "headcount plan",
    "spending plan",
    "capex",
    "annual plan",
    "financial plan",
}

_CASH_FLOW_KEYWORDS = {
    "cash flow",
    "burn rate",
    "burn",
    "runway",
    "cash position",
    "working capital",
}

_FORECAST_KEYWORDS = {
    "forecast",
    "projection",
    "arr forecast",
    "revenue projection",
    "financial model",
}

_LTV_CAC_KEYWORDS = {
    "ltv",
    "cac",
    "customer acquisition cost",
    "lifetime value",
    "payback period",
    "payback",
}

_GROSS_MARGIN_KEYWORDS = {
    "gross margin",
    "cogs",
    "cost of goods",
    "contribution margin",
}

_CHURN_KEYWORDS = {
    "churn",
    "retention rate",
    "logo churn",
    "revenue churn",
    "net revenue retention",
    "nrr",
    "grr",
}


def _read_file_lower(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read().lower()
    except OSError:
        return ""


def _walk_text_files(root: str):
    """Yield (path, lowercased_content) for text files under root."""
    text_exts = {".md", ".txt", ".rst", ".yaml", ".yml", ".json", ".toml", ".csv"}
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip hidden dirs and common noise dirs
        dirnames[:] = [
            d
            for d in dirnames
            if not d.startswith(".")
            and d not in {"node_modules", "__pycache__", ".venv", "venv"}
        ]
        for fname in filenames:
            if os.path.splitext(fname)[1].lower() in text_exts:
                fpath = os.path.join(dirpath, fname)
                yield fpath, _read_file_lower(fpath)


def _severity_for_gap(gap_type: str) -> str:
    """Map a gap type to a severity string."""
    mapping = {
        "no_pl_document": "CRITICAL",
        "no_budget_document": "HIGH",
        "no_cash_flow_doc": "HIGH",
        "no_revenue_forecast": "MEDIUM",
        "no_ltv_cac": "HIGH",
        "no_gross_margin": "HIGH",
        "no_churn_tracking": "MEDIUM",
    }
    return mapping.get(gap_type, "MEDIUM")


def scan_financial_artifacts(root: str) -> list[Finding]:
    """Scan the project for financial planning artifacts.

    Checks for:
    - P&L / income statement document (missing = CRITICAL)
    - Budget document (missing = HIGH)
    - Cash flow / burn / runway doc (missing = HIGH)
    - Revenue forecast / financial model (missing = MEDIUM)
    """
    findings: list[Finding] = []
    files = list(_walk_text_files(root))

    pl_files: list[str] = []
    budget_files: list[str] = []
    cash_flow_files: list[str] = []
    forecast_files: list[str] = []

    for fpath, content in files:
        fname_lower = os.path.basename(fpath).lower()
        combined = fname_lower + " " + content

        if any(kw in combined for kw in _FINANCIAL_KEYWORDS):
            pl_files.append(fpath)
        if any(kw in combined for kw in _BUDGET_KEYWORDS):
            budget_files.append(fpath)
        if any(kw in combined for kw in _CASH_FLOW_KEYWORDS):
            cash_flow_files.append(fpath)
        if any(kw in combined for kw in _FORECAST_KEYWORDS):
            forecast_files.append(fpath)

    if not pl_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_pl_document"),
                title="No P&L or income statement document found",
                detail=(
                    "No files containing P&L, income statement, revenue, expenses, or EBITDA "
                    "keywords were found. Financial reporting appears completely absent."
                ),
                location=root,
                recommendation=(
                    "Create a finance/ or docs/finance/ directory with a P&L template "
                    "covering revenue, COGS, gross margin, opex, and net income."
                ),
                effort="L",
                id="MINT-001",
            )
        )

    if not budget_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_budget_document"),
                title="Missing budget or annual plan document",
                detail=(
                    "No budget, headcount plan, or annual financial plan document found. "
                    "Without a budget, spend decisions lack a target to track against."
                ),
                location=root,
                recommendation=(
                    "Create docs/budget.md or finance/budget.csv with departmental "
                    "spending targets, headcount plan, and revenue goals."
                ),
                effort="M",
                id="MINT-002",
            )
        )

    if not cash_flow_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_cash_flow_doc"),
                title="Missing cash flow or runway document",
                detail=(
                    "No cash flow, burn rate, or runway document found. "
                    "Without burn rate tracking, the company cannot calculate runway or "
                    "make safe hiring and spend decisions."
                ),
                location=root,
                recommendation=(
                    "Create docs/runway.md with current cash balance, monthly burn rate, "
                    "and implied runway months at current and projected burn."
                ),
                effort="M",
                id="MINT-003",
            )
        )

    if not forecast_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_revenue_forecast"),
                title="Missing revenue forecast or financial model",
                detail=(
                    "No revenue forecast, financial projection, or financial model found. "
                    "Without a forward-looking model, fundraising and board reporting "
                    "lack a plan to track against."
                ),
                location=root,
                recommendation=(
                    "Create finance/model.md or a linked spreadsheet with 12-month "
                    "revenue projection, burn forecast, and 3 scenarios (base/bull/bear)."
                ),
                effort="L",
                id="MINT-004",
            )
        )

    return findings


def scan_unit_economics(root: str) -> list[Finding]:
    """Check for unit economics documents.

    Checks for:
    - LTV/CAC/payback period documentation (missing = HIGH)
    - Gross margin documentation (missing = HIGH)
    - Churn rate tracking (missing = MEDIUM)
    - NRR/GRR metrics (missing = MEDIUM)
    """
    findings: list[Finding] = []
    files = list(_walk_text_files(root))

    ltv_cac_files: list[str] = []
    gross_margin_files: list[str] = []
    churn_files: list[str] = []

    for fpath, content in files:
        fname_lower = os.path.basename(fpath).lower()
        combined = fname_lower + " " + content

        if any(kw in combined for kw in _LTV_CAC_KEYWORDS):
            ltv_cac_files.append(fpath)
        if any(kw in combined for kw in _GROSS_MARGIN_KEYWORDS):
            gross_margin_files.append(fpath)
        if any(kw in combined for kw in _CHURN_KEYWORDS):
            churn_files.append(fpath)

    if not ltv_cac_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_ltv_cac"),
                title="Missing LTV, CAC, or payback period documentation",
                detail=(
                    "No files containing LTV, CAC, customer acquisition cost, lifetime value, "
                    "or payback period keywords found. Unit economics are undefined. "
                    "Cannot evaluate growth spend efficiency without these metrics."
                ),
                location=root,
                recommendation=(
                    "Create docs/unit-economics.md defining CAC calculation method, "
                    "LTV formula, and target payback period. Benchmark: LTV:CAC > 3x, "
                    "payback < 18 months."
                ),
                effort="M",
                id="MINT-005",
            )
        )

    if not gross_margin_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_gross_margin"),
                title="Missing gross margin or COGS documentation",
                detail=(
                    "No gross margin, COGS, or cost of goods documentation found. "
                    "LTV calculations are invalid without gross margin. "
                    "SaaS gross margin target is 70%+; hosting and support costs "
                    "must be tracked to know where you stand."
                ),
                location=root,
                recommendation=(
                    "Add gross margin tracking to the P&L: revenue minus COGS "
                    "(hosting, support, third-party API costs) divided by revenue. "
                    "Target 70%+ for SaaS."
                ),
                effort="M",
                id="MINT-006",
            )
        )

    if not churn_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_churn_tracking"),
                title="Missing churn rate or NRR tracking",
                detail=(
                    "No churn rate, revenue churn, NRR, or GRR metrics found. "
                    "Without churn data, LTV calculations are guesses and "
                    "expansion revenue opportunities are invisible."
                ),
                location=root,
                recommendation=(
                    "Add monthly churn tracking to financial reporting: logo churn rate, "
                    "revenue churn rate, and net revenue retention (NRR). "
                    "Best-in-class SaaS NRR is 120%+."
                ),
                effort="S",
                id="MINT-007",
            )
        )

    return findings
