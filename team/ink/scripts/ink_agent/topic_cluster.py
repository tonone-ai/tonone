"""Content artifact scanner for the ink agent."""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, ROOT)
from team.shared.report_schema import Finding

_PILLAR_KEYWORDS = {
    "pillar",
    "pillar page",
    "hub page",
    "content hub",
    "ultimate guide",
    "complete guide",
    "definitive guide",
}
_KEYWORD_STRATEGY_KEYWORDS = {
    "keyword",
    "keyword research",
    "keyword strategy",
    "seo strategy",
    "search intent",
    "kw research",
    "target keyword",
}
_INTERNAL_LINK_KEYWORDS = {
    "internal link",
    "internal linking",
    "link cluster",
    "topic cluster",
}

# Directories commonly containing blog/content files
_CONTENT_DIRS = {"blog", "posts", "content", "articles", "writing", "docs"}


def _read_file_lower(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read().lower()
    except OSError:
        return ""


def _walk_text_files(root: str):
    """Yield (path, lowercased_content) for text files under root."""
    text_exts = {".md", ".txt", ".rst", ".html", ".htm"}
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


def _severity_for_content_gap(gap_type: str) -> str:
    """Map a content gap type to a severity string."""
    mapping = {
        "no_content": "CRITICAL",
        "few_posts": "HIGH",
        "no_pillar_page": "MEDIUM",
        "no_internal_linking": "MEDIUM",
        "no_keyword_strategy": "HIGH",
        "no_sitemap": "MEDIUM",
    }
    return mapping.get(gap_type, "MEDIUM")


def scan_content_coverage(root: str) -> list[Finding]:
    """Scan for blog/content files, pillar pages, and internal linking.

    Checks for:
    - No content files at all (CRITICAL)
    - Fewer than 5 posts (HIGH)
    - No pillar page (MEDIUM)
    - No internal linking strategy doc (MEDIUM)
    """
    findings: list[Finding] = []
    all_files = list(_walk_text_files(root))

    # Collect content files: anything inside content-like dirs OR markdown files generally
    content_files: list[str] = []
    for fpath, _ in all_files:
        parts = fpath.replace("\\", "/").split("/")
        in_content_dir = any(p.lower() in _CONTENT_DIRS for p in parts)
        is_md = fpath.endswith(".md")
        if in_content_dir or is_md:
            content_files.append(fpath)

    pillar_files: list[str] = []
    internal_link_files: list[str] = []

    for fpath, content in all_files:
        fname_lower = os.path.basename(fpath).lower()
        combined = fname_lower + " " + content

        if any(kw in combined for kw in _PILLAR_KEYWORDS):
            pillar_files.append(fpath)
        if any(kw in combined for kw in _INTERNAL_LINK_KEYWORDS):
            internal_link_files.append(fpath)

    post_count = len(content_files)

    if post_count == 0:
        findings.append(
            Finding(
                severity=_severity_for_content_gap("no_content"),
                title="No content files found",
                detail=(
                    "No blog posts, articles, or markdown content files detected. "
                    "Content marketing motion is entirely absent."
                ),
                location=root,
                recommendation=(
                    "Create a blog/ or content/ directory and publish at least "
                    "3-5 foundational posts targeting high-intent keywords."
                ),
                effort="L",
                id="INK-001",
            )
        )
    elif post_count < 5:
        findings.append(
            Finding(
                severity=_severity_for_content_gap("few_posts"),
                title=f"Thin content library ({post_count} post(s) found)",
                detail=(
                    f"Only {post_count} content file(s) found. "
                    "A library of fewer than 5 posts provides minimal SEO surface area "
                    "and limited organic acquisition potential."
                ),
                location=root,
                recommendation=(
                    "Publish at least 5 posts before investing in distribution. "
                    "Prioritize topics targeting bottom-of-funnel search intent."
                ),
                effort="L",
                id="INK-002",
            )
        )

    if not pillar_files:
        findings.append(
            Finding(
                severity=_severity_for_content_gap("no_pillar_page"),
                title="Missing pillar page",
                detail=(
                    "No pillar page, content hub, or definitive guide found. "
                    "Without a pillar, topic authority and internal link equity are fragmented."
                ),
                location=root,
                recommendation=(
                    "Create one comprehensive pillar page per core topic cluster "
                    "and link all cluster posts back to it."
                ),
                effort="M",
                id="INK-003",
            )
        )

    if not internal_link_files:
        findings.append(
            Finding(
                severity=_severity_for_content_gap("no_internal_linking"),
                title="No internal linking strategy documented",
                detail=(
                    "No internal linking guide or topic-cluster map found. "
                    "Unlinked content receives reduced crawl priority and link equity."
                ),
                location=root,
                recommendation=(
                    "Document a topic cluster map and internal linking rules "
                    "in docs/content-strategy.md."
                ),
                effort="S",
                id="INK-004",
            )
        )

    return findings


def scan_seo_signals(root: str) -> list[Finding]:
    """Scan for keyword research docs and sitemap.xml.

    Checks for:
    - Keyword strategy / research document (missing = HIGH)
    - sitemap.xml presence (missing = MEDIUM)
    """
    findings: list[Finding] = []
    all_files = list(_walk_text_files(root))

    keyword_files: list[str] = []
    sitemap_found = False

    for fpath, content in all_files:
        fname_lower = os.path.basename(fpath).lower()
        combined = fname_lower + " " + content

        if any(kw in combined for kw in _KEYWORD_STRATEGY_KEYWORDS):
            keyword_files.append(fpath)

        if fname_lower == "sitemap.xml":
            sitemap_found = True

    # Also check for sitemap.xml by name outside the text walk
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        if "sitemap.xml" in filenames:
            sitemap_found = True
            break

    if not keyword_files:
        findings.append(
            Finding(
                severity=_severity_for_content_gap("no_keyword_strategy"),
                title="Missing keyword research / SEO strategy document",
                detail=(
                    "No keyword research doc, keyword list, or SEO strategy found. "
                    "Content is being produced without validated search demand targeting."
                ),
                location=root,
                recommendation=(
                    "Create docs/seo-strategy.md with target keyword clusters, "
                    "monthly search volume estimates, and content assignments."
                ),
                effort="M",
                id="INK-005",
            )
        )

    if not sitemap_found:
        findings.append(
            Finding(
                severity=_severity_for_content_gap("no_sitemap"),
                title="No sitemap.xml found",
                detail=(
                    "sitemap.xml was not detected. Search engines may miss new content "
                    "or crawl it more slowly without an explicit sitemap."
                ),
                location=root,
                recommendation=(
                    "Generate a sitemap.xml and submit it to Google Search Console "
                    "and Bing Webmaster Tools."
                ),
                effort="S",
                id="INK-006",
            )
        )

    return findings
