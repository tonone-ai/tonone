"""
Tests for lib/site-signals — the public-website profiler behind /deal-signals.

Risk map:
- A false fact → HIGH: a wrong incumbent agency or an invented job opening in
  a cold email is worse than saying nothing. Precision beats recall.
- Collecting what the user didn't confirm → HIGH: the whole contract is that
  nothing is gathered until the user picks signals.
- Silent failure → MEDIUM: an unreachable site or an empty careers page has to
  show up as a failure entry, not as a clean empty result.
- Fetching internal hosts → MEDIUM: IPs and .local names must be rejected.

Offline: a fake fetch serves fixture pages; no network.
"""

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).parent.parent
PROFILE = REPO / "lib" / "site-signals" / "profile.py"

spec = importlib.util.spec_from_file_location("site_signals", PROFILE)
ss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ss)

NOW = datetime(2026, 10, 14, tzinfo=timezone.utc)
PAD = "<p>" + ("filler " * 120) + "</p>"

HOME = f"""<html><head>
<script async src="https://www.googletagmanager.com/gtag/js?id=AW-123456789"></script>
<script src="https://js.hs-scripts.com/1.js"></script>
<link href="https://assets.website-files.com/x.css">
</head><body>{PAD}
<footer>
  <a href="https://twitter.com/acme">Twitter</a>
  <a href="https://shopify.com">Powered by Shopify</a>
  Website by <a href="https://pixelworks.agency">Pixelworks</a>
</footer></body></html>"""

ROBOTS = "User-agent: GPTBot\nDisallow: /\n\nUser-agent: *\nDisallow: /private\n"
SITEMAP = """<urlset><url><loc>https://acme.com/</loc><lastmod>2026-01-01</lastmod></url>
<url><loc>https://acme.com/blog/a</loc><lastmod>2025-12-01</lastmod></url></urlset>"""
CAREERS = f"""<html><body>{PAD}<h2>Life at Acme</h2><h3>Our benefits</h3>
<ul><li><a href="/j/1">Senior Platform Engineer</a></li>
<li><a href="/j/2">Account Executive (Remote)</a></li>
<li><a href="/j/3">Engineers</a></li><li><a href="/blog">Developer blog</a></li></ul></body></html>"""
TEAM = f"""<html><body>{PAD}
<h3>Jane Doe</h3><p>Co-Founder &amp; CEO</p>
<h3>Request Service</h3><p>Manager of our service desk</p>
<h3>Sam Lee</h3><p>Support Engineer</p>
<script>var Return Value = "CEO";</script></body></html>"""

PAGES = {
    "https://acme.com/": HOME,
    "https://acme.com/robots.txt": ROBOTS,
    "https://acme.com/sitemap.xml": SITEMAP,
    "https://acme.com/careers": CAREERS,
    "https://acme.com/team": TEAM,
    "https://acme.com/private": "<html>secret</html>" + PAD,
}


def fake_fetch(url):
    body = PAGES.get(url)
    return (200, body) if body else (404, "")


def profile(signals="all", fetch=fake_fetch):
    return ss.profile_domain(
        "acme.com", ss.parse_signals(signals), fetch=fetch, now=NOW
    )


def by_signal(result):
    out = {}
    for o in result["observations"]:
        out.setdefault(o["signal"], []).append(o)
    return out


def test_every_observation_carries_evidence_and_confidence():
    result = profile()
    assert result["observations"]
    for o in result["observations"]:
        assert o["evidence_url"].startswith("https://")
        assert 0 < o["confidence"] <= 1
        assert o["observed_at"] == "2026-10-14T00:00:00Z"


def test_homepage_signals():
    obs = by_signal(profile())
    assert obs["RUNNING_GOOGLE_ADS"][0]["value_num"] == 1
    assert obs["RUNNING_META_ADS"][0]["value_num"] == 0
    assert obs["TECH_STACK"][0]["value_text"] == "Google Analytics, HubSpot, Webflow"
    assert obs["NO_SCHEMA_MARKUP"][0]["value_num"] == 1
    assert obs["NO_ONLINE_BOOKING"][0]["value_num"] == 1


