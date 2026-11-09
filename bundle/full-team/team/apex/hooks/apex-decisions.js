#!/usr/bin/env node
"use strict";

// apex-decisions — SessionStart hook + CLI for the project decision log
//
// Surfaces active, settled decisions at session start so the team does not
// re-litigate them. The log is `.tonone/decisions.jsonl`: append-only, one JSON
// record per line, never rewritten by this tool.
//
// Hook mode (no args, hook JSON on stdin): READ-ONLY. If the file exists, fold
// it and print active decisions as SessionStart `additionalContext` — newest
// first, irreversible ones first, max 10 entries and ~1500 chars, then
// "+N more: /apex-decisions list". Prints nothing when the file is missing or
// holds no active decisions. The file's existence IS the opt-in. Every error
// path (bad stdin, corrupt lines, unreadable file, timeout) fails open: no
// output, exit 0.
//
// Learnings share the file: {"kind":"learning","id":"L-YYYYMMDD-xxxx","ts",
// "lesson","scope"?,"source"?,"confirmed":1,"by","supersedes"?}. Absent kind =
// decision (legacy lines unchanged). {"op":"confirm","id","ts"} bumps the
// confirmed count. Supersede/redact work the same. The hook shows learnings
// after decisions (max 3, never ahead of irreversible decisions).
//
// Metrics (opt-in): TONONE_METRICS=on appends
// {"tool":"apex-decisions","event":"resurfaced","n":<decisions>,"learnings":<n>}
// to <project>/.tonone/metrics.jsonl. Counts only; errors swallowed.
//
// Disable: TONONE_DECISIONS=off (also 0, false, no).
//
// Records (one per line):
//   decision  {"id":"D-YYYYMMDD-xxxx","ts":ISO,"title","decision","why",
//              "scope"?:str,"reversible":bool,"status":"active",
//              "by":"apex|user|<agent>","supersedes"?:id}
//   redact    {"op":"redact","id":<target id>,"reason","ts":ISO}
// Fold: a record whose id is named by a later `supersedes` becomes
// "superseded". A redacted id has its text hidden everywhere (list, show,
// hook, --json). Redaction hides; it does NOT delete. Real removal of an
// accidental secret needs a manual edit of the file plus a git history rewrite.
//
// Project dir: CLAUDE_PROJECT_DIR, else walk up from cwd (max 20 levels) to the
// nearest `.tonone/decisions.jsonl`. `add` with no existing file creates
// `.tonone/decisions.jsonl` under CLAUDE_PROJECT_DIR or cwd.
//
// CLI:
//   node apex-decisions.js add --title T --decision D --why W [--scope S]
//                               [--irreversible] [--supersedes ID] [--by WHO]
//   node apex-decisions.js supersede ID --decision D --why W [--title T] [--scope S] [--irreversible] [--by WHO]
//   node apex-decisions.js redact ID --reason R
//   node apex-decisions.js list [--all] [--json]
//   node apex-decisions.js show ID
//   node apex-decisions.js learn --lesson L [--scope S] [--source S] [--by WHO]
//   node apex-decisions.js learnings [--all] [--json] [--query WORDS]
//   node apex-decisions.js confirm ID        (learning still holds; bumps count)
//   (supersede/redact accept learning IDs; supersede takes --lesson there)

const fs = require("fs");
const path = require("path");

const REL = path.join(".tonone", "decisions.jsonl");
const STDIN_TIMEOUT_MS = 3000;
const MAX_WALK = 20;
const MAX_READ_BYTES = 1024 * 1024; // larger files: read the tail only
const MAX_ENTRIES = 10;
const MAX_CHARS = 1500;
const MAX_LEARNINGS = 3;
const LIMITS = {
  title: 120,
  decision: 500,
  why: 500,
  scope: 200,
  reason: 200,
  by: 40,
  lesson: 300,
  source: 80,
};

