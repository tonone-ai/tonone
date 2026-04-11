"""Tests for data file completeness and schema integrity."""

from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "uiux" / "data"
STACKS_DIR = DATA_DIR / "stacks"

# Expected top-level CSV files (12 total)
TOP_LEVEL_CSVS = [
    "styles.csv",
    "colors.csv",
    "typography.csv",
    "google-fonts.csv",
    "products.csv",
    "ui-reasoning.csv",
    "landing.csv",
    "charts.csv",
    "ux-guidelines.csv",
    "react-performance.csv",
    "app-interface.csv",
    "icons.csv",
]

# Expected stack CSV files (16 total)
STACK_CSVS = [
    "react.csv",
    "nextjs.csv",
    "vue.csv",
    "nuxtjs.csv",
    "nuxt-ui.csv",
    "svelte.csv",
    "astro.csv",
    "html-tailwind.csv",
    "shadcn-ui.csv",
    "swiftui.csv",
    "react-native.csv",
    "flutter.csv",
    "jetpack-compose.csv",
    "angular.csv",
    "laravel.csv",
    "threejs.csv",
]


# ── file existence ────────────────────────────────────────────────────────────


def test_data_dir_exists():
    assert DATA_DIR.exists(), f"Data directory not found: {DATA_DIR}"


def test_stacks_dir_exists():
    assert STACKS_DIR.exists(), f"Stacks directory not found: {STACKS_DIR}"


def test_12_top_level_csvs_exist():
    missing = [f for f in TOP_LEVEL_CSVS if not (DATA_DIR / f).exists()]
    assert not missing, f"Missing top-level CSVs: {missing}"


def test_16_stack_csvs_exist():
    missing = [f for f in STACK_CSVS if not (STACKS_DIR / f).exists()]
    assert not missing, f"Missing stack CSVs: {missing}"


def test_total_csv_count():
    top = list(DATA_DIR.glob("*.csv"))
    stacks = list(STACKS_DIR.glob("*.csv"))
    assert len(top) >= 12, f"Expected at least 12 top-level CSVs, found {len(top)}"
    assert len(stacks) >= 16, f"Expected at least 16 stack CSVs, found {len(stacks)}"


# ── data row checks ───────────────────────────────────────────────────────────


def _has_data_rows(path: Path) -> bool:
    """Return True if the CSV has at least one data row beyond the header."""
    import csv

    with open(path, "r", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        rows = list(reader)
    return len(rows) > 1


def test_all_top_level_csvs_have_data_rows():
    empty = [f for f in TOP_LEVEL_CSVS if not _has_data_rows(DATA_DIR / f)]
    assert not empty, f"CSVs with no data rows: {empty}"


def test_all_stack_csvs_have_data_rows():
    empty = [f for f in STACK_CSVS if not _has_data_rows(STACKS_DIR / f)]
    assert not empty, f"Stack CSVs with no data rows: {empty}"


# ── schema / header checks ────────────────────────────────────────────────────


def _read_header(path: Path) -> list[str]:
    import csv

    with open(path, "r", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        return next(reader, [])


def test_styles_csv_has_expected_headers():
    headers = _read_header(DATA_DIR / "styles.csv")
    for col in ["Style Category", "Keywords", "Best For"]:
        assert col in headers, f"styles.csv missing column: {col}"


def test_colors_csv_has_expected_headers():
    headers = _read_header(DATA_DIR / "colors.csv")
    for col in ["Product Type", "Primary", "Background", "Foreground"]:
        assert col in headers, f"colors.csv missing column: {col}"


def test_products_csv_has_expected_headers():
    headers = _read_header(DATA_DIR / "products.csv")
    for col in ["Product Type", "Keywords"]:
        assert col in headers, f"products.csv missing column: {col}"


def test_typography_csv_has_expected_headers():
    headers = _read_header(DATA_DIR / "typography.csv")
    for col in ["Heading Font", "Body Font"]:
        assert col in headers, f"typography.csv missing column: {col}"


def test_google_fonts_csv_has_expected_headers():
    headers = _read_header(DATA_DIR / "google-fonts.csv")
    for col in ["Family", "Category"]:
        assert col in headers, f"google-fonts.csv missing column: {col}"


def test_stack_csvs_have_expected_headers():
    """All stack CSVs should share the same schema."""
    expected_cols = ["Category", "Guideline", "Description"]
    for fname in STACK_CSVS:
        headers = _read_header(STACKS_DIR / fname)
        for col in expected_cols:
            assert col in headers, f"{fname} missing column: {col}"
