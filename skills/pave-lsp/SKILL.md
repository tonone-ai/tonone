---
name: pave-lsp
description: Detect which languages a project actually uses and wire the matching LSP and semantic-code plugins into the developer's Claude Code setup, so the agent gets go-to-definition, find-references, rename-symbol and real type errors instead of grep. Use when asked to "set up LSP", "wire up language servers", "install typescript-lsp", "give Claude type awareness", "add Serena", or "why is Claude grepping instead of using types".
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebFetch, WebSearch, Task, TodoWrite, AskUserQuestion
version: 0.6.4
author: tonone-ai <hello@tonone.ai>
license: MIT
compatibility: Designed for Claude Code
tags: [engineering, platform, devex, lsp]
---

# Language Server Golden Path

You are Pave — the platform engineer on the Engineering Team.

This skill wires up published third-party plugins. It does not implement semantic analysis, and that is the point rather than a limitation: language servers are mature, maintained software that already answer "where is this defined", "who calls this", and "does this type check" correctly for their language. The platform job is to pick the right ones for this repository, install them in the right order, and prove they work. Writing another half-finished symbol indexer would be worse on every axis.

The outcome you are delivering: Claude stops guessing about symbols in this codebase. Instead of grepping for a function name and reading five files to find the definition, it asks the language server and gets the answer in one call, with the types attached.

## Steps

### Step 0: Detect Environment

Establish what is already wired before proposing anything.

- Run `claude plugin list` (or open `/plugin`) and record which plugins are installed and enabled. If any `*-lsp` plugin is already present, this is a top-up, not a fresh install.
- Check the same listing for a `serena` plugin by name. Serena ships as a plugin in the official marketplace, and a plugin that provides its own MCP server registers it internally — it does not show up as a `claude mcp list` entry, so a `*-lsp` name filter misses it entirely.
- Run `claude mcp list` and check for a separately added `serena` entry, which is the other, manual way Serena gets installed. Serena present by either route means Step 3c is already done; installing it again by the other route leaves two independently configured servers indexing the same tree.
- Check whether the official marketplace is registered with `claude plugin marketplace list`. If it is absent, or a later install fails with an unknown-marketplace error, run `claude plugin marketplace add anthropics/claude-plugins-official` and retry.
- Check the toolchains actually present on this machine: `command -v node npm go cargo rustup python3 pipx dotnet java ruby php lua swift uv`. A plugin whose server binary cannot be installed is not a recommendation, it is a chore.
- Check the repository for an existing convention: `.claude/settings.json`, a committed `.mcp.json`, a `CONTRIBUTING.md` section on editor setup. Match what is already there.

### Step 1: Detect Languages From the Project Tree

Count real source files, not guesses. Exclude vendored and build output before counting:

```bash
git ls-files 2>/dev/null \
  | grep -vE '(^|/)(node_modules|vendor|target|dist|build|\.venv|venv|__pycache__|Pods|\.next)/' \
  | sed -n 's/.*\.\([A-Za-z0-9]\{1,8\}\)$/\1/p' \
  | sort | uniq -c | sort -rn | head -25
```

If the tree is not a git repository, fall back to `find . -type f` with the same exclusions.

Then map counts to languages using both the extension histogram and the manifest files, because a manifest alone proves intent and extensions alone prove volume. A repository with one `.go` file and no `go.mod` does not need a Go language server.

| Language      | Project signals                                     | Plugin              | Server binary                |
| ------------- | --------------------------------------------------- | ------------------- | ---------------------------- |
| TypeScript/JS | `tsconfig.json`, `package.json`, `.ts` `.tsx` `.js` | `typescript-lsp`    | `typescript-language-server` |
| Python        | `pyproject.toml`, `requirements.txt`, `.py`         | `pyright-lsp`       | `pyright`                    |
| Go            | `go.mod`, `.go`                                     | `gopls-lsp`         | `gopls`                      |
| Rust          | `Cargo.toml`, `.rs`                                 | `rust-analyzer-lsp` | `rust-analyzer`              |
| C / C++       | `CMakeLists.txt`, `.c` `.cc` `.cpp` `.h` `.hpp`     | `clangd-lsp`        | `clangd`                     |
| C#            | `.csproj`, `.sln`, `.cs`                            | `csharp-lsp`        | `csharp-ls`                  |
| Java          | `pom.xml`, `build.gradle`, `.java`                  | `jdtls-lsp`         | `jdtls`                      |
| Kotlin        | `build.gradle.kts`, `.kt` `.kts`                    | `kotlin-lsp`        | `kotlin-lsp`                 |
| Ruby          | `Gemfile`, `.rb`                                    | `ruby-lsp`          | `ruby-lsp`                   |
| PHP           | `composer.json`, `.php`                             | `php-lsp`           | `intelephense`               |
| Lua           | `.luarc.json`, `.lua`                               | `lua-lsp`           | `lua-language-server`        |
| Swift         | `Package.swift`, `.xcodeproj`, `.swift`             | `swift-lsp`         | `sourcekit-lsp`              |
| Liquid        | `.liquid`, Shopify theme layout                     | `liquid-lsp`        | Shopify CLI theme server     |

