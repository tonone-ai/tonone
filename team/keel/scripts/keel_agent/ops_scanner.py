"""Operations artifact scanner for the keel agent."""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, ROOT)
from team.shared.report_schema import Finding

# Keywords that indicate process / SOP content
_SOP_KEYWORDS = {
    "sop",
    "standard operating procedure",
    "process",
    "runbook",
    "playbook",
    "workflow",
    "checklist",
}

# Keywords that indicate vendor / contract management content
_VENDOR_KEYWORDS = {
    "vendor",
    "contract",
    "agreement",
    "nda",
    "msa",
    "sow",
    "renewal",
    "procurement",
}

# Keywords that indicate OKR / goal tracking content
_OKR_KEYWORDS = {
    "okr",
    "objective",
    "key result",
    "goal",
    "target",
    "quarterly goal",
    "kpi",
    "metric",
}

# Combined ops keywords for broad presence check
_OPS_KEYWORDS = (
    _SOP_KEYWORDS
    | _VENDOR_KEYWORDS
    | _OKR_KEYWORDS
    | {"operations", "ops", "process map", "org process"}
)

# Keywords that indicate compliance / security policy content
_COMPLIANCE_KEYWORDS = {
    "soc2",
    "soc 2",
    "gdpr",
    "hipaa",
    "iso 27001",
    "compliance",
    "security policy",
    "data privacy",
    "privacy policy",
    "information security",
}

# Keywords that indicate legal / terms content
_LEGAL_KEYWORDS = {
    "terms of service",
    "terms and conditions",
    "privacy policy",
    "dpa",
    "data processing",
    "legal",
    "liability",
}

# Keywords that indicate business continuity / DR content
_BCP_KEYWORDS = {
    "business continuity",
    "disaster recovery",
    "bcp",
    "dr plan",
    "incident response plan",
    "failover",
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
        "no_ops_artifacts": "CRITICAL",
        "no_sop_docs": "HIGH",
        "no_vendor_docs": "MEDIUM",
        "no_okr_docs": "MEDIUM",
        "no_compliance_docs": "HIGH",
        "no_legal_docs": "HIGH",
        "no_bcp_docs": "LOW",
    }
    return mapping.get(gap_type, "MEDIUM")


def scan_ops_artifacts(root: str) -> list[Finding]:
    """Scan the project for operations artifacts.

    Checks for:
    - Any ops artifacts at all (missing = CRITICAL)
    - Process / SOP documents (missing = HIGH)
    - Vendor / contract management documents (missing = MEDIUM)
    - OKR / goal tracking documents (missing = MEDIUM)
    """
    findings: list[Finding] = []
    files = list(_walk_text_files(root))

    ops_files: list[str] = []
    sop_files: list[str] = []
    vendor_files: list[str] = []
    okr_files: list[str] = []

    for fpath, content in files:
        fname_lower = os.path.basename(fpath).lower()
        combined = fname_lower + " " + content

        if any(kw in combined for kw in _OPS_KEYWORDS):
            ops_files.append(fpath)
        if any(kw in combined for kw in _SOP_KEYWORDS):
            sop_files.append(fpath)
        if any(kw in combined for kw in _VENDOR_KEYWORDS):
            vendor_files.append(fpath)
        if any(kw in combined for kw in _OKR_KEYWORDS):
            okr_files.append(fpath)

    if not ops_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_ops_artifacts"),
                title="No operations artifacts found",
                detail=(
                    "No files containing operations, process, vendor, OKR, SOP, or runbook "
                    "keywords were found. Operations function appears completely undocumented."
                ),
                location=root,
                recommendation=(
                    "Create an ops/ or operations/ directory with at minimum a vendor list, "
                    "top-3 SOPs, and quarterly goals."
                ),
                effort="L",
                id="KEEL-001",
            )
        )

    if not sop_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_sop_docs"),
                title="Missing SOP or process documentation",
                detail=(
                    "No files containing SOP, standard operating procedure, runbook, playbook, "
                    "or workflow keywords were found. Recurring processes are undocumented and "
                    "cannot be delegated or replicated."
                ),
                location=root,
                recommendation=(
                    "Create docs/sops/ with at minimum one SOP for each process that happens "
                    "weekly. Each SOP needs a trigger, steps, owner, and escalation path."
                ),
                effort="M",
                id="KEEL-002",
            )
        )

    if not vendor_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_vendor_docs"),
                title="Missing vendor or contract documentation",
                detail=(
                    "No files containing vendor, contract, agreement, NDA, MSA, or procurement "
                    "keywords were found. Vendor relationships and renewal dates are untracked."
                ),
                location=root,
                recommendation=(
                    "Create docs/vendors.md or a vendor registry with tool name, cost, owner, "
                    "renewal date, and business criticality for each vendor."
                ),
                effort="S",
                id="KEEL-003",
            )
        )

    if not okr_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_okr_docs"),
                title="Missing OKR or goal tracking documentation",
                detail=(
                    "No files containing OKR, objective, key result, quarterly goal, or KPI "
                    "keywords were found. Team goals are informal or undocumented."
                ),
                location=root,
                recommendation=(
                    "Create docs/okrs.md with company objectives, team key results, owners, "
                    "and targets for the current quarter."
                ),
                effort="M",
                id="KEEL-004",
            )
        )

    return findings


