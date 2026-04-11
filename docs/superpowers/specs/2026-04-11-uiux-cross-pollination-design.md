# UI/UX Design Intelligence Cross-Pollination

**Date:** 2026-04-11
**Target:** 7 tonone agents (Form, Draft, Prism, Touch, Lens, Pitch, Surge)

## Goal

Add curated design intelligence (161 color palettes, 84 UI styles, 57 font pairings, 99 UX guidelines, 25 chart types, 16 stack-specific guides, BM25 search engine, and design system generator) to tonone agents — matching data domains to agent expertise, with shared data and per-agent scoped access.

## Architecture

### Shared Library: `lib/uiux/`

Single source of truth for all design intelligence data and search tooling. Lives at repo root.

```
lib/uiux/
├── pyproject.toml            # installable package "uiux", requires-python >=3.10
├── setup.sh                  # create venv, install package
├── tests/
│   ├── test_search.py        # BM25 ranking, regex matching, edge cases
│   ├── test_domains.py       # CSV loading, schema validation per domain
│   ├── test_design_system.py # generator output for known/unknown product types
│   └── test_cli.py           # CLI smoke tests
├── uiux/
│   ├── __init__.py
│   ├── search.py             # BM25 search engine (ported from source core.py)
│   ├── design_system.py      # design system generator (ported from source)
│   ├── cli.py                # shared CLI entrypoint
│   └── data/                 # all CSV databases
│       ├── styles.csv            (84 UI styles: general, landing page, BI dashboard)
│       ├── colors.csv            (161 industry-matched color palettes, shadcn-compatible)
│       ├── typography.csv        (57 curated font pairings with Google Fonts URLs)
│       ├── google-fonts.csv      (1,923 fonts from Google Fonts catalog)
│       ├── products.csv          (161 product types → style/color/pattern mapping)
│       ├── ui-reasoning.csv      (161 reasoning rules with anti-patterns, severity)
│       ├── landing.csv           (24 landing page patterns with CTA placement)
│       ├── charts.csv            (25 chart types with accessibility grades)
│       ├── ux-guidelines.csv     (99 UX guidelines: do/don't with code examples)
│       ├── react-performance.csv (React/Next.js performance best practices)
│       ├── app-interface.csv     (mobile/native UI rules: iOS, Android, RN)
│       ├── icons.csv             (icon catalog with Phosphor Icons)
│       └── stacks/               (16 framework-specific guideline files)
│           ├── react.csv
│           ├── nextjs.csv
│           ├── vue.csv
│           ├── nuxtjs.csv
│           ├── nuxt-ui.csv
│           ├── svelte.csv
│           ├── astro.csv
│           ├── html-tailwind.csv
│           ├── shadcn-ui.csv
│           ├── swiftui.csv
│           ├── react-native.csv
│           ├── flutter.csv
│           ├── jetpack-compose.csv
│           ├── angular.csv
│           ├── laravel.csv
│           └── threejs.csv
```

### Search Engine

Ported from source `core.py` (12KB). BM25 ranking + regex matching hybrid.

**Domains:** `style`, `color`, `chart`, `landing`, `product`, `ux`, `typography`, `icons`, `react`, `web`, `google-fonts`, `app-interface`, `stacks`

**CLI interface:**

```bash
python3 -m uiux search --domain color --query "fintech banking" --limit 5
python3 -m uiux design-system --product-type "fintech SaaS"
python3 -m uiux domains
```

### Design System Generator

Ported from source `design_system.py` (47KB). Runs 5 parallel searches (product, style, color, landing, typography), finds matching reasoning rule, applies JSON decision_rules conditionals, outputs complete design system specification.

**Output includes:** Pattern, Style, Colors (full token set), Typography, Key Effects, Anti-patterns, Pre-delivery checklist.

## Agent-to-Domain Mapping

### Form (Visual Designer)

**Domains:** style, color, typography, google-fonts, product

