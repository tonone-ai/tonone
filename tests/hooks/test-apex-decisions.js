const { test } = require("node:test");
const assert = require("node:assert");
const { spawnSync } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const HOOK = path.join(__dirname, "../../team/apex/hooks/apex-decisions.js");

function mk() {
  return fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), "apex-dec-")));
}
function env(dir, extra) {
  return {
    ...process.env,
    TONONE_DECISIONS: "",
    CLAUDE_PROJECT_DIR: dir,
    ...extra,
  };
}
function cli(dir, args, extra) {
  return spawnSync("node", [HOOK, ...args], {
    encoding: "utf8",
    timeout: 5000,
    cwd: dir,
    env: env(dir, extra),
  });
}
function hook(dir, input, extra) {
  return spawnSync("node", [HOOK], {
    input: typeof input === "string" ? input : JSON.stringify(input),
    encoding: "utf8",
    timeout: 5000,
    cwd: dir,
    env: env(dir, extra),
  });
}
const file = (dir) => path.join(dir, ".tonone", "decisions.jsonl");
const add = (dir, title, more = []) =>
  cli(dir, [
    "add",
    "--title",
    title,
    "--decision",
    "do " + title,
    "--why",
    "because " + title,
    ...more,
  ]);
const idOf = (r) => /(D-\d{8}-[0-9a-f]{4})/.exec(r.stdout)[1];
const ctx = (r) => JSON.parse(r.stdout).hookSpecificOutput.additionalContext;
const done = (d) => fs.rmSync(d, { recursive: true, force: true });

test("add writes a valid record and list shows it", () => {
  const d = mk();
  const r = add(d, "use postgres", ["--scope", "db/", "--irreversible"]);
  assert.strictEqual(r.status, 0, r.stderr);
  const rec = JSON.parse(fs.readFileSync(file(d), "utf8").trim());
  assert.match(rec.id, /^D-\d{8}-[0-9a-f]{4}$/);
  assert.strictEqual(rec.reversible, false);
  assert.strictEqual(rec.status, "active");
  assert.strictEqual(rec.scope, "db/");
  assert.strictEqual(rec.by, "apex");
  assert.match(cli(d, ["list"]).stdout, /use postgres/);
  done(d);
});

test("add validates required fields and supersedes target", () => {
  const d = mk();
  assert.strictEqual(cli(d, ["add", "--title", "x"]).status, 1);
  assert.strictEqual(
    add(d, "a", ["--supersedes", "D-20200101-0000"]).status,
    1,
  );
  assert.ok(!fs.existsSync(file(d)));
  done(d);
});

test("supersede makes old inactive; --all shows it", () => {
  const d = mk();
  const id = idOf(add(d, "old choice"));
  const r = cli(d, [
    "supersede",
    id,
    "--decision",
    "new way",
    "--why",
    "changed",
  ]);
  assert.strictEqual(r.status, 0, r.stderr);
  const act = cli(d, ["list", "--json"]);
  const rows = JSON.parse(act.stdout);
  assert.strictEqual(rows.length, 1);
  assert.strictEqual(rows[0].supersedes, id);
  assert.strictEqual(rows[0].title, "old choice"); // inherited
  const all = JSON.parse(cli(d, ["list", "--all", "--json"]).stdout);
  assert.strictEqual(all.find((x) => x.id === id).status, "superseded");
  assert.strictEqual(
    file(d) && fs.readFileSync(file(d), "utf8").trim().split("\n").length,
    2,
  );
  done(d);
});

test("redact hides text everywhere but never rewrites the file", () => {
  const d = mk();
  const id = idOf(add(d, "api key sk-SECRET123"));
  const before = fs.readFileSync(file(d), "utf8");
  assert.strictEqual(cli(d, ["redact", id, "--reason", "secret"]).status, 0);
  const after = fs.readFileSync(file(d), "utf8");
  assert.ok(after.startsWith(before)); // append-only
  for (const args of [
    ["list"],
    ["list", "--all"],
    ["list", "--all", "--json"],
    ["show", id],
  ]) {
    assert.ok(!cli(d, args).stdout.includes("SECRET123"), args.join(" "));
  }
  assert.strictEqual(hook(d, {}).stdout, "");
  assert.strictEqual(
    cli(d, ["supersede", id, "--decision", "x", "--why", "y"]).status,
    1,
  );
  done(d);
});

