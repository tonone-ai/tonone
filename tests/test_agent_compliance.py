"""
Agent definition compliance tests.

Validates that every agent in agents/*.md follows the team's behavioral contract:
frontmatter schema, model selection, communication protocol, identity line,
scope boundaries, and formatting rules from docs/output-kit.md.

These tests catch prompt drift — when agent definitions silently lose required
sections or deviate from the standard after edits.
"""

import re
from pathlib import Path

import yaml

REPO = Path(__file__).parent.parent
AGENTS_DIR = REPO / "agents"
AGENT_FILES = sorted(AGENTS_DIR.glob("*.md"))
AGENT_NAMES = [f.stem for f in AGENT_FILES]

# Valid agents from team/ directory (source of truth for the roster)
TEAM_AGENTS = sorted(
    [
        d.name
        for d in (REPO / "team").iterdir()
        if d.is_dir() and (d / ".claude-plugin" / "plugin.json").exists()
    ]
)

# Only Apex gets opus — everyone else must be sonnet
OPUS_AGENTS = {"apex"}

# Approved severity indicators (output-kit.md)
APPROVED_SEVERITY = {"■ CRITICAL", "▲ WARNING", "● INFO"}


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


# ---------------------------------------------------------------------------
# Frontmatter schema
# ---------------------------------------------------------------------------


def test_all_agents_have_frontmatter():
    """Every agent definition must start with YAML frontmatter (---)."""
    for f in AGENT_FILES:
        text = f.read_text()
        assert text.startswith("---"), f"agents/{f.name}: missing YAML frontmatter"


def test_frontmatter_required_fields():
    """Frontmatter must contain name, description, and model."""
    for f in AGENT_FILES:
        fm, _ = _parse_frontmatter(f)
        for field in ("name", "description", "model"):
            assert field in fm, f"agents/{f.name}: frontmatter missing '{field}'"


def test_frontmatter_name_matches_filename():
    """Frontmatter 'name' must match the filename (sans .md)."""
    for f in AGENT_FILES:
        fm, _ = _parse_frontmatter(f)
        if "name" not in fm:
            continue
        assert (
            fm["name"] == f.stem
        ), f"agents/{f.name}: frontmatter name '{fm['name']}' != filename '{f.stem}'"


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------


def test_model_selection():
    """
    Only Apex uses opus (orchestration needs). All specialists use sonnet.
    Wrong model = wasted cost (opus on a specialist) or degraded orchestration
    (sonnet on the lead).
    """
    for f in AGENT_FILES:
        fm, _ = _parse_frontmatter(f)
        model = fm.get("model")
        if not model:
            continue
        if f.stem in OPUS_AGENTS:
            assert (
                model == "opus"
            ), f"agents/{f.name}: lead agent must use 'opus', got '{model}'"
        else:
            assert (
                model == "sonnet"
            ), f"agents/{f.name}: specialist must use 'sonnet', got '{model}'"


# ---------------------------------------------------------------------------
# Required sections
# ---------------------------------------------------------------------------


def test_communication_section_exists():
    """
    Every agent must have a ## Communication section that enforces the
    output-kit protocol. Missing = no output format guarantee.
    """
    for f in AGENT_FILES:
        _, body = _parse_frontmatter(f)
        assert re.search(
            r"^## Communication", body, re.MULTILINE
        ), f"agents/{f.name}: missing '## Communication' section"


def test_communication_references_output_kit():
    """
    The Communication section must reference output-kit.md — the contract
    that binds all agent output to the 40-line rule and severity indicators.
    """
    for f in AGENT_FILES:
        _, body = _parse_frontmatter(f)
        # Find the Communication section content (up to next ##)
        match = re.search(
            r"^## Communication\n(.*?)(?=^## |\Z)", body, re.MULTILINE | re.DOTALL
        )
        if not match:
            continue  # caught by test_communication_section_exists
        section = match.group(1)
        assert (
            "output-kit" in section
        ), f"agents/{f.name}: ## Communication does not reference output-kit"