**Rationale:** Form owns visual direction — styles, color systems, typography, brand identity. The product/reasoning data helps Form make industry-informed visual decisions instead of aesthetic-only choices.

**Wrapper:** `team/form/scripts/form_agent/uiux/`

- `query(domain, terms, limit)` — search within allowed domains
- `design_system(product_type)` — full design system generation (Form-exclusive)

**New skills:**

| Skill          | Trigger                                          | Workflow                                                                                               |
| -------------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| `form-style`   | "select a UI style", "design direction for X"    | Search product → get reasoning rule → match style → output style + effects + anti-patterns + checklist |
| `form-palette` | "color palette for X", "industry-matched colors" | Search product → search color → output full shadcn-compatible token set                                |

**Enhanced skills:**

- `form-brand` — add style + color search for brand-aligned palette generation
- `form-tokens` — add design system generator reference for token architecture

### Draft (UX Designer)

**Domains:** ux, landing, product

**Rationale:** Draft owns user flows and interaction patterns. UX guidelines provide heuristic evaluation data. Landing patterns inform page-level information architecture. Product reasoning helps match UX patterns to industry expectations.

**Wrapper:** `team/draft/scripts/draft_agent/uiux/`

- `query(domain, terms, limit)` — search within allowed domains

**New skills:**

| Skill            | Trigger                            | Workflow                                                                     |
| ---------------- | ---------------------------------- | ---------------------------------------------------------------------------- |
| `draft-patterns` | "UX pattern for forms/nav/loading" | Search ux-guidelines → return do/don't + code examples                       |
| `draft-landing`  | "landing page structure for X"     | Search landing + product → section order, CTA placement, conversion strategy |

**Enhanced skills:**

- `draft-review` — add UX guidelines search for heuristic evaluation scoring

### Prism (Frontend/DX)

**Domains:** react, web, stacks (all 16), icons, chart

**Rationale:** Prism implements designs. Stack-specific guidelines prevent framework anti-patterns. Chart data guides visualization implementation. Icons provide component references. React-performance covers optimization.

**Wrapper:** `team/prism/scripts/prism_agent/uiux/`

- `query(domain, terms, limit)` — search within allowed domains
- `stack_guide(stack_name)` — return full guidelines for a specific framework

**New skills:**

| Skill         | Trigger                               | Workflow                                                                  |
| ------------- | ------------------------------------- | ------------------------------------------------------------------------- |
| `prism-stack` | "best practices for React/Vue/Svelte" | Load stack CSV → return framework-specific guidelines                     |
| `prism-chart` | "implement chart for X data"          | Search charts → chart type + library recommendation + accessibility grade |

**Enhanced skills:**

- `prism-component` — add stack guidelines + icons for implementation context
- `prism-ui` — add react-performance for optimization guidance

### Touch (Mobile)

**Domains:** app-interface, stacks (SwiftUI, React Native, Flutter, Jetpack Compose)

**Rationale:** Touch owns mobile. App-interface CSV has platform-specific UI rules (touch targets, safe areas, Dynamic Type, system gestures). Mobile stack guides provide framework-level best practices.

**Wrapper:** `team/touch/scripts/touch_agent/uiux/`

- `query(domain, terms, limit)` — search within allowed domains
- `stack_guide(stack_name)` — mobile stacks only (swiftui, react-native, flutter, jetpack-compose)

**New skill:**

| Skill      | Trigger                                       | Workflow                                                             |
| ---------- | --------------------------------------------- | -------------------------------------------------------------------- |
| `touch-ui` | "mobile UI guidelines", "touch targets for X" | Search app-interface + mobile stack → platform rules + code examples |

**Enhanced skills:**

- `touch-app` — add app-interface + mobile stack references for architecture decisions
- (touch-feature already detailed enough — no change)

### Lens (Data Analytics & BI)

**Domains:** chart, style (dashboard subset)

**Rationale:** Lens designs analytics dashboards. Chart type selection is core to BI work. Dashboard styles from styles.csv (10 BI/Analytics entries) inform visual treatment of data interfaces.

