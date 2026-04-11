"""
Design system generator — aggregates multi-domain BM25 searches and applies
UI reasoning rules to produce structured design recommendations.

Stdlib only — zero external dependencies.
"""

import csv
import json
import os
import re
from pathlib import Path

from .search import DATA_DIR, search

# ============ CONFIGURATION ============
_REASONING_FILE = DATA_DIR / "ui-reasoning.csv"

_SEARCH_CONFIG = {
    "product": {"max_results": 1},
    "style": {"max_results": 3},
    "color": {"max_results": 2},
    "landing": {"max_results": 2},
    "typography": {"max_results": 2},
}

_BOX_WIDTH = 90


# ============ HELPERS ============
def _load_reasoning() -> list[dict]:
    """Load UI reasoning rules from CSV."""
    if not _REASONING_FILE.exists():
        return []
    with open(_REASONING_FILE, "r", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _find_reasoning_rule(reasoning_data: list[dict], category: str) -> dict:
    """Return the best matching reasoning rule for a product category."""
    category_lower = category.lower()

    # Exact match
    for rule in reasoning_data:
        if rule.get("UI_Category", "").lower() == category_lower:
            return rule

    # Partial match
    for rule in reasoning_data:
        ui_cat = rule.get("UI_Category", "").lower()
        if ui_cat in category_lower or category_lower in ui_cat:
            return rule

    # Keyword match
    for rule in reasoning_data:
        ui_cat = rule.get("UI_Category", "").lower()
        keywords = re.split(r"[/\-\s]+", ui_cat)
        if any(kw and kw in category_lower for kw in keywords):
            return rule

    return {}


def _apply_reasoning(reasoning_data: list[dict], category: str) -> dict:
    """Apply reasoning rules and return a structured reasoning dict."""
    rule = _find_reasoning_rule(reasoning_data, category)

    if not rule:
        return {
            "pattern": "Hero + Features + CTA",
            "style_priority": ["Minimalism", "Flat Design"],
            "color_mood": "Professional",
            "typography_mood": "Clean",
            "key_effects": "Subtle hover transitions",
            "anti_patterns": "",
            "decision_rules": {},
            "severity": "MEDIUM",
        }

    decision_rules: dict = {}
    try:
        decision_rules = json.loads(rule.get("Decision_Rules", "{}"))
    except (json.JSONDecodeError, TypeError):
        pass

    return {
        "pattern": rule.get("Recommended_Pattern", ""),
        "style_priority": [
            s.strip() for s in rule.get("Style_Priority", "").split("+")
        ],
        "color_mood": rule.get("Color_Mood", ""),
        "typography_mood": rule.get("Typography_Mood", ""),
        "key_effects": rule.get("Key_Effects", ""),
        "anti_patterns": rule.get("Anti_Patterns", ""),
        "decision_rules": decision_rules,
        "severity": rule.get("Severity", "MEDIUM"),
    }


def _select_best_match(results: list[dict], priority_keywords: list[str]) -> dict:
    """Pick the result that best matches the priority keywords."""
    if not results:
        return {}
    if not priority_keywords:
        return results[0]

    # Exact style-name match first
    for priority in priority_keywords:
        priority_lower = priority.lower().strip()
        for result in results:
            style_name = result.get("Style Category", "").lower()
            if priority_lower in style_name or style_name in priority_lower:
                return result

    # Score by keyword match across all fields
    scored: list[tuple[int, dict]] = []
    for result in results:
        result_str = str(result).lower()
        score = 0
        for kw in priority_keywords:
            kw_lower = kw.lower().strip()
            if kw_lower in result.get("Style Category", "").lower():
                score += 10
            elif kw_lower in result.get("Keywords", "").lower():
                score += 3
            elif kw_lower in result_str:
                score += 1
        scored.append((score, result))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1] if scored and scored[0][0] > 0 else results[0]


