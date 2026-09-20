"use strict";

/**
 * tests/test_project_shape.js — lib/signals/project-shape.js
 *
 * Run: node --test tests/test_project_shape.js
 *
 * No credentials, no network. The one test that exercises the tie-break path
 * injects a fake decision layer rather than calling lib/jev, so the suite is
 * deterministic whether or not a key happens to be in the environment.
 */

const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const os = require("os");
const path = require("path");

const shape = require("../lib/signals/project-shape.js");

// ── Fixtures ────────────────────────────────────────────────────────────────

const roots = [];

function fixture(tree) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "tonone-shape-"));
  roots.push(root);
  for (const [rel, content] of Object.entries(tree)) {
    const full = path.join(root, rel);
    fs.mkdirSync(path.dirname(full), { recursive: true });
    fs.writeFileSync(full, content == null ? "" : content);
  }
  return root;
}

test.after(() => {
  for (const root of roots) {
    try {
      fs.rmSync(root, { recursive: true, force: true });
    } catch {}
  }
});

const NEXT_APP = {
  "package.json": JSON.stringify({
    dependencies: { next: "14.0.0", react: "18.0.0" },
    devDependencies: { tailwindcss: "3.4.0" },
  }),
  "next.config.js": "module.exports = {};",
  "app/page.tsx": "export default function Page() {}",
  "components/Button.tsx": "export function Button() {}",
};

const TERRAFORM_REPO = {
  "main.tf": 'resource "aws_vpc" "main" {}',
  ".terraform.lock.hcl": "",
  "terraform/network.tf": "",
  "k8s/deployment.yaml": "",
};

const PYTHON_DATA_REPO = {
  "requirements.txt": "pandas>=2.0\nnumpy\ndbt-core==1.7.0\n",
  "dbt_project.yml": "name: warehouse",
  "notebooks/eda.ipynb": "{}",
};

// ── The three shapes the roster recommender exists to get right ─────────────

test("a Next.js app recommends Prism, Form, Draft, Axe", async () => {
  const rec = await shape.recommend(fixture(NEXT_APP));
  assert.equal(rec.roster.id, "frontend-web");
  assert.deepEqual(shape.agentsFor(rec.roster), [
    "apex",
    "prism",
    "form",
    "draft",
    "axe",
  ]);
  assert.equal(rec.source, "signals");
});

test("a Terraform repo recommends Terra, Forge, Finop, Kube", async () => {
  const rec = await shape.recommend(fixture(TERRAFORM_REPO));
  assert.equal(rec.roster.id, "infra-iac");
  assert.deepEqual(shape.agentsFor(rec.roster), [
    "apex",
    "terra",
    "forge",
    "finop",
    "kube",
  ]);
});

test("a Python data repo recommends Flux, Lens, Clean, Feat", async () => {
  const rec = await shape.recommend(fixture(PYTHON_DATA_REPO));
  assert.equal(rec.roster.id, "data-python");
  assert.deepEqual(shape.agentsFor(rec.roster), [
    "apex",
    "flux",
    "lens",
    "clean",
    "feat",
  ]);
});

// ── Degradation ─────────────────────────────────────────────────────────────

test("an empty directory falls back to the default roster, not a guess", async () => {
  const rec = await shape.recommend(fixture({}));
  assert.equal(rec.roster.id, "starter");
  assert.equal(rec.source, "default");
  assert.equal(rec.confidence, 0);
  assert.equal(rec.alternate, null);
});

test("a directory that does not exist never throws", async () => {
  const rec = await shape.recommend("/nonexistent/tonone/shape/fixture");
  assert.equal(rec.roster.id, "starter");
  assert.equal(rec.signals.ok, false);
});

test("gather tolerates an unreadable path and returns an empty snapshot", () => {
  const signals = shape.gather("/nonexistent/tonone/shape/fixture");
  assert.equal(signals.dirs.size, 0);
  assert.equal(signals.files.size, 0);
  assert.equal(signals.deps.size, 0);
  assert.equal(shape.digest(signals), "an empty repository");
});

