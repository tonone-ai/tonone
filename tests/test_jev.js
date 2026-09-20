"use strict";

/**
 * Tests for the shared Jev decision layer (lib/jev/).
 *
 *   node --test tests/test_jev.js
 *
 * Node's built-in test runner, matching tests/hooks/*.js. No dependencies.
 *
 * The API paths are exercised against a throwaway HTTP server on localhost, so
 * nothing here ever reaches the real providers and the suite passes with no
 * credentials and no network.
 */

const { test } = require("node:test");
const assert = require("node:assert");
const http = require("http");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const ROOT = path.join(__dirname, "..");
const LIB = path.join(ROOT, "lib", "jev");
const CLI = path.join(LIB, "cli.js");

const client = require(path.join(LIB, "client.js"));
const local = require(path.join(LIB, "local.js"));
const cache = require(path.join(LIB, "cache.js"));

// ── Helpers ─────────────────────────────────────────────────────────────────

const JEV_ENV_KEYS = [
  "JEV_API_KEY",
  "TYPESAFE_API_KEY",
  "OPENROUTER_API_KEY",
  "TONONE_JEV_OFFLINE",
  "TONONE_JEV_ENDPOINT",
  "TONONE_JEV_MODEL",
  "TONONE_JEV_CACHE_DIR",
  "TONONE_JEV_TIMEOUT_MS",
];

function snapshotEnv() {
  const saved = {};
  for (const key of JEV_ENV_KEYS) saved[key] = process.env[key];
  return saved;
}

function restoreEnv(saved) {
  for (const key of JEV_ENV_KEYS) {
    if (saved[key] === undefined) delete process.env[key];
    else process.env[key] = saved[key];
  }
}

function tempCacheDir() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "jev-cache-"));
  process.env.TONONE_JEV_CACHE_DIR = dir;
  return dir;
}

function cleanup(dir) {
  try {
    fs.rmSync(dir, { recursive: true, force: true });
  } catch {}
}

/**
 * Start a throwaway decision endpoint. `handler(requestBody, res, state)` writes
 * the reply. Returns { url, state: { calls, bodies }, close() }.
 */
function startServer(handler) {
  const state = { calls: 0, bodies: [] };
  const server = http.createServer((req, res) => {
    let body = "";
    req.on("data", (chunk) => (body += chunk));
    req.on("end", () => {
      state.calls++;
      let parsed = null;
      try {
        parsed = JSON.parse(body);
      } catch {}
      state.bodies.push(parsed);
      handler(parsed, res, state);
    });
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const port = server.address().port;
      resolve({
        url: "http://127.0.0.1:" + port + "/v1/systemone",
        state: state,
        close: () =>
          new Promise((done) => {
            server.close(() => done());
          }),
      });
    });
  });
}

function sendJson(res, status, payload) {
  const body = typeof payload === "string" ? payload : JSON.stringify(payload);
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(body);
}

/** A well-formed reply for the single-question path (`single` names it "q"). */
function choiceReply(winner) {
  return {
    id: "gen-dec-test",
    model: "jev-1.13.0",
    answers: {
      q: {
        type: "choice",
        choice: winner,
        confidence: 0.91,
        probabilities: { billing: 0.91, orders: 0.09 },
      },
    },
    usage: { input_tokens: 120, output_tokens: 0 },
  };
}

// ── No credentials: the default path ────────────────────────────────────────

test("no credentials — choice answers locally and never touches the network", async () => {
  const saved = snapshotEnv();
  const dir = tempCacheDir();
  try {
    delete process.env.JEV_API_KEY;
    delete process.env.TYPESAFE_API_KEY;
    delete process.env.OPENROUTER_API_KEY;

    const result = await client.choice(
      "The customer was charged twice for one invoice and wants a refund.",
      "Which team owns this ticket?",
      {
        billing: "Charges, invoices, refunds, subscriptions",
        account: "Login, permissions, password and profile issues",
      },
    );
    assert.strictEqual(result.source, "local");
    assert.strictEqual(result.answer, "billing");
    assert.ok(
      result.confidence > 0,
      "expected non-zero confidence on a clear match",
    );
    assert.ok(result.probabilities.billing > result.probabilities.account);
  } finally {
    restoreEnv(saved);
    cleanup(dir);
  }
});

