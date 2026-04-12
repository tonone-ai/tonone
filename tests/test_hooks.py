"""
Tests for tonone worktree hooks.

These tests validate:
- JS syntax is valid (node --check)
- Hooks always exit 0 (silent-fail philosophy)
- Session hook output contains required Claude instructions
- Close hook source contains /ship suggestion
"""

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).parent.parent

# Hooks live in /hooks/ at the repo root (sibling to .claude-plugin/).
# They are registered in .claude-plugin/plugin.json via CLAUDE_PLUGIN_ROOT.
SESSION = REPO / "hooks" / "tonone-worktree-session.js"
CLOSE = REPO / "hooks" / "tonone-worktree-close.js"


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
    assert SESSION.exists(), f"Missing: {SESSION}"
    assert CLOSE.exists(), f"Missing: {CLOSE}"


# ---------------------------------------------------------------------------
# Syntax
# ---------------------------------------------------------------------------


def test_worktree_session_is_valid_js():
    """tonone-worktree-session.js must be syntactically valid Node.js."""
    result = subprocess.run(
        ["node", "--check", str(SESSION)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_worktree_close_is_valid_js():
    """tonone-worktree-close.js must be syntactically valid Node.js."""
    result = subprocess.run(
        ["node", "--check", str(CLOSE)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# tonone-worktree-session.js
# ---------------------------------------------------------------------------


def test_session_handles_invalid_json():
    """Session hook exits 0 on invalid stdin — hooks must never block user workflow on a crash."""
    proc = subprocess.run(
        ["node", str(SESSION)],
        input="not json",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0


def test_session_source_contains_required_instructions():
    """Session hook source must instruct Claude to call EnterWorktree and rename the branch."""
    source = SESSION.read_text()
    assert "WORKTREE_READY" in source
    assert "EnterWorktree" in source
    assert "git branch -m" in source
    assert "process.exit(1)" not in source, "session hook must never exit 1"


# ---------------------------------------------------------------------------
# tonone-worktree-close.js
# ---------------------------------------------------------------------------


def test_close_handles_invalid_json():
    """Close hook exits 0 on invalid stdin — hooks must never block user workflow on a crash."""
    proc = subprocess.run(
        ["node", str(CLOSE)],
        input="not json",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0


def test_close_source_contains_ship_suggestion():
    """Close hook source must suggest /ship for dirty sessions."""
    source = CLOSE.read_text()
    assert "/ship" in source
    assert "process.exit(1)" not in source, "close hook must never exit 1"


# ---------------------------------------------------------------------------
# tonone-git-gate.js
# ---------------------------------------------------------------------------

GIT_GATE = REPO / "hooks" / "tonone-git-gate.js"


def test_git_gate_file_exists():
    """Git gate hook file must exist."""
    assert GIT_GATE.exists(), f"Missing: {GIT_GATE}"


def test_git_gate_is_valid_js():
    """tonone-git-gate.js must be syntactically valid Node.js."""
    result = subprocess.run(
        ["node", "--check", str(GIT_GATE)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_git_gate_allows_non_git_commands():
    """Gate exits 0 for Bash commands that are not git commit/push."""
    for cmd in ["npm test", "echo hello", "git status", "git log", "git add ."]:
        rc, _, _ = run_hook(GIT_GATE, {
            "tool_name": "Bash",
            "tool_input": {"command": cmd},
        })
        assert rc == 0, f"Expected exit 0 for command={cmd!r}, got {rc}"


def test_git_gate_allows_non_bash_tools():
    """Gate exits 0 for tools other than Bash."""
    for tool in ["Edit", "Write", "Read", "Agent"]:
        rc, _, _ = run_hook(GIT_GATE, {
            "tool_name": tool,
            "tool_input": {"command": "git commit -m 'test'"},
        })
        assert rc == 0, f"Expected exit 0 for tool={tool}, got {rc}"


def test_git_gate_handles_invalid_json():
    """Git gate exits 0 on invalid stdin — must never block user on a crash."""
    proc = subprocess.run(
        ["node", str(GIT_GATE)],
        input="not json",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0


def test_git_gate_message_is_actionable():
    """When git gate blocks, source must contain GIT_GATE, EnterWorktree, and skip-worktree."""
    source = GIT_GATE.read_text()
    assert "GIT_GATE" in source
    assert "EnterWorktree" in source
    assert ".claude/skip-worktree" in source
    assert "process.exit(1)" in source
