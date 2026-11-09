"""Shared helpers for evals. Changing this file selects every eval."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def repo():
    return REPO


@pytest.fixture
def workdir(tmp_path):
    """Isolated project dir with a .git marker so tools do not walk into this repo."""
    (tmp_path / ".git").mkdir()
    return tmp_path


def stage(fixtures: Path, dest: Path, *names: str):
    """Copy named fixture files into dest, return their paths."""
    out = []
    for n in names:
        shutil.copy(fixtures / n, dest / n)
        out.append(dest / n)
    return out


def run(cmd, cwd=None, stdin=None):
    return subprocess.run(
        [str(c) for c in cmd],
        cwd=cwd,
        input=stdin,
        capture_output=True,
        text=True,
        timeout=30,
    )


PY = sys.executable
