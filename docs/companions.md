# Companions

Third-party MCP servers and plugins that make tonone agents better at specific jobs. Recommendations and routing only: nothing here is installed, bundled or required.

## What tonone ships

Grep finding (2026-11-09): **tonone ships no MCP servers; nothing is bundled.** No `.mcp.json` in the repo, no `mcpServers` in any manifest, no MCP wiring in `.claude-plugin/` or README. The only `.mcp.json` / `mcpServers` mentions are inside `team/pave/skills/pave-lsp/SKILL.md` (and its root mirror) and `hooks/tonone-skill-gate.js` (a code comment about preserving a user's own settings), which discuss other people's servers. Agents work without any companion; companions raise accuracy on specific tasks.

## Cost: read this first

Every enabled server costs context. Per the [Claude Code costs guide](https://code.claude.com/docs/en/costs#reduce-mcp-server-overhead), MCP tool definitions are deferred by default (tool search), so idle servers cost mainly tool names and server instructions, not full schemas. Still: run `/context` to see the real cost, run `/mcp` to disable servers you are not using, and enable per project rather than globally. Prefer a CLI (`gh`, `aws`) over an MCP server when one exists.

Install pointers link to each project's own docs. Check them; commands change and this doc does not repeat them. Marketplace entries below exist in `anthropics/claude-plugins-official` as of 2026-11-09 (install form: `/plugin install <name>@claude-plugins-official`).

## Recommendations

### Context7: current library docs

- **Gives:** version-specific library and framework documentation pulled at query time, instead of the model's training memory.
- **Helps:** Spine, Prism, Cortex, Relay when writing against a specific library version; Flux for ORM/driver APIs.
- **Install:** [github.com/upstash/context7](https://github.com/upstash/context7); also listed as `context7` in the official marketplace.
- **Cost:** one remote server, few tools. Cheap. Needs network; sends library queries to a third party.

### Browser verification: Playwright MCP or Chrome DevTools MCP

- **Gives:** a live browser the agent can drive and inspect: screenshots, DOM, console, network. Chrome DevTools MCP adds performance traces.
- **Helps:** Prism (check rendered components), Proof (E2E and flaky-test triage), Axe (audit the rendered page, not just the source), Form critique of shipped UI.
- **Install:** [github.com/microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp) (`playwright` in the marketplace); [github.com/ChromeDevTools/chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp) (`chrome-devtools-mcp` in the marketplace).
- **Cost:** the largest tool surface here, and screenshots/snapshots are heavy results. Pick one, not both. Enable only on UI work.

### Semantic code navigation: Serena or LSP plugins

- **Gives:** go-to-definition, find-references, symbol-level reads, real type errors. Serena adds symbol retrieval and edits across 40+ languages; LSP plugins give per-language type awareness.
- **Helps:** Spine, Pave, Atlas on large repos; anyone refactoring across files.
- **Install:** run [`/pave-lsp`](../team/pave/skills/pave-lsp/SKILL.md). It detects languages and handles install order, the Serena-vs-LSP choice and double-install traps. Serena upstream: [github.com/oraios/serena](https://github.com/oraios/serena) (`serena` in the marketplace). Overview: [code intelligence plugins](https://code.claude.com/docs/en/plugins/code-intelligence).
- **Cost:** each server is a long-lived process with its own index (memory, startup time). On a large repo choose one lane. Small repos: skip.

### Review and security plugins

- **Gives:** multi-agent PR review (`code-review`, `pr-review-toolkit`), pattern and LLM security review of generated code (`security-guidance`), deeper vulnerability scanning inside the session (`claude-security`).
- **Helps:** Warden (second opinion on findings), Apex review gate (`/apex-gate`, `/apex-review`), Proof (test-gap and error-handling review).
- **Install:** browse [github.com/anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official), or `/plugin` then Discover. Read each plugin's README for what it runs automatically; `security-guidance` warns on edits.
- **Cost:** review plugins spawn several agents per run, which is a cost multiplier, not a fixed overhead. Use on PRs that merit it. They complement tonone's gates; they do not replace Warden's threat modeling.

## Routing table

| tonone agent | Companion                               | Use it for                                 |
| ------------ | --------------------------------------- | ------------------------------------------ |
| Spine        | Context7, Serena/LSP                    | API against pinned lib versions; refactors |
| Prism        | Context7, Playwright or Chrome DevTools | Component APIs; verify rendered output     |
| Cortex       | Context7                                | SDK and model-provider docs                |
| Relay        | Context7                                | CI action and tool versions                |
| Proof        | Playwright, review plugins              | E2E runs; test review                      |
| Axe          | Playwright or Chrome DevTools           | Audit the live page                        |
| Form         | Playwright or Chrome DevTools           | Critique the rendered UI                   |
| Pave         | Serena/LSP via `/pave-lsp`              | Wire code intelligence for the team        |
| Atlas        | Serena/LSP                              | Map large repos without reading every file |
| Warden       | `security-guidance`, `claude-security`  | Second-opinion security review             |
| Apex         | `code-review`, `pr-review-toolkit`      | Extra reviewer behind the review gate      |

## Rule of thumb

Add a companion when an agent keeps getting a specific thing wrong (stale API, unverified UI, grep where types would do). Don't add one speculatively: each is context, a process, and a trust decision.