def scan_compliance_artifacts(root: str) -> list[Finding]:
    """Scan the project for compliance and legal artifacts.

    Checks for:
    - Compliance / security policy documents (missing = HIGH)
    - Legal docs / terms (missing = HIGH)
    - Business continuity / DR plan (missing = LOW)
    """
    findings: list[Finding] = []
    files = list(_walk_text_files(root))

    compliance_files: list[str] = []
    legal_files: list[str] = []
    bcp_files: list[str] = []

    for fpath, content in files:
        fname_lower = os.path.basename(fpath).lower()
        combined = fname_lower + " " + content

        if any(kw in combined for kw in _COMPLIANCE_KEYWORDS):
            compliance_files.append(fpath)
        if any(kw in combined for kw in _LEGAL_KEYWORDS):
            legal_files.append(fpath)
        if any(kw in combined for kw in _BCP_KEYWORDS):
            bcp_files.append(fpath)

    if not compliance_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_compliance_docs"),
                title="Missing compliance or security policy documentation",
                detail=(
                    "No files containing SOC2, GDPR, HIPAA, ISO 27001, compliance, or "
                    "security policy keywords were found. Compliance posture is undocumented "
                    "and cannot be demonstrated to enterprise customers or auditors."
                ),
                location=root,
                recommendation=(
                    "Create docs/compliance/ with an information security policy and a "
                    "compliance gap analysis against the most relevant framework "
                    "(SOC2 for SaaS, GDPR if EU data)."
                ),
                effort="L",
                id="KEEL-005",
            )
        )

    if not legal_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_legal_docs"),
                title="Missing legal or terms documentation",
                detail=(
                    "No files containing terms of service, privacy policy, DPA, or legal "
                    "keywords were found. Legal exposure is unmanaged and enterprise deals "
                    "will stall without these documents."
                ),
                location=root,
                recommendation=(
                    "Create docs/legal/ with terms of service, privacy policy, and a "
                    "standard NDA template. These are table-stakes for B2B sales."
                ),
                effort="M",
                id="KEEL-006",
            )
        )

    if not bcp_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_bcp_docs"),
                title="Missing business continuity or disaster recovery plan",
                detail=(
                    "No files containing business continuity, disaster recovery, BCP, "
                    "or incident response plan keywords were found. Recovery procedures "
                    "are undocumented."
                ),
                location=root,
                recommendation=(
                    "Create docs/bcp.md or docs/dr-plan.md with recovery objectives (RTO/RPO), "
                    "failure scenarios, and response steps for critical system outages."
                ),
                effort="M",
                id="KEEL-007",
            )
        )

    return findings
