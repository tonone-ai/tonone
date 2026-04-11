"""Surge agent design intelligence — landing, product, and ux domains."""

try:
    from uiux.search import search
except ImportError:

    def _missing(*a, **kw):
        raise RuntimeError(
            "uiux package not found — run: cd lib/uiux && bash setup.sh, "
            "then reinstall this agent"
        )

    search = _missing

ALLOWED_DOMAINS = {"landing", "product", "ux"}


def query(domain: str, terms: str, limit: int = 5) -> list[dict]:
    if domain not in ALLOWED_DOMAINS:
        raise ValueError(
            f"Domain '{domain}' not available for Surge agent. "
            f"Allowed: {sorted(ALLOWED_DOMAINS)}"
        )
    return search(domain=domain, query=terms, limit=limit)
