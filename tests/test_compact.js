"use strict";

/**
 * tests/test_compact.js — lib/compact/transcript-select.js
 *
 * Run: node --test tests/test_compact.js
 *
 * No credentials and no network. The Jev layer is exercised through an
 * injected fake decision layer, so the suite proves the veto semantics without
 * ever calling out. The one test that touches the real lib/jev runs it with
 * TONONE_JEV_OFFLINE=1 and asserts the module falls back to the heuristic.
 */

const test = require("node:test");
const assert = require("node:assert");

const sel = require("../lib/compact/transcript-select.js");

// ── Fixture helpers ─────────────────────────────────────────────────────────

let seq = 0;

function use(name, input, id) {
  return {
    type: "assistant",
    uuid: "u" + ++seq,
    message: {
      role: "assistant",
      content: [{ type: "tool_use", id: id, name: name, input: input }],
    },
  };
}

function result(id, content, isError) {
  const block = { type: "tool_result", tool_use_id: id, content: content };
  if (isError) block.is_error = true;
  return {
    type: "user",
    uuid: "r" + ++seq,
    message: { role: "user", content: [block] },
  };
}

function text(role, body) {
  return {
    type: role,
    uuid: "t" + ++seq,
    message: { role: role, content: [{ type: "text", text: body }] },
  };
}

function big(n, seed) {
  return (seed || "x")
    .repeat(Math.max(1, Math.ceil(n / (seed || "x").length)))
    .slice(0, n);
}

/** Build a transcript as JSONL text from record objects. */
function jsonl(records) {
  return records.map((r) => JSON.stringify(r)).join("\n") + "\n";
}

/** Pad a transcript with n throwaway recent exchanges so older ones age out. */
function padRecent(n) {
  const out = [];
  for (let i = 0; i < n; i++) {
    const id = "pad" + i;
    out.push(use("Bash", { command: "echo pad" + i }, id));
    out.push(result(id, "pad" + i));
  }
  return out;
}

// ── Parsing ─────────────────────────────────────────────────────────────────

test("parse tolerates blank lines, unparseable lines and non-message records", () => {
  const raw =
    JSON.stringify({ type: "system", subtype: "x" }) +
    "\n\n" +
    "{not json at all" +
    "\n" +
    JSON.stringify(text("user", "hello")) +
    "\n";
  const entries = sel.parse(raw);
  assert.equal(entries.length, 3);
  assert.equal(entries[1].json, null);
  assert.equal(entries[1].raw, "{not json at all");
  assert.equal(entries[2].role, "user");
});

test("parse accepts an array of already-parsed records", () => {
  const entries = sel.parse([text("user", "hi"), text("assistant", "there")]);
  assert.equal(entries.length, 2);
  assert.equal(entries[0].raw, null);
});

test("parse never throws on hostile input", () => {
  for (const input of [null, undefined, "", 0, {}, [null, 1, "x"], "\n\n\n"]) {
    assert.doesNotThrow(() => sel.parse(input));
  }
});

// ── Exchange building ───────────────────────────────────────────────────────

test("tool_use pairs with its tool_result by id, and byte size is measured", () => {
  const entries = sel.parse(
    jsonl([use("Read", { file_path: "/a.txt" }, "t1"), result("t1", "hello")]),
  );
  const ex = sel.buildExchanges(entries);
  assert.equal(ex.length, 1);
  assert.equal(ex[0].name, "Read");
  assert.equal(ex[0].target, "/a.txt");
  assert.equal(ex[0].bytes, 5);
  assert.equal(ex[0].isError, false);
});

test("an unpaired tool_use yields an exchange with no result and is always kept", () => {
  const records = padRecent(40).concat([
    use("Read", { file_path: "/a.txt" }, "orphan"),
  ]);
  const entries = sel.parse(jsonl(records));
  const p = sel.planSync(entries, {});
  const orphan = p.items.find((i) => i.id === "orphan");
  assert.equal(orphan.resultEntry, null);
  assert.equal(orphan.action, "keep");
  assert.equal(orphan.reason, "unpaired-tool-call");
});

test("tool_result content given as a block array is flattened to text", () => {
  const entries = sel.parse(
    jsonl([
      use("Bash", { command: "ls" }, "t1"),
      result("t1", [
        { type: "text", text: "one" },
        { type: "text", text: "two" },
      ]),
    ]),
  );
  const ex = sel.buildExchanges(entries);
  assert.equal(ex[0].bytes, "one\ntwo".length);
});

