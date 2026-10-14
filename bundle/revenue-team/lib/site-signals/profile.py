#!/usr/bin/env python3
"""site-signals — read a company's public website and emit buying signals.

The profiler behind /deal-signals. For each domain it fetches the homepage,
robots.txt and sitemap.xml, plus the team, careers and contact pages when
they exist: a handful of plain HTTP requests, no browser, no model call. It
then runs regexes over HTML it already has and emits one observation per
fact, each with a confidence and the URL that proves it.

    every fact is a row: signal, value, confidence, evidence_url, observed_at

That shape is deliberate (borrowed from Harvey, MIT, see NOTICE.md): a new
signal needs no schema change, re-running later gives a time series for
free, and an email can only cite what has a URL behind it.

Nothing is collected unless asked for. `--catalog` lists the signals; the
skill shows that list to the user, who confirms which to collect, and passes
them as `--signals`.

Usage:
    python3 profile.py --catalog
    python3 profile.py --signals RUNNING_GOOGLE_ADS,INCUMBENT_AGENCY acme.com
    python3 profile.py --signals all --domains-file targets.txt
    python3 profile.py --signals all --jsonl acme.com >> observations.jsonl

Prints exactly one JSON object and exits 0, including when sites are
unreachable: an unreachable site is reported as a failure entry, never
silently dropped. Exit 2 only on usage errors.
"""

from __future__ import annotations

import argparse
import html as htmllib
import ipaddress
import json
import re
import socket
import sys
import time
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from urllib.parse import urlparse

USER_AGENT = "tonone-site-signals/1.0 (+https://github.com/tonone-ai/tonone)"
TIMEOUT = 10.0
MAX_BYTES = 1_500_000
DOMAIN_DELAY = 1.0  # seconds between domains; be a polite visitor

# ── catalog ──────────────────────────────────────────────────────────────
CATALOG = {
    "RUNNING_GOOGLE_ADS": "Google Ads conversion tag on the homepage: they are paying for acquisition now.",
    "RUNNING_META_ADS": "Meta (Facebook) pixel on the homepage: paid social spend.",
    "TECH_STACK": "Platforms and tools detectable from page source (CMS, CRM, chat, analytics).",
    "NO_SCHEMA_MARKUP": "No JSON-LD structured data: a concrete, checkable SEO gap.",
    "NO_ONLINE_BOOKING": "No scheduling or booking link: leads have to call or email.",
    "INCUMBENT_AGENCY": "Agency credited in the footer ('website by ...'). Recorded only at confidence >= 0.75.",
    "BLOCKS_AI_CRAWLERS": "robots.txt disallows GPTBot, ClaudeBot or similar.",
    "SITE_PAGE_COUNT": "Number of URLs in sitemap.xml: a rough size signal.",
    "CONTENT_AGE_DAYS": "Days since the newest <lastmod> in sitemap.xml: stale content shows up here.",
    "CONTACT_FORM": "A contact or quote form exists (homepage or contact page).",
    "HIRING_ROLE": "Role titles found on a careers page: what they are hiring for.",
    "DECISION_MAKER": "Name and title of an owner, founder or senior role on a team/about page.",
}

