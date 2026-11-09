#!/usr/bin/env node
"use strict";

// form-design-lint — PostToolUse hook (Edit, MultiEdit, Write)
//
// Opt-in, read-only design linter for the file Claude just edited. Inert until
// enabled, and it NEVER blocks: findings are surfaced to the model as
// additionalContext, nothing else.
//
// Enable (either):
//   .tonone/design.json  {"hook": true}
//   env TONONE_DESIGN_LINT=on
// TONONE_DESIGN_LINT=off (also 0, false, no) always wins.
//
// Scope: only the edited file, only .tsx .jsx .vue .svelte .html .css .scss,
// only tier "immediate" rules (mechanical, high precision). Advisory/taste
// rules are CLI-only (/form-lint). Files over 300KB are skipped.
//
// Dedup: the same (file, rule, line-content) is reported once per session. State
// lives in os.tmpdir()/tonone-design-lint-<session>.json, capped at 400 entries.
//
// Contract: print a PostToolUse JSON and exit 0, or print nothing and exit 0.
// Every error path (bad JSON, unreadable file, timeout) fails open.

const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");

const STDIN_TIMEOUT_MS = 1500;
const BUDGET_MS = 1200;
const MAX_FILE_BYTES = 300 * 1024;
const MAX_SHOWN = 5;
const MAX_STATE = 400;
const WRITE_TOOLS = new Set(["Edit", "MultiEdit", "Write"]);
const EXTS = new Set([
  ".tsx",
  ".jsx",
  ".vue",
  ".svelte",
  ".html",
  ".css",
  ".scss",
]);

function envState() {
  const v = String(process.env.TONONE_DESIGN_LINT || "")
    .trim()
    .toLowerCase();
  if (["off", "0", "false", "no"].includes(v)) return "off";
  if (["on", "1", "true", "yes"].includes(v)) return "on";
  return "";
}

function statePath(sessionId) {
  const safe = String(sessionId || "nosession")
    .replace(/[^\w.-]/g, "_")
    .slice(0, 80);
  return path.join(os.tmpdir(), `tonone-design-lint-${safe}.json`);
}

function loadSeen(p) {
  try {
    const j = JSON.parse(fs.readFileSync(p, "utf8"));
    return Array.isArray(j.seen) ? j.seen : [];
  } catch {
    return [];
  }
}

function saveSeen(p, seen) {
  try {
    fs.writeFileSync(p, JSON.stringify({ v: 1, seen: seen.slice(-MAX_STATE) }));
  } catch {}
}

const hash = (s) =>
  crypto.createHash("sha1").update(s).digest("hex").slice(0, 12);

// Returns the hook output object, or null for "say nothing".
function evaluate(input) {
  const started = Date.now();
  if (!input || typeof input !== "object") return null;
  if (!WRITE_TOOLS.has(input.tool_name)) return null;
  const env = envState();
  if (env === "off") return null;

  const ti = input.tool_input || {};
  const fp = ti.file_path;
  if (typeof fp !== "string" || !fp) return null;
  const abs = path.resolve(input.cwd || process.cwd(), fp);
  if (!EXTS.has(path.extname(abs).toLowerCase())) return null;

  const lint = require("../scripts/design-lint/design-lint.js");
  const root = lint.findRoot(path.dirname(abs));
  const config = lint.loadConfig(root);
  if (env !== "on" && !config.hook) return null;

  const rel = path.relative(root, abs).split(path.sep).join("/");
  if (rel.startsWith("..") || lint.isIgnoredFile(config, rel)) return null;

  const st = fs.statSync(abs);
  if (!st.isFile() || st.size > MAX_FILE_BYTES) return null;
  const src = fs.readFileSync(abs, "utf8");

  const findings = lint.lintSource({
    file: rel,
    src,
    designMd: lint.loadDesignMd(root),
    config,
    tier: "immediate",
    deadline: started + BUDGET_MS,
  });
  if (!findings.length) return null;

  const lines = src.split("\n");
  const sp = statePath(input.session_id);
  const seen = loadSeen(sp);
  const fresh = [];
  for (const f of findings) {
    const h = hash(`${rel}|${f.rule}|${(lines[f.line - 1] || "").trim()}`);
    if (seen.includes(h)) continue;
    seen.push(h);
    fresh.push(f);
  }
  if (!fresh.length) return null;
  saveSeen(sp, seen);

  const shown = fresh
    .slice(0, MAX_SHOWN)
    .map((f) => `- ${rel}:${f.line} [${f.rule}] ${f.message} Fix: ${f.fix}`);
  const more = fresh.length - shown.length;
  const text = [
    `design-lint: ${fresh.length} mechanical issue(s) in ${rel}`,
    ...shown,
    ...(more > 0 ? [`${more} more, run /form-lint`] : []),
    "Fix them, or suppress with a reason (design-lint-disable-next-line <rule>). Advisory only; do not stop work.",
  ].join("\n");
  return {
    hookSpecificOutput: {
      hookEventName: "PostToolUse",
      additionalContext: text,
    },
  };
}

function emit(input) {
  try {
    const out = evaluate(input);
    if (out) process.stdout.write(JSON.stringify(out));
  } catch {}
  process.exit(0);
}

function main() {
  try {
    if (process.stdin.isTTY) return;
    let buf = "";
    let done = false;
    const finish = (run) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      if (!run) return process.exit(0);
      let input = null;
      try {
        input = JSON.parse(buf);
      } catch {}
      emit(input);
    };
    const timer = setTimeout(() => finish(false), STDIN_TIMEOUT_MS);
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (c) => {
      buf += c;
      if (buf.length > 4 * 1024 * 1024) finish(false);
    });
    process.stdin.on("end", () => finish(true));
    process.stdin.on("error", () => finish(false));
  } catch {
    process.exit(0);
  }
}

module.exports = { evaluate, envState };

if (require.main === module) main();
