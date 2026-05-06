"""Revenue pipeline artifact scanner for the deal agent."""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, ROOT)
from team.shared.report_schema import Finding

# Keywords that indicate CRM / deal-tracking content
_CRM_KEYWORDS = {
    "pipeline",
    "deal",
    "prospect",
    "arr",
    "mrr",
    "crm",
    "opportunity",
    "lead",
    "quota",
    "forecast",
    "revenue",
}

_ICP_KEYWORDS = {"icp", "ideal customer", "target customer", "customer profile"}
_PRICING_KEYWORDS = {"pricing", "price", "tier", "plan", "subscription", "cost"}
_OUTREACH_KEYWORDS = {
    "outreach",
    "sequence",
    "cadence",
    "cold email",
    "prospecting",
    "follow-up",
}
_DISCOVERY_KEYWORDS = {"discovery", "qualification", "disco call", "qualifying"}
_OBJECTION_KEYWORDS = {
    "objection",
    "objection handling",
    "pushback",
    "concern",
    "rebuttal",
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
        "no_icp": "HIGH",
        "no_pricing": "HIGH",
        "no_outreach_sequence": "MEDIUM",
        "no_discovery_guide": "HIGH",
        "no_objection_guide": "MEDIUM",
        "no_crm_artifacts": "CRITICAL",
    }
    return mapping.get(gap_type, "MEDIUM")


def scan_crm_artifacts(root: str) -> list[Finding]:
    """Scan the project for CRM and deal-tracking artifacts.

    Checks for:
    - Any files containing pipeline/deal/CRM keywords (missing = CRITICAL)
    - ICP / ideal customer profile document (missing = HIGH)
    - Pricing document (missing = HIGH)
    - Outreach sequence / cadence doc (missing = MEDIUM)
    """
    findings: list[Finding] = []
    files = list(_walk_text_files(root))

    crm_files: list[str] = []
    icp_files: list[str] = []
    pricing_files: list[str] = []
    outreach_files: list[str] = []

    for fpath, content in files:
        fname_lower = os.path.basename(fpath).lower()
        combined = fname_lower + " " + content

        if any(kw in combined for kw in _CRM_KEYWORDS):
            crm_files.append(fpath)
        if any(kw in combined for kw in _ICP_KEYWORDS):
            icp_files.append(fpath)
        if any(kw in combined for kw in _PRICING_KEYWORDS):
            pricing_files.append(fpath)
        if any(kw in combined for kw in _OUTREACH_KEYWORDS):
            outreach_files.append(fpath)

    if not crm_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_crm_artifacts"),
                title="No CRM or pipeline artifacts found",
                detail=(
                    "No files containing pipeline, deal, prospect, ARR, MRR, or CRM "
                    "keywords were found. Revenue motion appears completely absent."
                ),
                location=root,
                recommendation=(
                    "Create a deals/ or revenue/ directory with pipeline tracking, "
                    "ICP definition, and deal stages."
                ),
                effort="L",
                id="DEAL-001",
            )
        )

    if not icp_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_icp"),
                title="Missing ICP (Ideal Customer Profile) document",
                detail=(
                    "No file containing ICP or ideal-customer definition was found. "
                    "Without a clear ICP, outbound targeting and qualification are undefined."
                ),
                location=root,
                recommendation=(
                    "Create docs/icp.md describing firmographic criteria, "
                    "pain points, and buying triggers."
                ),
                effort="M",
                id="DEAL-002",
            )
        )

    if not pricing_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_pricing"),
                title="Missing pricing document",
                detail=(
                    "No pricing, plan, or tier document was found. "
                    "Reps cannot quote or close without documented pricing."
                ),
                location=root,
                recommendation=(
                    "Create docs/pricing.md with tier definitions, "
                    "discount authority matrix, and standard packaging."
                ),
                effort="M",
                id="DEAL-003",
            )
        )

    if not outreach_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_outreach_sequence"),
                title="Missing outreach sequence or cadence",
                detail=(
                    "No outreach sequence, cold-email template, or prospecting cadence found. "
                    "Top-of-funnel motion is unstructured."
                ),
                location=root,
                recommendation=(
                    "Add a cadence doc (e.g. docs/outreach-sequence.md) with "
                    "step-by-step touchpoints, copy, and timing."
                ),
                effort="M",
                id="DEAL-004",
            )
        )

    return findings


def scan_playbook_coverage(root: str) -> list[Finding]:
    """Check for sales playbook documents.

    Checks for:
    - Discovery / qualification guide (missing = HIGH)
    - Objection-handling guide (missing = MEDIUM)
    """
    findings: list[Finding] = []
    files = list(_walk_text_files(root))

    discovery_files: list[str] = []
    objection_files: list[str] = []

    for fpath, content in files:
        fname_lower = os.path.basename(fpath).lower()
        combined = fname_lower + " " + content

        if any(kw in combined for kw in _DISCOVERY_KEYWORDS):
            discovery_files.append(fpath)
        if any(kw in combined for kw in _OBJECTION_KEYWORDS):
            objection_files.append(fpath)

    if not discovery_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_discovery_guide"),
                title="Missing discovery / qualification guide",
                detail=(
                    "No discovery call guide or qualification framework (e.g. MEDDIC, BANT) "
                    "found. Reps lack a structured approach to qualify opportunities."
                ),
                location=root,
                recommendation=(
                    "Create docs/discovery-guide.md with question frameworks, "
                    "qualification criteria, and disqualification signals."
                ),
                effort="M",
                id="DEAL-005",
            )
        )

    if not objection_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_objection_guide"),
                title="Missing objection-handling guide",
                detail=(
                    "No objection-handling playbook found. Common objections "
                    "(price, timing, competition) are not addressed with structured responses."
                ),
                location=root,
                recommendation=(
                    "Create docs/objections.md mapping common objections "
                    "to proven responses and supporting evidence."
                ),
                effort="S",
                id="DEAL-006",
            )
        )

    return findings