# ── detectors (adapted from Harvey's profile collector, MIT) ─────────────
TECH_FINGERPRINTS = {
    "WordPress": (r"wp-content/", r"wp-includes/"),
    "Shopify": (r"cdn\.shopify\.com", r"myshopify\.com"),
    "Wix": (r"static\.parastorage\.com",),
    "Squarespace": (r"static1\.squarespace\.com",),
    "Webflow": (r"assets\.website-files\.com", r"data-wf-domain"),
    "Framer": (r"framerusercontent\.com",),
    "Next.js": (r"/_next/static/",),
    "HubSpot": (r"js\.hs-scripts\.com", r"js\.hsforms\.net"),
    "Marketo": (r"munchkin\.marketo\.net",),
    "Salesforce": (r"salesforce\.com/embeddedservice", r"force\.com/"),
    "Klaviyo": (r"static\.klaviyo\.com",),
    "Mailchimp": (r"chimpstatic\.com", r"list-manage\.com/subscribe"),
    "Google Analytics": (r"googletagmanager\.com/gtag", r"google-analytics\.com"),
    "Google Tag Manager": (r"googletagmanager\.com/gtm\.js",),
    "Segment": (r"cdn\.segment\.com",),
    "Hotjar": (r"static\.hotjar\.com",),
    "Intercom": (r"widget\.intercom\.io", r"js\.intercomcdn\.com"),
    "Drift": (r"js\.driftt\.com",),
    "Zendesk": (r"static\.zdassets\.com",),
    "Crisp": (r"client\.crisp\.chat",),
    "Calendly": (r"assets\.calendly\.com",),
    "Stripe": (r"js\.stripe\.com",),
    "Typeform": (r"embed\.typeform\.com",),
    "CallRail": (r"cdn\.callrail\.com",),
    "Cloudflare": (r"/cdn-cgi/",),
}

GOOGLE_ADS = (
    r"googleadservices\.com",
    r"gtag/js\?id=AW-",
    r"google_conversion",
    r"['\"]AW-\d{6,}",
)
META_PIXEL = (r"connect\.facebook\.net/[^\"']*fbevents\.js", r"fbq\s*\(\s*['\"]init")
BOOKING_HINTS = (
    r"calendly\.com",
    r"acuityscheduling",
    r"(?<![\w.\-])cal\.com/",
    r"setmore",
    r"squareup\.com/appointments",
    r"hubspot\.com/meetings",
    r"book(ing)?[-_ ]?(now|online|a[-_ ]?(call|demo|meeting))",
    r"book[-_ ]an?[-_ ]appointment",
    r"schedule[-_ ]?(an?[-_ ])?(appointment|call|demo|consultation)",
)
AI_CRAWLERS = (
    "gptbot",
    "google-extended",
    "ccbot",
    "anthropic-ai",
    "claudebot",
    "perplexitybot",
    "bytespider",
)

# Footer links that are never the site's agency.
BENIGN_HOSTS = (
    "facebook.",
    "instagram.",
    "twitter.",
    "x.com",
    "linkedin.",
    "youtube.",
    "tiktok.",
    "pinterest.",
    "yelp.",
    "threads.",
    "github.com",
    "medium.com",
    "google.com",
    "g.page",
    "goo.gl",
    "apple.com",
    "bing.com",
    "wa.me",
    "paypal",
    "stripe.com",
    "klarna",
    "affirm",
    "bbb.org",
    "trustpilot",
    "g2.com",
    "capterra",
    "accessibe",
    "userway",
    "termly",
    "iubenda",
    "onetrust",
    "cookiebot",
    "cloudflare",
    "godaddy",
    "wordpress.org",
    "wix.com",
    "squarespace.com",
    "shopify.com",
    "webflow.com",
    "framer.com",
    "w3.org",
    "schema.org",
    "gstatic",
    "googleapis",
    "cloudfront",
)
# "Powered by" is left out on purpose: it credits a platform or a product
# ("Powered by Shopify", a partner badge) far more often than an agency.
STRONG_CREDIT = re.compile(
    r"\b(website|site|web\s*design|designed|developed|built|created|"
    r"marketing)\s+(by|&)\b",
    re.I,
)
DESCRIPTIVE_CREDIT = re.compile(
    r"\b(web\s*design|website\s*design|digital\s*marketing|seo|marketing\s*"
    r"agency|web\s*development|design\s*agency)\b",
    re.I,
)
AGENCY_FLOOR = 0.75  # a wrong incumbent in an email is worse than none

