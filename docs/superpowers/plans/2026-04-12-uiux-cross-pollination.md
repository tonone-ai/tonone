# UI/UX Design Intelligence Cross-Pollination — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add design intelligence databases and search engine to 7 tonone agents via a shared library + per-agent scoped wrappers + 10 new skills + 8 enhanced skills.

**Architecture:** Shared Python package at `lib/uiux/` with BM25 search engine and 28 CSV data files. Each of 7 agents (Form, Draft, Prism, Touch, Lens, Pitch, Surge) gets a thin wrapper subpackage scoping access to relevant domains only. New skills call the wrapper via CLI, enhanced skills get additive sections referencing the wrapper.

**Tech Stack:** Python 3.10+, stdlib only (csv, re, math, pathlib, collections, json, argparse). No external dependencies.

**Spec:** `docs/superpowers/specs/2026-04-11-uiux-cross-pollination-design.md`

---

## Chunk 1: Foundation — Shared Library

### Task 1: Create lib/uiux package structure

**Files:**

- Create: `lib/uiux/pyproject.toml`
- Create: `lib/uiux/setup.sh`
- Create: `lib/uiux/uiux/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "uiux"
version = "0.1.0"
description = "Design intelligence search engine — BM25 over curated UI/UX databases"
license = "MIT"
requires-python = ">=3.10"
dependencies = []

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: Create setup.sh**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if command -v uv &>/dev/null; then
	uv venv "$SCRIPT_DIR/.venv"
	uv pip install -e "$SCRIPT_DIR" --python "$SCRIPT_DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
	python3 -m venv "$SCRIPT_DIR/.venv"
	"$SCRIPT_DIR/.venv/bin/pip" install -e "$SCRIPT_DIR"
else
	echo "ERROR: Python 3 is required. Install python3 or uv."
	exit 1
fi

echo "uiux ready."
```