test("hook silent without file, with empty file, and when env off", () => {
  const d = mk();
  const r = hook(d, { cwd: d });
  assert.strictEqual(r.status, 0);
  assert.strictEqual(r.stdout, "");
  fs.mkdirSync(path.join(d, ".tonone"));
  fs.writeFileSync(file(d), "");
  assert.strictEqual(hook(d, { cwd: d }).stdout, "");
  add(d, "thing");
  assert.ok(hook(d, { cwd: d }).stdout.length > 0);
  assert.strictEqual(
    hook(d, { cwd: d }, { TONONE_DECISIONS: "off" }).stdout,
    "",
  );
  done(d);
});

test("hook output: SessionStart additionalContext, irreversible first, read-only", () => {
  const d = mk();
  add(d, "reversible one");
  add(d, "locked one", ["--irreversible"]);
  const before = fs.readFileSync(file(d), "utf8");
  const out = JSON.parse(hook(d, { cwd: d, source: "startup" }).stdout);
  assert.strictEqual(out.hookSpecificOutput.hookEventName, "SessionStart");
  const text = out.hookSpecificOutput.additionalContext;
  assert.ok(text.indexOf("locked one") < text.indexOf("reversible one"));
  assert.match(text, /\[irreversible\]/);
  assert.strictEqual(fs.readFileSync(file(d), "utf8"), before);
  done(d);
});

test("cap: max 10 entries with +N more line", () => {
  const d = mk();
  for (let i = 0; i < 13; i++) add(d, "d" + i);
  const t = ctx(hook(d, { cwd: d }));
  assert.strictEqual(
    t.split("\n").filter((l) => l.startsWith("- ")).length,
    10,
  );
  assert.match(t, /\+3 more: \/apex-decisions list/);
  done(d);
});

test("cap: ~1500 chars with long entries", () => {
  const d = mk();
  const long = "w".repeat(480);
  for (let i = 0; i < 8; i++)
    cli(d, ["add", "--title", "t" + i, "--decision", long, "--why", long]);
  const t = ctx(hook(d, { cwd: d }));
  assert.ok(t.length <= 1600, `len ${t.length}`);
  assert.match(t, /\+\d+ more/);
  done(d);
});

test("corrupt lines, blank lines, unknown ops are skipped", () => {
  const d = mk();
  add(d, "good one");
  fs.appendFileSync(
    file(d),
    '{not json\n\n[1,2]\n{"op":"weird","id":"x"}\n"str"\n{"id":"D-1"}',
  );
  const r = hook(d, { cwd: d });
  assert.strictEqual(r.status, 0);
  assert.match(ctx(r), /good one/);
  // unterminated tail must not corrupt the next append
  assert.strictEqual(add(d, "after corrupt").status, 0);
  assert.match(ctx(hook(d, { cwd: d })), /after corrupt/);
  done(d);
});

test("hook fails open on garbage stdin and empty stdin", () => {
  const d = mk();
  add(d, "still shown");
  for (const input of ["\u0000\u0001 garbage {{{", "", "null", "[]"]) {
    const r = hook(d, input);
    assert.strictEqual(r.status, 0);
    assert.doesNotThrow(() => r.stdout && JSON.parse(r.stdout));
  }
  done(d);
});

test("oversize file: tail only, no crash", () => {
  const d = mk();
  fs.mkdirSync(path.join(d, ".tonone"));
  const junk =
    JSON.stringify({
      id: "D-x",
      title: "t",
      decision: "d",
      why: "w",
      ts: "2020-01-01T00:00:00Z",
      status: "active",
    }) + "\n";
  fs.writeFileSync(
    file(d),
    junk.repeat(Math.ceil((1024 * 1024 * 1.5) / junk.length)),
  );
  add(d, "newest tail");
  const r = hook(d, { cwd: d });
  assert.strictEqual(r.status, 0);
  assert.match(ctx(r), /newest tail/);
  done(d);
});

test("project discovery walks up from cwd when CLAUDE_PROJECT_DIR unset", () => {
  const d = mk();
  add(d, "found by walk");
  const sub = path.join(d, "a", "b");
  fs.mkdirSync(sub, { recursive: true });
  const r = spawnSync("node", [HOOK], {
    input: JSON.stringify({ cwd: sub }),
    encoding: "utf8",
    cwd: sub,
    env: { ...process.env, TONONE_DECISIONS: "", CLAUDE_PROJECT_DIR: "" },
  });
  assert.match(ctx(r), /found by walk/);
  done(d);
});
