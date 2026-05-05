"""Maps inter-module/agent dependencies, detects circular deps and unused internals."""

from __future__ import annotations

import ast
import os
import sys
from collections import defaultdict, deque
from typing import NamedTuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
from team.shared.report_schema import Finding


class Module(NamedTuple):
    dotted: str   # e.g. "team.spine.scripts.spine_agent.n_plus_one_detector"
    path: str     # absolute file path


def _dotted_name(root: str, filepath: str) -> str:
    """Convert an absolute file path to a dotted module name relative to root."""
    rel = os.path.relpath(filepath, root)
    parts = rel.replace(os.sep, "/").removesuffix("/__init__.py").removesuffix(".py")
    return parts.replace("/", ".")


def _collect_modules(team_dir: str) -> list[Module]:
    """Walk team/*/scripts/**/*.py and return Module records."""
    modules = []
    for agent_dir in sorted(os.listdir(team_dir)):
        scripts_dir = os.path.join(team_dir, agent_dir, "scripts")
        if not os.path.isdir(scripts_dir):
            continue
        for dirpath, _dirs, files in os.walk(scripts_dir):
            for fname in files:
                if fname.endswith(".py"):
                    abs_path = os.path.join(dirpath, fname)
                    dotted = _dotted_name(os.path.dirname(team_dir), abs_path)
                    modules.append(Module(dotted=dotted, path=abs_path))
    return modules


def _parse_imports(filepath: str) -> list[str]:
    """Return list of dotted module names imported in file (best-effort)."""
    try:
        with open(filepath, encoding="utf-8", errors="replace") as fh:
            source = fh.read()
        tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _detect_cycles(graph: dict[str, set[str]]) -> list[tuple[str, ...]]:
    """Return list of cycles found via DFS. Each cycle is a tuple of module names."""
    cycles: list[tuple[str, ...]] = []
    visited: set[str] = set()
    path: list[str] = []
    path_set: set[str] = set()

    def dfs(node: str) -> None:
        if node in path_set:
            idx = path.index(node)
            cycles.append(tuple(path[idx:]))
            return
        if node in visited:
            return
        visited.add(node)
        path.append(node)
        path_set.add(node)
        for neighbour in graph.get(node, set()):
            dfs(neighbour)
        path.pop()
        path_set.discard(node)

    for node in list(graph):
        dfs(node)

    # deduplicate cycles (same set of nodes, different start)
    seen: set[frozenset[str]] = set()
    unique: list[tuple[str, ...]] = []
    for c in cycles:
        key = frozenset(c)
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def analyze_dependencies(repo_root: str) -> list[Finding]:
    """
    Walk team/*/scripts/**/*.py, build import graph, detect:
      - Circular dependencies between internal modules
      - Internal modules that are never imported (unused)

    Returns a list of Finding objects.
    """
    team_dir = os.path.join(repo_root, "team")
    if not os.path.isdir(team_dir):
        print(f"  [dep-graph] team/ not found at {team_dir}", file=sys.stderr)
        return []

    modules = _collect_modules(team_dir)
    if not modules:
        return []

    module_set = {m.dotted for m in modules}

    # Build: module -> set of internal modules it imports
    graph: dict[str, set[str]] = defaultdict(set)
    for mod in modules:
        imports = _parse_imports(mod.path)
        for imp in imports:
            # only track internal (team.*) dependencies
            if imp.startswith("team.") and imp in module_set:
                graph[mod.dotted].add(imp)

    findings: list[Finding] = []

    # --- circular dependency detection ---
    cycles = _detect_cycles(dict(graph))
    for cycle in cycles:
        path_str = " -> ".join(cycle) + f" -> {cycle[0]}"
        findings.append(
            Finding(
                severity="HIGH",
                title="Circular dependency detected",
                detail=f"Import cycle: {path_str}",
                location=" | ".join(cycle),
                recommendation=(
                    "Extract shared logic to a common module or invert one dependency edge."
                ),
                effort="M",
                id="apex-dep-cycle",
            )
        )

    # --- unused internal modules ---
    all_imported: set[str] = set()
    for deps in graph.values():
        all_imported.update(deps)

    for mod in modules:
        # skip __init__ and test files
        if mod.dotted.endswith("__init__") or ".tests." in mod.dotted or "test_" in mod.dotted.split(".")[-1]:
            continue
        if mod.dotted not in all_imported and not graph.get(mod.dotted):
            # leaf module never imported by anything else
            findings.append(
                Finding(
                    severity="LOW",
                    title="Unused internal module",
                    detail=(
                        f"{mod.dotted} is never imported by any other internal module. "
                        "May be dead code or a missing dependency edge."
                    ),
                    location=os.path.relpath(mod.path, repo_root),
                    recommendation="Remove module if dead, or wire it into the correct caller.",
                    effort="S",
                    id="apex-dep-unused",
                )
            )

    print(
        f"  [dep-graph] {len(modules)} modules, "
        f"{len(cycles)} cycle(s), "
        f"{sum(1 for f in findings if f.id == 'apex-dep-unused')} unused"
    )
    return findings
