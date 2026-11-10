#!/usr/bin/env node
// tonone-mcp — tells an AI agent which tonone specialist agent or skill to use for a task.
// Read-only: serves the generated catalog indexes (agent-index.json, skill-index.json).
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const here = dirname(fileURLToPath(import.meta.url));

function loadIndex(file) {
  // Published package has ./data; in the repo the indexes live in ../docs.
  for (const dir of [join(here, "data"), join(here, "..", "docs")]) {
    const p = join(dir, file);
    if (existsSync(p)) return JSON.parse(readFileSync(p, "utf8"));
  }
  throw new Error(`tonone-mcp: ${file} not found`);
}

const STOP = new Set(
  "a an and the to of for in on with my our i we is are be do it this that how what use using need want help me can should".split(
    " ",
  ),
);
// Light stemming so "migrations"/"migration" and "crashing"/"crash" match.
const stem = (t) =>
  t.replace(/(ing|ed|es|s)$/, (m) => (t.length - m.length >= 4 ? "" : m));
const tokens = (s) =>
  (s.toLowerCase().match(/[a-z0-9]+/g) ?? [])
    .filter((t) => !STOP.has(t) && t.length > 1)
    .map(stem);

export function createCatalog(agents, skills) {
  const byName = new Map(agents.map((a) => [a.name, a]));
  const skillsOf = (agent) => skills.filter((s) => s.agent === agent);

  // Score = weighted token hits, each scaled by how rare the token is across the catalog (IDF),
  // so "keep" or "bill" in ordinary prose doesn't outrank a real domain term like "kubernetes".
  const docFreq = new Map();
  for (const doc of [
    ...agents.map((a) => `${a.name} ${a.hat} ${a.owns}`),
    ...skills.map((k) => `${k.name} ${k.description}`),
  ])
    for (const t of new Set(tokens(doc)))
      docFreq.set(t, (docFreq.get(t) ?? 0) + 1);
  const total = agents.length + skills.length;
  const idf = (t) => Math.log(1 + total / (docFreq.get(t) ?? 1));
  const score = (qTokens, fields) => {
    let sum = 0;
    for (const [text, weight] of fields) {
      const hay = new Set(tokens(text));
      for (const t of qTokens) if (hay.has(t)) sum += weight * idf(t);
    }
    return sum;
  };

  return {
    teams: () => {
      const m = new Map();
      for (const a of agents) m.set(a.team, [...(m.get(a.team) ?? []), a.name]);
      return [...m].map(([team, names]) => ({ team, agents: names }));
    },
    listAgents: (team) =>
      agents.filter(
        (a) => !team || a.team.toLowerCase() === team.toLowerCase(),
      ),
    getAgent: (name) => {
      const a = byName.get(name.toLowerCase());
      return a
        ? {
            ...a,
            skills: skillsOf(a.name).map((s) => ({
              skill: `/${s.name}`,
              description: s.description,
            })),
          }
        : null;
    },
    recommend: (task, limit = 5) => {
      const q = tokens(task);
      const rankedAgents = agents
        .map((a) => ({
          a,
          s: score(q, [
            [a.name, 1],
            [a.hat, 3],
            [a.owns, 2],
            [a.team, 1],
          ]),
        }))
        .filter((x) => x.s > 0)
        .sort((x, y) => y.s - x.s)
        .slice(0, limit)
        .map(({ a }) => ({
          agent: a.name,
          hat: a.hat,
          team: a.team,
          owns: a.owns,
        }));
      const rankedSkills = skills
        .map((k) => ({
          k,
          s: score(q, [
            [k.name, 2],
            [k.description, 1],
          ]),
        }))
        .filter((x) => x.s > 0)
        .sort((x, y) => y.s - x.s)
        .slice(0, limit)
        .map(({ k }) => ({
          skill: `/${k.name}`,
          agent: k.agent,
          description: k.description,
        }));
      return { agents: rankedAgents, skills: rankedSkills };
    },
  };
}

const text = (obj) => ({
  content: [{ type: "text", text: JSON.stringify(obj, null, 2) }],
});

async function main() {
  const catalog = createCatalog(
    loadIndex("agent-index.json"),
    loadIndex("skill-index.json"),
  );
  const server = new McpServer({ name: "tonone", version: "0.1.0" });

  server.registerTool(
    "recommend",
    {
      description:
        "Given a task in plain language, return the tonone specialist agents and slash-command skills best suited to it. Start here.",
      inputSchema: {
        task: z.string().min(2),
        limit: z.number().int().min(1).max(20).optional(),
      },
    },
    async ({ task, limit }) => text(catalog.recommend(task, limit)),
  );

  server.registerTool(
    "list_agents",
    {
      description:
        "List tonone agents. Without a team, returns the 15 teams and their agent names; with a team, returns that team's agents and what each owns.",
      inputSchema: { team: z.string().optional() },
    },
    async ({ team }) => text(team ? catalog.listAgents(team) : catalog.teams()),
  );

  server.registerTool(
    "get_agent",
    {
      description:
        "Describe one tonone agent: its role, what it owns, and every skill it exposes with when to use each.",
      inputSchema: { name: z.string() },
    },
    async ({ name }) => {
      const a = catalog.getAgent(name);
      return a
        ? text(a)
        : {
            isError: true,
            content: [
              {
                type: "text",
                text: `No agent named "${name}". Use list_agents to see names.`,
              },
            ],
          };
    },
  );

  await server.connect(new StdioServerTransport());
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1])
  await main();
