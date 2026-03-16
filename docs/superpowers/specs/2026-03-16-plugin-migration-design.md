# Plugin Migration Design

Migrate eng-team from pip-based distribution to Claude Code's native plugin system while keeping pip as a secondary install path.

## Context

The eng-team repo currently distributes agents as PyPI packages (`pip install cloudrun-agent` + `cloudrun-agent install`). The Claude Code ecosystem uses a native plugin system (`/plugin marketplace add` + `/plugin install`). This migration aligns eng-team with that convention.

## Decisions

- **Flat plugin per agent** inside team directories (preserves team grouping)
- **Python code in `scripts/`** with auto-venv via post-install hook
- **Pip path maintained** as secondary via `engteam` CLI and PyPI
- **Template updated** for plugin format
- **Team grouping** preserved in filesystem and as metadata in `marketplace.json`

## Repository Structure

```
eng-team/
├── marketplace.json                         # marketplace registry
│
├── cloud-architecture/                      # team directory (kept)
│   └── cloud-run-specialist/                # plugin
│       ├── .claude-plugin/
│       │   └── plugin.json                  # plugin manifest
│       ├── agents/
│       │   └── cloudrun-analyzer.md         # agent definition
│       ├── skills/
│       │   ├── cloudrun-dashboard/SKILL.md
│       │   ├── cloudrun-check/SKILL.md
│       │   ├── cloudrun-inspect/SKILL.md
│       │   └── cloudrun-history/SKILL.md
│       ├── hooks/
│       │   └── hooks.json                   # post-install venv setup
│       ├── scripts/
│       │   ├── setup.sh                     # creates venv, installs deps
│       │   ├── pyproject.toml               # Python package for venv
│       │   └── cloudrun_agent/              # Python source (moved)
│       │       ├── __init__.py
│       │       ├── cli.py                   # analyze subcommand entry point
│       │       ├── runner.py
│       │       ├── overview.py
│       │       ├── dashboard.py
│       │       ├── history.py
│       │       ├── models/
│       │       │   ├── __init__.py
│       │       │   └── service.py
│       │       ├── tools/
│       │       │   ├── __init__.py
│       │       │   ├── gcloud.py
│       │       │   ├── parser.py
│       │       │   └── metrics.py
│       │       └── analyzers/
│       │           ├── __init__.py
│       │           ├── resources.py
│       │           ├── performance.py
│       │           ├── pricing.py
│       │           ├── security.py
│       │           └── traffic.py
│       ├── tests/                           # agent tests (moved)
│       └── README.md
│
├── security/                                # future team
│   └── iam-auditor/
├── devops/                                  # future team
│   └── ci-cd-engineer/
│
├── src/engteam/                             # pip marketplace CLI (kept)
├── templates/new-agent/                     # updated for plugin format
├── tests/                                   # marketplace CLI tests
└── pyproject.toml                           # engteam PyPI package (kept)
```

## Plugin Manifest

`cloud-architecture/cloud-run-specialist/.claude-plugin/plugin.json`:

```json
{
  "name": "cloud-run-specialist",
  "version": "0.1.0",
  "description": "Audit Cloud Run fleet: resource waste, performance, pricing, traffic, security",
  "author": {
    "name": "thisisfatih",
    "url": "https://github.com/thisisfatih"
  },
  "repository": "https://github.com/thisisfatih/eng-team",
  "license": "MIT",
  "keywords": ["gcp", "cloud-run", "audit", "infrastructure"]
}
```

## Marketplace Registry

`marketplace.json` (repo root):

```json
{
  "name": "thisisfatih",
  "description": "Engineering Team - Claude Code agents that work as specialized engineers",
  "plugins": {
    "cloud-run-specialist": {
      "path": "cloud-architecture/cloud-run-specialist",
      "description": "Audit Cloud Run fleet: resource waste, performance, pricing, traffic, security",
      "team": "cloud-architecture"
    }
  }
}
```

New agents add an entry to `plugins` and create their directory under the appropriate team.

## User Flow

```bash
# Plugin path (primary)
/plugin marketplace add thisisfatih/eng-team
/plugin install cloud-run-specialist@thisisfatih

# Pip path (secondary, still works)
pip install cloudrun-agent
cloudrun-agent install
```

After either install method, skills are available immediately:

```
> /cloudrun-dashboard
> /cloudrun-check
```

Skills are namespaced by the plugin system as `/cloud-run-specialist:cloudrun-dashboard` with `/cloudrun-dashboard` as a shortcut when there's no collision.