def test_agency_credit_scored_and_platforms_ignored():
    agency = by_signal(profile())["INCUMBENT_AGENCY"]
    assert len(agency) == 1
    assert agency[0]["value_text"] == "Pixelworks"
    assert agency[0]["confidence"] == 0.9
    assert agency[0]["evidence_url"] == "https://pixelworks.agency"


def test_bare_footer_link_is_not_recorded_as_agency():
    page = f"<html><body>{PAD}<footer><a href='https://someshop.io'>Someshop</a></footer></body></html>"
    assert ss.detect_agency(page, "acme.com") is None


def test_robots_and_sitemap():
    obs = by_signal(profile())
    assert obs["BLOCKS_AI_CRAWLERS"][0]["value_num"] == 1
    assert obs["SITE_PAGE_COUNT"][0]["value_num"] == 2
    assert (
        obs["CONTENT_AGE_DAYS"][0]["value_num"]
        == (NOW.date() - datetime(2026, 1, 1).date()).days
    )


def test_hiring_roles_are_titles_not_headings():
    roles = [o["value_text"] for o in by_signal(profile())["HIRING_ROLE"]]
    assert roles == ["Senior Platform Engineer", "Account Executive (Remote)"]


def test_decision_makers_are_conservative():
    people = [o["value_text"] for o in by_signal(profile())["DECISION_MAKER"]]
    assert people == ["Jane Doe, Co-Founder & CEO"]


def test_only_confirmed_signals_are_collected():
    result = profile("RUNNING_GOOGLE_ADS")
    assert {o["signal"] for o in result["observations"]} == {"RUNNING_GOOGLE_ADS"}
    assert ss.parse_signals("") is None
    assert ss.parse_signals("NOT_A_SIGNAL") is None


def test_robots_disallow_all_skips_the_homepage():
    fetched = []

    def fetch(url):
        fetched.append(url)
        return (
            (200, "User-agent: *\nDisallow: /\n")
            if url.endswith("/robots.txt")
            else (200, HOME)
        )

    result = profile(fetch=fetch)
    assert result["observations"] == []
    assert "robots.txt disallows" in result["failures"][0]
    assert not any(u.endswith(".com/") for u in fetched)


def test_blocked_contact_page_is_a_failure_not_a_false_zero():
    pages = dict(PAGES)
    pages["https://acme.com/robots.txt"] = (
        "User-agent: *\nDisallow: /contact\nDisallow: /contact-us\n"
    )
    pages["https://acme.com/"] = HOME.replace(
        "<footer>", "<footer>"
    )  # no <form> on the homepage
    result = profile(
        "CONTACT_FORM", fetch=lambda u: (200, pages[u]) if u in pages else (404, "")
    )
    assert result["observations"] == []
    assert any("disallows the contact page" in f for f in result["failures"])


def test_absence_is_written_as_a_row():
    pages = dict(PAGES)
    pages["https://acme.com/"] = f"<html><body>{PAD}</body></html>"
    obs = by_signal(
        profile(
            "INCUMBENT_AGENCY,TECH_STACK",
            fetch=lambda u: (200, pages[u]) if u in pages else (404, ""),
        )
    )
    assert obs["INCUMBENT_AGENCY"][0]["value_num"] == 0
    assert obs["TECH_STACK"][0]["value_num"] == 0


def test_http_get_never_raises_and_refuses_internal_hosts(monkeypatch):
    assert ss.http_get("http://localhost/") == (0, "")
    monkeypatch.setattr(
        ss.socket, "getaddrinfo", lambda host, port: [(2, 1, 6, "", ("127.0.0.1", 0))]
    )
    assert ss.http_get("https://127.0.0.1.nip.io/") == (0, "")

    def boom(*a, **k):
        raise LookupError("unknown encoding: x-bogus")

    monkeypatch.setattr(
        ss.socket,
        "getaddrinfo",
        lambda host, port: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )
    monkeypatch.setattr(ss._OPENER, "open", boom)
    assert ss.http_get("https://example.com/") == (0, "")


