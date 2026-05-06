"""
Skill compliance tests.

Validates that every skill in skills/*/SKILL.md follows the team contract:
frontmatter schema, naming convention, output-kit reference, atlas-report
overflow clause, and identity line.

These tests are the primary defense against prompt drift in skills — when a
new skill is added or an existing one is edited without the standard lines.
"""

import re
from pathlib import Path

import yaml

REPO = Path(__file__).parent.parent
SKILLS_DIR = REPO / "skills"
SKILL_DIRS = sorted([d for d in SKILLS_DIR.iterdir() if d.is_dir()])

# Valid agent names (skill prefix must be one of these)
_AGENT_DIRS = [
    d
    for d in (REPO / "team").iterdir()
    if d.is_dir() and (d / ".claude-plugin" / "plugin.json").exists()
]
VALID_AGENTS = sorted(d.name for d in _AGENT_DIRS)

# The exact output-kit integration line that every skill must include
OUTPUT_KIT_REFERENCE = "output-kit"

# The atlas-report overflow clause
ATLAS_REPORT_REFERENCE = "atlas-report"

# Skills whose output is guaranteed short-form (< 40 lines by design).
# These are exempt from the atlas-report overflow clause because they
# can never exceed the CLI budget.
SHORT_FORM_SKILLS = {"apex-status"}

# Root-level cross-agent skills — not tied to any single agent in team/.
# Exempt from the agent-prefix rule and from output-kit/atlas-report refs
# because they do not produce structured CLI output.
SPECIAL_SKILLS = {"tonone-onboard", "contribute"}

# Agent entry-point skills — single-word names (/apex, /helm, /forge, etc.).
# These are intake routers: the user hands the agent a task and the skill
# routes internally to the right sub-skill. They follow different naming
# rules (no agent-action hyphen required) and different output rules
# (they delegate output to the sub-skill, never produce CLI output directly).
AGENT_ENTRY_SKILLS = {d.name for d in _AGENT_DIRS}

# Known severity indicator violations — real drift, tracked for cleanup.
# Remove entries as they get fixed in the skill definitions.
KNOWN_SEVERITY_DRIFT = {
    "draft-flow",  # ▲ FRICTION (should be ▲ WARNING)
    "echo-interview",  # ▲ HIGH, ● MEDIUM (should be ▲ WARNING, ● INFO)
    "echo-jobs",  # ▲ HIGH, ● MEDIUM
    "lumen-funnel",  # ▲ HIGH, ● MEDIUM
}

# Known emoji violations — real drift, tracked for cleanup.
KNOWN_EMOJI_DRIFT = {
    "atlas-map",  # emoji in Mermaid diagram templates
    "relay-ship",  # 🤖 in attribution signature
}


def _parse_frontmatter(path: Path) -> tuple[dict, str]:
    """Extract YAML frontmatter and body from a markdown file."""
    text = path.read_text()
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm = yaml.safe_load(parts[1]) or {}
    body = parts[2]
    return fm, body


def _skill_files() -> list[tuple[str, Path]]:
    """Return (skill_name, SKILL.md path) pairs for all skills."""
    result = []
    for d in SKILL_DIRS:
        skill_file = d / "SKILL.md"
        if skill_file.exists():
            result.append((d.name, skill_file))
    return result