test("no credentials — noul and score also resolve locally", async () => {
  const saved = snapshotEnv();
  const dir = tempCacheDir();
  try {
    delete process.env.JEV_API_KEY;
    delete process.env.TYPESAFE_API_KEY;
    delete process.env.OPENROUTER_API_KEY;

    const gate = await client.noul(
      "The app crashes when I click save.",
      "Is this a defect?",
      {
        criteria: {
          true: "The customer describes a crash, an error or broken behaviour.",
          false:
            "The customer is asking a question or requesting a new feature.",
        },
      },
    );
    assert.strictEqual(gate.source, "local");
    assert.strictEqual(typeof gate.answer, "boolean");
    assert.ok(gate.probability >= 0 && gate.probability <= 1);
    assert.strictEqual(gate.answer, true);

    const graded = await client.score(
      "The checkout outage is blocking revenue for every customer right now.",
      "How urgent?",
      [
        "Can wait for the next release",
        "Should be fixed this week",
        "Blocking revenue right now",
      ],
    );
    assert.strictEqual(graded.source, "local");
    assert.ok(
      graded.answer > 1,
      "an outage should land in the top half of the rubric",
    );
    assert.strictEqual(Object.keys(graded.legend).length, 3);
  } finally {
    restoreEnv(saved);
    cleanup(dir);
  }
});

test("local scorer is deterministic and breaks ties toward the first option", async () => {
  const a = local.localChoice("nothing in common here", "pick", [
    "alpha",
    "beta",
    "gamma",
  ]);
  const b = local.localChoice("nothing in common here", "pick", [
    "alpha",
    "beta",
    "gamma",
  ]);
  assert.deepStrictEqual(a, b);
  assert.strictEqual(a.answer, "alpha");
  assert.strictEqual(
    a.confidence,
    0,
    "no lexical signal must report zero confidence",
  );
});

test("local scorer reports zero confidence when the wording does not overlap", async () => {
  // This is the documented accuracy ceiling, asserted so it cannot drift into a
  // confident-looking guess: no shared vocabulary means no signal, and the
  // scorer says so instead of inventing a winner. "nobody can pay" and
  // "blocking revenue" mean the same thing to a reader and nothing to TF-IDF.
  const graded = local.localScore(
    "Checkout is down, nobody can pay.",
    "How urgent?",
    [
      "Can wait for the next release",
      "Should be fixed this week",
      "Blocking revenue right now",
    ],
  );
  assert.strictEqual(graded.confidence, 0);
  assert.strictEqual(
    graded.answer,
    1,
    "a flat distribution grades to the middle level",
  );
});

test("local confidence is capped so a lexical guess cannot look authoritative", async () => {
  const result = local.localChoice(
    "refund refund refund invoice invoice billing",
    "which?",
    { billing: "refund invoice billing charges", account: "zzz qqq" },
  );
  assert.ok(
    result.confidence <= local.LOCAL_CONFIDENCE_CEILING,
    "confidence " + result.confidence + " exceeded the local ceiling",
  );
});

// ── Provider resolution ─────────────────────────────────────────────────────

test("provider resolution order — typesafe keys win, then openrouter, then local", () => {
  const saved = snapshotEnv();
  try {
    for (const key of JEV_ENV_KEYS) delete process.env[key];

    assert.strictEqual(
      client.resolveProvider({}),
      null,
      "no keys means the local scorer",
    );

    let p = client.resolveProvider({ JEV_API_KEY: "k" });
    assert.strictEqual(p.name, "typesafe");
    assert.strictEqual(p.endpoint, "https://api.typesafe.ai/v1/systemone");
    assert.strictEqual(p.model, "jev-latest");

    p = client.resolveProvider({ TYPESAFE_API_KEY: "k" });
    assert.strictEqual(p.name, "typesafe");

    p = client.resolveProvider({ OPENROUTER_API_KEY: "sk-or-v1-x" });
    assert.strictEqual(p.name, "openrouter");
    assert.strictEqual(p.endpoint, "https://openrouter.ai/api/alpha/decisions");
    assert.strictEqual(p.model, "typesafe/jev-1.13");

    p = client.resolveProvider({
      JEV_API_KEY: "k",
      OPENROUTER_API_KEY: "sk-or-v1-x",
    });
    assert.strictEqual(p.name, "typesafe", "typesafe key takes precedence");

    assert.strictEqual(
      client.resolveProvider({ JEV_API_KEY: "k", TONONE_JEV_OFFLINE: "1" }),
      null,
      "offline flag forces the local scorer",
    );
  } finally {
    restoreEnv(saved);
  }
});