def _generate(query: str, project_name: str | None = None) -> dict:
    """Run multi-domain search + reasoning and return a design-system dict."""
    reasoning_data = _load_reasoning()

    # Step 1 — product category
    product_results = search("product", query, 1)
    category = (
        product_results[0].get("Product Type", "General")
        if product_results
        else "General"
    )

    # Step 2 — reasoning rules
    reasoning = _apply_reasoning(reasoning_data, category)
    style_priority = reasoning.get("style_priority", [])

    # Step 3 — multi-domain search
    search_results: dict[str, list[dict]] = {}
    for domain, cfg in _SEARCH_CONFIG.items():
        if domain == "style" and style_priority:
            priority_q = " ".join(style_priority[:2])
            combined_q = f"{query} {priority_q}"
            search_results[domain] = search(domain, combined_q, cfg["max_results"])
        elif domain == "product":
            search_results[domain] = product_results
        else:
            search_results[domain] = search(domain, query, cfg["max_results"])

    # Step 4 — best matches
    style_results = search_results.get("style", [])
    color_results = search_results.get("color", [])
    typography_results = search_results.get("typography", [])
    landing_results = search_results.get("landing", [])

    best_style = _select_best_match(style_results, style_priority)
    best_color = color_results[0] if color_results else {}
    best_typography = typography_results[0] if typography_results else {}
    best_landing = landing_results[0] if landing_results else {}

    # Step 5 — combine effects
    style_effects = best_style.get("Effects & Animation", "")
    reasoning_effects = reasoning.get("key_effects", "")
    combined_effects = style_effects if style_effects else reasoning_effects

    return {
        "project_name": project_name or query.upper(),
        "category": category,
        "pattern": {
            "name": best_landing.get(
                "Pattern Name", reasoning.get("pattern", "Hero + Features + CTA")
            ),
            "sections": best_landing.get("Section Order", "Hero > Features > CTA"),
            "cta_placement": best_landing.get("Primary CTA Placement", "Above fold"),
            "color_strategy": best_landing.get("Color Strategy", ""),
            "conversion": best_landing.get("Conversion Optimization", ""),
        },
        "style": {
            "name": best_style.get("Style Category", "Minimalism"),
            "type": best_style.get("Type", "General"),
            "effects": style_effects,
            "keywords": best_style.get("Keywords", ""),
            "best_for": best_style.get("Best For", ""),
            "performance": best_style.get("Performance", ""),
            "accessibility": best_style.get("Accessibility", ""),
            "light_mode": best_style.get("Light Mode ✓", ""),
            "dark_mode": best_style.get("Dark Mode ✓", ""),
        },
        "colors": {
            "primary": best_color.get("Primary", "#2563EB"),
            "on_primary": best_color.get("On Primary", ""),
            "secondary": best_color.get("Secondary", "#3B82F6"),
            "accent": best_color.get("Accent", "#F97316"),
            "background": best_color.get("Background", "#F8FAFC"),
            "foreground": best_color.get("Foreground", "#1E293B"),
            "muted": best_color.get("Muted", ""),
            "border": best_color.get("Border", ""),
            "destructive": best_color.get("Destructive", ""),
            "ring": best_color.get("Ring", ""),
            "notes": best_color.get("Notes", ""),
            "cta": best_color.get("Accent", "#F97316"),
            "text": best_color.get("Foreground", "#1E293B"),
        },
        "typography": {
            "heading": best_typography.get("Heading Font", "Inter"),
            "body": best_typography.get("Body Font", "Inter"),
            "mood": best_typography.get(
                "Mood/Style Keywords", reasoning.get("typography_mood", "")
            ),
            "best_for": best_typography.get("Best For", ""),
            "google_fonts_url": best_typography.get("Google Fonts URL", ""),
            "css_import": best_typography.get("CSS Import", ""),
        },
        "key_effects": combined_effects,
        "anti_patterns": reasoning.get("anti_patterns", ""),
        "decision_rules": reasoning.get("decision_rules", {}),
        "severity": reasoning.get("severity", "MEDIUM"),
    }