## Skills Restructuring

Skills move from flat `.md` files to the plugin-standard directory structure.

**Before:** `src/cloudrun_agent/skills/cloudrun-dashboard.md` (bundled in Python package, copied to `~/.claude/skills/` by `install.py`)
**After:** `cloud-architecture/cloud-run-specialist/skills/cloudrun-dashboard/SKILL.md`

Content stays the same. Python invocation paths update to use relative path resolution from the skill's own directory rather than relying on global commands:

```bash
# Before
cloudrun-agent analyze --project $PROJECT

# After (skill SKILL.md uses dirname-based resolution)
PLUGIN_ROOT="$(cd "$(dirname "$0")/../../" && pwd)"
"$PLUGIN_ROOT/scripts/.venv/bin/python" -m cloudrun_agent.runner --project $PROJECT
```

**Note:** If the Claude Code plugin system exposes a `$PLUGIN_DIR` environment variable, skills should use that instead of dirname resolution. This should be verified during implementation and the skills updated accordingly.

## Post-Install Hook & Venv Setup

`cloud-architecture/cloud-run-specialist/hooks/hooks.json`:

```json
{
  "hooks": [
    {
      "event": "post_install",
      "command": "bash scripts/setup.sh",
      "description": "Set up Python environment for analyzers"
    }
  ]
}
```

**Implementation note:** The `hooks.json` format and `post_install` event need to be verified against the actual Claude Code plugin hook system during implementation. If the plugin system does not support `post_install` hooks, the fallback strategy is:

1. Check if Claude Code's `hooks/hooks.json` supports lifecycle events
2. If not, use a `settings.json` PreToolUse hook that runs setup on first agent invocation
3. As a last resort, the agent definition itself can check for the venv and run `setup.sh` on first use

`cloud-architecture/cloud-run-specialist/scripts/setup.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if command -v uv &>/dev/null; then
  uv venv "$SCRIPT_DIR/.venv"
  uv pip install -e "$SCRIPT_DIR" --python "$SCRIPT_DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
  python3 -m venv "$SCRIPT_DIR/.venv"
  "$SCRIPT_DIR/.venv/bin/pip" install -e "$SCRIPT_DIR"
else
  echo "ERROR: Python 3 is required. Install python3 or uv."
  exit 1
fi

echo "Cloud Run Specialist ready."
```

`cloud-architecture/cloud-run-specialist/scripts/pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "cloudrun-agent"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = []

[tool.hatch.build.targets.wheel]
packages = ["cloudrun_agent"]

[project.scripts]
cloudrun-agent = "cloudrun_agent.cli:main"
```

The console script entry point provides `cloudrun-agent analyze` for pip users. The `install` subcommand is removed since the plugin system handles that.

The venv lives at `scripts/.venv/` inside the plugin directory. Self-contained, doesn't pollute the user's system. Uninstalling the plugin removes everything.

## Pip Path (Secondary)

The `engteam` CLI stays published on PyPI. The registry gains plugin metadata:

```python
@dataclass(frozen=True)
class AgentEntry:
    name: str
    team: str
    pypi_package: str
    plugin_name: str          # "cloud-run-specialist"
    marketplace: str          # "thisisfatih/eng-team"
    description: str
    skills: tuple[str, ...]
    status: str = "available"
```

`engteam list` shows both install methods. `engteam install` continues to work via pip. The `cloudrun-agent` PyPI package stays published - its `install.py` reads agent defs and skills from the plugin-standard directories (single source of truth, no duplication).

## Template

`templates/new-agent/` updates to produce plugin-format agents:

```
templates/new-agent/
├── .claude-plugin/
│   └── plugin.json              # manifest template
├── agents/
│   └── AGENT_SLUG.md            # agent definition template
├── skills/
│   └── SKILL_NAME/
│       └── SKILL.md             # skill template
├── hooks/
│   └── hooks.json               # post-install hook template
├── scripts/
│   ├── setup.sh                 # venv setup (reusable as-is)
│   ├── pyproject.toml           # Python package template
│   └── AGENT_MODULE/
│       ├── __init__.py
│       └── runner.py            # minimal analyzer scaffold
└── README.md
```

Workflow to add a new agent:

1. Copy `templates/new-agent/` to `<team>/<agent-name>/`
2. Replace placeholders in plugin.json, agent def, skills
3. Implement analyzers in `scripts/<module>/`
4. Add entry to `marketplace.json`
5. Add entry to `src/engteam/registry.py` (for pip path)