def test_role_and_title_precision():
    page = f"<html>{PAD}<ul><li>Become a Partner</li><li>Talk to an Engineer</li><li>Staff Engineer</li></ul></html>"
    assert ss.detect_roles(page) == ["Staff Engineer"]
    team = f"<html>{PAD}<h3>Ana Diaz</h3><p>Partnerships Lead</p><h3>Bo Chen</h3><p>Managing Partner</p></html>"
    leaders = [p["name"] for p in ss.detect_people(team) if p["decision_maker"]]
    assert leaders == ["Bo Chen"]
    assert not ss._any("<a href='https://medical.com/x'>x</a>", ss.BOOKING_HINTS)
    assert ss._any("<a>Book an appointment</a>", ss.BOOKING_HINTS)


def test_robots_txt_is_respected_for_our_agent():
    site = ss.Site("acme.com", fake_fetch)
    assert site.open()
    assert site.get("/private") == ""
    assert site.get("/careers")


def test_unreachable_site_is_a_failure_not_silence():
    result = profile(fetch=lambda url: (0, ""))
    assert result["observations"] == []
    assert result["failures"] and "unreachable" in result["failures"][0]


def test_empty_careers_page_is_reported():
    pages = dict(PAGES)
    pages["https://acme.com/careers"] = f"<html>{PAD}<h2>Join us</h2></html>"
    result = profile(
        "HIRING_ROLE", fetch=lambda u: (200, pages[u]) if u in pages else (404, "")
    )
    assert any("no role titles" in f for f in result["failures"])


def test_domain_normalization_rejects_internal_hosts():
    assert ss.normalize_domain("https://www.Acme.com/about") == "acme.com"
    assert ss.normalize_domain("acme.co.uk") == "acme.co.uk"
    for bad in (
        "10.0.0.1",
        "localhost",
        "printer.local",
        "http://192.168.1.1/",
        "# comment",
        "",
    ):
        assert ss.normalize_domain(bad) is None


