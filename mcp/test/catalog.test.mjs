import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createCatalog } from "../server.mjs";

const load = (f) =>
  JSON.parse(readFileSync(new URL(`../../docs/${f}`, import.meta.url), "utf8"));
const catalog = createCatalog(
  load("agent-index.json"),
  load("skill-index.json"),
);

test("recommend routes a Terraform drift task to terra", () => {
  const r = catalog.recommend("detect terraform state drift");
  assert.ok(
    r.agents.some((a) => a.agent === "terra"),
    JSON.stringify(r.agents),
  );
  assert.ok(
    r.skills.some((s) => s.skill === "/terra-drift"),
    JSON.stringify(r.skills),
  );
});

test("list_agents without team returns 15 teams", () => {
  assert.equal(catalog.teams().length, 15);
});

test("get_agent returns skills and null for unknown", () => {
  const a = catalog.getAgent("Forge");
  assert.ok(a.skills.length > 0);
  assert.equal(catalog.getAgent("nope"), null);
});

test("recommend ranks the domain specialist first", () => {
  const first = (q) => catalog.recommend(q, 3).agents[0].agent;
  assert.equal(first("kubernetes pods keep crashing"), "kube");
  assert.equal(first("write a changelog for the release"), "change");
  assert.equal(first("cold email sequence for CTOs"), "drip");
});