## Test Migration

Tests move from `cloud-architecture/cloud-run-specialist/tests/` to remain at the same relative location within the plugin directory. The test configuration updates:

**`cloud-architecture/cloud-run-specialist/scripts/pyproject.toml`** includes pytest config:

```toml
[tool.pytest.ini_options]
testpaths = ["../tests"]
pythonpath = ["."]
```

**Running tests during development:**

```bash
cd cloud-architecture/cloud-run-specialist/scripts
# First time: setup venv
bash setup.sh
# Run tests
.venv/bin/python -m pytest ../tests/
```

Tests run inside the plugin's `scripts/.venv` which has the analyzer code installed in editable mode.

## CI/CD Updates

The GitHub Actions workflow (`.github/workflows/publish.yml`) updates to match the new source location:

```yaml
publish-cloudrun-agent:
  name: Publish cloudrun-agent
  runs-on: ubuntu-latest
  environment: pypi

  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.13"

    - name: Install build tools
      run: pip install build

    - name: Build
      working-directory: cloud-architecture/cloud-run-specialist/scripts
      run: python -m build

    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
      with:
        packages-dir: cloud-architecture/cloud-run-specialist/scripts/dist/
        skip-existing: true
```

The `publish-engteam` job stays unchanged (root `pyproject.toml` is not moving).

The test workflow (`.github/workflows/test.yml`) also updates:

```yaml
test-cloudrun-agent:
  name: cloudrun-agent (Python ${{ matrix.python-version }})
  runs-on: ubuntu-latest
  strategy:
    matrix:
      python-version: ["3.10", "3.11", "3.12", "3.13"]

  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install uv
      uses: astral-sh/setup-uv@v4

    - name: Install and test
      working-directory: cloud-architecture/cloud-run-specialist/scripts
      run: |
        uv sync
        uv run pytest ../tests/ -v --tb=short
```

The `test-engteam` job stays unchanged.

## What Gets Deleted

- **`cloud-run-specialist/src/cloudrun_agent/install.py`** - plugin system handles installation
- **`cloud-run-specialist/src/` directory** (top-level) - Python source moves to `scripts/cloudrun_agent/`; `cli.py` is kept but moves to `scripts/cloudrun_agent/cli.py` with only the `analyze` subcommand (install subcommand removed)
- **`cloud-run-specialist/pyproject.toml`** (top-level) - replaced by `scripts/pyproject.toml`
- **`cloud-run-specialist/src/cloudrun_agent/agent_def/`** - `cloudrun-analyzer.md` moves to plugin `agents/` dir
- **`cloud-run-specialist/src/cloudrun_agent/skills/`** - skill `.md` files move to plugin `skills/<name>/SKILL.md`
- **`cloud-run-specialist/.claude/`** - Claude Code registration directory, no longer needed (plugin system auto-registers)
- **`cloud-run-specialist/uv.lock`** - regenerated from `scripts/pyproject.toml` during `setup.sh`
- **`cloud-run-specialist/dist/`** - build artifacts, no longer at this location
- **`cloud-run-specialist/CLAUDE.md`** - rewritten to reflect new `scripts/` layout

## .gitignore Updates

Add to root `.gitignore`:

```
# Plugin venvs (generated by setup.sh)
**/scripts/.venv/

# Plugin build artifacts
**/scripts/dist/
```

Verify that existing `.gitignore` patterns (`.claude/skills/`, `.claude/commands/`) do not conflict with the new plugin directory structure. They should not since plugin dirs use different paths (`skills/`, `agents/` at plugin root, not `.claude/`).

## Documentation Updates

Both README.md and CLAUDE.md update to reflect the migration:

**README.md** (repo root):

- Quick Start changes to show plugin install as primary, pip as secondary
- Available Agents table adds plugin install column
- Marketplace Commands section shows `/plugin` commands alongside `engteam` CLI

**CLAUDE.md** (repo root):

- Structure diagram updates to show plugin layout
- Adding a New Agent workflow updates for plugin format
- Development section updates with new test/run commands

**cloud-run-specialist/CLAUDE.md**:

- Rewritten to reflect `scripts/` layout and plugin structure
- Updated development commands (`cd scripts && .venv/bin/python -m pytest`)

**cloud-run-specialist/README.md**:

- Plugin install as primary Quick Start
- Pip install as alternative
