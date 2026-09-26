"use strict";

/**
 * Tests for the one-time star ask (hooks/tonone-star-ask.js).
 *
 *   node --test tests/test_star_ask.js
 *
 * Each end-to-end test points TONONE_CONFIG_DIR at a temporary directory, so
 * the suite never touches the developer's own ~/.config/tonone.
 */

const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

const HOOK = path.join(__dirname, "..", "hooks", "tonone-star-ask.js");
const { decide, ASK_AFTER } = require(HOOK);

const fresh = () => ({ asked: false, sessions: [] });
const start = (id) => ({ session_id: id, source: "startup" });

function run(dir, payload, env) {
  return spawnSync("node", [HOOK], {
    input: JSON.stringify(payload),
    env: { PATH: process.env.PATH, TONONE_CONFIG_DIR: dir, ...env },
    encoding: "utf8",
  });
}

test("asks exactly once, on the ASK_AFTER-th distinct session", () => {
  let state = fresh();
  const asks = [];
  for (let i = 1; i <= ASK_AFTER + 3; i++) {
    const r = decide(state, start("s" + i), {});
    state = r.state;
    asks.push(r.ask);
  }
  assert.strictEqual(asks.filter(Boolean).length, 1);
  assert.strictEqual(asks.indexOf(true), ASK_AFTER - 1);
});

test("repeated session_id does not advance the count", () => {
  let state = fresh();
  for (let i = 0; i < ASK_AFTER * 2; i++) {
    const r = decide(state, start("same"), {});
    assert.strictEqual(r.ask, false);
    state = r.state;
  }
  assert.deepStrictEqual(state.sessions, ["same"]);
});

test("resume, clear and compact sessions are not counted", () => {
  for (const source of ["resume", "clear", "compact"]) {
    const r = decide(fresh(), { session_id: "x", source }, {});
    assert.deepStrictEqual(r.state.sessions, []);
  }
});

test("opt-out and CI never ask", () => {
  const near = { asked: false, sessions: ["a", "b", "c", "d"] };
  assert.strictEqual(
    decide(near, start("e"), { TONONE_NO_STAR_ASK: "1" }).ask,
    false,
  );
  assert.strictEqual(decide(near, start("e"), { CI: "true" }).ask, false);
});

test("missing payload is ignored", () => {
  assert.strictEqual(decide(fresh(), null, {}).ask, false);
});

test("end to end: silent until threshold, then one systemMessage, then silent", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "tonone-star-"));
  for (let i = 1; i < ASK_AFTER; i++) {
    const r = run(dir, start("e" + i));
    assert.strictEqual(r.status, 0);
    assert.strictEqual(r.stdout, "");
  }
  const hit = run(dir, start("e" + ASK_AFTER));
  assert.strictEqual(hit.status, 0);
  const out = JSON.parse(hit.stdout);
  assert.match(out.systemMessage, /github\.com\/tonone-ai\/tonone/);
  assert.strictEqual(run(dir, start("later")).stdout, "");
});

test("end to end: unwritable state dir exits 0 silently", () => {
  const r = run("/dev/null/nope", start("z"));
  assert.strictEqual(r.status, 0);
  assert.strictEqual(r.stdout, "");
});