def test_identity_line_exists():
    """
    Every agent must open with 'You are <Name> —' identity line after frontmatter.
    This establishes the persona for the LLM. Missing = the agent has no identity.
    """
    for f in AGENT_FILES:
        _, body = _parse_frontmatter(f)
        # First non-empty line after frontmatter
        lines = [l for l in body.strip().splitlines() if l.strip()]
        assert lines, f"agents/{f.name}: empty body"
        first_line = lines[0]
        expected_name = f.stem.capitalize()
        assert first_line.startswith("You are"), (
            f"agents/{f.name}: first line must start with 'You are', "
            f"got: '{first_line[:60]}...'"
        )
        # Agent name should appear in the identity line
        assert (
            expected_name in first_line
        ), f"agents/{f.name}: identity line missing agent name '{expected_name}'"


def test_scope_or_operating_principle():
    """
    Every agent must have either ## Scope or ## Operating Principle (or both).
    These sections define what the agent owns and how it makes decisions.
    Apex and Cortex use Operating Principle without a formal Scope — that's fine.
    """
    for f in AGENT_FILES:
        _, body = _parse_frontmatter(f)
        has_scope = bool(re.search(r"^## Scope", body, re.MULTILINE))
        has_principle = bool(re.search(r"^## Operating Principle", body, re.MULTILINE))
        assert (
            has_scope or has_principle
        ), f"agents/{f.name}: missing both '## Scope' and '## Operating Principle'"


# ---------------------------------------------------------------------------
# Formatting rules (output-kit compliance)
# ---------------------------------------------------------------------------


def test_no_emoji_in_agent_definitions():
    """
    Output-kit forbids emoji. Agent definitions must use box-drawing characters
    and unicode indicators (■ ▲ ● →) instead.
    """
    # Emoji ranges — excludes legitimate unicode symbols (✓ ✗ ✦ ✧ etc.)
    # that are commonly used in technical tables and specs
    emoji_pattern = re.compile(
        "["
        "\U0001f600-\U0001f64f"  # emoticons
        "\U0001f300-\U0001f5ff"  # symbols & pictographs
        "\U0001f680-\U0001f6ff"  # transport & map
        "\U0001f1e0-\U0001f1ff"  # flags
        "\U0001f900-\U0001f9ff"  # supplemental symbols
        "\U0001fa00-\U0001fa6f"  # chess symbols
        "\U0001fa70-\U0001faff"  # symbols extended-A
        "]+",
        re.UNICODE,
    )
    for f in AGENT_FILES:
        text = f.read_text()
        matches = emoji_pattern.findall(text)
        assert (
            not matches
        ), f"agents/{f.name}: contains emoji {matches[:3]} — use box-drawing/unicode indicators"


def test_no_unauthorized_severity_indicators():
    """
    Only three severity indicators are allowed: ■ CRITICAL, ▲ WARNING, ● INFO.
    Custom indicators (e.g., ⚠ WARN, 🔴 ERROR) violate output-kit.
    Agent definitions that reference severity should use the approved set.
    """
    # Pattern catches things like "▲ WARN" (not WARNING) or "■ HIGH" (not CRITICAL)
    severity_pattern = re.compile(r"[■▲●]\s+[A-Z]{2,}")
    for f in AGENT_FILES:
        text = f.read_text()
        found = severity_pattern.findall(text)
        for indicator in found:
            assert indicator.strip() in APPROVED_SEVERITY, (
                f"agents/{f.name}: unauthorized severity indicator '{indicator}' — "
                f"allowed: {APPROVED_SEVERITY}"
            )


# ---------------------------------------------------------------------------
# Collaboration and boundary checks
# ---------------------------------------------------------------------------


def test_collaboration_references_valid_agents():
    """
    If an agent's ## Collaboration section names other agents, those agents
    must actually exist. Referencing a renamed or removed agent = broken handoff.
    """
    valid_names = set(AGENT_NAMES)
    for f in AGENT_FILES:
        _, body = _parse_frontmatter(f)
        match = re.search(
            r"^## Collaboration\n(.*?)(?=^## |\Z)", body, re.MULTILINE | re.DOTALL
        )
        if not match:
            continue
        section = match.group(1).lower()
        # Look for agent names mentioned in the section
        for name in TEAM_AGENTS:
            # Only flag if the name appears as a capitalized proper noun
            # (to avoid false positives on common words)
            cap_name = name.capitalize()
            if cap_name in match.group(1):
                assert name in valid_names, (
                    f"agents/{f.name}: Collaboration references '{cap_name}' "
                    f"but no agents/{name}.md exists"
                )