**Wrapper:** `team/lens/scripts/lens_agent/uiux/`

- `query(domain, terms, limit)` — chart + style domains only
- Style queries auto-filter to BI/Analytics Dashboard category by appending `" BI Dashboard"` to the query string before passing to `search()`. The wrapper's `query()` method intercepts `domain="style"` and rewrites: `terms = f"{terms} BI Dashboard"`

**New skill:**

| Skill        | Trigger                                             | Workflow                                                                                                                          |
| ------------ | --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `lens-chart` | "chart type for X data", "best visualization for Y" | Search charts → type + accessibility + library + interaction level. Optimized for BI: data density, drill-down, real-time context |

**Enhanced skills:**

- `lens-dashboard` — add chart type search + dashboard style reference

### Pitch (Product Marketing)

**Domains:** landing, product

**Rationale:** Pitch writes landing page copy and launch plans. Landing patterns inform copy structure (section order, CTA placement). Product data matches positioning to industry conventions.

**Wrapper:** `team/pitch/scripts/pitch_agent/uiux/`

- `query(domain, terms, limit)` — landing + product domains only

**New skill:**

| Skill           | Trigger                                                 | Workflow                                                                       |
| --------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `pitch-landing` | "landing page structure", "conversion-optimized layout" | Search landing + product → CTA strategy, section order, social proof placement |

**Enhanced skills:**

- `pitch-copy` — add landing pattern reference for copy-structure alignment

### Surge (Growth)

**Domains:** landing, product, ux

