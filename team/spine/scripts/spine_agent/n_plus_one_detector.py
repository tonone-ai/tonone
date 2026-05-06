"""N+1 query pattern detector — static analysis for Python ORM and raw SQL patterns."""

from __future__ import annotations

import ast
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from team.shared.report_schema import Finding

# ORM method names that indicate a database query
ORM_QUERY_METHODS = {
    "filter",
    "get",
    "all",
    "first",
    "last",
    "count",
    "exists",
    "values",
    "values_list",
    "aggregate",
    "annotate",
    "exclude",
    "order_by",
    "select_related",
    "prefetch_related",
    "defer",
    "only",
    "update",
    "delete",
}

# Patterns that suggest an unguarded related-field access
RELATED_ACCESS_INDICATORS = {
    "comments",
    "profile",
    "author",
    "owner",
    "tags",
    "orders",
    "items",
}


def _get_lineno(node: ast.AST) -> int:
    return getattr(node, "lineno", 0)


def _node_contains_orm_call(node: ast.AST) -> tuple[bool, str]:
    """Return (found, method_name) if node contains an ORM-style call."""
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Attribute):
                if func.attr in ORM_QUERY_METHODS:
                    return True, func.attr
            # objects.get(...) — bare attribute chain
            if isinstance(func, ast.Attribute) and isinstance(
                func.value, ast.Attribute
            ):
                if func.value.attr == "objects" and func.attr in ORM_QUERY_METHODS:
                    return True, f"objects.{func.attr}"
    return False, ""


def _node_contains_cursor_execute(node: ast.AST) -> bool:
    """Return True if node contains cursor.execute(...)."""
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Attribute) and func.attr == "execute":
                return True
    return False


def _node_contains_formatted_sql(node: ast.AST) -> bool:
    """Return True if node contains a %-formatted or f-string SQL query assignment."""
    for child in ast.walk(node):
        # %-format: "SELECT ... %s" % value
        if isinstance(child, ast.BinOp) and isinstance(child.op, ast.Mod):
            if isinstance(child.left, ast.Constant) and isinstance(
                child.left.value, str
            ):
                val: str = child.left.value.upper()
                if any(
                    kw in val
                    for kw in ("SELECT", "INSERT", "UPDATE", "DELETE", "WHERE")
                ):
                    return True
        # f-string SQL
        if isinstance(child, ast.JoinedStr):
            # wrapped in an Assign? check parent — approximate via sibling walk
            pass
    return False


