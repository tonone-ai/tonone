# lib/site-signals — buying signals from a company's public website

The profiler behind `/deal-signals`. Stdlib-only Python: for each domain it
fetches the homepage, `robots.txt`, `sitemap.xml`, and the team, careers and
contact pages when they exist. A few plain HTTP requests per company, no
browser, no API key, no model call.

```bash
python3 lib/site-signals/profile.py --catalog
python3 lib/site-signals/profile.py --signals RUNNING_GOOGLE_ADS,INCUMBENT_AGENCY acme.com
python3 lib/site-signals/profile.py --signals all --domains-file targets.txt --pretty
```

## One fact per row

Every finding is an observation:

```json
{
  "signal": "INCUMBENT_AGENCY",
  "value_num": null,
  "value_text": "Pixelworks",
  "confidence": 0.9,
  "evidence_url": "https://pixelworks.agency",
  "observed_at": "2026-10-14T09:12:00Z"
}
```

A new signal needs no schema change. Running again next quarter gives a time
series ("they dropped their agency", "they started running ads"), which is a
better trigger than any one-off fact. And an email can only cite a fact that
has a URL behind it.

## A cohort is a query, not a list

Append runs to a log, then ask questions of it with `cohort.py`:

```bash
python3 lib/site-signals/profile.py --signals all --jsonl --domains-file targets.txt \
  >> .tonone/deal/observations.jsonl
python3 lib/site-signals/cohort.py .tonone/deal/observations.jsonl \
  --require RUNNING_GOOGLE_ADS,INCUMBENT_AGENCY,NO_ONLINE_BOOKING
python3 lib/site-signals/cohort.py .tonone/deal/observations.jsonl --changes
```

Only facts from a company's latest run count: a fact that run no longer saw
(gone, or unobservable that time) stops matching. Where a check really ran,
absence is written as a row (`value_num: 0`); roles and people are not, since a
JavaScript careers page is unobservable, not "not hiring". Anything under 0.75
confidence is ignored, and every match carries the observations (with URLs)
that put it there. `--changes` lists signals whose value moved between the last
two runs where both runs could see them: "stopped running ads", "new agency". A change is usually a better
reason to write than any static fact.

## Nothing is collected until the user says so

`--signals` is required. The skill shows `--catalog` to the user, who picks
which signals to gather; the script refuses to run without that list.

## Precision over recall

A wrong specific in a cold email is worse than none. So:

- The footer agency credit is recorded only on credit wording ("website by",
  "designed by": 0.9; a descriptive anchor like "Web Design": 0.75). Bare
  links and "Powered by ..." (usually a platform or partner badge) are dropped.
- Job titles must end in a role noun or start with "Head of"/"VP"; section
  headings and plural nav links are dropped.
- People need a role next to their name, and a single business word ("Request
  Service") disqualifies a heading. Only owner/founder/senior titles are kept.

## A failure is an observation

An unreachable site, a missing sitemap, a careers page whose roles load from
Greenhouse or Ashby: each lands in the domain's `failures` list. An empty
result never means "checked and nothing there" unless it says so.

## Being a polite visitor

The script sends an honest user agent (`tonone-site-signals/1.0`), reads
`robots.txt` first and respects it for every page including the homepage, waits
a second between domains, and refuses IP addresses, `.local`/`.internal` hosts,
names that resolve to private addresses, and redirects to any of those.

Tests: `python -m pytest tests/test_site_signals.py` (offline fixtures).
Detectors adapted from Harvey's profile collector (MIT), see `NOTICE.md`.
