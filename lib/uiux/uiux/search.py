"""
BM25 search engine for UI/UX design data files.

Stdlib only — zero external dependencies.
"""

import csv
import re
from collections import defaultdict
from math import log
from pathlib import Path

# ============ CONFIGURATION ============
DATA_DIR = Path(__file__).parent / "data"

CSV_CONFIG = {
    "style": {
        "file": "styles.csv",
        "search_cols": [
            "Style Category",
            "Keywords",
            "Best For",
            "Type",
            "AI Prompt Keywords",
        ],
        "output_cols": [
            "Style Category",
            "Type",
            "Keywords",
            "Primary Colors",
            "Effects & Animation",
            "Best For",
            "Light Mode ✓",
            "Dark Mode ✓",
            "Performance",
            "Accessibility",
            "Framework Compatibility",
            "Complexity",
            "AI Prompt Keywords",
            "CSS/Technical Keywords",
            "Implementation Checklist",
            "Design System Variables",
        ],
    },
    "color": {
        "file": "colors.csv",
        "search_cols": ["Product Type", "Notes"],
        "output_cols": [
            "Product Type",
            "Primary",
            "On Primary",
            "Secondary",
            "On Secondary",
            "Accent",
            "On Accent",
            "Background",
            "Foreground",
            "Card",
            "Card Foreground",
            "Muted",
            "Muted Foreground",
            "Border",
            "Destructive",
            "On Destructive",
            "Ring",
            "Notes",
        ],
    },
    "chart": {
        "file": "charts.csv",
        "search_cols": [
            "Data Type",
            "Keywords",
            "Best Chart Type",
            "When to Use",
            "When NOT to Use",
            "Accessibility Notes",
        ],
        "output_cols": [
            "Data Type",
            "Keywords",
            "Best Chart Type",
            "Secondary Options",
            "When to Use",
            "When NOT to Use",
            "Data Volume Threshold",
            "Color Guidance",
            "Accessibility Grade",
            "Accessibility Notes",
            "A11y Fallback",
            "Library Recommendation",
            "Interactive Level",
        ],
    },
    "landing": {
        "file": "landing.csv",
        "search_cols": [
            "Pattern Name",
            "Keywords",
            "Conversion Optimization",
            "Section Order",
        ],
        "output_cols": [
            "Pattern Name",
            "Keywords",
            "Section Order",
            "Primary CTA Placement",
            "Color Strategy",
            "Conversion Optimization",
        ],
    },
    "product": {
        "file": "products.csv",
        "search_cols": [
            "Product Type",
            "Keywords",
            "Primary Style Recommendation",
            "Key Considerations",
        ],
        "output_cols": [
            "Product Type",
            "Keywords",
            "Primary Style Recommendation",
            "Secondary Styles",
            "Landing Page Pattern",
            "Dashboard Style (if applicable)",
            "Color Palette Focus",
        ],
    },
    "ux": {
        "file": "ux-guidelines.csv",
        "search_cols": ["Category", "Issue", "Description", "Platform"],
        "output_cols": [
            "Category",
            "Issue",
            "Platform",
            "Description",
            "Do",
            "Don't",
            "Code Example Good",
            "Code Example Bad",
            "Severity",
        ],
    },
    "typography": {
        "file": "typography.csv",
        "search_cols": [
            "Font Pairing Name",
            "Category",
            "Mood/Style Keywords",
            "Best For",
            "Heading Font",
            "Body Font",
        ],
        "output_cols": [
            "Font Pairing Name",
            "Category",
            "Heading Font",
            "Body Font",
            "Mood/Style Keywords",
            "Best For",
            "Google Fonts URL",
            "CSS Import",
            "Tailwind Config",
            "Notes",
        ],
    },
    "icons": {
        "file": "icons.csv",
        "search_cols": ["Category", "Icon Name", "Keywords", "Best For"],
        "output_cols": [
            "Category",
            "Icon Name",
            "Keywords",
            "Library",
            "Import Code",
            "Usage",
            "Best For",
            "Style",
        ],
    },
    "react": {
        "file": "react-performance.csv",
        "search_cols": ["Category", "Issue", "Keywords", "Description"],
        "output_cols": [
            "Category",
            "Issue",
            "Platform",
            "Description",
            "Do",
            "Don't",
            "Code Example Good",
            "Code Example Bad",
            "Severity",
        ],
    },
    "web": {
        "file": "app-interface.csv",
        "search_cols": ["Category", "Issue", "Keywords", "Description"],
        "output_cols": [
            "Category",
            "Issue",
            "Platform",
            "Description",
            "Do",
            "Don't",
            "Code Example Good",
            "Code Example Bad",
            "Severity",
        ],
    },
    "google-fonts": {
        "file": "google-fonts.csv",
        "search_cols": [
            "Family",
            "Category",
            "Stroke",
            "Classifications",
            "Keywords",
            "Subsets",
            "Designers",
        ],
        "output_cols": [
            "Family",
            "Category",
            "Stroke",
            "Classifications",
            "Styles",
            "Variable Axes",
            "Subsets",
            "Designers",
            "Popularity Rank",
            "Google Fonts URL",
        ],
    },
    "app-interface": {
        "file": "app-interface.csv",
        "search_cols": ["Category", "Issue", "Keywords", "Description"],
        "output_cols": [
            "Category",
            "Issue",
            "Platform",
            "Description",
            "Do",
            "Don't",
            "Code Example Good",
            "Code Example Bad",
            "Severity",
        ],
    },
    "ui-reasoning": {
        "file": "ui-reasoning.csv",
        "search_cols": [
            "UI_Category",
            "Style_Priority",
            "Color_Mood",
            "Typography_Mood",
        ],
        "output_cols": [
            "UI_Category",
            "Recommended_Pattern",
            "Style_Priority",
            "Color_Mood",
            "Typography_Mood",
            "Key_Effects",
            "Anti_Patterns",
            "Decision_Rules",
            "Severity",
        ],
    },
}