// ── Location ─────────────────────────────────────────────────────────────────

function findFile(env, cwd) {
  if (env.CLAUDE_PROJECT_DIR) {
    const f = path.join(env.CLAUDE_PROJECT_DIR, REL);
    return fs.existsSync(f) ? f : null;
  }
  let dir = path.resolve(cwd || process.cwd());
  for (let i = 0; i < MAX_WALK; i++) {
    const f = path.join(dir, REL);
    if (fs.existsSync(f)) return f;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

function targetFile(env, cwd) {
  return (
    findFile(env, cwd) ||
    path.join(env.CLAUDE_PROJECT_DIR || cwd || process.cwd(), REL)
  );
}

// ── Read + fold ──────────────────────────────────────────────────────────────

// Returns array of parsed objects; bad lines are skipped. Large file: tail only
// (the first, possibly partial, line of the tail is dropped).
function readRecords(file) {
  const st = fs.statSync(file);
  if (!st.isFile()) return [];
  let text;
  if (st.size > MAX_READ_BYTES) {
    const fd = fs.openSync(file, "r");
    try {
      const buf = Buffer.alloc(MAX_READ_BYTES);
      fs.readSync(fd, buf, 0, MAX_READ_BYTES, st.size - MAX_READ_BYTES);
      text = buf.toString("utf8");
    } finally {
      fs.closeSync(fd);
    }
    const nl = text.indexOf("\n");
    text = nl === -1 ? "" : text.slice(nl + 1);
  } else {
    text = fs.readFileSync(file, "utf8");
  }
  const out = [];
  for (const line of text.split("\n")) {
    const s = line.trim();
    if (!s) continue;
    try {
      const o = JSON.parse(s);
      if (
        o &&
        typeof o === "object" &&
        !Array.isArray(o) &&
        typeof o.id === "string"
      )
        out.push(o);
    } catch {}
  }
  return out;
}

function str(v) {
  return typeof v === "string" ? v : "";
}

// Fold to [{...record, status: active|superseded|redacted, superseded_by?, redacted_reason?}]
// in file order. Redacted records keep id/ts/by/status only.
function fold(records) {
  const decisions = new Map();
  const redacted = new Map();
  const supers = new Map(); // old id -> new id
  const confirms = new Map(); // id -> extra confirmations
  for (const r of records) {
    if (r.op === "confirm") {
      confirms.set(r.id, (confirms.get(r.id) || 0) + 1);
      continue;
    }
    if (r.op === "redact") {
      if (!redacted.has(r.id)) redacted.set(r.id, str(r.reason));
      continue;
    }
    if (r.op !== undefined) continue; // unknown op: ignore
    if (r.kind === "learning") {
      if (!str(r.lesson)) continue;
    } else if (!str(r.title) && !str(r.decision)) continue;
    if (decisions.has(r.id)) continue; // first write wins; ids are unique
    decisions.set(r.id, r);
    if (typeof r.supersedes === "string" && r.supersedes)
      supers.set(r.supersedes, r.id);
  }
  const out = [];
  for (const r of decisions.values()) {
    if (redacted.has(r.id)) {
      out.push({
        id: r.id,
        ts: r.ts,
        by: r.by,
        ...(r.kind === "learning" ? { kind: "learning" } : {}),
        status: "redacted",
        redacted_reason: redacted.get(r.id),
      });
    } else {
      const sb = supers.get(r.id);
      const rec = { ...r, status: sb ? "superseded" : "active" };
      if (r.kind === "learning")
        rec.confirmed = (Number(r.confirmed) || 1) + (confirms.get(r.id) || 0);
      if (sb) rec.superseded_by = sb;
      out.push(rec);
    }
  }
  return out;
}

const isLearning = (r) => r.kind === "learning";

function byRecency(a, b) {
  const ta = Date.parse(a.ts) || 0;
  const tb = Date.parse(b.ts) || 0;
  return tb - ta;
}

// Irreversible first, then newest first.
function ordered(active) {
  return active.slice().sort((a, b) => {
    const ia = a.reversible === false ? 0 : 1;
    const ib = b.reversible === false ? 0 : 1;
    return ia - ib || byRecency(a, b);
  });
}

// ── Hook rendering ───────────────────────────────────────────────────────────

function oneLine(s) {
  return str(s).replace(/\s+/g, " ").trim();
}

function formatEntry(r) {
  const tag = r.reversible === false ? " [irreversible]" : "";
  const scope = oneLine(r.scope) ? ` (scope: ${oneLine(r.scope)})` : "";
  return `- ${r.id}${tag} ${oneLine(r.title)}: ${oneLine(r.decision)} — why: ${oneLine(r.why)}${scope}`;
}

function formatLearning(r) {
  const n = Number(r.confirmed) || 1;
  const conf = n > 1 ? ` (x${n})` : "";
  const scope = oneLine(r.scope) ? ` (scope: ${oneLine(r.scope)})` : "";
  return `- ${r.id}${conf} ${oneLine(r.lesson)}${scope}`;
}

// Most confirmed first, then newest.
function orderedLearnings(ls) {
  return ls
    .slice()
    .sort(
      (a, b) =>
        (Number(b.confirmed) || 1) - (Number(a.confirmed) || 1) ||
        byRecency(a, b),
    );
}

// Returns {text, n, learnings} (counts = entries shown).
function render(active) {
  const decisions = active.filter((r) => !isLearning(r));
  const learnings = active.filter(isLearning);
  const empty = { text: "", n: 0, learnings: 0 };
  if (!decisions.length && !learnings.length) return empty;
  const lines = [];
  let used = 0;
  let nd = 0;
  let nl = 0;
  const push = (line, first) => {
    const room = MAX_CHARS - used - 1;
    if (line.length > room) {
      if (!first || room < 80) return false;
      line = line.slice(0, Math.max(room - 1, 0)) + "…"; // always show at least one
    }
    lines.push(line);
    used += line.length + 1;
    return true;
  };
  if (decisions.length) {
    push(
      "Active project decisions (settled — do not re-litigate; supersede via /apex-decisions):",
      true,
    );
    // Keep up to 2 slots for learnings, but never more than exist.
    const cap =
      MAX_ENTRIES - Math.min(2, Math.min(learnings.length, MAX_LEARNINGS));
    for (const r of ordered(decisions)) {
      if (nd >= cap || !push(formatEntry(r), nd === 0)) break;
      nd++;
    }
    if (decisions.length > nd)
      push(`+${decisions.length - nd} more: /apex-decisions list`);
  }
  if (learnings.length) {
    const first = !decisions.length;
    const hdr =
      "Project learnings (hints from past sessions — verify before relying; /apex-decisions learnings):";
    const cap = Math.min(MAX_LEARNINGS, MAX_ENTRIES - nd);
    if (cap > 0 && push(hdr, first)) {
      for (const r of orderedLearnings(learnings)) {
        if (nl >= cap || !push(formatLearning(r), first && nl === 0)) break;
        nl++;
      }
      if (nl === 0)
        lines.pop(); // header alone is noise
      else if (learnings.length > nl)
        push(`+${learnings.length - nl} more: /apex-decisions learnings`);
    }
  }
  if (nd + nl === 0) return empty;
  return { text: lines.join("\n"), n: nd, learnings: nl };
}

function renderContext(active) {
  return render(active).text;
}

// Opt-in local counter (TONONE_METRICS=on). Never throws, never affects output.
function metric(env, root, event, extra) {
  try {
    if (env.TONONE_METRICS !== "on") return;
    const dir = path.join(root, ".tonone");
    fs.mkdirSync(dir, { recursive: true });
    fs.appendFileSync(
      path.join(dir, "metrics.jsonl"),
      JSON.stringify({
        ts: new Date().toISOString(),
        tool: "apex-decisions",
        event,
        ...extra,
      }) + "\n",
    );
  } catch {}
}

function disabled(env) {
  return /^(off|0|false|no)$/i.test(String(env.TONONE_DECISIONS || ""));
}

function hookOutput(input, env) {
  if (disabled(env)) return "";
  const cwd =
    input && typeof input.cwd === "string" && input.cwd
      ? input.cwd
      : process.cwd();
  const file = findFile(env, cwd);
  if (!file) return "";
  const active = fold(readRecords(file)).filter((r) => r.status === "active");
  const r = render(active);
  const ctx = r.text;
  if (!ctx) return "";
  metric(env, path.dirname(path.dirname(file)), "resurfaced", {
    n: r.n,
    learnings: r.learnings,
  });
  return JSON.stringify({
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext: ctx,
    },
  });
}

// ── CLI ──────────────────────────────────────────────────────────────────────

class CliError extends Error {}

function parseArgs(argv) {
  const pos = [];
  const flags = {};
  const bool = new Set(["irreversible", "all", "json"]);
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const eq = a.indexOf("=");
      const k = eq === -1 ? a.slice(2) : a.slice(2, eq);
      if (bool.has(k)) flags[k] = true;
      else if (eq !== -1) flags[k] = a.slice(eq + 1);
      else {
        if (i + 1 >= argv.length) throw new CliError(`--${k} needs a value`);
        flags[k] = argv[++i];
      }
    } else pos.push(a);
  }
  return { pos, flags };
}

