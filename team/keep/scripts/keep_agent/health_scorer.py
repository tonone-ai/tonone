"""Customer success health artifact scanner for the keep agent."""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, ROOT)
from team.shared.report_schema import Finding

_ONBOARDING_KEYWORDS = {
    "onboarding",
    "onboard",
    "getting started",
    "quickstart",
    "setup guide",
    "activation",
    "first run",
    "welcome",
    "time-to-value",
    "ttv",
}
_TTV_KEYWORDS = {"time-to-value", "ttv", "time to value", "first value", "aha moment"}

_HEALTH_SCORE_KEYWORDS = {
    "health score",
    "health scoring",
    "account health",
    "customer health",
    "csat",
    "nps",
    "usage score",
    "engagement score",
}
_CHURN_KEYWORDS = {
    "churn",
    "churn playbook",
    "at-risk",
    "at risk",
    "cancellation",
    "save playbook",
    "win-back",
    "winback",
    "retention playbook",
}
_LIFECYCLE_KEYWORDS = {
    "lifecycle",
    "lifecycle email",
    "nurture",
    "drip",
    "check-in email",
    "renewal",
    "upsell",
    "expansion",
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


def _severity_for_cs_gap(gap_type: str) -> str:
    """Map a CS gap type to a severity string."""
    mapping = {
        "no_onboarding_sequence": "HIGH",
        "no_ttv_definition": "MEDIUM",
        "no_health_score": "HIGH",
        "no_churn_playbook": "HIGH",
        "no_lifecycle_emails": "MEDIUM",
    }
    return mapping.get(gap_type, "MEDIUM")


def scan_onboarding_coverage(root: str) -> list[Finding]:
    """Scan for onboarding docs and time-to-value definition.

    Checks for:
    - Onboarding sequence / flow document (missing = HIGH)
    - Time-to-value definition (missing = MEDIUM)
    """
    findings: list[Finding] = []
    files = list(_walk_text_files(root))

    onboarding_files: list[str] = []
    ttv_files: list[str] = []

    for fpath, content in files:
        fname_lower = os.path.basename(fpath).lower()
        combined = fname_lower + " " + content

        if any(kw in combined for kw in _ONBOARDING_KEYWORDS):
            onboarding_files.append(fpath)
        if any(kw in combined for kw in _TTV_KEYWORDS):
            ttv_files.append(fpath)

    if not onboarding_files:
        findings.append(
            Finding(
                severity=_severity_for_cs_gap("no_onboarding_sequence"),
                title="Missing onboarding sequence",
                detail=(
                    "No onboarding flow, getting-started guide, or activation checklist found. "
                    "New customers lack a structured path to first value."
                ),
                location=root,
                recommendation=(
                    "Create docs/onboarding.md with step-by-step setup, "
                    "milestone checkpoints, and owner assignments."
                ),
                effort="M",
                id="KEEP-001",
            )
        )

    if not ttv_files:
        findings.append(
            Finding(
                severity=_severity_for_cs_gap("no_ttv_definition"),
                title="Missing time-to-value (TTV) definition",
                detail=(
                    "No explicit time-to-value or 'aha moment' definition found. "
                    "Without a TTV target, onboarding success cannot be measured."
                ),
                location=root,
                recommendation=(
                    "Define the primary activation event and target TTV in "
                    "docs/onboarding.md or a dedicated metrics doc."
                ),
                effort="S",
                id="KEEP-002",
            )
        )

    return findings


def scan_churn_signals(root: str) -> list[Finding]:
    """Scan for health score model, churn triggers, and lifecycle emails.

    Checks for:
    - Health score definition (missing = HIGH)
    - Churn / save playbook (missing = HIGH)
    - Lifecycle email / renewal motion (missing = MEDIUM)
    """
    findings: list[Finding] = []
    files = list(_walk_text_files(root))

    health_files: list[str] = []
    churn_files: list[str] = []
    lifecycle_files: list[str] = []

    for fpath, content in files:
        fname_lower = os.path.basename(fpath).lower()
        combined = fname_lower + " " + content

        if any(kw in combined for kw in _HEALTH_SCORE_KEYWORDS):
            health_files.append(fpath)
        if any(kw in combined for kw in _CHURN_KEYWORDS):
            churn_files.append(fpath)
        if any(kw in combined for kw in _LIFECYCLE_KEYWORDS):
            lifecycle_files.append(fpath)

    if not health_files:
        findings.append(
            Finding(
                severity=_severity_for_cs_gap("no_health_score"),
                title="Missing customer health score definition",
                detail=(
                    "No health scoring model or account health definition found. "
                    "CSMs cannot identify at-risk accounts without measurable signals."
                ),
                location=root,
                recommendation=(
                    "Create docs/health-score.md defining input signals, weights, "
                    "thresholds (red/yellow/green), and intervention triggers."
                ),
                effort="M",
                id="KEEP-003",
            )
        )

    if not churn_files:
        findings.append(
            Finding(
                severity=_severity_for_cs_gap("no_churn_playbook"),
                title="Missing churn / save playbook",
                detail=(
                    "No churn playbook, at-risk runbook, or cancellation-save process found. "
                    "Revenue is at risk when accounts go dark or request cancellation."
                ),
                location=root,
                recommendation=(
                    "Create docs/churn-playbook.md with trigger criteria, "
                    "escalation path, save offers, and win-back sequences."
                ),
                effort="M",
                id="KEEP-004",
            )
        )

    if not lifecycle_files:
        findings.append(
            Finding(
                severity=_severity_for_cs_gap("no_lifecycle_emails"),
                title="Missing lifecycle email or renewal motion",
                detail=(
                    "No lifecycle emails, renewal cadence, or expansion motion found. "
                    "Proactive outreach is absent; renewal risk is unmanaged."
                ),
                location=root,
                recommendation=(
                    "Define a lifecycle email sequence covering 30/60/90-day check-ins, "
                    "renewal reminders, and upsell triggers."
                ),
                effort="M",
                id="KEEP-005",
            )
        )

    return findings
