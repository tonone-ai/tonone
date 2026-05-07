"""Support operation artifact scanner for the brace agent."""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, ROOT)
from team.shared.report_schema import Finding

# Keywords that indicate support / helpdesk content
_SUPPORT_KEYWORDS = {
    "support",
    "ticket",
    "helpdesk",
    "help desk",
    "customer support",
    "sla",
    "response time",
    "resolution time",
}

_SLA_KEYWORDS = {
    "sla",
    "service level",
    "response time",
    "resolution time",
    "first response",
    "time to resolve",
    "support tier",
}

_KB_KEYWORDS = {
    "knowledge base",
    "faq",
    "frequently asked",
    "help docs",
    "help center",
    "documentation",
    "how to",
    "troubleshooting",
}

_ESCALATION_KEYWORDS = {
    "escalation",
    "escalate",
    "tier 1",
    "tier 2",
    "tier 3",
    "l1",
    "l2",
    "l3",
    "handoff",
    "engineering escalation",
}

_CSAT_KEYWORDS = {
    "csat",
    "customer satisfaction",
    "nps",
    "net promoter",
    "satisfaction score",
    "survey",
    "rating",
}

_BUG_TRIAGE_KEYWORDS = {
    "bug report",
    "bug triage",
    "engineering handoff",
    "defect",
    "issue tracking",
    "jira",
    "linear",
    "github issue",
}

_PLAYBOOK_KEYWORDS = {
    "playbook",
    "runbook",
    "support guide",
    "support process",
    "agent guide",
    "rep guide",
    "response template",
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
        "no_support_artifacts": "CRITICAL",
        "no_sla": "HIGH",
        "no_kb": "HIGH",
        "no_escalation_path": "MEDIUM",
        "no_csat": "HIGH",
        "no_bug_triage": "MEDIUM",
        "no_support_playbook": "MEDIUM",
    }
    return mapping.get(gap_type, "MEDIUM")


def scan_support_artifacts(root: str) -> list[Finding]:
    """Scan the project for support operation artifacts.

    Checks for:
    - Any support/helpdesk artifacts at all (missing = CRITICAL)
    - SLA / response time docs (missing = HIGH)
    - Knowledge base / FAQ docs (missing = HIGH)
    - Escalation path docs (missing = MEDIUM)
    """
    findings: list[Finding] = []
    files = list(_walk_text_files(root))

    support_files: list[str] = []
    sla_files: list[str] = []
    kb_files: list[str] = []
    escalation_files: list[str] = []

    for fpath, content in files:
        fname_lower = os.path.basename(fpath).lower()
        combined = fname_lower + " " + content

        if any(kw in combined for kw in _SUPPORT_KEYWORDS):
            support_files.append(fpath)
        if any(kw in combined for kw in _SLA_KEYWORDS):
            sla_files.append(fpath)
        if any(kw in combined for kw in _KB_KEYWORDS):
            kb_files.append(fpath)
        if any(kw in combined for kw in _ESCALATION_KEYWORDS):
            escalation_files.append(fpath)

    if not support_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_support_artifacts"),
                title="No support or helpdesk artifacts found",
                detail=(
                    "No files containing support, ticket, helpdesk, SLA, or response time "
                    "keywords were found. Support operation appears completely absent."
                ),
                location=root,
                recommendation=(
                    "Create a support/ or helpdesk/ directory with ticket workflow, "
                    "SLA definitions, and knowledge base structure."
                ),
                effort="L",
                id="BRACE-001",
            )
        )

    if not sla_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_sla"),
                title="Missing SLA or response time documentation",
                detail=(
                    "No file containing SLA, service level agreement, response time, "
                    "or resolution time targets was found. Without defined SLAs, "
                    "support commitments are undefined and unmeasurable."
                ),
                location=root,
                recommendation=(
                    "Create docs/sla.md defining response time and resolution time "
                    "targets per tier and severity level."
                ),
                effort="M",
                id="BRACE-002",
            )
        )

    if not kb_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_kb"),
                title="Missing knowledge base or FAQ documentation",
                detail=(
                    "No knowledge base, FAQ, help docs, or help center content was found. "
                    "Without self-serve docs, all support volume requires human handling."
                ),
                location=root,
                recommendation=(
                    "Create a docs/help/ or knowledge-base/ directory with FAQ articles "
                    "grounded in the top support ticket categories."
                ),
                effort="L",
                id="BRACE-003",
            )
        )

    if not escalation_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_escalation_path"),
                title="Missing escalation path documentation",
                detail=(
                    "No escalation path, tier structure, or handoff process was found. "
                    "Without defined escalation criteria, issues route inconsistently "
                    "and engineering receives undifferentiated support requests."
                ),
                location=root,
                recommendation=(
                    "Create docs/escalation.md defining Tier 1, Tier 2, and engineering "
                    "escalation criteria with named owners and handoff templates."
                ),
                effort="M",
                id="BRACE-004",
            )
        )

    return findings


def scan_support_metrics(root: str) -> list[Finding]:
    """Scan for support metrics and quality artifacts.

    Checks for:
    - CSAT / customer satisfaction tracking (missing = HIGH)
    - Bug triage / engineering handoff process (missing = MEDIUM)
    - Support playbook / runbook (missing = MEDIUM)
    """
    findings: list[Finding] = []
    files = list(_walk_text_files(root))

    csat_files: list[str] = []
    bug_triage_files: list[str] = []
    playbook_files: list[str] = []

    for fpath, content in files:
        fname_lower = os.path.basename(fpath).lower()
        combined = fname_lower + " " + content

        if any(kw in combined for kw in _CSAT_KEYWORDS):
            csat_files.append(fpath)
        if any(kw in combined for kw in _BUG_TRIAGE_KEYWORDS):
            bug_triage_files.append(fpath)
        if any(kw in combined for kw in _PLAYBOOK_KEYWORDS):
            playbook_files.append(fpath)

    if not csat_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_csat"),
                title="Missing CSAT or customer satisfaction tracking",
                detail=(
                    "No CSAT, NPS, or customer satisfaction tracking was found. "
                    "Without satisfaction measurement, support quality is invisible "
                    "and degradation goes undetected."
                ),
                location=root,
                recommendation=(
                    "Implement post-resolution CSAT surveys (target: 4.2/5.0+) "
                    "and create docs/csat-process.md defining the measurement methodology."
                ),
                effort="M",
                id="BRACE-005",
            )
        )

    if not bug_triage_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_bug_triage"),
                title="Missing bug triage or engineering handoff process",
                detail=(
                    "No bug triage process, engineering handoff template, or issue tracking "
                    "integration was found. Without a defined handoff format, bug escalations "
                    "lack reproduction steps, environment context, and customer impact."
                ),
                location=root,
                recommendation=(
                    "Create docs/bug-triage.md with an engineering handoff template "
                    "covering reproduction steps, environment, customer impact, and urgency."
                ),
                effort="S",
                id="BRACE-006",
            )
        )

    if not playbook_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_support_playbook"),
                title="Missing support playbook or response templates",
                detail=(
                    "No support playbook, runbook, or response template collection was found. "
                    "Without standardized responses, support quality varies by rep "
                    "and common issues get inconsistent resolutions."
                ),
                location=root,
                recommendation=(
                    "Create docs/support-playbook.md with response templates for the "
                    "top 10 ticket types, tone guide, and per-issue runbooks."
                ),
                effort="M",
                id="BRACE-007",
            )
        )

    return findings
