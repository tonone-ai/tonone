# Third-party notices — `lib/uiux`

The CSV corpus under `uiux/data/` is vendored from **ui-ux-pro-max**, refreshed at release `v2.15.0` (2026-08-13). The search engine, CLI, and design-system generator in this package are tonone's own code; the data is not.

Upstream: <https://github.com/nextlevelbuilder/ui-ux-pro-max-skill>

```
MIT License

Copyright (c) 2024 Next Level Builder

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Refreshing the corpus: copy `src/ui-ux-pro-max/data/*.csv` and `src/ui-ux-pro-max/data/stacks/*.csv` from the upstream checkout, register any new file in `uiux/search.py` (`CSV_CONFIG` for a domain, `STACK_CONFIG` for a stack), update the expected-file lists in `tests/test_domains.py`, and record the new release in `docs/upstream.md`.
