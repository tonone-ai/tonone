# lib/copy-gate — deterministic checks on outbound copy

A prompt can tell a writer not to use "I hope this finds you well". It can't
make sure the writer listened. `gate.py` does: a stdlib-only script that every
copy-producing skill runs on its drafts before showing them to the user.

Used by `/deal-outreach`, `/buzz-outreach`, `/buzz-pitch`, `/buzz-hn`,
`/pitch-copy` and `/copy-write`.

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

## Changing it

Phrase lists and profiles are plain tuples and dicts at the top of `gate.py`.
Tests: `python -m pytest tests/test_copy_gate.py`. Design credit: Harvey's
pre-send gate (MIT), see `NOTICE.md`.