// ── API path ────────────────────────────────────────────────────────────────

test("configured key — a well-formed reply is reported as source 'jev'", async () => {
  const saved = snapshotEnv();
  const dir = tempCacheDir();
  const server = await startServer((body, res) => {
    sendJson(res, 200, choiceReply("billing"));
  });
  try {
    process.env.JEV_API_KEY = "test-key";
    process.env.TONONE_JEV_ENDPOINT = server.url;

    const result = await client.choice("charged twice", "which team?", {
      billing: "refunds",
      orders: "delivery",
    });
    assert.strictEqual(result.source, "jev");
    assert.strictEqual(result.answer, "billing");
    assert.strictEqual(result.confidence, 0.91);
    assert.strictEqual(server.state.calls, 1);

    const sent = server.state.bodies[0];
    assert.strictEqual(sent.model, "jev-latest");
    assert.ok(sent.questions.q, "the question must be sent under its name");
    assert.strictEqual(sent.questions.q.type, "choice");
    assert.deepStrictEqual(Object.keys(sent.questions.q.criteria), [
      "billing",
      "orders",
    ]);
  } finally {
    await server.close();
    restoreEnv(saved);
    cleanup(dir);
  }
});

test("batch sends several named questions in exactly one request", async () => {
  const saved = snapshotEnv();
  const dir = tempCacheDir();
  const server = await startServer((body, res) => {
    sendJson(res, 200, {
      model: "jev-1.13.0",
      answers: {
        isBug: { type: "noul", noul: 0.96 },
        team: {
          type: "choice",
          choice: "payments",
          confidence: 0.75,
          probabilities: { payments: 0.84, frontend: 0.16 },
        },
        urgency: {
          type: "score",
          score: 1.99,
          confidence: 0.99,
          legend: { 0: "low", 1: "mid", 2: "high" },
          probabilities: { 0: 0, 1: 0.01, 2: 0.99 },
        },
      },
      usage: { input_tokens: 663, output_tokens: 0, cost: 0.0000279 },
    });
  });
  try {
    process.env.JEV_API_KEY = "test-key";
    process.env.TONONE_JEV_ENDPOINT = server.url;

    const result = await client.batch("checkout is down", {
      isBug: { type: "noul", question: "Is this a defect?" },
      team: {
        type: "choice",
        question: "Owner?",
        options: ["payments", "frontend"],
      },
      urgency: {
        type: "score",
        question: "How urgent?",
        levels: ["low", "mid", "high"],
      },
    });

    assert.strictEqual(
      server.state.calls,
      1,
      "a batch must be one request, not three",
    );
    assert.strictEqual(result.source, "jev");
    assert.strictEqual(result.provider, "typesafe");
    assert.strictEqual(result.answers.isBug.answer, true);
    assert.strictEqual(result.answers.isBug.probability, 0.96);
    assert.strictEqual(result.answers.team.answer, "payments");
    assert.strictEqual(result.answers.urgency.answer, 1.99);
    assert.strictEqual(result.usage.input_tokens, 663);
    assert.deepStrictEqual(
      Object.keys(server.state.bodies[0].questions).sort(),
      ["isBug", "team", "urgency"],
    );
  } finally {
    await server.close();
    restoreEnv(saved);
    cleanup(dir);
  }
});

// ── Cache ───────────────────────────────────────────────────────────────────