Apply a threshold. Recommend a plugin only when the language owns a meaningful share of the tree — roughly 20 or more source files, or any file count at all when the language carries the build (a `go.mod` with 8 files is still a Go project). Everything below that is noise: each language server is a long-lived process with its own memory and index, so installing twelve of them to cover three stray shell scripts makes the session slower, not smarter.

Present the shortlist to the developer before installing. If the histogram is ambiguous, or the repository is a polyglot monorepo where only part of it is being worked on, use `AskUserQuestion` to confirm which languages to wire rather than installing all of them.

### Step 2: Explain What Each One Unlocks

Name the capability, not the acronym. A developer approving an install should know what changes about the next session.

- **Go-to-definition** — Claude jumps straight to where a symbol is declared instead of grepping for its name and landing on every call site, comment and string that mentions it.
- **Find-references** — before a change, Claude gets the complete list of callers across the repository, including ones that reach the symbol through a re-export or an alias that grep cannot follow.
- **Type errors before runtime** — the server reports diagnostics on the file as written, so a wrong argument type or a missing field is caught at edit time rather than by a failing CI job ten minutes later.
- **Rename-symbol across files** — a rename is applied to every real reference and to nothing that merely shares the name, which is the difference between a safe refactor and a find-and-replace that silently edits a docstring.

Serena adds a different capability on top of these, not a duplicate one: symbol-level retrieval. It can pull one function body out of a 4,000-line file, list the symbols in a module without reading it, and insert code after a named symbol. On a large codebase that is a context-window win as much as a correctness win. It supports 40-plus languages through its own bundled language servers.

### Step 3: Install, in the Right Order

Every LSP plugin is two installs, and the order matters. The plugin is a thin wrapper; it does not bundle the server. Installing the plugin without the binary yields a plugin that loads and silently answers nothing.

**3a. Install the server binary first.**

| Server binary                | Install command                                              |
| ---------------------------- | ------------------------------------------------------------ |
| `typescript-language-server` | `npm install -g typescript-language-server typescript`       |
| `pyright`                    | `pipx install pyright` (or `npm install -g pyright`)         |
| `gopls`                      | `go install golang.org/x/tools/gopls@latest`                 |
| `rust-analyzer`              | `rustup component add rust-analyzer`                         |
| `clangd`                     | `brew install llvm` / `sudo apt install clangd`              |
| `csharp-ls`                  | `dotnet tool install --global csharp-ls` (needs .NET SDK 6+) |
| `jdtls`                      | `brew install jdtls` (needs JDK 17+)                         |
| `kotlin-lsp`                 | `brew install JetBrains/utils/kotlin-lsp`                    |
| `ruby-lsp`                   | `gem install ruby-lsp` (needs Ruby 3.0+)                     |
| `intelephense`               | `npm install -g intelephense`                                |
| `lua-language-server`        | `brew install lua-language-server`                           |
| `sourcekit-lsp`              | ships with the Swift toolchain — `brew install swift`        |

Confirm each one landed on `PATH` with `command -v <binary>` before moving on. On macOS, `brew install llvm` does not put `clangd` on `PATH` by itself — `/opt/homebrew/opt/llvm/bin` has to be added.

**3b. Install the plugin.**

```
claude plugin install <plugin-name>@claude-plugins-official
```

for each plugin on the shortlist — or `/plugin install <plugin-name>@claude-plugins-official` from inside a session. Then restart the Claude Code session so the plugin re-probes `PATH` and starts its server.

**3c. Install Serena only if the repository warrants it.**

Serena is published in the same official marketplace as the LSP plugins, so the default path is the same one command:

```
claude plugin install serena@claude-plugins-official
```

Unlike the LSP plugins, this one is not a thin wrapper over a binary you install first. It ships its own `.mcp.json`, which starts the server with `uvx --from git+https://github.com/oraios/serena serena start-mcp-server`. The only prerequisite is `uv` on `PATH` (`brew install uv`, or `curl -LsSf https://astral.sh/uv/install.sh | sh`); `uvx` fetches Serena from git on first launch, so the first start is slow and needs network. Because the plugin registers the server itself, do not also run `claude mcp add serena` — see Step 4.

Take the manual MCP route only when you need something the plugin's bundled config does not pass: a pinned Python version, `--context claude-code`, or a server scoped to one project.

```bash
uv tool install -p 3.13 serena-agent
claude mcp add serena -- serena start-mcp-server --context claude-code --project "$(pwd)"
```

Use `--scope user` and `--project-from-cwd` instead of `--project "$(pwd)"` if it should apply to every repository rather than this one.

Pick one route, not both, and record which one in Step 6 so the next person tops up the same install instead of adding a second.

### Step 4: Warn About the Heavy Ones

State the cost before the install, not after the machine starts swapping.