# ============ FORMATTERS ============
def _hex_to_ansi(hex_color: str) -> str:
    """Convert hex color to ANSI truecolor swatch, or empty string if unsupported."""
    if not hex_color or not hex_color.startswith("#"):
        return ""
    colorterm = os.environ.get("COLORTERM", "")
    if colorterm not in ("truecolor", "24bit"):
        return ""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return ""
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return f"\033[38;2;{r};{g};{b}m██\033[0m "


def _ansi_ljust(s: str, width: int) -> str:
    """ljust that ignores ANSI escape sequences in the visible length calculation."""
    visible_len = len(re.sub(r"\033\[[0-9;]*m", "", s))
    return s + (" " * max(0, width - visible_len))


def _section_header(name: str, width: int) -> str:
    """Unicode section separator: ├─── NAME ───...┤"""
    label = f"─── {name} "
    fill = "─" * (width - len(label) - 1)
    return f"├{label}{fill}┤"


def _wrap_text(text: str, prefix: str, width: int) -> list[str]:
    """Word-wrap text into lines with the given prefix, bounded by width."""
    if not text:
        return []
    words = text.split()
    lines: list[str] = []
    current = prefix
    for word in words:
        if len(current) + len(word) + 1 <= width - 2:
            current += (" " if current != prefix else "") + word
        else:
            if current != prefix:
                lines.append(current)
            current = prefix + word
    if current != prefix:
        lines.append(current)
    return lines