def _scan_loop_body(
    loop_node: ast.AST,
    loop_lineno: int,
    filepath: str,
    source_lines: list[str],
) -> list[Finding]:
    """Inspect a loop body for N+1 indicators and return Findings."""
    findings: list[Finding] = []
    body = getattr(loop_node, "body", [])

    for stmt in body:
        # 1. ORM query method called inside loop body
        found_orm, method = _node_contains_orm_call(stmt)
        if found_orm:
            line = _get_lineno(stmt)
            snippet = (
                source_lines[line - 1].strip()
                if line and line <= len(source_lines)
                else ""
            )
            findings.append(
                Finding(
                    id="SPINE-N1-ORM",
                    severity="HIGH",
                    title="N+1 ORM query inside loop",
                    detail=(
                        f"ORM method `.{method}()` called inside a loop at line {line}. "
                        f"Each loop iteration triggers a separate DB query. "
                        f"Code: `{snippet}`"
                    ),
                    location=f"{filepath}:{line}",
                    recommendation=(
                        "Fetch all related objects before the loop using `.select_related()` "
                        "or `.prefetch_related()`, then access the cached result inside the loop."
                    ),
                    effort="S",
                )
            )

        # 2. cursor.execute inside loop
        if _node_contains_cursor_execute(stmt):
            line = _get_lineno(stmt)
            snippet = (
                source_lines[line - 1].strip()
                if line and line <= len(source_lines)
                else ""
            )
            findings.append(
                Finding(
                    id="SPINE-N1-SQL",
                    severity="HIGH",
                    title="Raw SQL execute() inside loop",
                    detail=(
                        f"`cursor.execute()` called inside a loop at line {line}. "
                        f"Code: `{snippet}`"
                    ),
                    location=f"{filepath}:{line}",
                    recommendation=(
                        "Collect all IDs first, then execute a single query with an IN clause: "
                        "`SELECT ... WHERE id IN (%s)` and join in Python."
                    ),
                    effort="S",
                )
            )

        # 3. String-formatted SQL inside loop
        if _node_contains_formatted_sql(stmt):
            line = _get_lineno(stmt)
            snippet = (
                source_lines[line - 1].strip()
                if line and line <= len(source_lines)
                else ""
            )
            findings.append(
                Finding(
                    id="SPINE-N1-FMTSQL",
                    severity="HIGH",
                    title="String-formatted SQL inside loop",
                    detail=(
                        f"SQL query constructed with string formatting inside a loop at line {line}. "
                        f"This is both an N+1 pattern and a SQL injection risk. "
                        f"Code: `{snippet}`"
                    ),
                    location=f"{filepath}:{line}",
                    recommendation=(
                        "Use parameterized queries and batch the loop into a single SQL IN clause."
                    ),
                    effort="S",
                )
            )

        # 4. Related field attribute access inside loop (likely missing prefetch/select)
        for child in ast.walk(stmt):
            if isinstance(child, ast.Attribute):
                if child.attr in RELATED_ACCESS_INDICATORS:
                    line = _get_lineno(child)
                    snippet = (
                        source_lines[line - 1].strip()
                        if line and line <= len(source_lines)
                        else ""
                    )
                    findings.append(
                        Finding(
                            id="SPINE-N1-RELATED",
                            severity="MEDIUM",
                            title=f"Likely N+1: `.{child.attr}` accessed in loop without eager load",
                            detail=(
                                f"Attribute `.{child.attr}` accessed inside a loop at line {line} — "
                                f"likely a lazy-loaded relation. Code: `{snippet}`"
                            ),
                            location=f"{filepath}:{line}",
                            recommendation=(
                                f"Add `.prefetch_related('{child.attr}')` or `.select_related('{child.attr}')` "
                                "to the queryset before the loop."
                            ),
                            effort="S",
                        )
                    )
                    break  # one finding per statement is enough for related access

    return findings


def _scan_async_for_sync_db(
    func_node: ast.AsyncFunctionDef,
    filepath: str,
    source_lines: list[str],
) -> list[Finding]:
    """Detect synchronous DB calls inside async functions."""
    findings: list[Finding] = []
    for node in ast.walk(func_node):
        if isinstance(node, (ast.For, ast.While)):
            if _node_contains_cursor_execute(node):
                line = _get_lineno(node)
                findings.append(
                    Finding(
                        id="SPINE-ASYNC-SYNC-DB",
                        severity="HIGH",
                        title="Sync DB call inside async handler loop",
                        detail=(
                            f"Blocking `cursor.execute()` called inside a loop in async function "
                            f"`{func_node.name}` at line {line}. This blocks the event loop."
                        ),
                        location=f"{filepath}:{line}",
                        recommendation=(
                            "Use an async DB driver (e.g. `asyncpg`, `aiosqlite`, `databases`) "
                            "or gather queries with `asyncio.gather()` outside the hot path."
                        ),
                        effort="M",
                    )
                )
    return findings


def scan_file(filepath: str) -> list[Finding]:
    """Scan a single Python file for N+1 patterns. Returns Finding list."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as fh:
            source = fh.read()
    except OSError:
        return []

    source_lines = source.splitlines()

    try:
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return []

    findings: list[Finding] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.While)):
            findings.extend(
                _scan_loop_body(node, _get_lineno(node), filepath, source_lines)
            )

        if isinstance(node, ast.AsyncFunctionDef):
            findings.extend(_scan_async_for_sync_db(node, filepath, source_lines))

    # Deduplicate by (id, location)
    seen: set[tuple[str, str]] = set()
    deduped: list[Finding] = []
    for f in findings:
        key = (f.id or "", f.location)
        if key not in seen:
            seen.add(key)
            deduped.append(f)

    return deduped


def scan_directory(target: str) -> list[Finding]:
    """Recursively scan all .py files under target. Returns Finding list."""
    findings: list[Finding] = []
    skip_dirs = {
        ".venv",
        "venv",
        "node_modules",
        ".git",
        "__pycache__",
        ".pytest_cache",
    }

    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in skip_dirs]
        for fname in files:
            if fname.endswith(".py"):
                findings.extend(scan_file(os.path.join(root, fname)))

    return findings