TEAM_PATHS = (
    "/team",
    "/about",
    "/about-us",
    "/our-team",
    "/leadership",
    "/company",
    "/company/team",
    "/people",
)
CAREERS_PATHS = ("/careers", "/jobs", "/join-us", "/company/careers", "/hiring")
CONTACT_PATHS = ("/contact", "/contact-us", "/get-a-quote", "/demo", "/request-demo")

NON_NAME_WORDS = frozenset("""
service services solutions systems products product platform pricing contact
about team our your their careers jobs home page company inc llc ltd corp
group partners customers case studies blog news events resources support help
login sign get started book demo request quote free learn more read view
privacy policy terms conditions cookie sitemap why choose us features overview
leadership board advisors investors mission values history story office
locations global north south east west menu search close open toggle
""".split())
ROLE_HINT = re.compile(
    r"\b(owner|founder|president|ceo|cfo|coo|cto|cmo|cro|principal|partner|"
    r"manager|director|head of|vp|vice president|chief|lead|officer|"
    r"engineer|designer|marketing|sales|operations|executive)\b",
    re.I,
)
DECISION_TITLES = re.compile(
    r"\b(owner|founder|co-founder|president|ceo|chief|principal|partner|"
    r"managing director|general manager|vp|vice president|head of|director)\b",
    re.I,
)
# A job title ends in a role noun ("Platform Engineer", "Account Executive",
# "Product Designer (Remote)") or starts with a seniority prefix ("Head of
# Growth"). Department words alone ("Support", "Developer docs") are nav links.
ROLE_NOUNS = (
    r"engineer|developer|designer|manager|director|lead|specialist|analyst|"
    r"scientist|executive|representative|consultant|coordinator|technician|"
    r"intern|architect|recruiter|writer|counsel|accountant|administrator|"
    r"strategist|researcher|associate|officer|partner|installer|estimator|foreman"
)
ROLE_TITLE = re.compile(
    rf"^(?:(?:head|vp|vice president|director) of\b.*|.*\b(?:{ROLE_NOUNS}))"
    r"(?:\s*[,(\-–|].{0,40})?$",
    re.I,
)
NOT_A_ROLE = re.compile(
    r"\b(how|our|we|you|your|why|blog|docs|benefits|life at|culture|"
    r"apply|view all|open roles|see all|learn more|become|talk to|contact|meet|"
    r"join|hire|find|work with|partner with)\b",
    re.I,
)
ATS_HOSTS = {
    "Greenhouse": r"boards\.greenhouse\.io|boards-api\.greenhouse\.io",
    "Lever": r"jobs\.lever\.co",
    "Ashby": r"jobs\.ashbyhq\.com",
    "Workable": r"apply\.workable\.com",
    "Teamtailor": r"teamtailor\.com",
}


def strip_code(page: str) -> str:
    """Drop script/style/comments before any text regex. Skipping this turns
    minified JS into 'people' named 'return value'."""
    page = re.sub(r"(?is)<script\b.*?</script>", " ", page)
    page = re.sub(r"(?is)<style\b.*?</style>", " ", page)
    return re.sub(r"(?s)<!--.*?-->", " ", page)


def _text(fragment: str) -> str:
    return re.sub(
        r"\s+", " ", htmllib.unescape(re.sub(r"(?s)<[^>]+>", " ", fragment))
    ).strip()


def _any(page: str, patterns) -> bool:
    return any(re.search(p, page, re.I) for p in patterns)


def detect_tech(page: str) -> list[str]:
    return sorted(n for n, pats in TECH_FINGERPRINTS.items() if _any(page, pats))


