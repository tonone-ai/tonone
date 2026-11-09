# Evals

An eval here is a deterministic behavioral check of a tool: run the real CLI on
fixture input and assert on its output. No LLM, no network, no randomness.
Unit tests (`tests/test_*.py`) cover functions; evals cover end-to-end CLI behavior.

## Layout

    tests/evals/<name>/eval.json     metadata + touchfiles
    tests/evals/<name>/test_*.py     the checks (pytest)
    tests/evals/<name>/fixtures/     input files
    tests/evals/conftest.py          shared helpers

## eval.json

    {
      "name": "form-lint",
      "description": "one line: what behavior this pins",
      "touchfiles": ["team/form/scripts/design-lint/**", "tests/evals/form-lint/**"]
    }

`touchfiles` are repo-relative globs (`**` crosses directories, `*` does not).
An eval runs when a changed file matches any glob. The global touchfiles
(`scripts/eval-select.py`, `tests/evals/conftest.py`) select every eval.

## Select and run

    python3 scripts/eval-select.py                    # git diff origin/main...HEAD (or main)
    python3 scripts/eval-select.py --files a.py b.js  # explicit files
    python3 scripts/eval-select.py --all
    python3 scripts/eval-select.py --run              # run pytest on the selection

Always include `tests/evals/<name>/**` in an eval's own touchfiles.
