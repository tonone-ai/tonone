"""LLM usage scanner — static analysis of codebase for LLM API anti-patterns."""

from __future__ import annotations

import ast
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from team.shared.report_schema import Finding

# Model name strings that should be configurable, not hardcoded
_HARDCODED_MODELS = {
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-haiku-20241022",
    "claude-sonnet-4-5",
    "claude-opus-4-5",
    "gpt-4",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-3.5-turbo",
    "gpt-4-turbo",
    "text-davinci-003",
    "gemini-pro",
    "gemini-1.5-pro",
    "mistral-large",
    "mixtral-8x7b-32768",
}

# Patterns that indicate LLM API import / usage
_LLM_IMPORT_RE = re.compile(
    r"""(?x)
    import\s+(anthropic|openai|litellm|langchain|llm|cohere|mistralai)|
    from\s+(anthropic|openai|litellm|langchain|llm|cohere|mistralai)\s+import
    """,
    re.MULTILINE,
)


def _iter_python_files(root: str):
    """Yield absolute paths to .py files under root, skipping venv/hidden dirs."""
    skip = {".venv", "venv", ".git", "node_modules", "__pycache__", ".mypy_cache"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".")]
        for fn in filenames:
            if fn.endswith(".py"):
                yield os.path.join(dirpath, fn)


def _file_has_llm_imports(source: str) -> bool:
    return bool(_LLM_IMPORT_RE.search(source))


class _LLMCallVisitor(ast.NodeVisitor):
    """Walk an AST to find LLM API call sites and flag issues."""

    def __init__(self, filepath: str, source_lines: list[str]):
        self.filepath = filepath
        self.source_lines = source_lines
        self.findings: list[Finding] = []

    # ------------------------------------------------------------------ helpers

    def _loc(self, node: ast.AST) -> str:
        return f"{self.filepath}:{getattr(node, 'lineno', 0)}"

    def _is_llm_call(self, node: ast.Call) -> bool:
        """Return True for LLM API invocation patterns (not constructor calls)."""
        code = ast.unparse(node.func) if hasattr(ast, "unparse") else ""
        # Must be a method call (contains a dot), not a bare constructor like anthropic.Anthropic()
        if "." not in code:
            return False
        return bool(
            re.search(
                r"(messages\.create|chat\.completions\.create|\.generate|\.complete|"
                r"\.stream|\.run|\.invoke|\.predict|\.call_model)",
                code,
                re.IGNORECASE,
            )
        )

    def _has_kwarg(self, node: ast.Call, name: str) -> bool:
        return any(kw.arg == name for kw in node.keywords)

    def _is_in_try(self, node: ast.AST) -> bool:
        """Check if node has a parent Try block (stored by visitor)."""
        return getattr(node, "_in_try", False)

    # ------------------------------------------------------------------ visitor

    def visit_Call(self, node: ast.Call):
        if self._is_llm_call(node):
            # 1. Missing max_tokens
            if not self._has_kwarg(node, "max_tokens") and not self._has_kwarg(node, "max_completion_tokens"):
                self.findings.append(Finding(
                    id="CORTEX-001",
                    severity="MEDIUM",
                    title="Missing max_tokens on LLM call",
                    detail=(
                        "LLM API call has no max_tokens limit. "
                        "Unbounded responses can cause unexpected costs and latency spikes."
                    ),
                    location=self._loc(node),
                    recommendation="Add max_tokens=<reasonable_limit> to cap response length and cost.",
                    effort="S",
                ))

            # 2. Missing timeout
            if not self._has_kwarg(node, "timeout"):
                self.findings.append(Finding(
                    id="CORTEX-002",
                    severity="MEDIUM",
                    title="Missing timeout on LLM call",
                    detail=(
                        "LLM API call has no timeout. Network hangs will block the event loop "
                        "or thread indefinitely."
                    ),
                    location=self._loc(node),
                    recommendation="Pass timeout=30 (or appropriate value) to the API call.",
                    effort="S",
                ))

            # 3. No error handling (not wrapped in try/except)
            if not self._is_in_try(node):
                self.findings.append(Finding(
                    id="CORTEX-003",
                    severity="HIGH",
                    title="LLM call without error handling",
                    detail=(
                        "LLM API call is not inside a try/except block. "
                        "Rate limit errors, network failures, and API errors will crash the caller."
                    ),
                    location=self._loc(node),
                    recommendation=(
                        "Wrap in try/except catching at minimum APIError, RateLimitError, and Exception."
                    ),
                    effort="S",
                ))

            # 4. Missing prompt caching headers
            if not self._has_kwarg(node, "cache_control") and not self._has_kwarg(node, "extra_headers"):
                self.findings.append(Finding(
                    id="CORTEX-004",
                    severity="LOW",
                    title="Missing prompt caching headers",
                    detail=(
                        "LLM API call does not use cache_control or extra_headers for prompt caching. "
                        "Repeated identical system prompts incur unnecessary token costs."
                    ),
                    location=self._loc(node),
                    recommendation=(
                        "Add cache_control={'type': 'ephemeral'} to large, reusable messages "
                        "to enable prompt caching."
                    ),
                    effort="M",
                ))

        self.generic_visit(node)

    def visit_Await(self, node: ast.Await):
        """Flag sync calls in async contexts — actually we want the inverse: sync calls inside async funcs."""
        self.generic_visit(node)


