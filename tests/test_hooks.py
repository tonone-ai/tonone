"""
Tests for tonone worktree hooks.

These tests validate:
- JS syntax is valid (node --check)
- Non-targeted tool names are passed through (exit 0)
- The opt-out whitelist for .claude/skip-worktree is respected
- ExitPlanMode is the only trigger for the creator hook
"""

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).parent.parent

# Hooks live in /hooks/ at the repo root (sibling to .claude-plugin/).
# They are registered in .claude-plugin/plugin.json via CLAUDE_PLUGIN_ROOT.
GATE = REPO / "hooks" / "tonone-worktree-gate.js"
CREATE = REPO / "hooks" / "tonone-worktree-create.js"


def run_hook(hook_path: Path, stdin_data: dict) -> tuple[int, str, str]:
    """Run a hook script with JSON on stdin. Returns (returncode, stdout, stderr)."""
    proc = subprocess.run(
        ["node", str(hook_path)],
        input=json.dumps(stdin_data),
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# File existence (must pass before other tests)
# ---------------------------------------------------------------------------


def test_hook_files_exist():
    """Both hook files must exist before other tests can run."""
    assert CREATE.exists(), f"Missing: {CREATE}"
    assert GATE.exists(), f"Missing: {GATE}"


# ---------------------------------------------------------------------------
# Syntax
# ---------------------------------------------------------------------------


def test_worktree_create_is_valid_js():
    """tonone-worktree-create.js must be syntactically valid Node.js."""
    result = subprocess.run(
        ["node", "--check", str(CREATE)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_worktree_gate_is_valid_js():
    """tonone-worktree-gate.js must be syntactically valid Node.js."""
    result = subprocess.run(
        ["node", "--check", str(GATE)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# tonone-worktree-create.js
# ---------------------------------------------------------------------------


def test_create_ignores_non_exit_plan_mode():
    """Creator hook exits 0 silently for tools other than ExitPlanMode."""
    for tool in ["Agent", "Edit", "Write", "Bash", "Read"]:
        rc, out, _ = run_hook(CREATE, {"tool_name": tool, "tool_input": {}})
        assert rc == 0, f"Expected exit 0 for tool={tool}, got {rc}"
        assert "WORKTREE_READY" not in out, f"Unexpected output for tool={tool}"


def test_create_handles_invalid_json():
    """Creator hook exits 0 on invalid stdin — hooks must never block user workflow on a crash."""
    proc = subprocess.run(
        ["node", str(CREATE)],
        input="not json",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0


# ---------------------------------------------------------------------------
# tonone-worktree-gate.js
# ---------------------------------------------------------------------------


def test_gate_allows_non_gated_tools():
    """Gate hook exits 0 for tools that don't modify files."""
    for tool in ["Bash", "Read", "Glob", "Grep", "Agent", "WebSearch"]:
        rc, _, _ = run_hook(GATE, {"tool_name": tool, "tool_input": {}})
        assert rc == 0, f"Expected exit 0 for tool={tool}, got {rc}"


def test_gate_allows_skip_marker_creation():
    """Writing .claude/skip-worktree is always allowed — it's the opt-out path."""
    rc, _, _ = run_hook(GATE, {
        "tool_name": "Write",
        "tool_input": {"file_path": ".claude/skip-worktree"},
    })
    assert rc == 0


def test_gate_allows_skip_marker_with_absolute_path():
    """Writing .claude/skip-worktree with absolute path is also allowed."""
    rc, _, _ = run_hook(GATE, {
        "tool_name": "Edit",
        "tool_input": {"file_path": "/some/repo/.claude/skip-worktree"},
    })
    assert rc == 0


def test_gate_handles_invalid_json():
    """Gate hook exits 0 on invalid stdin — hooks must never block user workflow on a crash."""
    proc = subprocess.run(
        ["node", str(GATE)],
        input="not json",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0


def test_gate_block_message_is_actionable():
    """When gate blocks, stderr must contain both action options."""
    source = GATE.read_text()
    assert "WORKTREE_REQUIRED" in source
    assert "EnterWorktree" in source
    assert ".claude/skip-worktree" in source
    assert "process.exit(1)" in source


# NOTE: The gate's actual blocking behavior (exit 1 on main with active plan) is
# environment-dependent (requires: not in a worktree AND a recent ~/.gstack plan).
# It is validated in the smoke test (Task 7 of the implementation plan) rather
# than here, where we can only inspect the source code for correctness.