test("scoreRosters is pure and survives a malformed snapshot", () => {
  const ranked = shape.scoreRosters(null);
  assert.equal(ranked.length, shape.ROSTERS.length);
  assert.ok(ranked.every((r) => r.score === 0));
});

test("a malformed package.json does not sink the whole snapshot", () => {
  const root = fixture({ "package.json": "{ not json", "main.tf": "" });
  const signals = shape.gather(root);
  assert.equal(signals.deps.size, 0);
  assert.ok(signals.files.has("main.tf"));
});

// ── Bounds ──────────────────────────────────────────────────────────────────

test("the walk ignores node_modules and other build output", () => {
  const root = fixture({
    "package.json": JSON.stringify({ dependencies: { next: "14" } }),
    "node_modules/next/package.json": "{}",
    "dist/bundle.js": "",
  });
  const signals = shape.gather(root);
  assert.ok(!signals.dirs.has("node_modules"));
  assert.ok(!signals.dirs.has("dist"));
});

test("the digest stays short enough to be cheap as a decision state", () => {
  const rec = shape.gather(fixture(NEXT_APP));
  assert.ok(shape.digest(rec).length < 1200);
});

// ── Output ──────────────────────────────────────────────────────────────────

test("the first install command installs exactly the roster", async () => {
  const rec = await shape.recommend(fixture(NEXT_APP));
  const commands = shape.installCommands(rec.roster);
  // Index 0 is the contract every caller shows. It must name every agent in
  // the roster and nothing else — a bundle in this slot would install ten
  // agents while silently omitting three the banner just promised.
  const named = commands[0]
    .replace("claude plugin install ", "")
    .split(" ")
    .map((token) => token.replace("@tonone-ai", ""));
  assert.deepEqual(named, shape.agentsFor(rec.roster));
  assert.equal(named[0], "apex");
  assert.equal(commands[1], "claude plugin install design-team@tonone-ai");
});

test("every roster's exact command covers its agents, bundles come after", () => {
  for (const roster of shape.ROSTERS.concat([shape.DEFAULT_ROSTER])) {
    const commands = shape.installCommands(roster);
    for (const agent of shape.agentsFor(roster)) {
      assert.ok(
        commands[0].includes(agent + "@tonone-ai"),
        `roster ${roster.id} omits ${agent} from its exact install command`,
      );
    }
    for (const bundle of roster.bundles) {
      assert.ok(
        commands
          .slice(1)
          .includes("claude plugin install " + bundle + "@tonone-ai"),
        `roster ${roster.id} lost bundle ${bundle}`,
      );
    }
  }
});

test("a lone SECURITY.md does not win a roster", async () => {
  // SECURITY.md is boilerplate in a large share of repositories. On its own
  // it must stay below MIN_SCORE, or every repo with a disclosure policy is
  // told it needs four security specialists.
  const rec = await shape.recommend(
    fixture({
      "SECURITY.md": "Report issues to security@example.com",
      "README.md": "",
    }),
  );
  assert.equal(rec.roster.id, shape.DEFAULT_ROSTER.id);
  assert.equal(rec.source, "default");

  // Real security tooling still wins.
  const armed = await shape.recommend(
    fixture({
      "SECURITY.md": "",
      ".snyk": "",
      ".github/codeql-config.yml": "",
    }),
  );
  assert.equal(armed.roster.id, "security");
});

test("render stays inside the onboarding budget", async () => {
  const rec = await shape.recommend(fixture(TERRAFORM_REPO));
  const lines = shape.render(rec);
  assert.ok(lines.length <= 4, "render must not scroll");
  assert.ok(
    lines.every((l) => l.length <= 56),
    "render must fit the banner",
  );
});