def _mark_try_nodes(tree: ast.AST) -> None:
    """Walk the AST and mark all nodes that are direct children of a Try body."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Try):
            for child in ast.walk(node):
                child._in_try = True  # type: ignore[attr-defined]


def _find_hardcoded_models(source: str, filepath: str) -> list[Finding]:
    """Scan source text for hardcoded model name strings."""
    findings = []
    for i, line in enumerate(source.splitlines(), 1):
        for model in _HARDCODED_MODELS:
            if model in line:
                findings.append(Finding(
                    id="CORTEX-005",
                    severity="LOW",
                    title="Hardcoded model name",
                    detail=(
                        f"Model name '{model}' is hardcoded. "
                        "Hard-wired model strings make it difficult to swap models or A/B test."
                    ),
                    location=f"{filepath}:{i}",
                    recommendation=(
                        "Move model name to a config file, environment variable, or constant. "
                        "e.g. MODEL = os.environ.get('LLM_MODEL', 'claude-3-5-sonnet-20241022')"
                    ),
                    effort="S",
                ))
                break  # one finding per line, even if multiple models
    return findings


def _find_sync_in_async(tree: ast.AST, filepath: str) -> list[Finding]:
    """Find synchronous LLM calls inside async function definitions."""
    findings = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.AsyncFunctionDef,)):
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and not isinstance(child, ast.Await):
                    code = ast.unparse(child.func) if hasattr(ast, "unparse") else ""
                    if re.search(
                        r"(messages\.create|chat\.completions\.create|client\.beta)",
                        code,
                        re.IGNORECASE,
                    ):
                        findings.append(Finding(
                            id="CORTEX-006",
                            severity="MEDIUM",
                            title="Synchronous LLM call inside async function",
                            detail=(
                                "A synchronous LLM API call is used inside an async function. "
                                "This blocks the event loop during the entire API round-trip."
                            ),
                            location=f"{filepath}:{getattr(child, 'lineno', 0)}",
                            recommendation=(
                                "Use the async client (e.g. AsyncAnthropic) and await the call."
                            ),
                            effort="M",
                        ))
    return findings


def scan_llm_usage(target_path: str) -> list[Finding]:
    """
    Scan all Python files under target_path for LLM API usage anti-patterns.
    Returns a list of Finding objects.
    """
    all_findings: list[Finding] = []

    try:
        py_files = list(_iter_python_files(target_path))
    except OSError as e:
        return []

    for filepath in py_files:
        try:
            with open(filepath, encoding="utf-8", errors="replace") as fh:
                source = fh.read()
        except OSError:
            continue

        # Only analyse files that import LLM libraries
        if not _file_has_llm_imports(source):
            # Still scan for hardcoded model names even without import (could be a config file)
            all_findings.extend(_find_hardcoded_models(source, filepath))
            continue

        source_lines = source.splitlines()

        # Hardcoded model names
        all_findings.extend(_find_hardcoded_models(source, filepath))

        # Parse AST — skip files with syntax errors
        try:
            tree = ast.parse(source, filename=filepath)
        except SyntaxError:
            continue

        _mark_try_nodes(tree)

        visitor = _LLMCallVisitor(filepath, source_lines)
        visitor.visit(tree)
        all_findings.extend(visitor.findings)

        # Sync calls inside async
        all_findings.extend(_find_sync_in_async(tree, filepath))

    return all_findings
