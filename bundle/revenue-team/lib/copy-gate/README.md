# lib/copy-gate — deterministic checks on outbound copy

A prompt can tell a writer not to use "I hope this finds you well". It can't
make sure the writer listened. `gate.py` does: a stdlib-only script that every
copy-producing skill runs on its drafts before showing them to the user.

Used by `/deal-outreach`, `/buzz-outreach`, `/buzz-pitch`, `/buzz-hn`,
`/pitch-copy`, `/copy-write`, `/copy-slop`, and as a final check in `/copy-audit`
and `/form-web`.

```bash
python3 lib/copy-gate/gate.py --list-profiles
python3 lib/copy-gate/gate.py --profile cold-email --allow-tokens drafts.md
```

## Input

Messages separated by `=== <label>` lines, with optional `Subject:` / `Title:`
header lines. Lines that are just `---` are ignored, so the template separators
skills already print can stay in place. Add `[profile=<name>]` to a marker to
check one message under a different profile (a LinkedIn note inside an email
sequence).

```
=== touch-1 email
Subject: inventory report
{{first_name}}, most ops teams your size rebuild the same report by hand ...

=== touch-2 linkedin [profile=linkedin-note]
Saw your talk on ...
```

## Output

One JSON object: overall `verdict` (PASS / WARN / FAIL), counts, and per-message
findings with a `code` and a plain-language `message`. Exit 0 when nothing
failed, 1 when something did, 2 on a usage error.

| Code                                            | What it catches                                                           |
| ----------------------------------------------- | ------------------------------------------------------------------------- |
| `PLACEHOLDER`                                   | Unfilled `[Name]` / `[Customer X]` slots, TODO, TBD, lorem ipsum          |
| `MERGE_TAG`                                     | `{{tokens}}` / `[[tokens]]` (unless `--allow-tokens`), single-brace typos |
| `BANNED_PHRASE`                                 | Spam triggers and AI tells; fails in every profile                        |
| `HYPE`                                          | Hype and filler; fails in cold email, pitches and HN, warns elsewhere     |
| `EM_DASH`                                       | Em dashes, the most recognisable machine-writing tell                     |
| `TOO_LONG`                                      | Word or character ceiling for the channel                                 |
| `LINKS` / `HTML`                                | Link budget, HTML in a plain-text channel                                 |
| `SUBJECT` / `TITLE`                             | Missing, too long, fake `Re:`/`Fwd:`, name in subject                     |
| `EXCLAIM` / `QUESTIONS` / `ALL_CAPS` / `OPENER` | Tone tells                                                                |

Ceilings are what blocks; each skill states its own lower target in prose.
The gate is a floor under the prompt, not a style guide. A PASS means nothing
mechanical is wrong, not that the copy is good.

## Slop checks (`--slop` or `--profile slop`)

A floor under taste: catches the patterns that mark copy as machine-written.
Opt-in on any profile with `--slop`; the `slop` profile runs only these checks.
Existing profile checks still run first, and their word lists are reused, so
nothing is counted twice.

```bash
python3 lib/copy-gate/gate.py --profile slop drafts.md
python3 lib/copy-gate/gate.py --profile marketing-copy --slop --waive seamless drafts.md
python3 lib/copy-gate/gate.py --profile slop --slop-warn 4 --slop-fail 8 --device em_dash=2:4 drafts.md
```

| Code                        | Level          | What it catches                                                                                                                                                                                                               |
| --------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RESIDUE`                   | always FAIL    | "Certainly!" opener, "I hope this helps", "great question", knowledge-cutoff talk, placeholder-named slots (`{{placeholder}}`, `[Your Name]`). TODO, lorem ipsum, `[Name]` slots and "as an AI" already FAIL in every profile |
| `SLOP_WORD` / `SLOP_PHRASE` | WARN, scored   | AI-tell words (tapestry, leverage, robust, elevate, unlock, empower ...) and stock phrases ("look no further", "when it comes to"). `delve`, `seamless`, `game-changer` etc. come from the existing `SOFT_PHRASES`            |
| `SLOP_EM_DASH`              | WARN / FAIL    | Em dashes per 100 words (warn above 1.0, fail above 2.0 and at least 2). Profiles that ban em dashes outright keep `EM_DASH` instead                                                                                          |
| `SLOP_FRAGMENT_HEADING`     | WARN 1, FAIL 3 | Whole lines like "Fast. Simple."                                                                                                                                                                                              |
| `SLOP_CONTRAST`             | WARN 2, FAIL 4 | "not X, but Y" (1 point) and "It's not X. It's Y." (2 points). "not only ... but also" is exempt                                                                                                                              |
| `SLOP_ING_RIDER`            | WARN 2, FAIL 4 | ", making it easier", ", ensuring that", ", enabling you"                                                                                                                                                                     |
| `SLOP_TRIAD`                | WARN 3, FAIL 5 | Single-word "A, B, and C" lists                                                                                                                                                                                               |
| `SLOP_RHETORICAL_OPENER`    | WARN 1, FAIL 3 | Paragraphs opening "Tired of ...?", "What if ...?"                                                                                                                                                                            |
| `SLOP_BUDGET`               | WARN / FAIL    | Total score per message: words 1 each, stock phrases and spam triggers 2 each, a device that trips its warn limit adds its count. Default warn 3, fail 6                                                                      |

Each message also carries a `slop` object (`score`, budgets, per-device counts).

Override budgets with `--slop-warn N --slop-fail N` and a device with
`--device NAME=WARN:FAIL` (repeatable). Residue ignores budgets.

### Waivers

Client-supplied words (a product named "Seamless Pay") are waived, not edited.
A waived term is masked before any check runs, so it is neither flagged nor
scored, and it appears in the JSON as `waived` with its reason and count. A
single word also covers its inflections (`seamless` waives `seamlessly`).

- `--waive word1,word2` for a one-off run (reason recorded as `--waive flag`).
- `.tonone/copy-waivers.json`, found by walking up from the current directory
  when slop is on, or pass `--waivers PATH`:

```json
{ "waive": [{ "term": "seamless", "reason": "client product name" }] }
```

An entry without a `reason` is a usage error (exit 2).

## Changing it

Phrase lists and profiles are plain tuples and dicts at the top of `gate.py`.
Tests: `python -m pytest tests/test_copy_gate.py tests/test_copy_slop.py`. Design credit: Harvey's
pre-send gate (MIT), see `NOTICE.md`.