function need(flags, k) {
  const v = typeof flags[k] === "string" ? flags[k].trim() : "";
  if (!v) throw new CliError(`--${k} is required`);
  return check(k, v);
}

function opt(flags, k) {
  const v = typeof flags[k] === "string" ? flags[k].trim() : "";
  return v ? check(k, v) : undefined;
}

function check(k, v) {
  if (LIMITS[k] && v.length > LIMITS[k])
    throw new CliError(`--${k} too long (${v.length} > ${LIMITS[k]})`);
  return v;
}

function newId(taken, now, prefix = "D") {
  const day = now.toISOString().slice(0, 10).replace(/-/g, "");
  for (let i = 0; i < 50; i++) {
    const id = `${prefix}-${day}-${Math.floor(Math.random() * 0x10000)
      .toString(16)
      .padStart(4, "0")}`;
    if (!taken.has(id)) return id;
  }
  throw new CliError("could not allocate a unique id");
}

// Single appendFileSync call (O_APPEND). A leading newline guards against a
// file whose last line was left unterminated.
function appendLine(file, obj) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  let prefix = "";
  try {
    const st = fs.statSync(file);
    if (st.size > 0) {
      const fd = fs.openSync(file, "r");
      try {
        const b = Buffer.alloc(1);
        fs.readSync(fd, b, 0, 1, st.size - 1);
        if (b[0] !== 0x0a) prefix = "\n";
      } finally {
        fs.closeSync(fd);
      }
    }
  } catch {}
  fs.appendFileSync(file, prefix + JSON.stringify(obj) + "\n", { flag: "a" });
}