- [ ] **Step 3: Create uiux/**init**.py**

```python
"""Design intelligence search engine — BM25 over curated UI/UX databases."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Make setup.sh executable and verify package installs**

Run: `chmod +x lib/uiux/setup.sh && cd lib/uiux && bash setup.sh`
Expected: "uiux ready."

- [ ] **Step 5: Commit**

```bash
git add lib/uiux/pyproject.toml lib/uiux/setup.sh lib/uiux/uiux/__init__.py
git commit -m "feat: scaffold lib/uiux shared package"
```

---

### Task 2: Download CSV data files from source repo

**Files:**

- Create: `lib/uiux/uiux/data/*.csv` (12 files)
- Create: `lib/uiux/uiux/data/stacks/*.csv` (16 files)

- [ ] **Step 1: Create data directories**

Run: `mkdir -p lib/uiux/uiux/data/stacks`

- [ ] **Step 2: Download all 12 top-level CSVs**

Run the following script to download all CSV files from the source repo:

```bash
cd lib/uiux/uiux/data
BASE="https://raw.githubusercontent.com/tonone-ai/uiux-data/main/data"

for f in styles.csv colors.csv typography.csv google-fonts.csv products.csv ui-reasoning.csv landing.csv charts.csv ux-guidelines.csv react-performance.csv app-interface.csv icons.csv; do
  curl -sL "$BASE/$f" -o "$f"
done
```

- [ ] **Step 3: Download all 16 stack CSVs**

```bash
cd lib/uiux/uiux/data/stacks
BASE="https://raw.githubusercontent.com/tonone-ai/uiux-data/main/data/stacks"

for f in react.csv nextjs.csv vue.csv nuxtjs.csv nuxt-ui.csv svelte.csv astro.csv html-tailwind.csv shadcn-ui.csv swiftui.csv react-native.csv flutter.csv jetpack-compose.csv angular.csv laravel.csv threejs.csv; do
  curl -sL "$BASE/$f" -o "$f"
done
```

- [ ] **Step 4: Verify all files downloaded with content**

Run: `find lib/uiux/uiux/data -name "*.csv" | wc -l`
Expected: 28

Run: `head -1 lib/uiux/uiux/data/styles.csv`
Expected: Header row starting with "No,Style Category,Type,Keywords..."

- [ ] **Step 5: Commit**

```bash
git add lib/uiux/uiux/data/
git commit -m "feat: add design intelligence CSV data files (28 databases)"
```

---

### Task 3: Port BM25 search engine

**Files:**

- Create: `lib/uiux/uiux/search.py`

The source is at `https://raw.githubusercontent.com/tonone-ai/uiux-data/main/scripts/core.py` (12KB). Port it with these modifications:

1. Change `DATA_DIR` to use `importlib.resources` or `Path(__file__).parent / "data"` (relative to package)
2. Keep all CSV_CONFIG domain mappings exactly as source
3. Keep the BM25 algorithm exactly as source
4. Add `app-interface` and `stacks` to CSV_CONFIG if not already present
5. Ensure all imports are stdlib only
6. Export: `search(domain, query, limit)` function and `DOMAINS` set

- [ ] **Step 1: Fetch source core.py**

Run: `curl -sL "https://raw.githubusercontent.com/tonone-ai/uiux-data/main/scripts/core.py" -o /tmp/uiux-core-source.py`

- [ ] **Step 2: Port to lib/uiux/uiux/search.py**

Read `/tmp/uiux-core-source.py` and port with these changes:

- `DATA_DIR = Path(__file__).parent / "data"` (not relative to scripts/)
- Keep `CSV_CONFIG` dict with all domain mappings
- Keep `BM25Searcher` class and `search()` function
- Add missing domains if needed: `app-interface` → `app-interface.csv`, `stacks` → `stacks/` directory
- For `stacks` domain: implement a `search_stacks(stack_name)` that loads the specific stack CSV by name
- Export `DOMAINS = set(CSV_CONFIG.keys())` at module level
- Ensure the main `search()` function signature is: `search(domain: str, query: str, limit: int = 3) -> list[dict]`

- [ ] **Step 3: Write test to verify search works**

Create `lib/uiux/tests/__init__.py` (empty) and `lib/uiux/tests/test_search.py`:

```python
import pytest
from uiux.search import search, DOMAINS

def test_domains_exist():
    assert "style" in DOMAINS
    assert "color" in DOMAINS
    assert "chart" in DOMAINS
    assert "landing" in DOMAINS
    assert "product" in DOMAINS
    assert "ux" in DOMAINS
    assert "typography" in DOMAINS

def test_search_returns_results():
    results = search(domain="color", query="fintech banking", limit=3)
    assert isinstance(results, list)
    assert len(results) > 0
    assert len(results) <= 3

def test_search_respects_limit():
    results = search(domain="style", query="minimalism", limit=1)
    assert len(results) <= 1

def test_search_invalid_domain():
    with pytest.raises((ValueError, KeyError)):
        search(domain="nonexistent", query="test")

def test_search_empty_query():
    results = search(domain="style", query="", limit=3)
    assert isinstance(results, list)

def test_result_has_expected_fields():
    results = search(domain="color", query="SaaS", limit=1)
    if results:
        assert "Product Type" in results[0]
```

- [ ] **Step 4: Run tests**

Run: `cd lib/uiux && .venv/bin/python -m pytest tests/test_search.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add lib/uiux/uiux/search.py lib/uiux/tests/
git commit -m "feat: port BM25 search engine from design intelligence"
```

---

### Task 4: Port design system generator

**Files:**

- Create: `lib/uiux/uiux/design_system.py`

Source: `https://raw.githubusercontent.com/tonone-ai/uiux-data/main/scripts/design_system.py` (47KB).

- [ ] **Step 1: Fetch source**

Run: `curl -sL "https://raw.githubusercontent.com/tonone-ai/uiux-data/main/scripts/design_system.py" -o /tmp/uiux-design-system-source.py`

- [ ] **Step 2: Port to lib/uiux/uiux/design_system.py**

Read `/tmp/uiux-design-system-source.py` and port with these changes:

- Import `search` from `.search` (relative import within package)
- Remove any external dependencies — use only stdlib
- Keep the core logic: product type → parallel searches → reasoning rule matching → decision_rules application → design system output
- Export: `generate_design_system(product_type: str) -> str` function
- Output format: structured text with Pattern, Style, Colors (full token set), Typography, Key Effects, Anti-patterns, Pre-delivery checklist

- [ ] **Step 3: Write test**

Add to `lib/uiux/tests/test_design_system.py`:

```python
import pytest
from uiux.design_system import generate_design_system

def test_generates_for_known_product():
    result = generate_design_system("fintech SaaS")
    assert isinstance(result, str)
    assert len(result) > 100

def test_handles_unknown_product():
    result = generate_design_system("completely unknown product xyz")
    assert isinstance(result, str)
    # Should still return something (fallback/default)

def test_output_contains_key_sections():
    result = generate_design_system("e-commerce")
    result_lower = result.lower()
    assert "style" in result_lower or "pattern" in result_lower
    assert "color" in result_lower
```

- [ ] **Step 4: Run tests**

Run: `cd lib/uiux && .venv/bin/python -m pytest tests/test_design_system.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add lib/uiux/uiux/design_system.py lib/uiux/tests/test_design_system.py
git commit -m "feat: port design system generator from design intelligence"
```

---

### Task 5: Build CLI entrypoint

**Files:**

- Create: `lib/uiux/uiux/cli.py`
- Create: `lib/uiux/uiux/__main__.py`

- [ ] **Step 1: Write CLI**

`lib/uiux/uiux/cli.py`:

```python
"""CLI for uiux design intelligence search."""

import argparse
import json
import sys

from .search import search, DOMAINS
from .design_system import generate_design_system


def main():
    parser = argparse.ArgumentParser(description="UI/UX design intelligence search")
    sub = parser.add_subparsers(dest="command")

    # search
    s = sub.add_parser("search", help="Search a design domain")
    s.add_argument("--domain", required=True, choices=sorted(DOMAINS))
    s.add_argument("--query", required=True)
    s.add_argument("--limit", type=int, default=3)

    # design-system
    ds = sub.add_parser("design-system", help="Generate a complete design system")
    ds.add_argument("--product-type", required=True)

    # domains
    sub.add_parser("domains", help="List available search domains")

    args = parser.parse_args()

    if args.command == "search":
        results = search(domain=args.domain, query=args.query, limit=args.limit)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif args.command == "design-system":
        output = generate_design_system(args.product_type)
        print(output)
    elif args.command == "domains":
        print(json.dumps(sorted(DOMAINS), indent=2))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write **main**.py**

`lib/uiux/uiux/__main__.py`:

```python
"""Allow running as: python3 -m uiux"""
from .cli import main

main()
```

- [ ] **Step 3: Write CLI smoke test**

`lib/uiux/tests/test_cli.py`:

```python
import subprocess
import json
import sys
from pathlib import Path

VENV_PYTHON = str(Path(__file__).parent.parent / ".venv" / "bin" / "python")


def run_cli(*args):
    result = subprocess.run(
        [VENV_PYTHON, "-m", "uiux", *args],
        capture_output=True, text=True, timeout=30,
    )
    return result


def test_domains_returns_json():
    r = run_cli("domains")
    assert r.returncode == 0
    domains = json.loads(r.stdout)
    assert isinstance(domains, list)
    assert "style" in domains
    assert "color" in domains


def test_search_returns_json():
    r = run_cli("search", "--domain", "color", "--query", "fintech")
    assert r.returncode == 0
    results = json.loads(r.stdout)
    assert isinstance(results, list)


def test_design_system_returns_output():
    r = run_cli("design-system", "--product-type", "SaaS")
    assert r.returncode == 0
    assert len(r.stdout) > 50


def test_invalid_domain_fails():
    r = run_cli("search", "--domain", "fake", "--query", "test")
    assert r.returncode != 0
```

- [ ] **Step 4: Run all tests**

Run: `cd lib/uiux && .venv/bin/python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add lib/uiux/uiux/cli.py lib/uiux/uiux/__main__.py lib/uiux/tests/test_cli.py
git commit -m "feat: add uiux CLI entrypoint with search, design-system, domains commands"
```

---

### Task 6: Write domain validation tests

**Files:**

- Create: `lib/uiux/tests/test_domains.py`

- [ ] **Step 1: Write domain CSV loading tests**

```python
import csv
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "uiux" / "data"

EXPECTED_HEADERS = {
    "styles.csv": ["Style Category", "Type", "Keywords"],
    "colors.csv": ["Product Type", "Primary", "On Primary"],
    "typography.csv": ["Font Pairing Name", "Category", "Heading Font"],
    "charts.csv": ["Data Type", "Keywords", "Best Chart Type"],
    "ux-guidelines.csv": ["Category", "Issue", "Platform"],
    "products.csv": ["Product Type", "Keywords", "Primary Style Recommendation"],
    "ui-reasoning.csv": ["UI_Category", "Recommended_Pattern", "Style_Priority"],
    "landing.csv": ["Pattern Name", "Keywords", "Section Order"],
    "google-fonts.csv": ["Family", "Category"],
    "react-performance.csv": [],  # verify file loads, don't check specific headers
    "app-interface.csv": [],
    "icons.csv": [],
}


def test_all_csvs_exist():
    for filename in EXPECTED_HEADERS:
        assert (DATA_DIR / filename).exists(), f"Missing: {filename}"


def test_stacks_directory_has_16_files():
    stacks = list((DATA_DIR / "stacks").glob("*.csv"))
    assert len(stacks) == 16


def test_csv_headers_match():
    for filename, expected_cols in EXPECTED_HEADERS.items():
        if not expected_cols:
            continue
        with open(DATA_DIR / filename, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            for col in expected_cols:
                assert col in headers, f"{filename} missing column: {col}"


def test_csvs_have_data_rows():
    for filename in EXPECTED_HEADERS:
        with open(DATA_DIR / filename, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) > 1, f"{filename} has no data rows"
```

- [ ] **Step 2: Run tests**

Run: `cd lib/uiux && .venv/bin/python -m pytest tests/test_domains.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add lib/uiux/tests/test_domains.py
git commit -m "test: add domain CSV validation tests"
```

---

## Chunk 2: Agent Wrappers + Setup Changes

All 7 agents follow the same pattern. Each task below is independent and can be run in parallel.

### Template: Agent Wrapper

For each agent, create these files:

- `team/{agent}/scripts/{agent}_agent/uiux/__init__.py` — wrapper with ALLOWED_DOMAINS
- `team/{agent}/scripts/{agent}_agent/uiux/__main__.py` — CLI entrypoint
- Modify: `team/{agent}/scripts/pyproject.toml` — add uiux dependency
- Modify: `team/{agent}/scripts/setup.sh` — add uiux lib check
- Create: `team/{agent}/tests/test_uiux.py` — smoke tests

---

### Task 7: Form agent wrapper

**Files:**

- Create: `team/form/scripts/form_agent/uiux/__init__.py`
- Create: `team/form/scripts/form_agent/uiux/__main__.py`
- Modify: `team/form/scripts/pyproject.toml`
- Modify: `team/form/scripts/setup.sh`
- Create: `team/form/tests/test_uiux.py`

- [ ] **Step 1: Create wrapper **init**.py**

```python
"""Form agent design intelligence — visual design domains."""

try:
    from uiux.search import search
    from uiux.design_system import generate_design_system
except ImportError:
    def _missing(*a, **kw):
        raise RuntimeError(
            "uiux package not found — run: cd lib/uiux && bash setup.sh, "
            "then reinstall this agent"
        )
    search = _missing
    generate_design_system = _missing

ALLOWED_DOMAINS = {"style", "color", "typography", "google-fonts", "product"}


def query(domain: str, terms: str, limit: int = 5) -> list[dict]:
    if domain not in ALLOWED_DOMAINS:
        raise ValueError(f"Domain '{domain}' not available for Form agent. Allowed: {sorted(ALLOWED_DOMAINS)}")
    return search(domain=domain, query=terms, limit=limit)
```

- [ ] **Step 2: Create wrapper **main**.py**

```python
"""CLI: python3 -m form_agent.uiux search --domain color --query 'fintech'"""

import argparse
import json
import sys

from . import query, ALLOWED_DOMAINS

try:
    from uiux.design_system import generate_design_system
except ImportError:
    generate_design_system = None


def main():
    parser = argparse.ArgumentParser(description="Form design intelligence")
    sub = parser.add_subparsers(dest="cmd")

    s = sub.add_parser("search")
    s.add_argument("--domain", required=True, choices=sorted(ALLOWED_DOMAINS))
    s.add_argument("--query", required=True)
    s.add_argument("--limit", type=int, default=5)

    ds = sub.add_parser("design-system")
    ds.add_argument("--product-type", required=True)

    sub.add_parser("domains")

    args = parser.parse_args()
    if args.cmd == "domains":
        print(json.dumps(sorted(ALLOWED_DOMAINS)))
    elif args.cmd == "search":
        results = query(args.domain, args.query, args.limit)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif args.cmd == "design-system":
        if generate_design_system is None:
            print("ERROR: uiux package not installed", file=sys.stderr)
            sys.exit(1)
        print(generate_design_system(args.product_type))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Update pyproject.toml**

Add uiux dependency to `team/form/scripts/pyproject.toml`:

```toml
[project]
name = "form"
version = "0.1.0"
description = "Visual designer — brand identity, color systems, typography, UI design, and design systems"
license = "MIT"
requires-python = ">=3.10"
dependencies = ["uiux"]

[tool.uv.sources]
uiux = { path = "../../../lib/uiux", editable = true }

[tool.pytest.ini_options]
testpaths = ["../tests"]
pythonpath = ["."]
```

- [ ] **Step 4: Update setup.sh**

Add uiux lib check to `team/form/scripts/setup.sh` — insert after `SCRIPT_DIR` line:

```bash
UIUX_LIB="$SCRIPT_DIR/../../../lib/uiux"
if [ ! -d "$UIUX_LIB/uiux" ]; then
	echo "uiux lib not found at $UIUX_LIB — skipping design intelligence"
fi
```

- [ ] **Step 5: Write wrapper smoke test**

`team/form/tests/test_uiux.py`:

```python
import pytest
from form_agent.uiux import query, ALLOWED_DOMAINS


def test_allowed_domains():
    assert ALLOWED_DOMAINS == {"style", "color", "typography", "google-fonts", "product"}


def test_rejects_disallowed_domain():
    with pytest.raises(ValueError, match="not available for Form"):
        query("ux", "test")


def test_query_returns_results():
    results = query("color", "fintech", limit=2)
    assert isinstance(results, list)
    assert len(results) > 0
```

- [ ] **Step 6: Run tests**

Run: `cd team/form/scripts && bash setup.sh && .venv/bin/python -m pytest ../tests/test_uiux.py -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add team/form/scripts/form_agent/uiux/ team/form/scripts/pyproject.toml team/form/scripts/setup.sh team/form/tests/test_uiux.py
git commit -m "feat: add Form agent uiux wrapper (style, color, typography, google-fonts, product)"
```

---

### Task 8: Draft agent wrapper

**Files:**

- Create: `team/draft/scripts/draft_agent/uiux/__init__.py`
- Create: `team/draft/scripts/draft_agent/uiux/__main__.py`
- Modify: `team/draft/scripts/pyproject.toml`
- Modify: `team/draft/scripts/setup.sh`
- Create: `team/draft/tests/test_uiux.py`

Same pattern as Task 7 with these differences:

- `ALLOWED_DOMAINS = {"ux", "landing", "product"}`
- No `design_system` import (search only)
- No `design-system` CLI subcommand
- Error message: "not available for Draft agent"
- pyproject.toml name: "draft"
- Test checks: `ALLOWED_DOMAINS == {"ux", "landing", "product"}`
- Test query: `query("ux", "navigation", limit=2)`
- Rejects: `query("style", "test")` → ValueError

- [ ] **Step 1: Create wrapper **init**.py** (same template, Draft domains)
- [ ] **Step 2: Create wrapper **main**.py** (search + domains only, no design-system)
- [ ] **Step 3: Update pyproject.toml** (add uiux dep)
- [ ] **Step 4: Update setup.sh** (add uiux lib check)
- [ ] **Step 5: Write test** (`test_uiux.py`)
- [ ] **Step 6: Run tests and verify**
- [ ] **Step 7: Commit**

```bash
git commit -m "feat: add Draft agent uiux wrapper (ux, landing, product)"
```

---

### Task 9: Prism agent wrapper

Same pattern. Differences:

- `ALLOWED_DOMAINS = {"react", "web", "stacks", "icons", "chart"}`
- Additional method: `stack_guide(stack_name: str) -> list[dict]` that loads `stacks/{stack_name}.csv`
- Test query: `query("chart", "time series", limit=2)`
- Rejects: `query("color", "test")` → ValueError

- [ ] Steps 1-7 (same pattern)

```bash
git commit -m "feat: add Prism agent uiux wrapper (react, web, stacks, icons, chart)"
```

---

### Task 10: Touch agent wrapper

Same pattern. Differences:

- `ALLOWED_DOMAINS = {"app-interface", "stacks"}`
- `stack_guide()` limited to mobile stacks: swiftui, react-native, flutter, jetpack-compose
- Additional validation: `stack_guide("react")` raises ValueError (not a mobile stack)
- Test query: `query("app-interface", "touch targets", limit=2)`
- Rejects: `query("style", "test")` → ValueError

- [ ] Steps 1-7 (same pattern)

```bash
git commit -m "feat: add Touch agent uiux wrapper (app-interface, mobile stacks)"
```

---

### Task 11: Lens agent wrapper

Same pattern. Differences:

- `ALLOWED_DOMAINS = {"chart", "style"}`
- Style queries auto-filter: when `domain="style"`, wrapper appends `" BI Dashboard"` to query
- Test: `query("style", "monitoring")` internally searches "monitoring BI Dashboard"
- Test query: `query("chart", "comparison data", limit=2)`
- Rejects: `query("color", "test")` → ValueError

- [ ] Steps 1-7 (same pattern)

```bash
git commit -m "feat: add Lens agent uiux wrapper (chart, style/dashboard)"
```

---

### Task 12: Pitch agent wrapper

Same pattern. Differences:

- `ALLOWED_DOMAINS = {"landing", "product"}`
- Search only, no design-system
- Test query: `query("landing", "SaaS", limit=2)`
- Rejects: `query("chart", "test")` → ValueError

- [ ] Steps 1-7 (same pattern)

```bash
git commit -m "feat: add Pitch agent uiux wrapper (landing, product)"
```

---

### Task 13: Surge agent wrapper

Same pattern. Differences:

- `ALLOWED_DOMAINS = {"landing", "product", "ux"}`
- Search only, no design-system
- Test query: `query("ux", "forms validation", limit=2)`
- Rejects: `query("style", "test")` → ValueError

- [ ] Steps 1-7 (same pattern)

```bash
git commit -m "feat: add Surge agent uiux wrapper (landing, product, ux)"
```

---

## Chunk 3: New Skills (10 total)

Each new skill is a `SKILL.md` file in `team/{agent}/skills/{skill-name}/SKILL.md`. All skills are independent and can be created in parallel.

---

### Task 14: form-style skill

**Files:**

- Create: `team/form/skills/form-style/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

````markdown
---
name: form-style
description: |
  Use when asked to select a UI style, choose a design direction, pick a visual
  approach for a product, or match a style to an industry. Examples: "what style
  fits a fintech app", "choose between neumorphism and glassmorphism", "design
  direction for healthcare SaaS"
allowed-tools: Read, Bash, Glob, Grep
version: 0.6.6
author: tonone-ai <hello@tonone.ai>
license: MIT
---

# form-style — UI Style Selection

## When to use

Product needs a visual direction. Industry or product type is known or discoverable from context.

## Workflow

1. **Identify product type** from user request or project context
2. **Search product reasoning:**
   ```bash
   python3 -m form_agent.uiux search --domain product --query "{product_type}" --limit 3
   ```
````

3. **Get recommended style details:**
   ```bash
   python3 -m form_agent.uiux search --domain style --query "{recommended_style}" --limit 3
   ```
4. **Cross-reference anti-patterns** from the product search results — check the `Anti_Patterns` field
5. **Output** the recommendation using the format below

## Output format

```
┌─ Style Recommendation ─────────────────────┐
│ Product:     {product_type}                 │
│ Style:       {primary_style}                │
│ Fallback:    {secondary_style}              │
├─ Effects ───────────────────────────────────┤
│ {key_effects from style search}             │
├─ Anti-patterns ─────────────────────────────┤
│ ✗ {anti_pattern_1}                          │
│ ✗ {anti_pattern_2}                          │
├─ Implementation Checklist ──────────────────┤
│ □ {checklist_item_1}                        │
│ □ {checklist_item_2}                        │
└─────────────────────────────────────────────┘
```

## Anti-patterns

- Never pick style based on aesthetics alone — match to product type + audience
- Never ignore anti-pattern list from reasoning rules
- Never recommend more than 2 combined styles (primary + fallback)
- Never recommend a style marked as incompatible with the target framework

````

- [ ] **Step 2: Commit**

```bash
git add team/form/skills/form-style/
git commit -m "feat: add form-style skill — UI style selection via design intelligence"
````

---

### Task 15: form-palette skill

**Files:**

- Create: `team/form/skills/form-palette/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Trigger: "color palette for X", "industry-matched colors", "generate palette"

Workflow:

1. Search product: `python3 -m form_agent.uiux search --domain product --query "{product_type}"`
2. Search color: `python3 -m form_agent.uiux search --domain color --query "{product_type}"`
3. Output full shadcn-compatible token set (Primary, On Primary, Secondary, On Secondary, Accent, On Accent, Background, Foreground, Card, Card Foreground, Muted, Muted Foreground, Border, Destructive, On Destructive, Ring)

Anti-patterns: Never use colors that violate WCAG AA contrast against their "On" counterpart. Never ignore industry color conventions (e.g., green for finance, blue for healthcare).

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: add form-palette skill — industry-matched color palette generation"
```

---

### Task 16: draft-patterns skill

**Files:**

- Create: `team/draft/skills/draft-patterns/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Trigger: "UX pattern for forms/nav/loading", "best practice for X interaction"

Workflow:

1. Search UX guidelines: `python3 -m draft_agent.uiux search --domain ux --query "{pattern_category}"`
2. Return structured do/don't with code examples from the results
3. Include severity level from the guideline data

Anti-patterns: Never recommend patterns without checking platform context (web vs mobile vs native). Never ignore severity ratings.

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: add draft-patterns skill — UX pattern lookup via design intelligence"
```

---

### Task 17: draft-landing skill

**Files:**

- Create: `team/draft/skills/draft-landing/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Trigger: "landing page structure for X", "page layout for conversion"

Workflow:

1. Search landing: `python3 -m draft_agent.uiux search --domain landing --query "{product_type}"`
2. Search product: `python3 -m draft_agent.uiux search --domain product --query "{product_type}"`
3. Output: section order, CTA placement, conversion optimization notes

Anti-patterns: Never skip the "So what?" test for each section. Never add sections without a conversion purpose.

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: add draft-landing skill — landing page pattern selection"
```

---

### Task 18: prism-stack skill

**Files:**

- Create: `team/prism/skills/prism-stack/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Trigger: "best practices for React/Vue/Svelte", "framework guidelines for X"

Workflow:

1. Detect stack from project (package.json, imports, etc.)
2. Load stack guide: `python3 -m prism_agent.uiux search --domain stacks --query "{stack_name}"`
3. Output framework-specific guidelines, performance rules, component patterns

Anti-patterns: Never apply guidelines from wrong framework version. Never mix framework idioms (e.g., React patterns in Vue code).

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: add prism-stack skill — framework-specific implementation guidelines"
```

---

### Task 19: prism-chart skill

**Files:**

- Create: `team/prism/skills/prism-chart/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Trigger: "implement chart for X data", "best visualization for Y", "chart component"

Workflow:

1. Search charts: `python3 -m prism_agent.uiux search --domain chart --query "{data_type}"`
2. Output: chart type, library recommendation, accessibility grade, interaction level, color guidance, fallback for a11y

Anti-patterns: Never choose chart type without considering data volume threshold. Never skip accessibility fallback for charts with grade below AA.

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: add prism-chart skill — data visualization implementation guidance"
```

---

### Task 20: touch-ui skill

**Files:**

- Create: `team/touch/skills/touch-ui/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Trigger: "mobile UI guidelines", "touch targets for X", "iOS/Android UI rules"

Workflow:

1. Search app-interface: `python3 -m touch_agent.uiux search --domain app-interface --query "{platform} {topic}"`
2. Search mobile stack: `python3 -m touch_agent.uiux search --domain stacks --query "{framework}"`
3. Output: platform-specific rules with code examples

Anti-patterns: Never apply iOS patterns on Android or vice versa. Never set touch targets below 44x44pt (iOS) or 48x48dp (Android).

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: add touch-ui skill — mobile UI guidelines lookup"
```

---

### Task 21: lens-chart skill

**Files:**

- Create: `team/lens/skills/lens-chart/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Trigger: "chart type for X data", "best visualization for analytics", "dashboard chart selection"

Workflow:

1. Search charts: `python3 -m lens_agent.uiux search --domain chart --query "{data_type}"`
2. Search dashboard style: `python3 -m lens_agent.uiux search --domain style --query "{dashboard_context}"`
3. Output optimized for BI: data density, drill-down capability, real-time support, library recommendation

Anti-patterns: Never choose decorative charts over data-dense ones for BI. Never skip the "does this answer a decision?" test.

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: add lens-chart skill — BI-optimized chart type selection"
```

---

### Task 22: pitch-landing skill

**Files:**

- Create: `team/pitch/skills/pitch-landing/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Trigger: "landing page structure", "conversion-optimized layout", "page for launch"

Workflow:

1. Search landing: `python3 -m pitch_agent.uiux search --domain landing --query "{product_type}"`
2. Search product: `python3 -m pitch_agent.uiux search --domain product --query "{product_type}"`
3. Output: CTA strategy, section order, social proof placement, conversion optimization

Anti-patterns: Never structure copy without a positioning anchor. Never add sections that don't serve conversion.

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: add pitch-landing skill — conversion-optimized landing page patterns"
```

---

### Task 23: surge-landing skill

**Files:**

- Create: `team/surge/skills/surge-landing/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Trigger: "growth-optimized landing", "activation funnel layout", "experiment-friendly page"

Workflow:

1. Search landing: `python3 -m surge_agent.uiux search --domain landing --query "{product_type}"`
2. Search product: `python3 -m surge_agent.uiux search --domain product --query "{product_type}"`
3. Search UX for friction: `python3 -m surge_agent.uiux search --domain ux --query "forms validation loading"`
4. Output: experiment-friendly patterns, activation triggers, funnel structure, friction points

Anti-patterns: Never optimize for vanity metrics. Never add friction to capture data before demonstrating value.

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: add surge-landing skill — growth-optimized landing page patterns"
```

---

## Chunk 4: Enhanced Skills (8 total)

Each enhanced skill gets an additive `## Design Intelligence (via uiux)` section appended. All are independent and can be done in parallel.

---

### Task 24: Enhance form-brand

**Files:**

- Modify: `team/form/skills/form-brand/SKILL.md`

- [ ] **Step 1: Read current file**

Read `team/form/skills/form-brand/SKILL.md` to find exact insertion point.

- [ ] **Step 2: Insert between Phase 3 (Brand Adjectives + Visual Language) and Phase 4 (Design Tokens + Brand Brief)**

Insert this section after Phase 3.4 and before Phase 4.1 — color/style intelligence must be available before tokens and brand brief are produced:

````markdown
## Design Intelligence (via uiux)

After defining brand adjectives (Phase 3), query the design database to validate color and style choices against industry data:

```bash
python3 -m form_agent.uiux search --domain color --query "{industry/product_type}" --limit 3
python3 -m form_agent.uiux search --domain style --query "{product_type}" --limit 3
```
````

Use results to:

- Validate color palette aligns with industry conventions
- Check recommended style matches brand adjectives
- Cross-reference anti-patterns before finalizing

````

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: enhance form-brand with design intelligence color/style lookup"
````

---

### Task 25: Enhance form-tokens

**Files:**

- Modify: `team/form/skills/form-tokens/skill.md`

- [ ] **Step 1: Read and append after Phase 2 (Token Architecture)**

````markdown
## Design Intelligence (via uiux)

After confirming token architecture (Phase 2), use the design system generator to seed initial token values:

```bash
python3 -m form_agent.uiux design-system --product-type "{product_type}"
```
````

Use the generated design system output to:

- Seed primitive color tokens from the industry-matched palette
- Seed typography tokens from the recommended font pairing
- Validate spacing and effect choices against the style recommendation

````

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: enhance form-tokens with design system generator integration"
````

---

### Task 26: Enhance draft-review

**Files:**

- Modify: `team/draft/skills/draft-review/SKILL.md`

- [ ] **Step 1: Read and append after Step 3 (Nielsen's Heuristics)**

````markdown
## Design Intelligence (via uiux)

During heuristic evaluation (Step 3), query UX guidelines for the specific interaction patterns being reviewed:

```bash
python3 -m draft_agent.uiux search --domain ux --query "{pattern_category}" --limit 5
```
````

Use results to:

- Supplement Nielsen's heuristics with specific do/don't guidelines
- Check severity ratings from the database against your own assessment
- Reference platform-specific rules (web vs mobile) from the results

````

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: enhance draft-review with UX guidelines database lookup"
````

---

### Task 27: Enhance prism-component

**Files:**

- Modify: `team/prism/skills/prism-component/SKILL.md`

- [ ] **Step 1: Read and append after Step 0 (Read Environment)**

````markdown
## Design Intelligence (via uiux)

After detecting the project framework (Step 0), load stack-specific guidelines and icon references:

```bash
python3 -m prism_agent.uiux search --domain stacks --query "{detected_framework}" --limit 3
python3 -m prism_agent.uiux search --domain icons --query "{component_type}" --limit 5
```
````

Use results to:

- Follow framework-specific component patterns (e.g., React composition vs Vue slots)
- Select appropriate icons from the Phosphor Icons catalog
- Apply stack-specific accessibility and performance guidelines

````

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: enhance prism-component with stack guidelines and icon lookup"
````

---

### Task 28: Enhance prism-ui

**Files:**

- Modify: `team/prism/skills/prism-ui/SKILL.md`

- [ ] **Step 1: Read and append after Step 2 (Plan Component Structure)**

````markdown
## Design Intelligence (via uiux)

After planning the component structure (Step 2), query React/performance guidelines:

```bash
python3 -m prism_agent.uiux search --domain react --query "{optimization_area}" --limit 3
```
````

Use results to:

- Apply framework-specific performance patterns (memoization, code splitting, Suspense)
- Avoid documented performance anti-patterns
- Choose correct data fetching strategy based on the guidelines

````

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: enhance prism-ui with React performance guidelines lookup"
````

---

### Task 29: Enhance touch-app

**Files:**

- Modify: `team/touch/skills/touch-app/SKILL.md`

- [ ] **Step 1: Read and append inside Step 2 (Produce the Architecture), after Platform Decision section**

````markdown
## Design Intelligence (via uiux)

After the platform decision is made (Step 2, Platform Decision section), query platform-specific UI rules:

```bash
python3 -m touch_agent.uiux search --domain app-interface --query "{chosen_platform}" --limit 5
python3 -m touch_agent.uiux search --domain stacks --query "{chosen_framework}" --limit 3
```
````

Use results to:

- Validate platform choice against UI convention requirements (iOS vs Android)
- Apply framework-specific architecture patterns from stack guidelines
- Set performance budgets using platform-specific touch target and animation rules

````

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: enhance touch-app with mobile UI guidelines and stack lookup"
````

---

### Task 30: Enhance lens-dashboard

**Files:**

- Modify: `team/lens/skills/lens-dashboard/SKILL.md`

- [ ] **Step 1: Read and append after Step 2 (Define Dashboard Spec)**

````markdown
## Design Intelligence (via uiux)

When selecting chart types for each panel (Step 2), query the chart database:

```bash
python3 -m lens_agent.uiux search --domain chart --query "{data_type}" --limit 3
```
````

Use results to:

- Select optimal chart type based on data characteristics and volume threshold
- Check accessibility grade — prefer AA or higher for public dashboards
- Apply the recommended library (Chart.js, Recharts, D3, etc.) matching the detected stack
- Use the dashboard style search for overall visual treatment

````

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: enhance lens-dashboard with chart type intelligence"
````

---

### Task 31: Enhance pitch-copy

**Files:**

- Modify: `team/pitch/skills/pitch-copy/SKILL.md`

- [ ] **Step 1: Read and append after Step 1 (Establish Context)**

````markdown
## Design Intelligence (via uiux)

After establishing context (Step 1), query landing page patterns for structural guidance:

```bash
python3 -m pitch_agent.uiux search --domain landing --query "{product_type}" --limit 3
```
````

Use results to:

- Align copy block structure with proven landing page section orders
- Place CTAs according to the pattern's recommended placement
- Apply conversion optimization techniques specific to the product type

````

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: enhance pitch-copy with landing page pattern intelligence"
````

---

## Final Verification

### Task 32: End-to-end smoke test

- [ ] **Step 1: Verify shared library**

```bash
cd lib/uiux && .venv/bin/python -m pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 2: Verify Form wrapper (representative agent)**

```bash
cd team/form/scripts && bash setup.sh && .venv/bin/python -m pytest ../tests/test_uiux.py -v
```

Expected: All tests pass.

- [ ] **Step 3: Verify CLI works end-to-end**

```bash
cd team/form/scripts && .venv/bin/python -m form_agent.uiux search --domain color --query "fintech" --limit 2
```

Expected: JSON array with color palette results.

- [ ] **Step 4: Verify skill files exist**

```bash
find team/*/skills/*-style team/*/skills/*-palette team/*/skills/*-patterns team/*/skills/*-landing team/*/skills/*-stack team/*/skills/*-chart team/*/skills/*-ui -name "SKILL.md" 2>/dev/null | wc -l
```

Expected: 10

- [ ] **Step 5: Final commit**

```bash
git add -A
git status  # verify no unwanted files
git commit -m "feat: complete uiux design intelligence cross-pollination across 7 agents"
```