test("cache miss then hit — the second identical call does not reach the server", async () => {
  const saved = snapshotEnv();
  const dir = tempCacheDir();
  const server = await startServer((body, res) => {
    sendJson(res, 200, choiceReply("billing"));
  });
  try {
    process.env.JEV_API_KEY = "test-key";
    process.env.TONONE_JEV_ENDPOINT = server.url;

    const first = await client.choice("charged twice", "which team?", {
      billing: "refunds",
      orders: "delivery",
    });
    assert.strictEqual(first.source, "jev");
    assert.ok(!first.cached, "the first call is a miss");
    assert.strictEqual(server.state.calls, 1);

    const second = await client.choice("charged twice", "which team?", {
      billing: "refunds",
      orders: "delivery",
    });
    assert.strictEqual(second.source, "jev");
    assert.strictEqual(
      second.cached,
      true,
      "the second call must be served from cache",
    );
    assert.strictEqual(server.state.calls, 1, "no second request may be made");

    const uncached = await client.choice(
      "charged twice",
      "which team?",
      { billing: "refunds", orders: "delivery" },
      { cache: false },
    );
    assert.strictEqual(uncached.source, "jev");
    assert.strictEqual(
      server.state.calls,
      2,
      "cache: false must bypass the cache",
    );
  } finally {
    await server.close();
    restoreEnv(saved);
    cleanup(dir);
  }
});

test("cache — stable keys, expiry, and corrupt entries are treated as misses", () => {
  const saved = snapshotEnv();
  const dir = tempCacheDir();
  try {
    const a = cache.keyFor({ b: 1, a: [1, { z: 0, y: 1 }] });
    const b = cache.keyFor({ a: [1, { y: 1, z: 0 }], b: 1 });
    assert.strictEqual(a, b, "key order must not change the content address");
    assert.match(a, /^[0-9a-f]{64}$/);

    assert.strictEqual(cache.get(a), null, "cold cache is a miss");
    assert.strictEqual(cache.set(a, { hello: "world" }), true);
    assert.deepStrictEqual(cache.get(a), { hello: "world" });

    // Expiry: rewrite the entry with a creation time older than the TTL.
    const file = cache.entryPath(a);
    const entry = JSON.parse(fs.readFileSync(file, "utf8"));
    entry.createdAt = Date.now() - (cache.TTL_MS + 60000);
    fs.writeFileSync(file, JSON.stringify(entry));
    assert.strictEqual(
      cache.get(a),
      null,
      "an entry past the 7-day TTL is a miss",
    );
    assert.strictEqual(
      fs.existsSync(file),
      false,
      "an expired entry is removed",
    );

    // Corruption: a truncated or garbage file must not throw.
    assert.strictEqual(cache.set(a, { hello: "again" }), true);
    fs.writeFileSync(file, '{"v":1,"createdAt":');
    assert.strictEqual(cache.get(a), null, "a corrupt entry is a miss");
    assert.strictEqual(
      fs.existsSync(file),
      false,
      "a corrupt entry is removed",
    );

    // A key that is not a content address is rejected rather than written.
    assert.strictEqual(cache.set("../../escape", { x: 1 }), false);
    assert.strictEqual(cache.get("../../escape"), null);

    // Concurrent writers: last one wins, no partial reads, no throw.
    for (let i = 0; i < 25; i++) cache.set(a, { i: i });
    assert.strictEqual(cache.get(a).i, 24);
  } finally {
    restoreEnv(saved);
    cleanup(dir);
  }
});

test("cache — an unwritable cache directory degrades to no caching, not an error", async () => {
  const saved = snapshotEnv();
  const dir = tempCacheDir();
  const server = await startServer((body, res) => {
    sendJson(res, 200, choiceReply("billing"));
  });
  try {
    process.env.JEV_API_KEY = "test-key";
    process.env.TONONE_JEV_ENDPOINT = server.url;
    // A file where the cache root should be: every write fails.
    const blocked = path.join(dir, "blocked");
    fs.writeFileSync(blocked, "not a directory");
    process.env.TONONE_JEV_CACHE_DIR = blocked;

    const result = await client.choice("charged twice", "which team?", {
      billing: "refunds",
      orders: "delivery",
    });
    assert.strictEqual(result.source, "jev");
    assert.strictEqual(server.state.calls, 1);
  } finally {
    await server.close();
    restoreEnv(saved);
    cleanup(dir);
  }
});

// ── Failure modes ───────────────────────────────────────────────────────────