function publicView(r) {
  return r.status === "redacted"
    ? {
        id: r.id,
        ts: r.ts,
        by: r.by,
        ...(r.kind ? { kind: r.kind } : {}),
        status: "redacted",
        redacted_reason: r.redacted_reason,
      }
    : r;
}

function describe(r, full) {
  if (r.status === "redacted")
    return `${r.id} [redacted] ${r.redacted_reason || ""}`.trim();
  const tag = r.reversible === false ? " [irreversible]" : "";
  const st =
    r.status === "active"
      ? ""
      : ` (${r.status}${r.superseded_by ? " by " + r.superseded_by : ""})`;
  if (isLearning(r)) {
    const c = r.confirmed > 1 ? ` x${r.confirmed}` : "";
    const head = `${r.id}${c}${st} ${oneLine(r.lesson)}`;
    if (!full) return head;
    return [
      head,
      r.scope ? `  scope:    ${oneLine(r.scope)}` : null,
      r.source ? `  source:   ${oneLine(r.source)}` : null,
      `  by:       ${r.by || "?"}  at ${r.ts || "?"}`,
      r.supersedes ? `  supersedes: ${r.supersedes}` : null,
    ]
      .filter(Boolean)
      .join("\n");
  }
  const head = `${r.id}${tag}${st} ${oneLine(r.title)}`;
  if (!full) return head;
  return [
    head,
    `  decision: ${oneLine(r.decision)}`,
    `  why:      ${oneLine(r.why)}`,
    r.scope ? `  scope:    ${oneLine(r.scope)}` : null,
    `  by:       ${r.by || "?"}  at ${r.ts || "?"}`,
    r.supersedes ? `  supersedes: ${r.supersedes}` : null,
  ]
    .filter(Boolean)
    .join("\n");
}

