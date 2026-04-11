"""Form agent design intelligence — style, color, typography, fonts, and product domains."""

try:
    from uiux.search import search
except ImportError:

    def _missing(*a, **kw):
        raise RuntimeError(
            "uiux package not found — run: cd lib/uiux && bash setup.sh, "
            "then reinstall this agent"
        )

    search = _missing

try:
    from uiux.design_system import generate_design_system
except ImportError:

    def _missing(*a, **kw):
        raise RuntimeError(
            "uiux package not found — run: cd lib/uiux && bash setup.sh, "
            "then reinstall this agent"
        )

    generate_design_system = _missing

ALLOWED_DOMAINS = {"style", "color", "typography", "google-fonts", "product"}


def query(domain: str, terms: str, limit: int = 5) -> list[dict]:
    if domain not in ALLOWED_DOMAINS:
        raise ValueError(
            f"Domain '{domain}' not available for Form agent. "
            f"Allowed: {sorted(ALLOWED_DOMAINS)}"
        )
    return search(domain=domain, query=terms, limit=limit)