test("targetOf normalizes bash whitespace so a repeated command matches itself", () => {
  assert.equal(
    sel.targetOf("Bash", { command: "git   status\n  --short" }),
    sel.targetOf("Bash", { command: "git status --short" }),
  );
});

// ── The heuristic: what it refuses to touch ─────────────────────────────────

test("user and assistant prose is never a candidate", () => {
  const records = [
    text("user", big(50000)),
    text("assistant", big(50000)),
  ].concat(padRecent(40));
  const p = sel.planSync(sel.parse(jsonl(records)), {});
  assert.equal(p.totals.exchanges, 40);
  assert.equal(p.totals.dropped, 0);
  assert.equal(p.totals.truncated, 0);
});

test("recent exchanges are kept however large and however redundant", () => {
  const records = [
    use("Read", { file_path: "/a.txt" }, "r1"),
    result("r1", big(100000)),
    use("Read", { file_path: "/a.txt" }, "r2"),
    result("r2", big(100000)),
  ];
  const p = sel.planSync(sel.parse(jsonl(records)), {});
  assert.deepEqual(
    p.items.map((i) => i.action),
    ["keep", "keep"],
  );
  assert.equal(p.items[0].reason, "recent");
});

test("an error result is kept even when old, huge and superseded", () => {
  const records = [
    use("Bash", { command: "npm test" }, "e1"),
    result("e1", big(60000, "ERR: missing config at /etc/app.toml\n"), true),
    use("Bash", { command: "npm test" }, "e2"),
    result("e2", "ok"),
  ].concat(padRecent(40));
  const p = sel.planSync(sel.parse(jsonl(records)), {});
  const it = p.items.find((i) => i.id === "e1");
  assert.equal(it.action, "keep");
  assert.equal(it.reason, "error-result");
});

test("a mutating tool's result is kept even when old, huge and repeated", () => {
  const records = [
    use("Write", { file_path: "/a.txt" }, "w1"),
    result("w1", big(60000)),
    use("Write", { file_path: "/a.txt" }, "w2"),
    result("w2", big(60000)),
  ].concat(padRecent(40));
  const p = sel.planSync(sel.parse(jsonl(records)), {});
  const it = p.items.find((i) => i.id === "w1");
  assert.equal(it.action, "keep");
  assert.equal(it.reason, "mutating-tool");
});

test("a small result is kept even when old and superseded — exact strings live there", () => {
  const records = [
    use("Bash", { command: "cat .env.example" }, "s1"),
    result("s1", "DATABASE_URL=postgres://localhost:5432/app"),
    use("Bash", { command: "cat .env.example" }, "s2"),
    result("s2", "DATABASE_URL=postgres://localhost:5432/app"),
  ].concat(padRecent(40));
  const p = sel.planSync(sel.parse(jsonl(records)), {});
  const it = p.items.find((i) => i.id === "s1");
  assert.equal(it.action, "keep");
  assert.equal(it.reason, "small");
});

test("a large old read is kept when nothing later looked at the same thing", () => {
  const records = [
    use("Read", { file_path: "/only-once.txt" }, "k1"),
    result("k1", big(5000)),
  ].concat(padRecent(40));
  const p = sel.planSync(sel.parse(jsonl(records)), {});
  const it = p.items.find((i) => i.id === "k1");
  assert.equal(it.action, "keep");
  assert.equal(it.reason, "no-rule-fires");
});

// ── The heuristic: what it does touch ───────────────────────────────────────

