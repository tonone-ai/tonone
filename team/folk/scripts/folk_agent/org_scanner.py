"""People and org artifact scanner for the folk agent."""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, ROOT)
from team.shared.report_schema import Finding

# Keywords that indicate org design / team structure content
_ORG_KEYWORDS = {
    "org chart",
    "org design",
    "reporting structure",
    "team structure",
    "headcount",
}

# Keywords that indicate job descriptions / open roles
_JD_KEYWORDS = {
    "job description",
    "job req",
    "open role",
    "hiring for",
    "responsibilities",
    "requirements",
    "qualifications",
}

# Keywords that indicate compensation / salary content
_COMP_KEYWORDS = {
    "compensation",
    "salary band",
    "salary range",
    "comp band",
    "equity",
    "stock options",
    "base salary",
}

# Keywords that indicate onboarding content
_ONBOARDING_KEYWORDS = {
    "onboarding",
    "first day",
    "new hire",
    "getting started",
    "employee handbook",
}

# General people / HR keywords (used for FOLK-001 presence check)
_PEOPLE_KEYWORDS = {
    "hiring",
    "hr",
    "people ops",
    "talent",
    "recruiter",
    "interview",
    "offer letter",
    "performance",
}

# Keywords that indicate performance review content
_PERFORMANCE_KEYWORDS = {
    "performance review",
    "performance evaluation",
    "perf review",
    "annual review",
    "okr",
    "goals",
    "kpi",
    "review cycle",
}

# Keywords that indicate career ladder / leveling content
_CAREER_KEYWORDS = {
    "career ladder",
    "leveling",
    "level",
    "l1",
    "l2",
    "ic1",
    "ic2",
    "engineering levels",
    "promotion criteria",
}

# Keywords that indicate culture / values content
_CULTURE_KEYWORDS = {
    "values",
    "culture",
    "principles",
    "mission",
    "company values",
    "team norms",
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
        "no_people_artifacts": "CRITICAL",
        "no_org_chart": "HIGH",
        "no_jds": "HIGH",
        "no_comp_bands": "HIGH",
        "no_onboarding": "MEDIUM",
        "no_performance_review": "HIGH",
        "no_career_ladder": "MEDIUM",
        "no_culture_doc": "LOW",
    }
    return mapping.get(gap_type, "MEDIUM")


def scan_people_artifacts(root: str) -> list[Finding]:
    """Scan the project for people and HR artifacts.

    Checks for:
    - Any files containing people/HR keywords (missing = CRITICAL)
    - Org chart or org design doc (missing = HIGH)
    - Job descriptions / JDs (missing = HIGH)
    - Comp or salary bands (missing = HIGH)
    - Onboarding docs (missing = MEDIUM)
    """
    findings: list[Finding] = []
    files = list(_walk_text_files(root))

    people_files: list[str] = []
    org_files: list[str] = []
    jd_files: list[str] = []
    comp_files: list[str] = []
    onboarding_files: list[str] = []

    for fpath, content in files:
        fname_lower = os.path.basename(fpath).lower()
        combined = fname_lower + " " + content

        if any(kw in combined for kw in _PEOPLE_KEYWORDS):
            people_files.append(fpath)
        if any(kw in combined for kw in _ORG_KEYWORDS):
            org_files.append(fpath)
        if any(kw in combined for kw in _JD_KEYWORDS):
            jd_files.append(fpath)
        if any(kw in combined for kw in _COMP_KEYWORDS):
            comp_files.append(fpath)
        if any(kw in combined for kw in _ONBOARDING_KEYWORDS):
            onboarding_files.append(fpath)

    if not people_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_people_artifacts"),
                title="No people or HR artifacts found",
                detail=(
                    "No files containing hiring, HR, people ops, talent, or interview "
                    "keywords were found. People operations appear completely absent."
                ),
                location=root,
                recommendation=(
                    "Create a people/ or hr/ directory with at minimum: an org chart, "
                    "one job description, and a comp band document."
                ),
                effort="L",
                id="FOLK-001",
            )
        )

    if not org_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_org_chart"),
                title="Missing org chart or org design document",
                detail=(
                    "No file containing org chart, org design, reporting structure, or "
                    "team structure keywords was found. Without a documented org structure, "
                    "reporting relationships and decision rights are undefined."
                ),
                location=root,
                recommendation=(
                    "Create docs/org-chart.md describing reporting lines, team structure, "
                    "and spans of control for the current team."
                ),
                effort="M",
                id="FOLK-002",
            )
        )

    if not jd_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_jds"),
                title="Missing job descriptions or open role definitions",
                detail=(
                    "No file containing job description, open role, responsibilities, or "
                    "qualifications keywords was found. Hiring without documented role "
                    "definitions produces inconsistent interviews and misaligned hires."
                ),
                location=root,
                recommendation=(
                    "Create a jobs/ or hiring/ directory with at least one job description "
                    "per open role, including role outcome, comp band, and success metrics."
                ),
                effort="M",
                id="FOLK-003",
            )
        )

    if not comp_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_comp_bands"),
                title="Missing compensation bands or salary framework",
                detail=(
                    "No file containing compensation, salary band, comp band, or equity "
                    "keywords was found. Without documented comp bands, offers are "
                    "inconsistent and equity grants are arbitrary."
                ),
                location=root,
                recommendation=(
                    "Create docs/comp-bands.md with salary ranges by level and role, "
                    "equity philosophy, and total comp benchmarking methodology."
                ),
                effort="M",
                id="FOLK-004",
            )
        )

    if not onboarding_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_onboarding"),
                title="Missing onboarding documentation",
                detail=(
                    "No file containing onboarding, first day, new hire, or employee "
                    "handbook keywords was found. Without a documented onboarding process, "
                    "new hire time-to-productivity is undefined and manager-dependent."
                ),
                location=root,
                recommendation=(
                    "Create docs/onboarding.md with a 30/60/90-day plan, day 1 checklist, "
                    "and role-specific success milestones."
                ),
                effort="M",
                id="FOLK-005",
            )
        )

    return findings