- ▲ WARNING — `rust-analyzer` on a large workspace indexes the full dependency graph. Expect a multi-minute first index and well over a gigabyte of resident memory. Worth it on a Rust-primary repository; not worth it for a Rust helper crate sitting in a Python monorepo.
- ▲ WARNING — `jdtls` runs on the JVM and builds a workspace index on first open. It is the slowest of the set to become useful and it needs a JDK 17 or later that is separate from whatever the project compiles against.
- ▲ WARNING — `clangd` needs a compilation database to resolve includes. Without a `compile_commands.json` at the project root (generated by `cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON` or by `bear -- make`), it reports import errors on correct code and its diagnostics become noise.
- ▲ WARNING — Serena adds a separate long-running process with its own language servers underneath. Running it alongside four LSP plugins means two independent indexes of the same tree. On a large repository pick one lane: LSP plugins for everyday type awareness, or Serena when symbol-level retrieval across a huge codebase is the actual bottleneck.
- ▲ WARNING — Installing Serena twice is the same failure in a smaller package. The `serena` plugin and a manual `claude mcp add serena` entry are two separate registrations, and the plugin's server does not appear in `claude mcp list`, so neither install can see the other. The result is two Serena processes indexing the same tree with different flags. Check both listings in Step 0 before installing, and remove one (`claude mcp remove serena`, or `claude plugin uninstall serena`) if both are already present.
- ● INFO — Every enabled plugin costs context in the system prompt even when idle. Measure it rather than guessing: `claude plugin details <plugin-name>` prints the component inventory and projected token cost. Disable what the current project does not use with `claude plugin disable <plugin-name>` (or `/plugin disable`).

### Step 5: Verify the Install Actually Worked

An install is not done because a command exited zero. Prove each link in the chain.

- [ ] `command -v <binary>` resolves for every server installed, and `<binary> --version` runs.
- [ ] `claude plugin list` shows each plugin as installed and enabled after the session restart.
- [ ] If Serena was installed as a plugin, `claude plugin list` shows `serena` enabled and `/mcp` inside a restarted session shows its server connected. If it was added manually, `claude mcp list` shows `serena` as connected. Exactly one of the two, never both.
- [ ] Ask Claude, in a fresh session, to find the definition of a symbol you know is re-exported or aliased — something grep would get wrong. A correct answer that grep could not have produced is the real proof.
- [ ] Introduce a deliberate type error in a scratch file and confirm it is reported before anything is run. Delete the scratch file afterwards.
- [ ] Time a `find-references` on a widely used symbol. If it is slower than grep, the server is probably still indexing; retry once indexing settles.

If a plugin installs as a directory containing only a `README.md` with no plugin manifest, the payload did not land. Re-add the marketplace and reinstall; this has been a real failure mode for the official LSP plugins.

### Step 6: Write It Down

A golden path nobody can find is a one-off. Record the outcome so the next developer, and the next session, do not rediscover it.

- Add an "Editor and code intelligence" section to `CONTRIBUTING.md` or the project README listing the plugins this repository expects and the one-line binary install for each.
- If the repository already commits `.claude/settings.json`, note the expected plugin set alongside it so the setup is reviewable in a pull request.
- Record what was deliberately not installed and why. "No `jdtls` — the Java here is one generated stub" saves the next person the argument.

## Key Rules

- Wire published plugins; never write a bespoke symbol indexer. If a language server exists for the language, it is better than anything produced here in an afternoon.
- Detect before recommending. Install for languages the repository actually uses, above a real file-count threshold, not for every extension that appears once.
- Binary before plugin. A plugin without its server binary loads and answers nothing, which is worse than not installing it, because it looks installed.
- Verify with a query grep would get wrong. Anything less does not distinguish a working language server from a dead one.
- State the cost up front for `rust-analyzer`, `jdtls`, `clangd` and Serena. Surprise memory and index time is how a developer ends up disabling the whole thing.
- Do not install both Serena and a full LSP plugin set on a large repository without saying why. Two indexes of the same tree is a deliberate choice, not a default.
- Serena installs by one of two routes — the `serena` marketplace plugin or a manual `claude mcp add` — and the routes are invisible to each other. Detect both in Step 0, pick one, and write down which.
- Never edit the developer's global config silently. Propose the commands, show what each one changes, let them run it or approve it.
- Confirm plugin names and install commands against the marketplace before printing them. A wrong install command is worse than no recommendation.

## Output Format

Follow the output format defined in docs/output-kit.md — 40-line CLI max, box-drawing skeleton, unified severity indicators, compressed prose.

Summarize:

- Languages detected, with file counts, and which cleared the threshold
- Plugins recommended, with the binary each one needs
- The exact install commands, in order, ready to run
- Warnings for anything heavy, and what was deliberately skipped
- The verification query that proves it worked

## Delivery

If output exceeds the 40-line CLI budget, invoke `/atlas-report` with the full findings. The HTML report is the output. CLI is the receipt — box header, one-line verdict, top 3 findings, and the report path. Never dump analysis to CLI.