test("a large old read superseded by a later read of the same file is dropped", () => {
  const records = [
    use("Read", { file_path: "/a.txt" }, "d1"),
    result("d1", big(9000)),
    use("Read", { file_path: "/a.txt" }, "d2"),
    result("d2", big(9000)),
  ].concat(padRecent(40));
  const p = sel.planSync(sel.parse(jsonl(records)), {});
  const first = p.items.find((i) => i.id === "d1");
  const second = p.items.find((i) => i.id === "d2");
  assert.equal(first.action, "drop");
  assert.match(first.reason, /^superseded-by-#\d+$/);
  assert.equal(second.action, "keep", "the surviving later read must be kept");
});

test("supersession does not cross tools or targets", () => {
  const records = [
    use("Read", { file_path: "/a.txt" }, "x1"),
    result("x1", big(9000)),
    use("Read", { file_path: "/b.txt" }, "x2"),
    result("x2", big(9000)),
    use("Grep", { pattern: "foo", path: "/a.txt" }, "x3"),
    result("x3", big(9000)),
  ].concat(padRecent(40));
  const p = sel.planSync(sel.parse(jsonl(records)), {});
  for (const id of ["x1", "x2", "x3"]) {
    assert.equal(p.items.find((i) => i.id === id).action, "keep");
  }
});

test("a later failed read does not supersede an earlier successful one", () => {
  const records = [
    use("Read", { file_path: "/a.txt" }, "g1"),
    result("g1", big(9000)),
    use("Read", { file_path: "/a.txt" }, "g2"),
    result("g2", "ENOENT", true),
  ].concat(padRecent(40));
  const p = sel.planSync(sel.parse(jsonl(records)), {});
  assert.equal(p.items.find((i) => i.id === "g1").action, "keep");
});

test("a very large old unsuperseded result is truncated, not dropped", () => {
  const records = [
    use("WebFetch", { url: "https://example.com/big" }, "h1"),
    result("h1", big(50000)),
  ].concat(padRecent(40));
  const p = sel.planSync(sel.parse(jsonl(records)), {});
  const it = p.items.find((i) => i.id === "h1");
  assert.equal(it.action, "truncate");
  assert.equal(it.reason, "large-and-old");
});

test("an unknown tool is never dropped, only ever truncated", () => {
  const records = [
    use("mcp__somewhere__fetch_everything", { q: "x" }, "m1"),
    result("m1", big(50000)),
    use("mcp__somewhere__fetch_everything", { q: "x" }, "m2"),
    result("m2", big(50000)),
  ].concat(padRecent(40));
  const p = sel.planSync(sel.parse(jsonl(records)), {});
  assert.equal(p.items.find((i) => i.id === "m1").action, "truncate");
  assert.equal(p.items.find((i) => i.id === "m2").action, "truncate");
});

test("totals add up and freed bytes never exceed the total", () => {
  const records = [
    use("Read", { file_path: "/a.txt" }, "a1"),
    result("a1", big(40000)),
    use("Read", { file_path: "/a.txt" }, "a2"),
    result("a2", big(40000)),
    use("WebFetch", { url: "u" }, "a3"),
    result("a3", big(40000)),
  ].concat(padRecent(40));
  const p = sel.planSync(sel.parse(jsonl(records)), {});
  const t = p.totals;
  assert.equal(t.kept + t.truncated + t.dropped, t.exchanges);
  assert.ok(t.bytesFreed <= t.bytesTotal);
  assert.ok(t.bytesKept <= t.bytesTotal);
});

// ── Emission is verbatim ────────────────────────────────────────────────────

test("emit copies every untouched line byte-for-byte, including unparseable ones", () => {
  const records = [
    text("user", "keep me exactly"),
    use("Bash", { command: "ls" }, "b1"),
    result("b1", "a\nb"),
  ];
  const raw = jsonl(records).trimEnd() + "\n{ broken line \n";
  const entries = sel.parse(raw);
  const p = sel.planSync(entries, {});
  const out = sel.emit(entries, p);
  const inLines = raw.split("\n").filter((l) => l.trim() !== "");
  const outLines = out.split("\n").filter((l) => l.trim() !== "");
  assert.deepEqual(outLines, inLines);
});

test("emit replaces a dropped result wholesale and leaves its tool_use intact", () => {
  const records = [
    use("Read", { file_path: "/a.txt" }, "d1"),
    result("d1", big(9000, "SECRET-CONTENT-")),
    use("Read", { file_path: "/a.txt" }, "d2"),
    result("d2", big(9000, "SECRET-CONTENT-")),
  ].concat(padRecent(40));
  const entries = sel.parse(jsonl(records));
  const p = sel.planSync(entries, {});
  const out = sel.emit(entries, p);
  const lines = out.split("\n").filter(Boolean).map(JSON.parse);
  const dropped = lines.find(
    (l) =>
      l.message &&
      l.message.content[0] &&
      l.message.content[0].tool_use_id === "d1",
  );
  assert.match(
    dropped.message.content[0].content,
    /^\[tonone-compact\] dropped 9000 bytes/,
  );
  const useLine = lines.find(
    (l) =>
      l.message && l.message.content[0] && l.message.content[0].id === "d1",
  );
  assert.deepEqual(useLine.message.content[0].input, { file_path: "/a.txt" });
});

test("a truncated result keeps an exact prefix and an exact suffix of the original", () => {
  const body = big(50000, "abcdefghij");
  const records = [
    use("WebFetch", { url: "u" }, "h1"),
    result("h1", body),
  ].concat(padRecent(40));
  const entries = sel.parse(jsonl(records));
  const p = sel.planSync(entries, {});
  const out = sel.emit(entries, p);
  const line = out
    .split("\n")
    .filter(Boolean)
    .map(JSON.parse)
    .find(
      (l) =>
        l.message &&
        l.message.content[0] &&
        l.message.content[0].tool_use_id === "h1",
    );
  const kept = line.message.content[0].content;
  const opts = p.options;
  assert.ok(
    kept.startsWith(body.slice(0, opts.keepHeadBytes)),
    "head must be verbatim",
  );
  assert.ok(
    kept.endsWith(body.slice(body.length - opts.keepTailBytes)),
    "tail must be verbatim",
  );
  assert.match(
    kept,
    /\[tonone-compact\] elided \d+ characters verbatim from the middle/,
  );
  assert.ok(kept.length < body.length);
});

test("emit on an all-keep plan reproduces the input exactly", () => {
  const raw = jsonl([
    text("user", "hello"),
    use("Read", { file_path: "/a.txt" }, "t1"),
    result("t1", "small"),
  ]);
  const entries = sel.parse(raw);
  const p = sel.planSync(entries, {});
  assert.equal(p.totals.dropped, 0);
  assert.equal(p.totals.truncated, 0);
  assert.equal(sel.emit(entries, p), raw);
});

// ── The Jev veto ────────────────────────────────────────────────────────────

function fakeJev(answerFor, source) {
  return {
    resolveProvider: () => ({
      name: "typesafe",
      endpoint: "https://x",
      model: "m",
      key: "k",
    }),
    batch: async (state, questions) => {
      const answers = {};
      for (const name of Object.keys(questions)) {
        answers[name] = {
          type: "noul",
          answer: answerFor(name, state),
          probability: 0.9,
          confidence: 0.9,
          source: source || "jev",
        };
      }
      return {
        answers: answers,
        source: source || "jev",
        provider: "typesafe",
        cached: false,
      };
    },
  };
}

const supersededFixture = () =>
  [
    use("Read", { file_path: "/a.txt" }, "d1"),
    result("d1", big(9000)),
    use("Read", { file_path: "/a.txt" }, "d2"),
    result("d2", big(9000)),
    use("WebFetch", { url: "u" }, "h1"),
    result("h1", big(50000)),
    use("Read", { file_path: "/solo.txt" }, "k1"),
    result("k1", big(5000)),
  ].concat(padRecent(40));

test("jev saying 'still needed' can only move entries toward keeping", async () => {
  const entries = sel.parse(jsonl(supersededFixture()));
  const before = sel.planSync(entries, {});
  const after = await sel.plan(entries, { jev: fakeJev(() => true) });
  assert.equal(after.source, "jev");
  assert.equal(after.items.find((i) => i.id === "d1").action, "truncate"); // was drop
  assert.equal(after.items.find((i) => i.id === "h1").action, "keep"); // was truncate
  assert.ok(after.totals.dropped <= before.totals.dropped);
  assert.ok(after.totals.bytesKept >= before.totals.bytesKept);
});

test("jev saying 'not needed' can demote a keep only as far as truncate", async () => {
  const entries = sel.parse(jsonl(supersededFixture()));
  const before = sel.planSync(entries, {});
  const after = await sel.plan(entries, { jev: fakeJev(() => false) });
  assert.equal(after.items.find((i) => i.id === "k1").action, "truncate");
  assert.equal(after.items.find((i) => i.id === "k1").reason, "jev-not-needed");
  assert.equal(
    after.totals.dropped,
    before.totals.dropped,
    "jev must never add a drop the heuristic did not propose",
  );
});

test("jev never touches recent, error, mutating or small entries", async () => {
  const records = [
    use("Bash", { command: "npm test" }, "e1"),
    result("e1", big(60000, "ERR "), true),
    use("Write", { file_path: "/a.txt" }, "w1"),
    result("w1", big(60000)),
    use("Bash", { command: "cat .env" }, "s1"),
    result("s1", "KEY=abc"),
  ].concat(padRecent(40));
  const entries = sel.parse(jsonl(records));
  const after = await sel.plan(entries, { jev: fakeJev(() => false) });
  for (const id of ["e1", "w1", "s1"]) {
    assert.equal(
      after.items.find((i) => i.id === id).action,
      "keep",
      id + " must stay kept",
    );
  }
  for (const it of after.items.filter(
    (i) => i.fromEnd < after.options.keepRecent,
  )) {
    assert.equal(it.action, "keep");
  }
});

test("a non-hosted jev answer is ignored entirely", async () => {
  const entries = sel.parse(jsonl(supersededFixture()));
  const before = sel.planSync(entries, {});
  const after = await sel.plan(entries, { jev: fakeJev(() => false, "local") });
  assert.equal(after.source, "heuristic");
  assert.match(after.jevError, /not trusted/);
  assert.deepEqual(
    after.items.map((i) => i.action),
    before.items.map((i) => i.action),
  );
});

test("no provider configured means no network call and the heuristic plan", async () => {
  let called = false;
  const noProvider = {
    resolveProvider: () => null,
    batch: async () => {
      called = true;
      return null;
    },
  };
  const entries = sel.parse(jsonl(supersededFixture()));
  const after = await sel.plan(entries, { jev: noProvider });
  assert.equal(called, false);
  assert.equal(after.source, "heuristic");
  assert.equal(after.jevError, "no Jev provider configured");
});

test("a jev layer that throws or returns garbage still yields the heuristic plan", async () => {
  const entries = sel.parse(jsonl(supersededFixture()));
  const base = sel.planSync(entries, {});
  const layers = [
    {
      resolveProvider: () => ({ name: "x" }),
      batch: async () => {
        throw new Error("boom");
      },
    },
    { resolveProvider: () => ({ name: "x" }), batch: async () => null },
    {
      resolveProvider: () => ({ name: "x" }),
      batch: async () => ({ answers: null, source: "jev" }),
    },
    {
      resolveProvider: () => {
        throw new Error("nope");
      },
      batch: async () => null,
    },
  ];
  for (const jev of layers) {
    const after = await sel.plan(entries, { jev: jev });
    assert.equal(after.source, "heuristic");
    assert.deepEqual(
      after.items.map((i) => i.action),
      base.items.map((i) => i.action),
    );
  }
});

test("the real lib/jev path works offline with no key configured", async () => {
  const entries = sel.parse(jsonl(supersededFixture()));
  const after = await sel.plan(entries, { env: { TONONE_JEV_OFFLINE: "1" } });
  assert.equal(after.source, "heuristic");
  assert.equal(after.jevError, "no Jev provider configured");
});

test("useJev:false skips the decision layer entirely", async () => {
  const entries = sel.parse(jsonl(supersededFixture()));
  let called = false;
  const after = await sel.plan(entries, {
    useJev: false,
    jev: {
      resolveProvider: () => {
        called = true;
        return null;
      },
      batch: async () => null,
    },
  });
  assert.equal(called, false);
  assert.equal(after.source, "heuristic");
});

// ── Rendering and degenerate input ──────────────────────────────────────────

test("render produces text for an empty transcript without throwing", () => {
  const p = sel.planSync(sel.parse(""), {});
  assert.equal(p.totals.exchanges, 0);
  const out = sel.render(p);
  assert.match(out, /exchanges=0/);
  assert.ok(
    out.split("\n").length <= 40,
    "render must fit the 40-line CLI budget",
  );
});

test("render of a large plan stays within the 40-line budget", () => {
  const records = [];
  for (let i = 0; i < 300; i++) {
    records.push(use("Read", { file_path: "/same.txt" }, "b" + i));
    records.push(result("b" + i, big(9000)));
  }
  const p = sel.planSync(sel.parse(jsonl(records.concat(padRecent(40)))), {});
  assert.ok(p.totals.dropped > 100);
  assert.ok(sel.render(p).split("\n").length <= 40);
});

test("planSync and emit never throw on degenerate transcripts", () => {
  const nasty = [
    "",
    "\n",
    "null\n",
    JSON.stringify({
      type: "assistant",
      message: { role: "assistant", content: "a string" },
    }),
    JSON.stringify({
      type: "user",
      message: { role: "user", content: [null, 3, { type: "tool_result" }] },
    }),
    JSON.stringify({
      message: { content: [{ type: "tool_use", id: 7, name: null }] },
    }),
  ];
  for (const raw of nasty) {
    const entries = sel.parse(raw);
    let p;
    assert.doesNotThrow(() => {
      p = sel.planSync(entries, {});
    }, raw);
    assert.doesNotThrow(() => sel.emit(entries, p), raw);
  }
});

test("options are clamped to sane numbers and bad ones are ignored", () => {
  const entries = sel.parse(jsonl(supersededFixture()));
  const p = sel.planSync(entries, {
    keepRecent: "lots",
    smallBytes: -5,
    hugeBytes: null,
  });
  assert.equal(p.options.keepRecent, sel.DEFAULTS.keepRecent);
  assert.equal(p.options.smallBytes, sel.DEFAULTS.smallBytes);
  assert.equal(p.options.hugeBytes, sel.DEFAULTS.hugeBytes);
});

// ── Regressions: target identity ────────────────────────────────────────────

test("two partial reads of one file with different ranges are not the same target", () => {
  assert.notEqual(
    sel.targetOf("Read", { file_path: "/x/app.py", offset: 1, limit: 100 }),
    sel.targetOf("Read", { file_path: "/x/app.py", offset: 900, limit: 100 }),
  );
  assert.equal(
    sel.targetOf("Read", { file_path: "/x/app.py", offset: 1, limit: 100 }),
    sel.targetOf("Read", { limit: 100, file_path: "/x/app.py", offset: 1 }),
  );
});

test("a later disjoint partial read never drops an earlier one", () => {
  const marker = "CRITICAL_SECRET_CONSTRAINT_ALPHA";
  const records = [
    use("Read", { file_path: "/x/app.py", offset: 1, limit: 100 }, "p1"),
    result("p1", big(5000) + marker),
    use("Read", { file_path: "/x/app.py", offset: 900, limit: 100 }, "p2"),
    result("p2", big(5000, "zzzz")),
  ].concat(padRecent(40));
  const entries = sel.parse(jsonl(records));
  const p = sel.planSync(entries, {});
  assert.equal(p.items.find((i) => i.id === "p1").action, "keep");
  assert.ok(
    sel.emit(entries, p).includes(marker),
    "the earlier region must survive",
  );
});

test("Grep output modes and WebFetch prompts are distinct targets", () => {
  assert.notEqual(
    sel.targetOf("Grep", {
      pattern: "foo",
      path: "/a",
      output_mode: "content",
    }),
    sel.targetOf("Grep", {
      pattern: "foo",
      path: "/a",
      output_mode: "files_with_matches",
    }),
  );
  assert.notEqual(
    sel.targetOf("WebFetch", {
      url: "https://e.com",
      prompt: "list the endpoints",
    }),
    sel.targetOf("WebFetch", {
      url: "https://e.com",
      prompt: "list the auth scopes",
    }),
  );
});

test("a repeated identical call is still one target, and description is cosmetic", () => {
  assert.equal(
    sel.targetOf("Read", { file_path: "/a.txt" }),
    sel.targetOf("Read", { file_path: "/a.txt" }),
  );
  assert.equal(
    sel.targetOf("Bash", { command: "ls", description: "List files" }),
    sel.targetOf("Bash", { command: "ls", description: "Show the directory" }),
  );
});

test("two long distinct inputs that share a prefix do not collide", () => {
  const a = { q: "p".repeat(900) + "AAA" };
  const b = { q: "p".repeat(900) + "BBB" };
  assert.notEqual(sel.targetOf("mcp__x__y", a), sel.targetOf("mcp__x__y", b));
});

// ── Regressions: the toolUseResult sidecar ──────────────────────────────────

/** A tool result in the shape Claude Code actually writes: payload twice. */
function resultWithSidecar(id, content, sidecar) {
  const rec = result(id, content);
  rec.toolUseResult = sidecar;
  return rec;
}

test("a dropped payload does not survive in the top-level toolUseResult", () => {
  const marker = "SECRET_PAYLOAD_OMEGA";
  const body = big(9000, "pad-") + marker;
  const records = [
    use("Read", { file_path: "/a.txt" }, "r1"),
    resultWithSidecar("r1", body, { type: "text", file: { content: body } }),
    use("Read", { file_path: "/a.txt" }, "r2"),
    resultWithSidecar("r2", body, { type: "text", file: { content: body } }),
  ].concat(padRecent(40));
  const entries = sel.parse(jsonl(records));
  const p = sel.planSync(entries, {});
  const it = p.items.find((i) => i.id === "r1");
  assert.equal(it.action, "drop");
  assert.ok(it.sidecarBytes > 9000, "the sidecar must be measured");
  assert.equal(it.bytes, it.inlineBytes + it.sidecarBytes);
  const out = sel.emit(entries, p);
  const line = out
    .split("\n")
    .filter(Boolean)
    .map(JSON.parse)
    .find(
      (l) =>
        l.message &&
        l.message.content[0] &&
        l.message.content[0].tool_use_id === "r1",
    );
  assert.equal(line.toolUseResult.tonone_compact, "dropped");
  assert.ok(
    !JSON.stringify(line).includes(marker),
    "no part of the dropped record may still carry the payload",
  );
});

test("a truncated record's sidecar is replaced, and the inline head and tail stay verbatim", () => {
  const body = big(50000, "abcdefghij");
  const records = [
    use("WebFetch", { url: "u" }, "h1"),
    resultWithSidecar("h1", body, { bytes: body.length, result: body }),
  ].concat(padRecent(40));
  const entries = sel.parse(jsonl(records));
  const p = sel.planSync(entries, {});
  const it = p.items.find((i) => i.id === "h1");
  assert.equal(it.action, "truncate");
  const line = sel
    .emit(entries, p)
    .split("\n")
    .filter(Boolean)
    .map(JSON.parse)
    .find(
      (l) =>
        l.message &&
        l.message.content[0] &&
        l.message.content[0].tool_use_id === "h1",
    );
  assert.equal(line.toolUseResult.tonone_compact, "elided");
  const kept = line.message.content[0].content;
  assert.ok(kept.startsWith(body.slice(0, p.options.keepHeadBytes)));
  assert.ok(kept.endsWith(body.slice(body.length - p.options.keepTailBytes)));
});

test("emit shrinks the file by at least the bytes the plan claims to free", () => {
  const body = big(9000, "pad-");
  const records = [
    use("Read", { file_path: "/a.txt" }, "r1"),
    resultWithSidecar("r1", body, { type: "text", file: { content: body } }),
    use("Read", { file_path: "/a.txt" }, "r2"),
    resultWithSidecar("r2", body, { type: "text", file: { content: body } }),
  ].concat(padRecent(40));
  const raw = jsonl(records);
  const entries = sel.parse(raw);
  const p = sel.planSync(entries, {});
  const shrank =
    Buffer.byteLength(raw) - Buffer.byteLength(sel.emit(entries, p));
  assert.ok(
    shrank >= p.totals.bytesFreed * 0.9,
    "claimed " + p.totals.bytesFreed + " freed, file shrank " + shrank,
  );
  assert.ok(p.totals.bytesTranscript >= p.totals.bytesTotal);
});

test("a record with two tool_result blocks leaves its ambiguous sidecar alone", () => {
  const body = big(9000, "pad-");
  const pair = {
    type: "user",
    uuid: "rr",
    message: {
      role: "user",
      content: [
        { type: "tool_result", tool_use_id: "m1", content: body },
        { type: "tool_result", tool_use_id: "m2", content: body },
      ],
    },
    toolUseResult: { content: body },
  };
  const records = [
    use("Read", { file_path: "/a.txt" }, "m1"),
    use("Read", { file_path: "/b.txt" }, "m2"),
    pair,
    use("Read", { file_path: "/a.txt" }, "m3"),
    result("m3", body),
  ].concat(padRecent(40));
  const entries = sel.parse(jsonl(records));
  const p = sel.planSync(entries, {});
  const it = p.items.find((i) => i.id === "m1");
  assert.equal(it.sidecarBytes, 0, "an unattributable sidecar is not measured");
  assert.doesNotThrow(() => sel.emit(entries, p));
});

test("a transcript with no sidecars is accounted exactly as before", () => {
  const records = [
    use("Read", { file_path: "/a.txt" }, "n1"),
    result("n1", big(9000)),
  ].concat(padRecent(40));
  const p = sel.planSync(sel.parse(jsonl(records)), {});
  assert.equal(p.totals.bytesSidecar, 0);
  assert.equal(p.totals.bytesInline, p.totals.bytesTotal);
});
