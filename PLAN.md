# v0.1.0 Launch Plan

## All Steps Complete

- [x] **1. Lower Python to >=3.10** in both pyproject.toml
- [x] **2. Fix LICENSE** copyright holder → tonone-ai
- [x] **3. Fix pyproject.toml URLs** → github.com/tonone-ai/tonone
- [x] **4. Add classifiers** for Python 3.10-3.13
- [x] **5. Fix sys.argv mutation** → cli.py accepts argv param, install.py uses parse_known_args
- [x] **6. Fix bare `except Exception`** → specific handlers + `--verbose` traceback + fallback hint
- [x] **7. Backup before overwrite** → `_backup_if_exists()` creates .bak, warns on missing skills
- [x] **8. `--version` and `--verbose` flags** → all three CLIs
- [x] **9. Progress indicator** → `[1/12] my-api (us-central1)` + zero-services early return
- [x] **10. Actionable error remediation** → `_remediation_hint()` maps 6 gcloud errors to fixes
- [x] **11. Tests** → 42 engteam tests + 43 new cloudrun-agent tests = 315 total (all passing)
- [x] **12. GitHub Actions CI** → test.yml (matrix 3.10-3.13) + publish.yml (PyPI on tag)
- [x] **13. READMEs updated** → standalone cloudrun-agent as primary path, correct URLs, Python 3.10+
- [x] **14. TODOS.md** → 5 deferred items
- [x] **15. .gitignore** → ready to commit
- [x] **16. Simplify `get_all_teams()`** → one-liner dict.fromkeys

## Pre-Publish Checklist

- [x] All 16 items complete
- [x] All 315 tests pass (42 engteam + 273 cloudrun-agent)
- [ ] `hatch build` succeeds for both packages
- [ ] Test upload to TestPyPI
- [ ] `pip install` from TestPyPI works
- [ ] README renders correctly on PyPI
- [ ] Initial git commit + tag v0.1.0
- [ ] Create GitHub repo: github.com/tonone-ai/tonone
- [ ] Push to GitHub
- [ ] Publish to PyPI
- [ ] Verify: `pip install cloudrun-agent && cloudrun-agent install` works
- [ ] Verify: `pip install engteam && engteam list` works