test("malformed API response — falls back locally and reports source 'fallback'", async () => {
  const saved = snapshotEnv();
  const dir = tempCacheDir();
  const server = await startServer((body, res) => {
    // Right status, wrong shape: the answer carries no `choice`.
    sendJson(res, 200, { answers: { q: { type: "choice", nonsense: true } } });
  });
  try {
    process.env.JEV_API_KEY = "test-key";
    process.env.TONONE_JEV_ENDPOINT = server.url;

    const result = await client.choice(
      "the customer wants a refund for a duplicate invoice",
      "which team?",
      {
        billing: "refunds invoices charges",
        orders: "delivery tracking returns",
      },
      { retries: 0 },
    );
    assert.strictEqual(result.source, "fallback");
    assert.strictEqual(
      result.answer,
      "billing",
      "the local scorer still answers",
    );
  } finally {
    await server.close();
    restoreEnv(saved);
    cleanup(dir);
  }
});

test("unparseable body and error statuses also fall back", async () => {
  const saved = snapshotEnv();
  const dir = tempCacheDir();
  let mode = "garbage";
  const server = await startServer((body, res) => {
    if (mode === "garbage") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end("<html>not json at all</html>");
    } else {
      sendJson(res, 401, {
        detail: { error_type: "authentication_error", message: "bad key" },
      });
    }
  });
  try {
    process.env.JEV_API_KEY = "test-key";
    process.env.TONONE_JEV_ENDPOINT = server.url;

    const garbage = await client.choice(
      "refund please",
      "which team?",
      ["billing", "orders"],
      {
        retries: 0,
      },
    );
    assert.strictEqual(garbage.source, "fallback");
    assert.ok(garbage.answer !== undefined);

    mode = "401";
    const unauthorized = await client.batch(
      "refund please",
      {
        q: {
          type: "choice",
          question: "which team?",
          options: ["billing", "orders"],
        },
      },
      { retries: 0, cache: false },
    );
    assert.strictEqual(unauthorized.source, "fallback");
    assert.strictEqual(unauthorized.error, "http 401");
    assert.strictEqual(unauthorized.answers.q.source, "fallback");
  } finally {
    await server.close();
    restoreEnv(saved);
    cleanup(dir);
  }
});

test("network failure — a dead endpoint never throws and never blocks", async () => {
  const saved = snapshotEnv();
  const dir = tempCacheDir();
  // Bind, capture the port, then close it: nothing is listening there.
  const server = await startServer((body, res) => sendJson(res, 200, {}));
  const deadUrl = server.url;
  await server.close();
  try {
    process.env.JEV_API_KEY = "test-key";
    process.env.TONONE_JEV_ENDPOINT = deadUrl;

    const started = Date.now();
    const result = await client.choice(
      "the customer wants a refund for a duplicate invoice",
      "which team?",
      {
        billing: "refunds invoices charges",
        orders: "delivery tracking returns",
      },
      { retries: 0, timeoutMs: 2000 },
    );
    assert.strictEqual(result.source, "fallback");
    assert.strictEqual(result.answer, "billing");
    assert.ok(Date.now() - started < 5000, "a dead endpoint must fail fast");
  } finally {
    restoreEnv(saved);
    cleanup(dir);
  }
});

test("timeout — a hanging endpoint falls back within the deadline", async () => {
  const saved = snapshotEnv();
  const dir = tempCacheDir();
  const sockets = [];
  const server = await startServer((body, res) => {
    sockets.push(res);
    // Never respond.
  });
  try {
    process.env.JEV_API_KEY = "test-key";
    process.env.TONONE_JEV_ENDPOINT = server.url;

    const result = await client.choice(
      "refund please",
      "which team?",
      ["billing", "orders"],
      {
        retries: 0,
        timeoutMs: 300,
      },
    );
    assert.strictEqual(result.source, "fallback");
  } finally {
    for (const res of sockets) {
      try {
        res.destroy();
      } catch {}
    }
    await server.close();
    restoreEnv(saved);
    cleanup(dir);
  }
});