# Stack configs — stacks/ subdirectory, common columns
STACK_CONFIG = {
    "react": {"file": "stacks/react.csv"},
    "nextjs": {"file": "stacks/nextjs.csv"},
    "vue": {"file": "stacks/vue.csv"},
    "nuxtjs": {"file": "stacks/nuxtjs.csv"},
    "nuxt-ui": {"file": "stacks/nuxt-ui.csv"},
    "svelte": {"file": "stacks/svelte.csv"},
    "astro": {"file": "stacks/astro.csv"},
    "html-tailwind": {"file": "stacks/html-tailwind.csv"},
    "shadcn-ui": {"file": "stacks/shadcn-ui.csv"},
    "swiftui": {"file": "stacks/swiftui.csv"},
    "react-native": {"file": "stacks/react-native.csv"},
    "flutter": {"file": "stacks/flutter.csv"},
    "jetpack-compose": {"file": "stacks/jetpack-compose.csv"},
    "angular": {"file": "stacks/angular.csv"},
    "laravel": {"file": "stacks/laravel.csv"},
    "threejs": {"file": "stacks/threejs.csv"},
}

_STACK_COLS = {
    "search_cols": ["Category", "Guideline", "Description", "Do", "Don't"],
    "output_cols": [
        "Category",
        "Guideline",
        "Description",
        "Do",
        "Don't",
        "Code Good",
        "Code Bad",
        "Severity",
        "Docs URL",
    ],
}

AVAILABLE_STACKS = list(STACK_CONFIG.keys())

# All searchable domain names (CSV_CONFIG keys + stack keys under "stacks" prefix)
DOMAINS = set(CSV_CONFIG.keys())