def scan_performance_culture(root: str) -> list[Finding]:
    """Scan the project for performance and culture artifacts.

    Checks for:
    - Performance review / evaluation docs (missing = HIGH)
    - Career ladder / leveling framework (missing = MEDIUM)
    - Culture docs / values (missing = LOW)
    """
    findings: list[Finding] = []
    files = list(_walk_text_files(root))

    performance_files: list[str] = []
    career_files: list[str] = []
    culture_files: list[str] = []

    for fpath, content in files:
        fname_lower = os.path.basename(fpath).lower()
        combined = fname_lower + " " + content

        if any(kw in combined for kw in _PERFORMANCE_KEYWORDS):
            performance_files.append(fpath)
        if any(kw in combined for kw in _CAREER_KEYWORDS):
            career_files.append(fpath)
        if any(kw in combined for kw in _CULTURE_KEYWORDS):
            culture_files.append(fpath)

    if not performance_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_performance_review"),
                title="Missing performance review or evaluation system",
                detail=(
                    "No file containing performance review, performance evaluation, "
                    "OKR, or review cycle keywords was found. Without a documented "
                    "performance system, feedback is ad hoc and promotion criteria "
                    "are undefined."
                ),
                location=root,
                recommendation=(
                    "Create docs/performance-review.md with review cadence, rating "
                    "scale, calibration process, and manager guidance."
                ),
                effort="M",
                id="FOLK-006",
            )
        )

    if not career_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_career_ladder"),
                title="Missing career ladder or leveling framework",
                detail=(
                    "No file containing career ladder, leveling, or promotion criteria "
                    "keywords was found. Without a leveling framework, employees cannot "
                    "understand their growth path and managers cannot make consistent "
                    "promotion decisions."
                ),
                location=root,
                recommendation=(
                    "Create docs/career-ladder.md with level definitions, "
                    "promotion criteria, and example behaviors per level."
                ),
                effort="M",
                id="FOLK-007",
            )
        )

    if not culture_files:
        findings.append(
            Finding(
                severity=_severity_for_gap("no_culture_doc"),
                title="Missing culture or values documentation",
                detail=(
                    "No file containing values, culture, principles, or team norms "
                    "keywords was found. Without documented culture, new hires calibrate "
                    "to behavior they observe rather than the culture you intend."
                ),
                location=root,
                recommendation=(
                    "Create docs/culture.md with 3-5 company values expressed as "
                    "specific behaviors, team operating norms, and communication protocols."
                ),
                effort="S",
                id="FOLK-008",
            )
        )

    return findings