test("invalid endpoint string falls back instead of throwing", async () => {
  const saved = snapshotEnv();
  const dir = tempCacheDir();
  try {
    process.env.JEV_API_KEY = "test-key";
    process.env.TONONE_JEV_ENDPOINT = "not a url";
    const result = await client.choice(
      "refund",
      "which?",
      ["billing", "orders"],
      {
        retries: 0,
      },
    );
    assert.strictEqual(result.source, "fallback");
  } finally {
    restoreEnv(saved);
    cleanup(dir);
  }
});

// ── Degenerate input ────────────────────────────────────────────────────────

test("empty options — answer null, confidence 0, and no request is made", async () => {
  const saved = snapshotEnv();
  const dir = tempCacheDir();
  const server = await startServer((body, res) =>
    sendJson(res, 200, choiceReply("billing")),
  );
  try {
    process.env.JEV_API_KEY = "test-key";
    process.env.TONONE_JEV_ENDPOINT = server.url;

    for (const empty of [[], {}, null, undefined, "not a list"]) {
      const result = await client.choice("some state", "which team?", empty);
      assert.strictEqual(result.answer, null, "empty options must answer null");
      assert.strictEqual(result.confidence, 0);
      assert.strictEqual(result.source, "local");
    }
    assert.strictEqual(
      server.state.calls,
      0,
      "a question with no options is never sent",
    );

    // One option is decided without a model too.
    const single = await client.choice("some state", "which?", ["only"]);
    assert.strictEqual(single.answer, "only");
    assert.strictEqual(server.state.calls, 0);

    // Empty levels behave the same way.
    const graded = await client.score("some state", "how urgent?", []);
    assert.strictEqual(graded.answer, null);
    assert.strictEqual(graded.source, "local");
    assert.strictEqual(server.state.calls, 0);
  } finally {
    await server.close();
    restoreEnv(saved);
    cleanup(dir);
  }
});

test("empty and malformed batches resolve rather than throw", async () => {
  const saved = snapshotEnv();
  const dir = tempCacheDir();
  try {
    delete process.env.JEV_API_KEY;
    delete process.env.TYPESAFE_API_KEY;
    delete process.env.OPENROUTER_API_KEY;

    const empty = await client.batch("state", {});
    assert.deepStrictEqual(empty.answers, {});
    assert.strictEqual(empty.error, "no valid questions");

    const junk = await client.batch("state", {
      a: { type: "unknown" },
      b: null,
      c: 7,
    });
    assert.deepStrictEqual(junk.answers, {});

    const mixed = await client.batch("refund please", {
      good: {
        type: "choice",
        question: "which?",
        options: ["billing", "orders"],
      },
      bad: { type: "nope" },
    });
    assert.ok(mixed.answers.good, "valid questions survive an invalid sibling");
    assert.strictEqual(mixed.answers.bad, undefined);
  } finally {
    restoreEnv(saved);
    cleanup(dir);
  }
});

test("empty and non-string state never throws", async () => {
  const saved = snapshotEnv();
  const dir = tempCacheDir();
  try {
    delete process.env.JEV_API_KEY;
    delete process.env.TYPESAFE_API_KEY;
    delete process.env.OPENROUTER_API_KEY;

    for (const state of [
      "",
      null,
      undefined,
      42,
      { a: { b: ["nested", "state"] } },
      ["x"],
    ]) {
      const result = await client.choice(state, "which?", [
        "billing",
        "orders",
      ]);
      assert.ok(result.answer === "billing" || result.answer === "orders");
      assert.strictEqual(result.source, "local");
    }
  } finally {
    restoreEnv(saved);
    cleanup(dir);
  }
});

// ── CLI ─────────────────────────────────────────────────────────────────────

function runCli(args, env) {
  return spawnSync("node", [CLI].concat(args), {
    encoding: "utf8",
    timeout: 20000,
    env: Object.assign({}, process.env, env || {}),
  });
}