**Rationale:** Surge optimizes acquisition and activation funnels. Landing/product data through a growth lens — which patterns drive activation, where to place experiments, viral mechanics. UX guidelines added (beyond Pitch's set) because activation funnel friction is a UX problem — Surge needs form validation patterns, loading state best practices, and navigation anti-patterns to diagnose and fix conversion drops.

**Wrapper:** `team/surge/scripts/surge_agent/uiux/`

- `query(domain, terms, limit)` — landing + product + ux domains

**New skill:**

| Skill           | Trigger                                                | Workflow                                                                                                                                                                                                                   |
| --------------- | ------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `surge-landing` | "growth-optimized landing", "activation funnel layout" | Search landing + product + ux → experiment-friendly patterns, activation triggers, funnel structure. UX domain queried for friction points: form validation, loading states, navigation anti-patterns that hurt conversion |

## Per-Agent Wrapper Pattern

Each wrapper is a **subpackage** (directory with `__init__.py` + `__main__.py`), not a flat file. This enables `python3 -m` CLI invocation.

```
team/{agent}/scripts/{agent}_agent/
├── __init__.py
├── uiux/                   # wrapper subpackage
│   ├── __init__.py         # exports query(), design_system() (Form only)
│   └── __main__.py         # CLI: search, design-system, domains
```

**`uiux/__init__.py`:**

```python
"""Agent design intelligence wrapper — scoped to agent's domains."""

from uiux.search import search
from uiux.design_system import generate_design_system  # Form only

ALLOWED_DOMAINS = {"domain1", "domain2"}  # agent-specific

def query(domain: str, terms: str, limit: int = 5) -> list[dict]:
    if domain not in ALLOWED_DOMAINS:
        raise ValueError(f"Domain '{domain}' not available for this agent")
    return search(domain=domain, query=terms, limit=limit)
```

**`uiux/__main__.py`:**

```python
"""CLI entrypoint: python3 -m {agent}_agent.uiux search --domain color 'fintech'"""
import argparse, json, sys
from . import query, ALLOWED_DOMAINS

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")

    s = sub.add_parser("search")
    s.add_argument("--domain", required=True)
    s.add_argument("--query", required=True)
    s.add_argument("--limit", type=int, default=5)

    sub.add_parser("domains")

    args = parser.parse_args()
    if args.cmd == "domains":
        print(json.dumps(sorted(ALLOWED_DOMAINS)))
    elif args.cmd == "search":
        results = query(args.domain, args.query, args.limit)
        print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
```

**CLI invocation from skills:**

```bash
python3 -m {agent}_agent.uiux search --domain {domain} --query "{query}"
python3 -m {agent}_agent.uiux domains
```

**Graceful degradation:** If `uiux` package is not installed, the wrapper's `__init__.py` catches `ImportError` and raises a clear error: `"uiux package not found — run: cd lib/uiux && bash setup.sh, then reinstall this agent"`.

## Dependency Chain

No separate shared venv. The `uiux` package is installed as an editable dependency **into each agent's own venv**.

```
team/{agent}/scripts/pyproject.toml         # 1. declares uiux as relative path dependency
    dependencies = ["uiux"]
    [tool.uv.sources]                       # uv-style path dep
    uiux = { path = "../../../lib/uiux", editable = true }
    ↓
team/{agent}/scripts/setup.sh               # 2. creates agent venv, installs agent + uiux
    ↓
team/{agent}/hooks/hooks.json               # 3. post_install triggers setup.sh
```

**Updated `setup.sh` pattern** (added lines marked with `# NEW`):

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

UIUX_LIB="$SCRIPT_DIR/../../../lib/uiux"                          # NEW
if [ ! -d "$UIUX_LIB/uiux" ]; then                                # NEW
	echo "uiux lib not found at $UIUX_LIB — skipping design intelligence"  # NEW
fi                                                                  # NEW

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

echo "{Agent} ready."
```

**Both `uv` and `pip` handle relative path editable installs.** The `pyproject.toml` uses `[tool.uv.sources]` for uv compatibility, while pip falls back to the `[project.dependencies]` entry. Tested pattern: `pip install -e .` resolves the relative path in `pyproject.toml` automatically.

## New Skill Format

**Filename:** `SKILL.md` (uppercase) — matches the majority convention across tonone agents. Only Form's newer skills and relay-ship use lowercase `skill.md`; all other agents use `SKILL.md`.

All new skills follow tonone convention:

```markdown
---
name: {agent}-{action}
description: |
  Use when [trigger conditions with examples]
allowed-tools: Read, Bash, Glob, Grep
version: 0.6.6
author: tonone-ai <hello@tonone.ai>
license: MIT
---

# {agent}-{action} — Title

## When to use

[Conditions and context]

## Workflow

1. [Step with actual CLI command]
2. [Step with actual CLI command]
3. [Output formatting step]

## Output format

[Structured output matching tonone output kit: 40-line max, box-drawing, severity indicators]

## Anti-patterns

- [What not to do, sourced from ui-reasoning.csv where applicable]
```

## Existing Skill Enhancement Pattern

Additive only — append a `## Design Intelligence (via uiux)` section to existing SKILL.md. No rewriting of existing skill logic.

**Exact insertion points for each enhanced skill:**

| Skill             | Insert after phase/section   | Trigger                                   | Query                                                                                 |
| ----------------- | ---------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------- |
| `form-brand`      | Phase 2 (Color System)       | When defining brand color palette         | `search --domain color "{industry}"` + `search --domain style "{product_type}"`       |
| `form-tokens`     | Phase 1 (Token Architecture) | When scaffolding token layers             | `design-system --product-type "{type}"` to seed primitive + semantic tokens           |
| `draft-review`    | Phase 2 (Friction Pass)      | When evaluating interaction patterns      | `search --domain ux "{pattern_category}"` for heuristic do/don't                      |
| `prism-component` | Phase 1 (Stack Detection)    | After detecting project framework         | `search --domain stacks "{framework}"` + `search --domain icons "{component_type}"`   |
| `prism-ui`        | Phase 3 (Performance)        | When optimizing render performance        | `search --domain react "{optimization_area}"`                                         |
| `touch-app`       | Phase 2 (Platform Selection) | After choosing iOS/Android/cross-platform | `search --domain app-interface "{platform}"` + `search --domain stacks "{framework}"` |
| `lens-dashboard`  | Phase 1 (Chart Selection)    | When choosing visualization types         | `search --domain chart "{data_type}"`                                                 |
| `pitch-copy`      | Phase 2 (Page Structure)     | When structuring landing page copy blocks | `search --domain landing "{product_type}"` for section order + CTA placement          |

**Template for each insertion:**

```markdown
## Design Intelligence (via uiux)

After [specific phase step above], query the design database:

\`\`\`bash
python3 -m {agent}\_agent.uiux search --domain {domain} --query "{query}"
\`\`\`

Use results to [specific action]: validate choice against industry data / seed initial values / check for anti-patterns.
```

## Inventory

| Category             | Count       | Files                                                                                                                                             |
| -------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Shared library       | 1 directory | `lib/uiux/` — 4 Python files (**init**, search, design_system, cli) + 28 CSVs (12 top-level + 16 stacks/) + pyproject.toml + setup.sh = ~34 files |
| Shared library tests | 1 directory | `lib/uiux/tests/` — search unit tests, domain scoping tests, CLI smoke tests                                                                      |
| New skills           | 10          | form-style, form-palette, draft-patterns, draft-landing, prism-stack, prism-chart, touch-ui, lens-chart, pitch-landing, surge-landing             |
| Enhanced skills      | 8           | form-brand, form-tokens, draft-review, prism-component, prism-ui, touch-app, lens-dashboard, pitch-copy                                           |
| Agent wrappers       | 7           | form, draft, prism, touch, lens, pitch, surge — each gets uiux/ subpackage (**init**.py + **main**.py)                                            |
| Setup changes        | 7           | Each agent's setup.sh and pyproject.toml updated                                                                                                  |
| **Total new files**  | **~70**     | 34 lib + 4 test files + 10 skills + 14 wrapper files + 7 setup changes = ~69 files                                                                |

## What Does NOT Change

- Agent definitions (`agents/*.md`) — no scope or responsibility changes
- Existing skill logic — only additive sections appended
- Plugin manifests (`.claude-plugin/plugin.json`) — skills auto-discovered
- Bundle configurations — no changes
- Hooks — only setup.sh dependency chain added

## Risks and Mitigations

| Risk                                                 | Mitigation                                                                       |
| ---------------------------------------------------- | -------------------------------------------------------------------------------- |
| Path dependency breaks if agent installed standalone | Wrapper fails gracefully: "uiux package not found — run lib/uiux/setup.sh first" |
| google-fonts.csv is 745KB, bloats repo               | Single copy in shared lib, not duplicated per agent                              |
| Source repo search engine has external deps          | Port with zero external deps — BM25 is pure Python, CSV stdlib                   |
| Design system generator is 47KB of logic             | Only exposed to Form agent, others get search-only access                        |

## Testing

### Shared Library Tests (`lib/uiux/tests/`)

| Test file               | Covers                                                                                                                     |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `test_search.py`        | BM25 ranking correctness, regex matching, empty queries, missing domains, result limit enforcement                         |
| `test_domains.py`       | All 13 domains load their CSVs without error, column schemas match expected headers                                        |
| `test_design_system.py` | Generator produces valid output for known product types, handles unknown product types gracefully                          |
| `test_cli.py`           | CLI smoke tests: `search` returns JSON, `domains` lists all, `design-system` produces output, invalid domain returns error |

### Per-Agent Wrapper Tests (`team/{agent}/tests/`)

Each agent with a uiux wrapper gets one test file `test_uiux.py`:

| Test                         | Covers                                                                        |
| ---------------------------- | ----------------------------------------------------------------------------- |
| `test_allowed_domains`       | Wrapper only exposes agent's assigned domains, rejects others with ValueError |
| `test_query_returns_results` | At least one domain returns non-empty results for a known query               |
| `test_cli_smoke`             | `python3 -m {agent}_agent.uiux domains` returns expected domain list          |

### Coverage target

80% for `lib/uiux/` (core search + generator). Wrapper tests are smoke-level — the shared library tests cover the heavy logic.
