# tonone-mcp

MCP server that answers one question for an AI agent: _which tonone specialist should handle this task?_
It serves the catalog of [tonone](https://github.com/tonone-ai/tonone) — 140 agents across 15 teams and 573 skills — read-only, no network, no credentials.

## Tools

| Tool          | Use                                                                         |
| ------------- | --------------------------------------------------------------------------- |
| `recommend`   | Plain-language task in, best-matching agents and `/skills` out. Start here. |
| `list_agents` | No args: the 15 teams. With `team`: that team's agents and what each owns.  |
| `get_agent`   | One agent's role, what it owns, and every skill with when to use it.        |

## Install

```bash
claude mcp add tonone -- npx -y tonone-mcp
```

Any MCP client works the same way: command `npx`, args `["-y", "tonone-mcp"]`.

This server only describes the catalog. To run the agents, install the plugin: `/plugin marketplace add tonone-ai/tonone`.

## Develop

```bash
npm install && npm test   # reads ../docs/*.json; `npm pack` copies them into ./data
```