test("cli — every command prints one JSON object and exits 0", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "jev-cli-"));
  const env = {
    TONONE_JEV_CACHE_DIR: dir,
    TONONE_JEV_OFFLINE: "1",
    JEV_API_KEY: "",
    TYPESAFE_API_KEY: "",
    OPENROUTER_API_KEY: "",
  };
  try {
    const provider = runCli(["provider"], env);
    assert.strictEqual(provider.status, 0, provider.stderr);
    assert.strictEqual(JSON.parse(provider.stdout).provider, "local");

    const choice = runCli(
      [
        "choice",
        "--state",
        "the customer wants a refund for a duplicate invoice",
        "--question",
        "which team?",
        "--options",
        "billing,orders,account",
      ],
      env,
    );
    assert.strictEqual(choice.status, 0, choice.stderr);
    const parsedChoice = JSON.parse(choice.stdout);
    assert.strictEqual(parsedChoice.ok, true);
    assert.strictEqual(parsedChoice.source, "local");
    assert.ok(
      ["billing", "orders", "account"].indexOf(parsedChoice.answer) !== -1,
    );

    const stateFile = path.join(dir, "state.txt");
    fs.writeFileSync(
      stateFile,
      "checkout is down and blocking revenue right now",
    );
    const score = runCli(
      [
        "score",
        "--state-file",
        stateFile,
        "--question",
        "how urgent?",
        "--levels",
        "can wait for the next release,should be fixed this week,blocking revenue right now",
      ],
      env,
    );
    assert.strictEqual(score.status, 0, score.stderr);
    assert.ok(JSON.parse(score.stdout).answer > 1);

    const questionsFile = path.join(dir, "q.json");
    fs.writeFileSync(
      questionsFile,
      JSON.stringify({
        team: {
          type: "choice",
          question: "owner?",
          options: ["billing", "frontend"],
        },
      }),
    );
    const batchRun = runCli(
      ["batch", "--state", "refund request", "--questions-file", questionsFile],
      env,
    );
    assert.strictEqual(batchRun.status, 0, batchRun.stderr);
    assert.ok(JSON.parse(batchRun.stdout).answers.team);

    const noul = runCli(
      [
        "noul",
        "--state",
        "the app crashes when I click save",
        "--question",
        "is this a defect?",
        "--criteria-true",
        "a crash, an error or broken behaviour",
        "--criteria-false",
        "a question or a feature request",
      ],
      env,
    );
    assert.strictEqual(noul.status, 0, noul.stderr);
    assert.strictEqual(JSON.parse(noul.stdout).answer, true);
  } finally {
    cleanup(dir);
  }
});

test("cli — bad input still exits 0 with a JSON error", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "jev-cli-"));
  const env = { TONONE_JEV_CACHE_DIR: dir, TONONE_JEV_OFFLINE: "1" };
  try {
    const cases = [
      [[], "no command"],
      [["bogus"], "unknown command"],
      [
        [
          "choice",
          "--state-file",
          path.join(dir, "missing.txt"),
          "--options",
          "a,b",
        ],
        "cannot read",
      ],
      [["batch", "--state", "x"], "requires --questions-file"],
    ];
    for (const [args, fragment] of cases) {
      const run = runCli(args, env);
      assert.strictEqual(
        run.status,
        0,
        "exit code must be 0 for: " + args.join(" "),
      );
      const parsed = JSON.parse(run.stdout);
      assert.strictEqual(parsed.ok, false);
      assert.ok(
        String(parsed.error).indexOf(fragment) !== -1,
        "expected '" + fragment + "' in: " + parsed.error,
      );
    }

    const badJson = path.join(dir, "bad.json");
    fs.writeFileSync(badJson, "{not json");
    const run = runCli(
      ["batch", "--state", "x", "--questions-file", badJson],
      env,
    );
    assert.strictEqual(run.status, 0);
    assert.strictEqual(JSON.parse(run.stdout).ok, false);
  } finally {
    cleanup(dir);
  }
});

test("cli — stdin state via --state-file -", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "jev-cli-"));
  try {
    const run = spawnSync(
      "node",
      [
        CLI,
        "choice",
        "--state-file",
        "-",
        "--question",
        "which?",
        "--options",
        "billing,orders",
      ],
      {
        input: "the customer wants a refund for a duplicate invoice",
        encoding: "utf8",
        timeout: 20000,
        env: Object.assign({}, process.env, {
          TONONE_JEV_CACHE_DIR: dir,
          TONONE_JEV_OFFLINE: "1",
        }),
      },
    );
    assert.strictEqual(run.status, 0, run.stderr);
    assert.strictEqual(JSON.parse(run.stdout).answer, "billing");
  } finally {
    cleanup(dir);
  }
});