def test_cli_requires_confirmed_signals():
    proc = subprocess.run(
        [sys.executable, "-I", str(PROFILE), "acme.com"], capture_output=True, text=True
    )
    assert proc.returncode == 2
    assert json.loads(proc.stdout)["ok"] is False
    proc = subprocess.run(
        [sys.executable, "-I", str(PROFILE), "--catalog"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert set(json.loads(proc.stdout)["signals"]) == set(ss.CATALOG)


# ── cohort.py ────────────────────────────────────────────────────────────
cspec = importlib.util.spec_from_file_location(
    "site_cohort", REPO / "lib" / "site-signals" / "cohort.py"
)
co = importlib.util.module_from_spec(cspec)
cspec.loader.exec_module(co)


def _obs(domain, signal, num=None, text="", conf=1.0, at="2026-10-01T00:00:00Z"):
    return {
        "domain": domain,
        "signal": signal,
        "value_num": num,
        "value_text": text,
        "confidence": conf,
        "evidence_url": f"https://{domain}/",
        "observed_at": at,
    }


LOG = [
    _obs("a.com", "RUNNING_GOOGLE_ADS", 1),
    _obs("a.com", "INCUMBENT_AGENCY", text="Pixelworks", conf=0.9),
    _obs("a.com", "NO_ONLINE_BOOKING", 1),
    _obs("b.com", "RUNNING_GOOGLE_ADS", 1),
    _obs("b.com", "INCUMBENT_AGENCY", text="Guess Co", conf=0.35),
    _obs("c.com", "RUNNING_GOOGLE_ADS", 1),
    _obs("c.com", "INCUMBENT_AGENCY", text="Studio", conf=0.75),
    _obs("c.com", "NO_ONLINE_BOOKING", 0),
    _obs("d.com", "TECH_STACK", text="HubSpot, WordPress"),
]


def test_cohort_is_a_query_with_reasons():
    # "Ads AND agency AND no booking": b.com's agency is below the confidence
    # floor; c.com already has booking (NO_ONLINE_BOOKING=0).
    result = co.cohort(
        LOG, co.parse_terms("RUNNING_GOOGLE_ADS,INCUMBENT_AGENCY,NO_ONLINE_BOOKING"), []
    )
    assert [m["domain"] for m in result["cohort"]] == ["a.com"]
    assert {r["signal"] for r in result["cohort"][0]["because"]} == {
        "RUNNING_GOOGLE_ADS",
        "INCUMBENT_AGENCY",
        "NO_ONLINE_BOOKING",
    }
    # --exclude NO_ONLINE_BOOKING means "has booking": the opposite set.
    has_booking = co.cohort(
        LOG, co.parse_terms("RUNNING_GOOGLE_ADS"), co.parse_terms("NO_ONLINE_BOOKING")
    )
    assert [m["domain"] for m in has_booking["cohort"]] == ["b.com", "c.com"]


def test_cohort_value_match():
    result = co.cohort(LOG, co.parse_terms("TECH_STACK=hubspot"), [])
    assert [m["domain"] for m in result["cohort"]] == ["d.com"]


def test_fact_not_seen_in_latest_run_is_stale():
    # Next run: roles unobservable (JS careers page) -> only a failure row.
    log = LOG + [
        _obs("d.com", "HIRING_ROLE", 1, text="Staff Engineer"),
        {
            "domain": "d.com",
            "failure": "careers page has no role titles",
            "observed_at": "2026-12-01T00:00:00Z",
        },
    ]
    assert co.cohort(log, co.parse_terms("HIRING_ROLE"), [])["matches"] == 0


def test_disappeared_fact_stops_matching_and_is_a_change():
    # The next run no longer sees a.com's agency: profile.py writes num=0.
    log = LOG + [_obs("a.com", "INCUMBENT_AGENCY", 0, at="2026-12-01T00:00:00Z")]
    result = co.cohort(log, co.parse_terms("INCUMBENT_AGENCY"), [])
    assert "a.com" not in [m["domain"] for m in result["cohort"]]
    moved = co.changes(log)
    assert (
        moved[0]["domain"] == "a.com"
        and moved[0]["was"] == "Pixelworks"
        and moved[0]["now"] == []
    )


def test_latest_observation_wins_and_changes_are_reported():
    log = LOG + [_obs("a.com", "RUNNING_GOOGLE_ADS", 0, at="2026-12-01T00:00:00Z")]
    result = co.cohort(log, co.parse_terms("RUNNING_GOOGLE_ADS"), [])
    assert "a.com" not in [m["domain"] for m in result["cohort"]]
    moved = co.changes(log)
    assert moved == [
        {
            "domain": "a.com",
            "signal": "RUNNING_GOOGLE_ADS",
            "was": 1,
            "now": [],
            "since": "2026-10-01T00:00:00Z",
            "observed_at": "2026-12-01T00:00:00Z",
            "evidence_url": "https://a.com/",
        }
    ]


def test_jsonl_output_feeds_cohort(tmp_path, monkeypatch, capsys):
    original = ss.profile_domain
    monkeypatch.setattr(
        ss, "profile_domain", lambda d, w: original(d, w, fetch=fake_fetch, now=NOW)
    )
    assert ss.main(["--signals", "all", "--jsonl", "acme.com"]) == 0
    log = tmp_path / "observations.jsonl"
    log.write_text(capsys.readouterr().out)
    lines = [json.loads(l) for l in log.read_text().splitlines()]
    assert all(l["domain"] == "acme.com" for l in lines)
    result = co.cohort(
        co.load(str(log)), co.parse_terms("RUNNING_GOOGLE_ADS,INCUMBENT_AGENCY"), []
    )
    assert [m["domain"] for m in result["cohort"]] == ["acme.com"]
