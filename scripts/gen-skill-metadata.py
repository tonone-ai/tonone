#!/usr/bin/env python3
"""
Backfill `tags` and `compatibility` frontmatter fields across every SKILL.md
in the repo (team/<agent>/skills/ source + skills/ root mirror, wherever
both exist).

Context: agentskills.io spec lists both as optional; a third-party
marketplace (tonsofskills.com, jeremylongshore) requested them for their
own grading rubric — see GitHub issue #107. `compatibility` is a fixed
string. `tags` are derived from a per-agent domain table plus the skill's
own name suffix, not free-form generation, so the same skill always gets
the same tags regardless of when this runs.

Idempotent: skips any file that already has either field.
"""

import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

COMPATIBILITY = "Designed for Claude Code"
MAX_TAGS = 5  # keeps tag lists scannable in marketplace listings

# agent slug -> 2-3 base domain tags (team + specialty)
AGENT_TAGS = {
    # Engineering
    "apex": ["engineering", "orchestration"],
    "forge": ["engineering", "infrastructure", "cloud"],
    "relay": ["engineering", "devops", "ci-cd"],
    "spine": ["engineering", "backend", "api"],
    "flux": ["engineering", "data", "database"],
    "warden": ["engineering", "security"],
    "vigil": ["engineering", "observability", "reliability"],
    "prism": ["engineering", "frontend"],
    "cortex": ["engineering", "ml", "ai"],
    "touch": ["engineering", "mobile"],
    "volt": ["engineering", "embedded", "iot"],
    "atlas": ["engineering", "documentation"],
    "lens": ["engineering", "analytics", "bi"],
    "proof": ["engineering", "qa", "testing"],
    "pave": ["engineering", "platform", "devex"],
    # Product
    "helm": ["product", "strategy"],
    "echo": ["product", "user-research"],
    "lumen": ["product", "analytics"],
    "draft": ["product", "ux"],
    "form": ["product", "design", "visual"],
    "crest": ["product", "strategy"],
    "pitch": ["product", "marketing"],
    "surge": ["product", "growth"],
    "deal": ["product", "sales", "revenue"],
    "keep": ["product", "customer-success"],
    "ink": ["product", "content", "marketing"],
    "buzz": ["product", "pr", "community"],
    # Operations
    "mint": ["operations", "finance"],
    "folk": ["operations", "people", "hr"],
    "keel": ["operations", "process", "vendor"],
    "brace": ["operations", "support"],
    # Legal
    "brief": ["legal", "contracts"],
    "clause": ["legal", "contracts"],
    "bind": ["legal", "compliance"],
    "frame": ["legal", "governance"],
    "shield": ["legal", "regulatory"],
    "scope": ["legal", "ip", "trademark"],
    "audit": ["legal", "compliance"],
    "cite": ["legal", "research"],
    "lodge": ["legal", "filings"],
    "terms": ["legal", "privacy"],
    # Design
    "hue": ["design", "color"],
    "grid": ["design", "layout"],
    "glyph": ["design", "typography"],
    "move": ["design", "motion"],
    "wire": ["design", "prototyping"],
    "mark": ["design", "brand"],
    "cut": ["design", "illustration"],
    "axe": ["design", "accessibility"],
    "tone": ["design", "tokens"],
    "copy": ["design", "content", "ux-writing"],
    # Data Science
    "cast": ["data-science", "forecasting"],
    "feat": ["data-science", "feature-engineering"],
    "fit": ["data-science", "model-training"],
    "score": ["data-science", "evaluation"],
    "drift": ["data-science", "monitoring"],
    "vect": ["data-science", "embeddings", "vector-search"],
    "tune": ["data-science", "fine-tuning"],
    "plot": ["data-science", "visualization"],
    "clean": ["data-science", "data-quality"],
    "eval": ["data-science", "experimentation"],
    # Security Operations
    "red": ["security", "offensive"],
    "blue": ["security", "defensive"],
    "hunt": ["security", "threat-hunting"],
    "patch": ["security", "vulnerability-management"],
    "chain": ["security", "supply-chain"],
    "sast": ["security", "appsec"],
    "siem": ["security", "detection"],
    "resp": ["security", "incident-response"],
    "zero": ["security", "zero-trust"],
    "phish": ["security", "awareness"],
    # Developer Experience
    "guide": ["devex", "documentation"],
    "sample": ["devex", "code-samples"],
    "mock": ["devex", "api-mocking"],
    "schema": ["devex", "api-schema"],
    "port": ["devex", "sdk"],
    "change": ["devex", "changelog"],
    "onboard": ["devex", "onboarding"],
    "bench": ["devex", "performance"],
    "compat": ["devex", "backwards-compatibility"],
    "gate": ["devex", "api-governance"],
    # Infrastructure Specialist
    "kube": ["infrastructure", "kubernetes"],
    "terra": ["infrastructure", "terraform", "iac"],
    "finop": ["infrastructure", "finops", "cost"],
    "serv": ["infrastructure", "reliability"],
    "edge": ["infrastructure", "edge-computing", "cdn"],
    "cache": ["infrastructure", "caching"],
    "queue": ["infrastructure", "messaging"],
    "mesh": ["infrastructure", "service-mesh"],
    "multi": ["infrastructure", "multi-cloud"],
    "chaos": ["infrastructure", "chaos-engineering"],
    # AI Operations
    "deploy": ["ai-ops", "model-serving"],
    "evals": ["ai-ops", "llm-evaluation"],
    "trace": ["ai-ops", "observability"],
    "guard": ["ai-ops", "guardrails"],
    "budget": ["ai-ops", "cost"],
    "token": ["ai-ops", "context-management"],
    "prompt": ["ai-ops", "prompt-engineering"],
    "embed": ["ai-ops", "embeddings"],
    "rank": ["ai-ops", "ranking"],
}

