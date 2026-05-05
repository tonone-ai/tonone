"""Prompt evaluator — static quality checks on prompt files in the codebase."""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from team.shared.report_schema import Finding

# Rough chars-per-token ratio for GPT-style tokenizers (conservative estimate)
_CHARS_PER_TOKEN = 4
_TOKEN_LIMIT_HIGH = 8000   # flag at HIGH above this
_TOKEN_LIMIT_MEDIUM = 4000  # flag at MEDIUM above this

# Patterns that suggest raw user input interpolation (injection risk)
_INJECTION_PATTERNS = [
    re.compile(r"\{user_input\}", re.IGNORECASE),
    re.compile(r"\{user_message\}", re.IGNORECASE),
    re.compile(r"\{user_query\}", re.IGNORECASE),
    re.compile(r"\{user_text\}", re.IGNORECASE),
    re.compile(r"\{input\}", re.IGNORECASE),
    re.compile(r"\{query\}", re.IGNORECASE),
    re.compile(r"\{message\}", re.IGNORECASE),
    re.compile(r"f\".*\{user", re.IGNORECASE),
    re.compile(r"f'.*\{user", re.IGNORECASE),
    re.compile(r"\.format\(.*user", re.IGNORECASE),
    re.compile(r"%s.*user", re.IGNORECASE),
]

# Patterns that indicate output format instructions are present
_FORMAT_INSTRUCTION_PATTERNS = [
    re.compile(r"\bjson\b", re.IGNORECASE),
    re.compile(r"\bxml\b", re.IGNORECASE),
    re.compile(r"\bmarkdown\b", re.IGNORECASE),
    re.compile(r"output format", re.IGNORECASE),
    re.compile(r"respond (?:with|in|using)", re.IGNORECASE),
    re.compile(r"return (?:a |an )?(?:json|list|dict|object|string)", re.IGNORECASE),
    re.compile(r"format your (?:response|answer|output)", re.IGNORECASE),
    re.compile(r"your (?:response|answer|output) (?:should|must|will) be", re.IGNORECASE),
    re.compile(r"<output>|<format>|<schema>", re.IGNORECASE),
    re.compile(r"```(?:json|xml|yaml)", re.IGNORECASE),
]

# Prompt file name patterns
_PROMPT_FILENAME_RE = re.compile(
    r"(?i)(prompt|system|instruction|template|persona|few.?shot)",
)
_PROMPT_EXTENSIONS = {".txt", ".md", ".jinja", ".jinja2", ".j2", ".tmpl", ".template"}
_PROMPT_DIRS = {"prompts", "prompt", "templates", "system_prompts", "instructions"}


def _iter_prompt_files(root: str):
    """
    Yield absolute paths to likely prompt files under root.
    Includes: *.txt in prompts/ dirs, files named *prompt*, *system*, *template*.
    Excludes: .venv, node_modules, .git, __pycache__, CHANGELOG.md, README.md.
    """
    skip_dirs = {".venv", "venv", ".git", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache"}
    skip_filenames = {"README.md", "CHANGELOG.md", "LICENSE", "LICENSE.md", "CONTRIBUTING.md"}

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".")]

        # Check if we're inside a prompts/ dir
        parts = set(dirpath.replace("\\", "/").split("/"))
        in_prompt_dir = bool(parts & _PROMPT_DIRS)

        for fn in filenames:
            if fn in skip_filenames:
                continue
            ext = os.path.splitext(fn)[1].lower()
            name_lower = fn.lower()

            is_prompt = (
                in_prompt_dir and ext in _PROMPT_EXTENSIONS
                or _PROMPT_FILENAME_RE.search(name_lower)
                or (ext == ".txt" and _PROMPT_FILENAME_RE.search(name_lower))
            )
            if is_prompt:
                yield os.path.join(dirpath, fn)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


def _check_length(text: str, filepath: str) -> list[Finding]:
    tokens = _estimate_tokens(text)
    if tokens > _TOKEN_LIMIT_HIGH:
        return [Finding(
            id="CORTEX-101",
            severity="HIGH",
            title="Prompt exceeds 8000-token limit",
            detail=(
                f"Estimated {tokens} tokens (>{_TOKEN_LIMIT_HIGH}). "
                "Very long prompts increase cost per call and can exceed model context windows."
            ),
            location=filepath,
            recommendation=(
                "Compress the prompt: remove redundant examples, summarise background context, "
                "or split into smaller focused prompts."
            ),
            effort="M",
        )]
    if tokens > _TOKEN_LIMIT_MEDIUM:
        return [Finding(
            id="CORTEX-101",
            severity="MEDIUM",
            title="Prompt is large (>4000 tokens)",
            detail=(
                f"Estimated {tokens} tokens (>{_TOKEN_LIMIT_MEDIUM}). "
                "Large prompts increase cost per call significantly."
            ),
            location=filepath,
            recommendation="Review prompt for redundancy; consider splitting into system + user turns.",
            effort="S",
        )]
    return []


def _check_injection(text: str, filepath: str) -> list[Finding]:
    findings = []
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            findings.append(Finding(
                id="CORTEX-102",
                severity="HIGH",
                title="Potential prompt injection risk",
                detail=(
                    f"Prompt file appears to interpolate raw user input directly "
                    f"(matched pattern: {pattern.pattern!r}). "
                    "Unvalidated user content can override system instructions."
                ),
                location=filepath,
                recommendation=(
                    "Sanitize user input before interpolation. "
                    "Use a dedicated user turn rather than embedding in the system prompt. "
                    "Consider adding explicit instruction-following guards."
                ),
                effort="M",
            ))
            break  # one finding per file is sufficient
    return findings


def _check_output_format(text: str, filepath: str) -> list[Finding]:
    """Flag prompts that lack any output format instructions."""
    # Skip very short prompts — they may be intentionally minimal
    if _estimate_tokens(text) < 50:
        return []
    for pattern in _FORMAT_INSTRUCTION_PATTERNS:
        if pattern.search(text):
            return []
    return [Finding(
        id="CORTEX-103",
        severity="LOW",
        title="Missing output format instructions",
        detail=(
            "Prompt does not appear to specify an output format. "
            "Without format guidance, model outputs vary in structure across calls."
        ),
        location=filepath,
        recommendation=(
            "Add explicit output format instructions, e.g. 'Respond with valid JSON matching: {...}'. "
            "Include a concrete example of the expected output."
        ),
        effort="S",
    )]


def evaluate_prompts(target_path: str) -> list[Finding]:
    """
    Find prompt files under target_path and run quality checks.
    Returns a list of Finding objects. Does not call any LLM API.
    """
    all_findings: list[Finding] = []

    try:
        prompt_files = list(_iter_prompt_files(target_path))
    except OSError:
        return []

    for filepath in prompt_files:
        try:
            with open(filepath, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue

        if not text.strip():
            continue

        all_findings.extend(_check_length(text, filepath))
        all_findings.extend(_check_injection(text, filepath))
        all_findings.extend(_check_output_format(text, filepath))

    return all_findings