test("every roster names agents that exist in team/", () => {
  const all = shape.ROSTERS.concat([shape.DEFAULT_ROSTER]);
  for (const roster of all) {
    for (const agent of shape.agentsFor(roster)) {
      assert.ok(
        fs.existsSync(
          path.join(__dirname, "..", "team", agent, ".claude-plugin"),
        ),
        `roster ${roster.id} names unknown agent ${agent}`,
      );
    }
  }
});

test("every roster names bundles that exist in bundle/", () => {
  const all = shape.ROSTERS.concat([shape.DEFAULT_ROSTER]);
  for (const roster of all) {
    for (const bundle of roster.bundles) {
      assert.ok(
        fs.existsSync(path.join(__dirname, "..", "bundle", bundle)),
        `roster ${roster.id} names unknown bundle ${bundle}`,
      );
    }
  }
});

// ── Tie-break ───────────────────────────────────────────────────────────────

// A repo that is genuinely two things at once: a Next.js front end and an
// LLM product. The deterministic scorer puts them close; the decision layer
// arbitrates.
const AMBIGUOUS = {
  "package.json": JSON.stringify({
    dependencies: { next: "14", react: "18", langchain: "0.2" },
  }),
  "prompts/system.md": "",
  "evals/cases.json": "{}",
};

test("a near-tie consults the decision layer and honours its pick", async () => {
  const calls = [];
  const fakeJev = {
    choice: async (state, question, options) => {
      calls.push({ state, question, options });
      return {
        type: "choice",
        answer: "ai-product",
        confidence: 0.9,
        probabilities: { "ai-product": 0.9 },
        source: "jev",
      };
    },
  };
  const rec = await shape.recommend(fixture(AMBIGUOUS), { jev: fakeJev });
  assert.equal(calls.length, 1, "the decision layer should be consulted once");
  assert.equal(rec.roster.id, "ai-product");
  assert.equal(rec.source, "jev");
});

test("a low-confidence local answer does not override the scorer", async () => {
  const fakeJev = {
    choice: async () => ({
      type: "choice",
      answer: "ai-product",
      confidence: 0.2,
      probabilities: {},
      source: "local",
    }),
  };
  const rec = await shape.recommend(fixture(AMBIGUOUS), { jev: fakeJev });
  assert.equal(rec.source, "signals");
});

test("an answer outside the shortlist is ignored", async () => {
  const fakeJev = {
    choice: async () => ({
      type: "choice",
      answer: "legal-review",
      confidence: 0.99,
      probabilities: {},
      source: "jev",
    }),
  };
  const rec = await shape.recommend(fixture(AMBIGUOUS), { jev: fakeJev });
  assert.equal(rec.source, "signals");
  assert.ok(shape.ROSTERS.some((r) => r.id === rec.roster.id));
});

test("a decision layer that rejects does not break the recommendation", async () => {
  const fakeJev = {
    choice: async () => {
      throw new Error("provider exploded");
    },
  };
  const rec = await shape.recommend(fixture(AMBIGUOUS), { jev: fakeJev });
  assert.equal(rec.source, "signals");
  assert.ok(rec.roster.id);
});

test("a clear winner never reaches the decision layer", async () => {
  let called = false;
  const fakeJev = {
    choice: async () => {
      called = true;
      return { answer: null, confidence: 0, source: "local" };
    },
  };
  await shape.recommend(fixture(TERRAFORM_REPO), { jev: fakeJev });
  assert.equal(called, false, "a decided shape must cost zero decisions");
});

// ── Real decision layer, no credentials ─────────────────────────────────────

test("the real lib/jev path works offline with no key configured", async () => {
  const rec = await shape.recommend(fixture(AMBIGUOUS), {
    env: { TONONE_JEV_OFFLINE: "1" },
    timeoutMs: 1000,
  });
  assert.ok(rec.roster.id);
  assert.ok(["signals", "local", "jev", "fallback"].includes(rec.source));
});