def detect_agency(page: str, domain: str):
    """(name, confidence, href) for the agency credited in the footer, or None."""
    cleaned = strip_code(page)
    m = re.search(r"(?is)<footer\b.*?</footer>", cleaned)
    region = m.group(0) if m else cleaned[-12000:]
    best = None
    for link in re.finditer(
        r'(?is)<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', region
    ):
        href, anchor = link.group(1), _text(link.group(2))
        if not href.startswith("http") or not anchor or len(anchor) > 80:
            continue
        host = (urlparse(href).netloc or "").lower().removeprefix("www.")
        if not host or host.endswith(domain) or domain.endswith(host):
            continue
        if any(b in href.lower() for b in BENIGN_HOSTS):
            continue
        context = _text(region[max(0, link.start() - 120) : link.start()])
        if STRONG_CREDIT.search(f"{context} {anchor}"):
            conf = 0.9
        elif DESCRIPTIVE_CREDIT.search(anchor):
            conf = 0.75
        else:
            conf = 0.35
        if conf >= AGENCY_FLOOR and (best is None or conf > best[1]):
            best = (anchor, conf, href)
    return best


def blocks_ai_crawlers(robots: str) -> bool:
    low = robots.lower()
    return any(
        re.search(
            rf"user-agent:\s*{re.escape(bot)}\s*(?:\n\s*user-agent:[^\n]*)*\s*\n\s*disallow:\s*/\s*(\n|$)",
            low,
        )
        for bot in AI_CRAWLERS
    )


def detect_people(page: str) -> list[dict]:
    """Name + title pairs from a team page. Conservative on purpose: a name
    needs a role nearby, and one business word disqualifies a heading."""
    cleaned = strip_code(page)
    people, seen = [], set()
    for m in re.finditer(
        r"(?is)<(h[1-6]|strong|b)[^>]*>\s*([A-Z][a-z'\-]+(?:\s+[A-Z]\.?)?\s+"
        r"[A-Z][a-zA-Z'\-]+)\s*</\1>(?=(.{0,220}))",
        cleaned,
    ):
        name = re.sub(r"\s+", " ", m.group(2)).strip()
        after = m.group(3)
        nxt = re.search(r"(?i)<(h[1-6]|strong|b)\b", after)
        after = _text(after[: nxt.start()] if nxt else after)
        if name.lower() in seen or re.search(r"\d|@", name):
            continue
        if any(t.strip(".,'-").lower() in NON_NAME_WORDS for t in name.split()):
            continue
        if not ROLE_HINT.search(after[:160]):
            continue
        title = re.match(r"[\s,|\-–—·]*([A-Za-z][A-Za-z ,/&'\-]{2,60})", after)
        title = title.group(1).strip(" ,") if title else ""
        seen.add(name.lower())
        people.append(
            {
                "name": name,
                "title": title[:80],
                "decision_maker": bool(DECISION_TITLES.search(title)),
            }
        )
        if len(people) >= 12:
            break
    return people


def detect_roles(page: str) -> list[str]:
    roles = []
    for m in re.finditer(
        r"(?is)<(h[2-5]|a|li)[^>]*>\s*([^<]{6,70})\s*</\1>", strip_code(page)
    ):
        t = re.sub(r"\s+", " ", htmllib.unescape(m.group(2))).strip()
        if len(t.split()) > 8 or NOT_A_ROLE.search(t) or not ROLE_TITLE.match(t):
            continue
        if t.lower() not in (r.lower() for r in roles):
            roles.append(t)
        if len(roles) >= 5:
            break
    return roles


def detect_ats(page: str) -> str:
    """Name of the hosted job board the careers page embeds, if any."""
    for name, pattern in ATS_HOSTS.items():
        if re.search(pattern, page, re.I):
            return name
    return ""


def has_form(page: str) -> bool:
    return bool(re.search(r"(?is)<form\b", strip_code(page)))


# ── fetching ─────────────────────────────────────────────────────────────
def normalize_domain(raw: str) -> str | None:
    raw = raw.strip().lower()
    if not raw or raw.startswith("#"):
        return None
    host = urlparse(raw if "://" in raw else f"https://{raw}").netloc or raw
    host = host.split("@")[-1].split(":")[0].removeprefix("www.").strip("/")
    if not re.fullmatch(r"[a-z0-9][a-z0-9.\-]*\.[a-z]{2,}", host):
        return None
    try:  # a bare IP is not a company website, and may be internal
        ipaddress.ip_address(host)
        return None
    except ValueError:
        pass
    if host.endswith((".local", ".internal", ".localhost")):
        return None
    return host


