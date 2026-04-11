"""Tests for uiux CLI (subprocess-based)."""

import json
import subprocess
import sys
from pathlib import Path

PYTHON = str(Path(__file__).parent.parent / ".venv" / "bin" / "python")


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PYTHON, "-m", "uiux", *args],
        capture_output=True,
        text=True,
    )


# ── domains subcommand ────────────────────────────────────────────────────────


def test_domains_exits_zero():
    result = _run("domains")
    assert result.returncode == 0


def test_domains_returns_json_list():
    result = _run("domains")
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) > 0


def test_domains_contains_known_domains():
    result = _run("domains")
    data = json.loads(result.stdout)
    assert "style" in data
    assert "color" in data
    assert "product" in data


# ── search subcommand ─────────────────────────────────────────────────────────


def test_search_exits_zero():
    result = _run("search", "--domain", "style", "--query", "minimalism")
    assert result.returncode == 0


def test_search_returns_json():
    result = _run("search", "--domain", "style", "--query", "minimalism")
    data = json.loads(result.stdout)
    assert "domain" in data
    assert "results" in data


def test_search_respects_limit():
    result = _run("search", "--domain", "style", "--query", "design", "--limit", "2")
    data = json.loads(result.stdout)
    assert data["count"] <= 2


def test_search_invalid_domain_fails():
    result = _run("search", "--domain", "invalid-domain-xyz", "--query", "test")
    assert result.returncode != 0


def test_search_product_domain():
    result = _run("search", "--domain", "product", "--query", "saas")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["domain"] == "product"


def test_search_color_domain():
    result = _run("search", "--domain", "color", "--query", "dark professional")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data["results"], list)


# ── design-system subcommand ──────────────────────────────────────────────────


def test_design_system_exits_zero():
    result = _run("design-system", "--product-type", "SaaS dashboard")
    assert result.returncode == 0


def test_design_system_returns_output():
    result = _run("design-system", "--product-type", "SaaS dashboard")
    assert len(result.stdout) > 100


def test_design_system_contains_pattern():
    result = _run("design-system", "--product-type", "e-commerce")
    assert "PATTERN" in result.stdout


def test_design_system_contains_colors():
    result = _run("design-system", "--product-type", "fintech")
    assert "COLORS" in result.stdout
