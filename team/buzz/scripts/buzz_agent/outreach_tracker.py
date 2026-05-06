"""PR and community artifact scanner for the buzz agent."""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, ROOT)
from team.shared.report_schema import Finding

_PRESS_KIT_KEYWORDS = {
    "press kit",
    "press pack",
    "media kit",
    "brand assets",
    "press assets",
    "logos",
    "boilerplate",
    "company overview",
    "fact sheet",
}
_MEDIA_LIST_KEYWORDS = {
    "media list",
    "press list",
    "journalist list",
    "reporter list",
    "outlet list",
    "contact list",
    "media contacts",
}
_PITCH_TEMPLATE_KEYWORDS = {
    "pitch template",
    "pitch email",
    "press pitch",
    "media pitch",
    "story angle",
    "press release template",
}
_CONTRIBUTOR_GUIDE_KEYWORDS = {
    "contributing",
    "contributor",
    "contributor guide",
    "how to contribute",
    "contributing.md",
    "pull request guide",
}
_COMMUNITY_PLATFORM_KEYWORDS = {
    "discord",
    "slack community",
    "slack workspace",
    "community forum",
    "community platform",
    "github discussions",
    "forum",
}
_COMMUNITY_HEALTH_KEYWORDS = {
    "community",
    "community health",
    "code of conduct",
    "coc",
    "community guidelines",
    "moderation",
}


def _read_file_lower(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read().lower()
    except OSError:
        return ""


def _walk_text_files(root: str):
    """Yield (path, lowercased_content) for text files under root."""
    text_exts = {
        ".md",
        ".txt",
        ".rst",
        ".yaml",
        ".yml",
        ".json",
        ".toml",
        ".csv",
        ".html",
    }
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


def _severity_for_pr_gap(gap_type: str) -> str:
    """Map a PR/community gap type to a severity string."""
    mapping = {
        "no_press_kit": "HIGH",
        "no_media_list": "MEDIUM",
        "no_pitch_template": "MEDIUM",
        "no_contributor_guide": "MEDIUM",
        "no_community_platform": "HIGH",
        "no_community_docs": "MEDIUM",
    }
    return mapping.get(gap_type, "MEDIUM")


def scan_press_assets(root: str) -> list[Finding]:
    """Scan for press kit, media list, and pitch templates.

    Checks for:
    - Press kit / media kit (missing = HIGH)
    - Media list / journalist contacts (missing = MEDIUM)
    - Pitch template (missing = MEDIUM)
    """
    findings: list[Finding] = []
    files = list(_walk_text_files(root))

    press_kit_files: list[str] = []
    media_list_files: list[str] = []
    pitch_template_files: list[str] = []

    for fpath, content in files:
        fname_lower = os.path.basename(fpath).lower()
        combined = fname_lower + " " + content

        if any(kw in combined for kw in _PRESS_KIT_KEYWORDS):
            press_kit_files.append(fpath)
        if any(kw in combined for kw in _MEDIA_LIST_KEYWORDS):
            media_list_files.append(fpath)
        if any(kw in combined for kw in _PITCH_TEMPLATE_KEYWORDS):
            pitch_template_files.append(fpath)

    if not press_kit_files:
        findings.append(
            Finding(
                severity=_severity_for_pr_gap("no_press_kit"),
                title="Missing press kit / media kit",
                detail=(
                    "No press kit, media kit, or brand asset package found. "
                    "Journalists and partners cannot self-serve company info or logos, "
                    "slowing earned media."
                ),
                location=root,
                recommendation=(
                    "Create a press/ directory with company boilerplate, logo files, "
                    "founding story, key stats, and executive bios."
                ),
                effort="M",
                id="BUZZ-001",
            )
        )

    if not media_list_files:
        findings.append(
            Finding(
                severity=_severity_for_pr_gap("no_media_list"),
                title="Missing media list / journalist contacts",
                detail=(
                    "No media list or journalist contact list found. "
                    "PR outreach cannot be executed without a curated list of relevant contacts."
                ),
                location=root,
                recommendation=(
                    "Build and maintain a media list in docs/media-list.csv "
                    "with journalist name, outlet, beat, and contact info."
                ),
                effort="M",
                id="BUZZ-002",
            )
        )

    if not pitch_template_files:
        findings.append(
            Finding(
                severity=_severity_for_pr_gap("no_pitch_template"),
                title="Missing pitch template",
                detail=(
                    "No press pitch template or story angle doc found. "
                    "Without reusable templates, every outreach starts from scratch."
                ),
                location=root,
                recommendation=(
                    "Create docs/pitch-template.md with subject line formulas, "
                    "hook angles, and a standard pitch structure."
                ),
                effort="S",
                id="BUZZ-003",
            )
        )

    return findings


def scan_community_health(root: str) -> list[Finding]:
    """Scan for community platform definition, contributor guide, and community docs.

    Checks for:
    - Community platform defined (missing = HIGH)
    - Contributor guide (missing = MEDIUM)
    - Community guidelines / code of conduct (missing = MEDIUM)
    """
    findings: list[Finding] = []
    files = list(_walk_text_files(root))

    community_platform_files: list[str] = []
    contributor_files: list[str] = []
    community_health_files: list[str] = []

    for fpath, content in files:
        fname_lower = os.path.basename(fpath).lower()
        combined = fname_lower + " " + content

        if any(kw in combined for kw in _COMMUNITY_PLATFORM_KEYWORDS):
            community_platform_files.append(fpath)
        if any(kw in combined for kw in _CONTRIBUTOR_GUIDE_KEYWORDS):
            contributor_files.append(fpath)
        if any(kw in combined for kw in _COMMUNITY_HEALTH_KEYWORDS):
            community_health_files.append(fpath)

    if not community_platform_files:
        findings.append(
            Finding(
                severity=_severity_for_pr_gap("no_community_platform"),
                title="No community platform defined",
                detail=(
                    "No Discord, Slack workspace, GitHub Discussions, or other community "
                    "platform reference found. Community engagement cannot happen without "
                    "a defined home for users."
                ),
                location=root,
                recommendation=(
                    "Define and document the community platform in docs/community.md. "
                    "Include the invite link, channel structure, and moderation policy."
                ),
                effort="M",
                id="BUZZ-004",
            )
        )

    if not contributor_files:
        findings.append(
            Finding(
                severity=_severity_for_pr_gap("no_contributor_guide"),
                title="Missing contributor guide",
                detail=(
                    "No CONTRIBUTING.md or contributor guide found. "
                    "External contributors cannot participate without clear instructions, "
                    "limiting open-source community growth."
                ),
                location=root,
                recommendation=(
                    "Create CONTRIBUTING.md with setup instructions, PR process, "
                    "coding standards, and a first-issue label strategy."
                ),
                effort="S",
                id="BUZZ-005",
            )
        )

    if not community_health_files:
        findings.append(
            Finding(
                severity=_severity_for_pr_gap("no_community_docs"),
                title="Missing community guidelines / code of conduct",
                detail=(
                    "No code of conduct or community guidelines found. "
                    "Without behavioral norms, community moderation is inconsistent "
                    "and contributor safety is undefined."
                ),
                location=root,
                recommendation=(
                    "Add a CODE_OF_CONDUCT.md (Contributor Covenant is a good baseline) "
                    "and link to it from README and community platform."
                ),
                effort="S",
                id="BUZZ-006",
            )
        )

    return findings