def _public_host(host: str) -> bool:
    """True only when every address the host resolves to is public. Blocks
    names like 127.0.0.1.nip.io that pass the syntax check but point inside."""
    try:
        infos = socket.getaddrinfo(host, None)
    except (OSError, UnicodeError):
        return False
    for info in infos:
        addr = info[4][0].split("%")[0]
        try:
            if not ipaddress.ip_address(addr).is_global:
                return False
        except ValueError:
            return False
    return bool(infos)


class _CheckedRedirects(urllib.request.HTTPRedirectHandler):
    """Refuse a redirect hop to anything that isn't a public website, before
    the hop is requested."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        host = urlparse(newurl).hostname or ""
        if normalize_domain(host) is None or not _public_host(host):
            raise urllib.error.URLError(f"redirect to non-public host {host!r} refused")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_CheckedRedirects)


def http_get(url: str) -> tuple[int, str]:
    """(status, body). Status 0 means the request failed outright. Never
    raises: any network, decoding or protocol error is a status-0 answer."""
    host = urlparse(url).hostname or ""
    if normalize_domain(host) is None or not _public_host(host):
        return 0, ""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xml,text/plain,*/*;q=0.8",
        },
    )
    try:
        with _OPENER.open(req, timeout=TIMEOUT) as resp:
            raw = resp.read(MAX_BYTES)
            charset = resp.headers.get_content_charset() or "utf-8"
            try:
                return resp.status, raw.decode(charset, errors="replace")
            except LookupError:  # a charset Python doesn't know
                return resp.status, raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:  # URLError, timeouts, IncompleteRead, bad headers, ...
        return 0, ""


class Site:
    """One domain's fetches. robots.txt is read first and respected for our
    own agent on every page, the homepage included."""

    def __init__(self, domain: str, fetch=http_get):
        self.domain, self.fetch = domain, fetch
        self.base, self.home, self.robots_txt = "", "", ""
        self._robots = None
        self.blocked: list[str] = []  # paths robots.txt kept us out of
        self.why_closed = "homepage unreachable (https, www, http all failed)"

    def open(self) -> bool:
        for base in (
            f"https://{self.domain}",
            f"https://www.{self.domain}",
            f"http://{self.domain}",
        ):
            status, robots = self.fetch(base + "/robots.txt")
            self.robots_txt = robots if status == 200 else ""
            rp = urllib.robotparser.RobotFileParser()
            rp.parse(self.robots_txt.splitlines())
            self._robots, self.base = rp, base
            if not self.allowed("/"):
                self.why_closed = (
                    "robots.txt disallows our agent on the homepage; not profiled"
                )
                return False
            status, body = self.fetch(base + "/")
            if status == 200 and body:
                self.home = body
                return True
        self.base, self._robots = "", None
        return False

    def allowed(self, path: str) -> bool:
        return self._robots is None or self._robots.can_fetch(
            USER_AGENT, self.base + path
        )

    def get(self, path: str) -> str:
        if not self.allowed(path):
            self.blocked.append(path)
            return ""
        status, body = self.fetch(self.base + path)
        return body if status == 200 else ""

    def first_present(self, paths) -> tuple[str, str]:
        for path in paths:
            body = self.get(path)
            if body and len(body) > 500:
                return self.base + path, body
        return "", ""

    def blocked_among(self, paths) -> list[str]:
        return [p for p in paths if p in self.blocked]


# ── the profile ──────────────────────────────────────────────────────────
def profile_domain(domain: str, wanted: set[str], fetch=http_get, now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    site = Site(domain, fetch)
    out = {
        "domain": domain,
        "site": "",
        "observations": [],
        "failures": [],
        "observed_at": stamp,
    }

    def add(signal, *, num=None, text="", conf=1.0, url=""):
        if signal in wanted:
            out["observations"].append(
                {
                    "signal": signal,
                    "value_num": num,
                    "value_text": text,
                    "confidence": conf,
                    "evidence_url": url or site.base + "/",
                    "observed_at": stamp,
                }
            )

    if not site.open():
        out["failures"].append(site.why_closed)
        return out
    out["site"] = site.base
    home = site.home

    add("RUNNING_GOOGLE_ADS", num=int(_any(home, GOOGLE_ADS)))
    add("RUNNING_META_ADS", num=int(_any(home, META_PIXEL)))
    tech = detect_tech(home)
    # Where a check really ran, absence is written as a row (value_num=0).
    # Roles and people are not: a careers page that loads roles with
    # JavaScript is unobservable, not "not hiring".
    add("TECH_STACK", num=1 if tech else 0, text=", ".join(tech))
    has_schema = bool(
        re.search(r"application/ld\+json", home, re.I) and re.search(r'"@type"', home)
    )
    add("NO_SCHEMA_MARKUP", num=int(not has_schema))
    add("NO_ONLINE_BOOKING", num=int(not _any(home, BOOKING_HINTS)))

    if "INCUMBENT_AGENCY" in wanted:
        agency = detect_agency(home, domain)
        if agency:
            add(
                "INCUMBENT_AGENCY", num=1, text=agency[0], conf=agency[1], url=agency[2]
            )
        else:
            add("INCUMBENT_AGENCY", num=0)

    if "BLOCKS_AI_CRAWLERS" in wanted:
        if site.robots_txt:
            add(
                "BLOCKS_AI_CRAWLERS",
                num=int(blocks_ai_crawlers(site.robots_txt)),
                url=site.base + "/robots.txt",
            )
        else:
            out["failures"].append("no robots.txt; BLOCKS_AI_CRAWLERS not observed")

    if wanted & {"SITE_PAGE_COUNT", "CONTENT_AGE_DAYS"}:
        sm = site.get("/sitemap.xml")
        sm_url = site.base + "/sitemap.xml"
        if not sm:
            out["failures"].append(
                "robots.txt disallows /sitemap.xml"
                if "/sitemap.xml" in site.blocked
                else "no sitemap.xml; page count and content age not observed"
            )
        else:
            locs = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", sm)
            if locs:
                add(
                    "SITE_PAGE_COUNT",
                    num=len(locs),
                    url=sm_url,
                    text=(
                        "sitemap index (child sitemaps not followed)"
                        if "<sitemapindex" in sm
                        else ""
                    ),
                )
            dates = re.findall(r"<lastmod>\s*(\d{4}-\d{2}-\d{2})", sm)
            if dates:
                newest = max(dates)
                try:
                    age = (
                        now.date() - datetime.strptime(newest, "%Y-%m-%d").date()
                    ).days
                    add(
                        "CONTENT_AGE_DAYS",
                        num=age,
                        text=f"newest lastmod {newest}",
                        url=sm_url,
                    )
                except ValueError:
                    pass

    if "CONTACT_FORM" in wanted:
        if has_form(home):
            add("CONTACT_FORM", num=1, url=site.base + "/")
        else:
            curl, chtml = site.first_present(CONTACT_PATHS)
            if chtml:
                add("CONTACT_FORM", num=int(has_form(chtml)), url=curl)
            elif site.blocked_among(CONTACT_PATHS):
                out["failures"].append(
                    "robots.txt disallows the contact page; CONTACT_FORM not observed"
                )
            else:
                add("CONTACT_FORM", num=0)

    if "HIRING_ROLE" in wanted:
        curl, chtml = site.first_present(CAREERS_PATHS)
        if not chtml:
            out["failures"].append(
                "robots.txt disallows the careers page"
                if site.blocked_among(CAREERS_PATHS)
                else "no careers page found at common paths"
            )
        roles = detect_roles(chtml) if chtml else []
        for role in roles:
            add("HIRING_ROLE", num=1, text=role, conf=0.75, url=curl)
        ats = detect_ats(chtml) if chtml else ""
        if chtml and not roles:
            out["failures"].append(
                f"careers page loads roles from {ats}; open {curl} to read them"
                if ats
                else f"careers page {curl} has no role titles in its static HTML"
            )

    if "DECISION_MAKER" in wanted:
        turl, thtml = site.first_present(TEAM_PATHS)
        if not thtml:
            out["failures"].append(
                "robots.txt disallows the team/about page"
                if site.blocked_among(TEAM_PATHS)
                else "no team/about page found at common paths"
            )
        leaders = [
            p for p in (detect_people(thtml) if thtml else []) if p["decision_maker"]
        ]
        for person in leaders:
            add(
                "DECISION_MAKER",
                num=1,
                text=f"{person['name']}, {person['title']}",
                conf=0.8,
                url=turl,
            )
        if thtml and not leaders:
            out["failures"].append(
                f"team page {turl} names no owner, founder or senior title"
            )

    return out


def parse_signals(raw: str) -> set[str] | None:
    if raw.strip().lower() == "all":
        return set(CATALOG)
    codes = {c.strip().upper() for c in raw.split(",") if c.strip()}
    return codes if codes and codes <= set(CATALOG) else None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Public-website buying signals, one fact per row."
    )
    ap.add_argument("domains", nargs="*")
    ap.add_argument("--domains-file")
    ap.add_argument("--signals", help="comma-separated codes from --catalog, or 'all'")
    ap.add_argument("--catalog", action="store_true")
    ap.add_argument("--pretty", action="store_true")
    ap.add_argument(
        "--jsonl",
        action="store_true",
        help="one observation or failure per line, for appending to a log",
    )
    args = ap.parse_args(argv)
    indent = 2 if args.pretty else None

    if args.catalog:
        print(
            json.dumps(
                {
                    "ok": True,
                    "cost": "free: plain HTTP, no API keys",
                    "signals": CATALOG,
                },
                indent=indent,
            )
        )
        return 0
    wanted = parse_signals(args.signals or "")
    if wanted is None:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "pass --signals with codes from --catalog "
                    "(nothing is collected until the user confirms which)",
                    "signals": sorted(CATALOG),
                },
                indent=indent,
            )
        )
        return 2

    raw = list(args.domains)
    if args.domains_file:
        try:
            raw += open(args.domains_file, encoding="utf-8").read().splitlines()
        except OSError as e:
            print(
                json.dumps(
                    {"ok": False, "error": f"cannot read domains file: {e}"},
                    indent=indent,
                )
            )
            return 2
    domains, rejected = [], []
    for r in raw:
        d = normalize_domain(r)
        if d and d not in domains:
            domains.append(d)
        elif r.strip() and not r.strip().startswith("#") and not d:
            rejected.append(r.strip())
    if not domains:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "no valid public domains given",
                    "rejected": rejected,
                },
                indent=indent,
            )
        )
        return 2

    results = []
    for i, d in enumerate(domains):
        if i:
            time.sleep(DOMAIN_DELAY)
        results.append(profile_domain(d, wanted))
    if args.jsonl:
        for r in results:
            for o in r["observations"]:
                print(json.dumps({"domain": r["domain"], **o}, ensure_ascii=False))
            for f in r["failures"]:
                print(
                    json.dumps(
                        {
                            "domain": r["domain"],
                            "failure": f,
                            "observed_at": r["observed_at"],
                        },
                        ensure_ascii=False,
                    )
                )
        return 0
    print(
        json.dumps(
            {
                "ok": True,
                "signals": sorted(wanted),
                "rejected": rejected,
                "profiled": len(results),
                "reachable": sum(1 for r in results if r["site"]),
                "observations": sum(len(r["observations"]) for r in results),
                "results": results,
            },
            indent=indent,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