function runCli(argv, env, cwd, now, out) {
  const [cmd, ...rest] = argv;
  const { pos, flags } = parseArgs(rest);
  const file = targetFile(env, cwd);
  const exists = fs.existsSync(file);
  const folded = exists ? fold(readRecords(file)) : [];
  const byId = new Map(folded.map((r) => [r.id, r]));

  const addLearning = (fields, supersedes) => {
    const rec = {
      id: newId(new Set(byId.keys()), now, "L"),
      ts: now.toISOString(),
      kind: "learning",
      lesson: fields.lesson,
    };
    if (fields.scope) rec.scope = fields.scope;
    if (fields.source) rec.source = fields.source;
    rec.confirmed = 1;
    rec.status = "active";
    rec.by = opt(flags, "by") || env.TONONE_DECISION_BY || "apex";
    if (supersedes) rec.supersedes = supersedes;
    appendLine(file, rec);
    out(
      `${supersedes ? "superseded " + supersedes + " with " : "learned "}${rec.id}: ${rec.lesson}`,
    );
  };

  const addRecord = (fields, supersedes) => {
    const rec = {
      id: newId(new Set(byId.keys()), now),
      ts: now.toISOString(),
      title: fields.title,
      decision: fields.decision,
      why: fields.why,
    };
    if (fields.scope) rec.scope = fields.scope;
    rec.reversible = !flags.irreversible;
    rec.status = "active";
    rec.by = opt(flags, "by") || env.TONONE_DECISION_BY || "apex";
    if (supersedes) rec.supersedes = supersedes;
    appendLine(file, rec);
    out(
      `${supersedes ? "superseded " + supersedes + " with " : "logged "}${rec.id}: ${rec.title}`,
    );
  };

  const requireTarget = (id) => {
    if (!id) throw new CliError("decision ID required");
    const t = byId.get(id);
    if (!t) throw new CliError(`no such decision: ${id}`);
    return t;
  };

  switch (cmd) {
    case "add": {
      let sup = opt(flags, "supersedes");
      if (sup && isLearning(requireTarget(sup)))
        throw new CliError(`${sup} is a learning; use supersede`);
      return addRecord(
        {
          title: need(flags, "title"),
          decision: need(flags, "decision"),
          why: need(flags, "why"),
          scope: opt(flags, "scope"),
        },
        sup,
      );
    }
    case "supersede": {
      const old = requireTarget(pos[0]);
      if (old.status === "redacted")
        throw new CliError(`${old.id} is redacted; add a new decision instead`);
      if (isLearning(old))
        return addLearning(
          {
            lesson: need(flags, "lesson"),
            scope: opt(flags, "scope") || old.scope,
            source: opt(flags, "source"),
          },
          old.id,
        );
      return addRecord(
        {
          title: opt(flags, "title") || old.title,
          decision: need(flags, "decision"),
          why: need(flags, "why"),
          scope: opt(flags, "scope") || old.scope,
        },
        old.id,
      );
    }
    case "redact": {
      const t = requireTarget(pos[0]);
      const reason = need(flags, "reason");
      appendLine(file, {
        op: "redact",
        id: t.id,
        reason,
        ts: now.toISOString(),
      });
      return out(
        `redacted ${t.id} (text hidden; file still holds it — edit file + rewrite git history to truly remove)`,
      );
    }
    case "learn":
      return addLearning({
        lesson: need(flags, "lesson"),
        scope: opt(flags, "scope"),
        source: opt(flags, "source") || now.toISOString().slice(0, 10),
      });
    case "confirm": {
      const t = requireTarget(pos[0]);
      if (!isLearning(t)) throw new CliError(`${t.id} is not a learning`);
      if (t.status !== "active")
        throw new CliError(`${t.id} is ${t.status}; cannot confirm`);
      appendLine(file, { op: "confirm", id: t.id, ts: now.toISOString() });
      return out(`confirmed ${t.id} (x${t.confirmed + 1})`);
    }
    case "learnings": {
      const q = (opt(flags, "query") || "")
        .toLowerCase()
        .split(/\s+/)
        .filter(Boolean);
      const rows = folded
        .filter((r) => isLearning(r) && (flags.all || r.status === "active"))
        .filter(
          (r) =>
            !q.length ||
            (r.status !== "redacted" &&
              q.every((w) =>
                `${r.lesson} ${r.scope || ""}`.toLowerCase().includes(w),
              )),
        );
      rows.sort(byRecency);
      if (flags.json) return out(JSON.stringify(rows.map(publicView), null, 2));
      if (!rows.length) return out("no learnings");
      return out(rows.map((r) => describe(r, false)).join("\n"));
    }
    case "list": {
      const rows = (
        flags.all ? folded : folded.filter((r) => r.status === "active")
      )
        .filter((r) => !isLearning(r))
        .slice();
      rows.sort(byRecency);
      if (flags.json) return out(JSON.stringify(rows.map(publicView), null, 2));
      if (!rows.length)
        return out(
          exists
            ? "no active decisions"
            : "no decision log (add one to create .tonone/decisions.jsonl)",
        );
      return out(rows.map((r) => describe(r, false)).join("\n"));
    }
    case "show": {
      const t = requireTarget(pos[0]);
      return out(describe(t, true));
    }
    default:
      throw new CliError(
        "usage: add|supersede|redact|list|show|learn|learnings|confirm — see header of apex-decisions.js",
      );
  }
}