def _format_ascii(ds: dict) -> str:
    """Render design system as a Unicode box diagram."""
    project = ds.get("project_name", "PROJECT")
    pattern = ds.get("pattern", {})
    style = ds.get("style", {})
    colors = ds.get("colors", {})
    typography = ds.get("typography", {})
    effects = ds.get("key_effects", "")
    anti_patterns = ds.get("anti_patterns", "")

    w = _BOX_WIDTH - 1
    lines: list[str] = []

    lines.append("╔" + "═" * w + "╗")
    lines.append(
        _ansi_ljust(f"║  TARGET: {project} - RECOMMENDED DESIGN SYSTEM", _BOX_WIDTH)
        + "║"
    )
    lines.append("╚" + "═" * w + "╝")
    lines.append("┌" + "─" * w + "┐")

    # Pattern
    lines.append(_section_header("PATTERN", _BOX_WIDTH + 1))
    lines.append(f"│  Name: {pattern.get('name', '')}".ljust(_BOX_WIDTH) + "│")
    if pattern.get("conversion"):
        lines.append(
            f"│     Conversion: {pattern.get('conversion', '')}".ljust(_BOX_WIDTH) + "│"
        )
    if pattern.get("cta_placement"):
        lines.append(
            f"│     CTA: {pattern.get('cta_placement', '')}".ljust(_BOX_WIDTH) + "│"
        )
    sections = [s.strip() for s in pattern.get("sections", "").split(">") if s.strip()]
    lines.append("│     Sections:".ljust(_BOX_WIDTH) + "│")
    for i, section in enumerate(sections, 1):
        lines.append(f"│       {i}. {section}".ljust(_BOX_WIDTH) + "│")

    # Style
    lines.append(_section_header("STYLE", _BOX_WIDTH + 1))
    lines.append(f"│  Name: {style.get('name', '')}".ljust(_BOX_WIDTH) + "│")
    light = style.get("light_mode", "")
    dark = style.get("dark_mode", "")
    if light or dark:
        lines.append(
            f"│     Mode Support: Light {light}  Dark {dark}".ljust(_BOX_WIDTH) + "│"
        )
    for line in _wrap_text(
        f"Keywords: {style.get('keywords', '')}", "│     ", _BOX_WIDTH
    ):
        lines.append(line.ljust(_BOX_WIDTH) + "│")
    for line in _wrap_text(
        f"Best For: {style.get('best_for', '')}", "│     ", _BOX_WIDTH
    ):
        lines.append(line.ljust(_BOX_WIDTH) + "│")
    if style.get("performance") or style.get("accessibility"):
        pa = f"Performance: {style.get('performance', '')} | Accessibility: {style.get('accessibility', '')}"
        lines.append(f"│     {pa}".ljust(_BOX_WIDTH) + "│")

    # Colors
    lines.append(_section_header("COLORS", _BOX_WIDTH + 1))
    color_entries = [
        ("Primary", "primary", "--color-primary"),
        ("On Primary", "on_primary", "--color-on-primary"),
        ("Secondary", "secondary", "--color-secondary"),
        ("Accent/CTA", "accent", "--color-accent"),
        ("Background", "background", "--color-background"),
        ("Foreground", "foreground", "--color-foreground"),
        ("Muted", "muted", "--color-muted"),
        ("Border", "border", "--color-border"),
        ("Destructive", "destructive", "--color-destructive"),
        ("Ring", "ring", "--color-ring"),
    ]
    for label, key, css_var in color_entries:
        hex_val = colors.get(key, "")
        if not hex_val:
            continue
        swatch = _hex_to_ansi(hex_val)
        content = f"│     {swatch}{label + ':':14s} {hex_val:10s} ({css_var})"
        lines.append(_ansi_ljust(content, _BOX_WIDTH) + "│")
    if colors.get("notes"):
        for line in _wrap_text(
            f"Notes: {colors.get('notes', '')}", "│     ", _BOX_WIDTH
        ):
            lines.append(line.ljust(_BOX_WIDTH) + "│")

    # Typography
    lines.append(_section_header("TYPOGRAPHY", _BOX_WIDTH + 1))
    lines.append(
        f"│  {typography.get('heading', '')} / {typography.get('body', '')}".ljust(
            _BOX_WIDTH
        )
        + "│"
    )
    for line in _wrap_text(f"Mood: {typography.get('mood', '')}", "│     ", _BOX_WIDTH):
        lines.append(line.ljust(_BOX_WIDTH) + "│")
    for line in _wrap_text(
        f"Best For: {typography.get('best_for', '')}", "│     ", _BOX_WIDTH
    ):
        lines.append(line.ljust(_BOX_WIDTH) + "│")
    if typography.get("google_fonts_url"):
        lines.append(
            f"│     Google Fonts: {typography.get('google_fonts_url', '')}".ljust(
                _BOX_WIDTH
            )
            + "│"
        )
    if typography.get("css_import"):
        lines.append(
            f"│     CSS Import: {typography.get('css_import', '')[:70]}...".ljust(
                _BOX_WIDTH
            )
            + "│"
        )

    # Key Effects
    if effects:
        lines.append(_section_header("KEY EFFECTS", _BOX_WIDTH + 1))
        for line in _wrap_text(effects, "│     ", _BOX_WIDTH):
            lines.append(line.ljust(_BOX_WIDTH) + "│")

    # Avoid
    if anti_patterns:
        lines.append(_section_header("AVOID", _BOX_WIDTH + 1))
        for line in _wrap_text(anti_patterns, "│     ", _BOX_WIDTH):
            lines.append(line.ljust(_BOX_WIDTH) + "│")

    # Checklist
    lines.append(_section_header("PRE-DELIVERY CHECKLIST", _BOX_WIDTH + 1))
    checklist = [
        "[ ] No emojis as icons (use SVG: Heroicons/Lucide)",
        "[ ] cursor-pointer on all clickable elements",
        "[ ] Hover states with smooth transitions (150-300ms)",
        "[ ] Light mode: text contrast 4.5:1 minimum",
        "[ ] Focus states visible for keyboard nav",
        "[ ] prefers-reduced-motion respected",
        "[ ] Responsive: 375px, 768px, 1024px, 1440px",
    ]
    for item in checklist:
        lines.append(f"│     {item}".ljust(_BOX_WIDTH) + "│")

    lines.append("└" + "─" * w + "┘")
    return "\n".join(lines)


# ============ PUBLIC API ============
def generate_design_system(product_type: str) -> str:
    """
    Generate a complete design system recommendation for the given product type.

    Args:
        product_type: Description of the product (e.g. "SaaS dashboard", "e-commerce luxury").

    Returns:
        Formatted design system as a Unicode box diagram string.
    """
    ds = _generate(product_type)
    return _format_ascii(ds)