# ============ BM25 IMPLEMENTATION ============
class BM25:
    """BM25 ranking algorithm for text search."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.corpus: list[list[str]] = []
        self.doc_lengths: list[int] = []
        self.avgdl: float = 0.0
        self.idf: dict[str, float] = {}
        self.doc_freqs: dict[str, int] = defaultdict(int)
        self.N: int = 0

    def tokenize(self, text: str) -> list[str]:
        """Lowercase, split on non-word chars, filter tokens shorter than 3 chars."""
        text = re.sub(r"[^\w\s]", " ", str(text).lower())
        return [w for w in text.split() if len(w) > 2]

    def fit(self, documents: list[str]) -> None:
        """Build BM25 index from a list of documents."""
        self.corpus = [self.tokenize(doc) for doc in documents]
        self.N = len(self.corpus)
        if self.N == 0:
            return
        self.doc_lengths = [len(doc) for doc in self.corpus]
        self.avgdl = sum(self.doc_lengths) / self.N

        for doc in self.corpus:
            seen: set[str] = set()
            for word in doc:
                if word not in seen:
                    self.doc_freqs[word] += 1
                    seen.add(word)

        for word, freq in self.doc_freqs.items():
            self.idf[word] = log((self.N - freq + 0.5) / (freq + 0.5) + 1)

    def score(self, query: str) -> list[tuple[int, float]]:
        """Return (doc_index, bm25_score) pairs sorted descending by score."""
        query_tokens = self.tokenize(query)
        scores: list[tuple[int, float]] = []

        for idx, doc in enumerate(self.corpus):
            doc_score = 0.0
            doc_len = self.doc_lengths[idx]
            term_freqs: dict[str, int] = defaultdict(int)
            for word in doc:
                term_freqs[word] += 1

            for token in query_tokens:
                if token in self.idf:
                    tf = term_freqs[token]
                    idf = self.idf[token]
                    numerator = tf * (self.k1 + 1)
                    denominator = tf + self.k1 * (
                        1 - self.b + self.b * doc_len / self.avgdl
                    )
                    doc_score += idf * numerator / denominator

            scores.append((idx, doc_score))

        return sorted(scores, key=lambda x: x[1], reverse=True)


# ============ INTERNAL HELPERS ============
def _load_csv(filepath: Path) -> list[dict]:
    """Load a CSV file and return a list of row dicts."""
    with open(filepath, "r", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _search_csv(
    filepath: Path,
    search_cols: list[str],
    output_cols: list[str],
    query: str,
    limit: int,
) -> list[dict]:
    """Core BM25 search over a CSV file. Returns list of result dicts."""
    if not filepath.exists():
        return []

    data = _load_csv(filepath)
    documents = [" ".join(str(row.get(col, "")) for col in search_cols) for row in data]

    bm25 = BM25()
    bm25.fit(documents)
    ranked = bm25.score(query)

    results: list[dict] = []
    for idx, score in ranked[:limit]:
        if score > 0:
            row = data[idx]
            results.append({col: row.get(col, "") for col in output_cols if col in row})

    return results


# ============ PUBLIC API ============
def search(domain: str, query: str, limit: int = 3) -> list[dict]:
    """
    Search the given design domain using BM25.

    Args:
        domain: One of the keys in CSV_CONFIG (e.g. "style", "color", "product").
                Use search_stack() for stack-specific searches.
        query:  Free-text search query.
        limit:  Maximum number of results to return (default 3).

    Returns:
        List of result dicts with output column keys.

    Raises:
        ValueError: If domain is not recognised.
    """
    if domain not in CSV_CONFIG:
        raise ValueError(
            f"Unknown domain: {domain!r}. Valid domains: {sorted(CSV_CONFIG)}"
        )

    config = CSV_CONFIG[domain]
    filepath = DATA_DIR / config["file"]
    return _search_csv(
        filepath, config["search_cols"], config["output_cols"], query, limit
    )


def search_stack(stack: str, query: str, limit: int = 3) -> list[dict]:
    """
    Search stack-specific guidelines.

    Args:
        stack:  One of AVAILABLE_STACKS (e.g. "react", "nextjs", "shadcn-ui").
        query:  Free-text search query.
        limit:  Maximum number of results to return (default 3).

    Returns:
        List of result dicts with stack guideline columns.

    Raises:
        ValueError: If stack is not recognised.
    """
    if stack not in STACK_CONFIG:
        raise ValueError(
            f"Unknown stack: {stack!r}. Available stacks: {AVAILABLE_STACKS}"
        )

    filepath = DATA_DIR / STACK_CONFIG[stack]["file"]
    return _search_csv(
        filepath,
        _STACK_COLS["search_cols"],
        _STACK_COLS["output_cols"],
        query,
        limit,
    )
