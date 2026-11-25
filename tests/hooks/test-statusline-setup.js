const { test } = require("node:test");
const assert = require("node:assert");
const { spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const HOOK = path.join(__dirname, "../../hooks/tonone-statusline-setup.js");

function setup(settings) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "sl-"));
  const claude = path.join(root, "claude");
  const cfg = path.join(root, "cfg");
  fs.mkdirSync(claude, { recursive: true });
  if (settings !== undefined)
    fs.writeFileSync(path.join(claude, "settings.json"), settings);
  return { root, claude, cfg };
}

function run(s, args = [], env = {}) {
  return spawnSync("node", [HOOK, ...args], {
    encoding: "utf8",
    timeout: 5000,
    env: {
      ...process.env,
      CI: "",
      CLAUDE_CONFIG_DIR: s.claude,
      TONONE_CONFIG_DIR: s.cfg,
      ...env,
    },
  });
}

const settings = (s) =>
  fs.readFileSync(path.join(s.claude, "settings.json"), "utf8");
const state = (s) => {
  try {
    return fs.readFileSync(path.join(s.cfg, "statusline"), "utf8").trim();
  } catch {
    return "";
  }
};
const cleanup = (s) => fs.rmSync(s.root, { recursive: true, force: true });

test("first session: tells the user once and changes nothing", () => {
  const s = setup("{}");
  try {
    const out = JSON.parse(run(s).stdout);
    assert.deepStrictEqual(Object.keys(out), ["systemMessage"]);
    assert.match(out.systemMessage, /! node .*--yes/);
    assert.match(out.systemMessage, /! node .*--never/);
    assert.doesNotMatch(out.systemMessage, /AskUserQuestion|do not mention/i);
    assert.strictEqual(settings(s), "{}");
    assert.strictEqual(state(s), "asked");
    assert.strictEqual(run(s).stdout, "", "must not ask twice");
  } finally {
    cleanup(s);
  }
});

test("--yes installs, remembers, and keeps other settings", () => {
  const s = setup('{"x":1}');
  try {
    run(s, ["--yes"]);
    const parsed = JSON.parse(settings(s));
    assert.strictEqual(parsed.x, 1);
    assert.match(parsed.statusLine.command, /tonone-statusline\.js/);
    assert.strictEqual(state(s), "on");
  } finally {
    cleanup(s);
  }
});

test("--never: no install, no more asks", () => {
  const s = setup("{}");
  try {
    run(s, ["--never"]);
    assert.strictEqual(state(s), "never");
    assert.strictEqual(run(s).stdout, "");
    assert.strictEqual(settings(s), "{}");
  } finally {
    cleanup(s);
  }
});

test("existing statusLine: never asked, never replaced", () => {
  const original = '{"statusLine":{"type":"command","command":"echo mine"}}';
  const s = setup(original);
  try {
    assert.strictEqual(run(s).stdout, "");
    assert.strictEqual(state(s), "never");
    run(s, ["--yes"]);
    assert.strictEqual(settings(s), original);
  } finally {
    cleanup(s);
  }
});

test("unreadable settings: never touched, never asked", () => {
  const s = setup("{bad");
  try {
    assert.strictEqual(run(s).stdout, "");
    run(s, ["--yes"]);
    assert.strictEqual(settings(s), "{bad");
  } finally {
    cleanup(s);
  }
});

test("missing settings file is created on --yes", () => {
  const s = setup(undefined);
  try {
    run(s, ["--yes"]);
    assert.match(settings(s), /tonone-statusline\.js/);
  } finally {
    cleanup(s);
  }
});

test("TONONE_STATUSLINE=1 installs without asking; =0 and CI stay silent", () => {
  const a = setup("{}");
  const b = setup("{}");
  const c = setup("{}");
  try {
    assert.strictEqual(run(a, [], { TONONE_STATUSLINE: "1" }).stdout, "");
    assert.match(settings(a), /tonone-statusline\.js/);
    assert.strictEqual(run(b, [], { TONONE_STATUSLINE: "0" }).stdout, "");
    assert.strictEqual(settings(b), "{}");
    assert.strictEqual(run(c, [], { CI: "1" }).stdout, "");
    assert.strictEqual(state(c), "");
  } finally {
    [a, b, c].forEach(cleanup);
  }
});