// ── Main ─────────────────────────────────────────────────────────────────────

function main() {
  const argv = process.argv.slice(2);
  if (argv.length) {
    try {
      runCli(argv, process.env, process.cwd(), new Date(), (s) =>
        process.stdout.write(s + "\n"),
      );
    } catch (e) {
      process.stderr.write(
        `apex-decisions: ${e instanceof CliError ? e.message : "error: " + (e && e.message)}\n`,
      );
      process.exitCode = 1;
    }
    return;
  }
  try {
    if (process.stdin.isTTY) return;
    let buf = "";
    let done = false;
    const finish = (run) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      if (!run) return;
      try {
        let input = null;
        try {
          input = JSON.parse(buf);
        } catch {}
        const o = hookOutput(input, process.env);
        if (o) process.stdout.write(o + "\n");
      } catch {}
    };
    const timer = setTimeout(() => {
      finish(false);
      process.exit(0);
    }, STDIN_TIMEOUT_MS);
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (c) => {
      buf += c;
      if (buf.length > 4 * 1024 * 1024) finish(false);
    });
    process.stdin.on("end", () => finish(true));
    process.stdin.on("error", () => finish(false));
  } catch {}
}

if (require.main === module) main();

module.exports = { fold, readRecords, renderContext, hookOutput, runCli };
