"""Draft agent design intelligence — ux, landing, and product domains."""

try:
    from uiux.search import search
except ImportError:

    def _missing(*a, **kw):
        raise RuntimeError(
            "uiux package not found — run: cd lib/uiux && bash setup.sh, "
            "then reinstall this agent"
        )

    search = _missing

ALLOWED_DOMAINS = {"ux", "landing", "product"}


def query(domain: str, terms: str, limit: int = 5) -> list[dict]:
    if domain not in ALLOWED_DOMAINS:
        raise ValueError(
            f"Domain '{domain}' not available for Draft agent. "
            f"Allowed: {sorted(ALLOWED_DOMAINS)}"
        )
    return search(domain=domain, query=terms, limit=limit)