def _strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks (``` ... ```) from text."""
    return re.sub(r"```[\s\S]*?```", "", text)


# ---------------------------------------------------------------------------
# Frontmatter schema
# ---------------------------------------------------------------------------


def test_all_skills_have_frontmatter():
    """Every skill must start with YAML frontmatter."""
    for name, path in _skill_files():
        text = path.read_text()
        assert text.startswith("---"), f"skills/{name}: missing YAML frontmatter"


def test_frontmatter_required_fields():
    """Frontmatter must contain name and description at minimum."""
    for name, path in _skill_files():
        fm, _ = _parse_frontmatter(path)
        for field in ("name", "description"):
            assert field in fm, f"skills/{name}: frontmatter missing '{field}'"


def test_frontmatter_name_matches_directory():
    """Frontmatter 'name' must match the skill directory name."""
    for name, path in _skill_files():
        fm, _ = _parse_frontmatter(path)
        fm_name = fm.get("name")
        if not fm_name:
            continue
        assert (
            fm_name == name
        ), f"skills/{name}: frontmatter name '{fm_name}' != directory '{name}'"


# ---------------------------------------------------------------------------
# Naming convention
# ---------------------------------------------------------------------------


def test_skill_name_is_kebab_case():
    """Skill names must be kebab-case (lowercase with hyphens, alphanumeric segments).
    Agent entry-point skills (single-word: /apex, /helm, etc.) are exempt —
    they are the agent itself, not an agent-action pair.
    Special cross-agent meta-skills (tonone-onboard, contribute) are also exempt."""
    for name, _ in _skill_files():
        if name in AGENT_ENTRY_SKILLS or name in SPECIAL_SKILLS:
            continue
        assert re.match(
            r"^[a-z][a-z0-9]*(-[a-z][a-z0-9]*)+$", name
        ), f"skills/{name}: name must be kebab-case (agent-action)"


def test_skill_prefix_is_valid_agent():
    """
    Skill name prefix (before first hyphen) must match an agent in team/.
    A skill named 'foo-audit' without a 'foo' agent = orphaned skill.
    """
    for name, _ in _skill_files():
        if name in SPECIAL_SKILLS:
            continue
        prefix = name.split("-")[0]
        assert (
            prefix in VALID_AGENTS
        ), f"skills/{name}: prefix '{prefix}' is not a valid agent in team/"


# ---------------------------------------------------------------------------
# Description quality
# ---------------------------------------------------------------------------


def test_description_has_trigger_phrases():
    """
    Skill description must include quoted trigger phrases that users would say.
    These help Claude Code's skill suggestion system route correctly.
    Pattern: 'Use when asked to "X"' or 'Use when asked about "X"'.
    Agent entry-point skills are exempt — their trigger IS the agent name itself.
    """
    # Match quoted strings in the description
    quote_pattern = re.compile(r'"[^"]{3,}"')
    for name, path in _skill_files():
        if name in AGENT_ENTRY_SKILLS or name in SPECIAL_SKILLS:
            continue
        fm, _ = _parse_frontmatter(path)
        desc = fm.get("description", "")
        if isinstance(desc, str):
            desc_text = desc
        else:
            desc_text = str(desc)
        matches = quote_pattern.findall(desc_text)
        assert len(matches) >= 2, (
            f"skills/{name}: description has {len(matches)} quoted trigger phrase(s), "
            f"need >= 2 for routing accuracy"
        )


# ---------------------------------------------------------------------------
# Output-kit compliance
# ---------------------------------------------------------------------------


def test_skills_reference_output_kit():
    """
    Every skill must reference output-kit.md — the 40-line rule, severity
    indicators, and communication protocol. Without this, output format is
    not guaranteed.
    Agent entry-point skills are exempt — they delegate output to sub-skills.
    """
    for name, path in _skill_files():
        if name in SPECIAL_SKILLS or name in AGENT_ENTRY_SKILLS:
            continue
        text = path.read_text()
        assert OUTPUT_KIT_REFERENCE in text, (
            f"skills/{name}: does not reference 'output-kit' — "
            f"add the standard integration line from docs/output-kit.md § Skill Integration"
        )


def test_skills_reference_atlas_report():
    """
    Every skill must include the atlas-report overflow clause. This ensures
    findings exceeding the 40-line CLI budget are routed to an HTML report
    instead of dumped to the terminal. Short-form skills and agent entry-point
    skills are exempt (entry skills delegate output to the sub-skill they invoke).
    """
    for name, path in _skill_files():
        if (
            name in SHORT_FORM_SKILLS
            or name in SPECIAL_SKILLS
            or name in AGENT_ENTRY_SKILLS
        ):
            continue
        text = path.read_text()
        assert ATLAS_REPORT_REFERENCE in text, (
            f"skills/{name}: does not reference 'atlas-report' — "
            f"add the overflow clause for > 40-line output"
        )


# ---------------------------------------------------------------------------
# Identity and workflow structure
# ---------------------------------------------------------------------------


def test_skills_have_identity_or_title():
    """
    Skills must establish context via either:
    1. Identity line: 'You are <AgentName> —' (workflow skills)
    2. Titled header: '# <skill-name>' (reference/pattern skills)

    Without one of these, the LLM has no role context when executing the skill.
    """
    for name, path in _skill_files():
        if name in SPECIAL_SKILLS:
            continue
        text = path.read_text()
        prefix = name.split("-")[0].capitalize()
        has_identity = f"You are {prefix}" in text
        has_title = f"# {name}" in text
        assert has_identity or has_title, (
            f"skills/{name}: missing both identity line 'You are {prefix}' "
            f"and title header '# {name}'"
        )


def test_skills_have_structured_workflow():
    """
    Skills must have a structured workflow with at least 2 steps.
    Accepted formats:
    - ### Step N: ... (standard workflow skills)
    - N. **bold text** (numbered list skills)
    - ## Phase N: ... (multi-phase skills)
    - ## Workflow with numbered items (reference skills)
    Agent entry-point skills are exempt — their workflow is a single routing
    decision expressed as a lookup table, not a multi-step process.
    """
    # Patterns that indicate structured workflow steps
    step_patterns = [
        re.compile(r"^#{2,3}\s+Step\s+\d+", re.MULTILINE),  # ### Step 0, ### Step 1
        re.compile(r"^\d+\.\s+\*\*", re.MULTILINE),  # 1. **Discovery**
        re.compile(r"^#{2,3}\s+Phase\s+\d+", re.MULTILINE),  # ## Phase 1: ...
    ]
    for name, path in _skill_files():
        if name in AGENT_ENTRY_SKILLS:
            continue
        _, body = _parse_frontmatter(path)
        total_steps = 0
        for pattern in step_patterns:
            total_steps += len(pattern.findall(body))
        assert total_steps >= 2, (
            f"skills/{name}: only {total_steps} structured step(s) found — "
            f"skills must have at least 2 workflow steps "
            f"(### Step N, N. **bold**, or ## Phase N)"
        )


# ---------------------------------------------------------------------------
# Severity indicator compliance
# ---------------------------------------------------------------------------


APPROVED_SEVERITY = {"■ CRITICAL", "▲ WARNING", "● INFO"}


def test_no_unauthorized_severity_in_skills():
    """
    Skills that use severity indicators must use only the approved three:
    ■ CRITICAL, ▲ WARNING, ● INFO. Custom indicators break visual consistency.

    Known violations are tracked in KNOWN_SEVERITY_DRIFT and tested separately
    to avoid blocking CI while still catching new drift.
    """
    severity_pattern = re.compile(r"[■▲●]\s+[A-Z]{2,}")
    new_violations = []
    for name, path in _skill_files():
        if name in KNOWN_SEVERITY_DRIFT:
            continue
        text = path.read_text()
        found = severity_pattern.findall(text)
        for indicator in found:
            if indicator.strip() not in APPROVED_SEVERITY:
                new_violations.append(f"{name}: '{indicator.strip()}'")
    assert (
        not new_violations
    ), f"New unauthorized severity indicator(s): {new_violations}"


def test_known_severity_drift_still_exists():
    """
    Track known severity violations. When a skill is fixed, remove it from
    KNOWN_SEVERITY_DRIFT. This test fails if you fix a skill but forget to
    update the allowlist — keeping the drift list honest.
    """
    severity_pattern = re.compile(r"[■▲●]\s+[A-Z]{2,}")
    for name in KNOWN_SEVERITY_DRIFT:
        path = SKILLS_DIR / name / "SKILL.md"
        if not path.exists():
            continue
        text = path.read_text()
        found = severity_pattern.findall(text)
        has_violation = any(s.strip() not in APPROVED_SEVERITY for s in found)
        assert has_violation, (
            f"skills/{name}: severity drift was fixed — "
            f"remove '{name}' from KNOWN_SEVERITY_DRIFT in this test file"
        )


# ---------------------------------------------------------------------------
# No emoji
# ---------------------------------------------------------------------------


def test_no_emoji_in_skills():
    """
    Skills must not contain emoji outside of fenced code blocks.
    Output-kit requires box-drawing and unicode indicators instead.

    Known violations are tracked in KNOWN_EMOJI_DRIFT.
    """
    emoji_pattern = re.compile(
        "["
        "\U0001f600-\U0001f64f"
        "\U0001f300-\U0001f5ff"
        "\U0001f680-\U0001f6ff"
        "\U0001f1e0-\U0001f1ff"
        "\U0001f900-\U0001f9ff"
        "\U0001fa00-\U0001fa6f"
        "\U0001fa70-\U0001faff"
        "]+",
        re.UNICODE,
    )
    new_violations = []
    for name, path in _skill_files():
        if name in KNOWN_EMOJI_DRIFT:
            continue
        text = _strip_code_blocks(path.read_text())
        matches = emoji_pattern.findall(text)
        if matches:
            new_violations.append(f"{name}: {matches[:3]}")
    assert not new_violations, f"New emoji violation(s): {new_violations}"


def test_known_emoji_drift_still_exists():
    """
    Track known emoji violations. When fixed, remove from KNOWN_EMOJI_DRIFT.
    """
    emoji_pattern = re.compile(
        "["
        "\U0001f600-\U0001f64f"
        "\U0001f300-\U0001f5ff"
        "\U0001f680-\U0001f6ff"
        "\U0001f1e0-\U0001f1ff"
        "\U0001f900-\U0001f9ff"
        "\U0001fa00-\U0001fa6f"
        "\U0001fa70-\U0001faff"
        "]+",
        re.UNICODE,
    )
    for name in KNOWN_EMOJI_DRIFT:
        path = SKILLS_DIR / name / "SKILL.md"
        if not path.exists():
            continue
        text = path.read_text()
        matches = emoji_pattern.findall(text)
        assert matches, (
            f"skills/{name}: emoji drift was fixed — "
            f"remove '{name}' from KNOWN_EMOJI_DRIFT in this test file"
        )