# Cross-agent skills with no single-owner agent (exempt from the agent-prefix
# rule in tests/test_skill_compliance.py's SPECIAL_SKILLS) — the slug-based
# lookup above can't tag these, so they get an explicit fallback.
SPECIAL_SKILL_TAGS = {
    "tonone-onboard": ["onboarding", "documentation", "getting-started"],
}

# Directories that can legitimately contain a file named SKILL.md that isn't
# one of this repo's own skills (vendored deps, virtualenvs, caches).
EXCLUDED_DIR_NAMES = {".venv", "node_modules", "__pycache__", ".git"}

FRONTMATTER_RE = re.compile(r"^---\n(.*?\n)---\n", re.DOTALL)
NAME_RE = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)
LICENSE_RE = re.compile(r"^(license:.*)$", re.MULTILINE)


def agent_slug_from_skill_name(skill_name: str) -> str:
    return skill_name.split("-")[0]


def suffix_tags(skill_name: str, agent_slug: str) -> list:
    """Words after the agent prefix, kebab-cased, deduped against base tags."""
    suffix = skill_name[len(agent_slug) :].lstrip("-")
    if not suffix:
        return []
    return [suffix.replace("_", "-")]


def build_tags(skill_name: str) -> list:
    if skill_name in SPECIAL_SKILL_TAGS:
        return SPECIAL_SKILL_TAGS[skill_name][:MAX_TAGS]

    agent_slug = agent_slug_from_skill_name(skill_name)
    if agent_slug not in AGENT_TAGS:
        raise ValueError(
            f"no AGENT_TAGS entry for '{agent_slug}' (skill: {skill_name}) — "
            f"add one to AGENT_TAGS or SPECIAL_SKILL_TAGS before running --apply"
        )
    base = AGENT_TAGS.get(agent_slug, [])
    extra = suffix_tags(skill_name, agent_slug)
    tags = []
    for t in base + extra:
        if t not in tags:
            tags.append(t)
    return tags[:MAX_TAGS]


def find_skill_files():
    for base in (REPO_ROOT / "team", REPO_ROOT / "skills"):
        if not base.exists():
            continue
        for path in base.rglob("SKILL.md"):
            if EXCLUDED_DIR_NAMES.intersection(path.parts):
                continue
            yield path


def _atomic_write(path: Path, text: str):
    """Write via temp-file + os.replace so a crash mid-write can't truncate
    the original file — os.replace is atomic on the same filesystem."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def process(path: Path, dry_run: bool):
    """Returns ("ok", (skill_name, tags)) on success, or (skip_reason, None)."""
    text = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return ("no_frontmatter", None)
    fm = m.group(1)
    if "tags:" in fm or "compatibility:" in fm:
        return ("already_tagged", None)

    name_m = NAME_RE.search(fm)
    if not name_m:
        return ("no_name_field", None)
    skill_name = name_m.group(1)

    tags = build_tags(skill_name)
    tags_line = "tags: [" + ", ".join(tags) + "]"
    compat_line = f"compatibility: {COMPATIBILITY}"

    license_m = LICENSE_RE.search(fm)
    if license_m:
        insert_after = license_m.end()
        new_fm = (
            fm[:insert_after]
            + "\n"
            + compat_line
            + "\n"
            + tags_line
            + fm[insert_after:]
        )
    else:
        new_fm = fm.rstrip("\n") + "\n" + compat_line + "\n" + tags_line + "\n"

    new_text = "---\n" + new_fm + "---\n" + text[m.end() :]

    if not dry_run:
        _atomic_write(path, new_text)
    return ("ok", (skill_name, tags))


def main():
    import sys

    dry_run = "--apply" not in sys.argv
    changed = []
    skip_counts = {"no_frontmatter": 0, "already_tagged": 0, "no_name_field": 0}
    for path in find_skill_files():
        reason, result = process(path, dry_run)
        if reason == "ok":
            changed.append((path, *result))
        else:
            skip_counts[reason] += 1

    print(f"{'[dry-run] ' if dry_run else ''}{len(changed)} files updated")
    skipped_total = sum(skip_counts.values())
    if skipped_total:
        detail = ", ".join(f"{k}={v}" for k, v in skip_counts.items() if v)
        print(f"{skipped_total} files skipped ({detail})")
    if dry_run:
        for path, name, tags in changed[:15]:
            print(f"  {path.relative_to(REPO_ROOT)}  tags={tags}")
        if len(changed) > 15:
            print(f"  ... and {len(changed) - 15} more")
        print("\nRun with --apply to write changes.")


if __name__ == "__main__":
    main()
