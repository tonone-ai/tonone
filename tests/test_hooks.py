"""
Tests for tonone hook infrastructure.
"""

import importlib
import importlib.util
from pathlib import Path

REPO = Path(__file__).parent.parent
BUMP_VERSION = REPO / "scripts" / "bump-version.py"


def _load_bump_version():
    spec = importlib.util.spec_from_file_location("bump_version", BUMP_VERSION)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bump_version_excludes_worktrees(tmp_path):
    """find_files() must not return paths inside .claude/worktrees/."""
    mod = _load_bump_version()

    fake_root = tmp_path
    wt_plugin = (
        fake_root
        / ".claude"
        / "worktrees"
        / "my-feature"
        / ".claude-plugin"
        / "plugin.json"
    )
    wt_plugin.parent.mkdir(parents=True)
    wt_plugin.write_text('{"name":"tonone","version":"0.0.0"}')

    real_plugin = fake_root / ".claude-plugin" / "plugin.json"
    real_plugin.parent.mkdir(parents=True)
    real_plugin.write_text('{"name":"tonone","version":"0.0.0"}')

    orig_root = mod.REPO_ROOT
    orig_tmpl = mod.TEMPLATE_DIR
    mod.REPO_ROOT = fake_root
    mod.TEMPLATE_DIR = str(fake_root / "templates")

    try:
        plugin_files, _ = mod.find_files()
        paths = [str(p) for p in plugin_files]
        assert any(
            "claude-plugin" in p and "worktrees" not in p for p in paths
        ), "real plugin.json should be included"
        assert not any(
            "worktrees" in p for p in paths
        ), f"worktree plugin.json must be excluded, got: {paths}"
    finally:
        mod.REPO_ROOT = orig_root
        mod.TEMPLATE_DIR = orig_tmpl
