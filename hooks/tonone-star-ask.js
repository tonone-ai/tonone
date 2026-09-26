#!/usr/bin/env node
"use strict";

// tonone-star-ask — SessionStart hook
// Asks for a GitHub star exactly once, after the user has started tonone in
// ASK_AFTER distinct sessions. Most people install through the plugin
// marketplace and never see the repo page, so this is the only place they
// hear that a star helps. Never blocks the session on any error.
//
// Counts only fresh sessions (source "startup"), keyed by session_id, so a
// resume, /clear or compaction does not advance the count, and the hook being
// declared in more than one place cannot count the same session twice.
//
// Opt out: TONONE_NO_STAR_ASK=1. Skipped automatically when CI is set.

const fs = require("fs");
const os = require("os");
const path = require("path");

// ── Config ────────────────────────────────────────────────────────────────────

const STATE_DIR =
  process.env.TONONE_CONFIG_DIR || path.join(os.homedir(), ".config", "tonone");
const STATE_FILE = path.join(STATE_DIR, "star-ask.json");
const ASK_AFTER = 5;
const REPO_URL = "https://github.com/tonone-ai/tonone";
const STDIN_BUDGET_MS = 1000;

const MESSAGE =
  `tonone: ${ASK_AFTER} sessions in. If the team has been useful, a GitHub star ` +
  `helps other people find it: ${REPO_URL}\n` +
  `(Shown once. TONONE_NO_STAR_ASK=1 turns it off.)`;

// ── Helpers ───────────────────────────────────────────────────────────────────

function readState() {
  try {
    const s = JSON.parse(fs.readFileSync(STATE_FILE, "utf8"));
    return {
      asked: s.asked === true,
      sessions: Array.isArray(s.sessions) ? s.sessions : [],
    };
  } catch {
    return { asked: false, sessions: [] };
  }
}

function writeState(state) {
  try {
    fs.mkdirSync(STATE_DIR, { recursive: true });
    fs.writeFileSync(STATE_FILE, JSON.stringify(state));
  } catch {}
}

// Pure decision: given state and the hook payload, return the next state and
// whether to ask now.
function decide(state, payload, env) {
  if (env.TONONE_NO_STAR_ASK === "1" || env.CI) return { state, ask: false };
  if (state.asked) return { state, ask: false };
  const id = payload && payload.session_id;
  const source = payload && payload.source;
  if (!id || (source && source !== "startup")) return { state, ask: false };
  if (state.sessions.includes(id)) return { state, ask: false };

  const sessions = state.sessions.concat(id).slice(-ASK_AFTER);
  if (sessions.length >= ASK_AFTER) {
    return { state: { asked: true, sessions: [] }, ask: true };
  }
  return { state: { asked: false, sessions }, ask: false };
}

function readPayload(cb) {
  if (process.stdin.isTTY) return cb(null);
  let body = "";
  let done = false;
  const finish = () => {
    if (done) return;
    done = true;
    try {
      cb(JSON.parse(body));
    } catch {
      cb(null);
    }
  };
  setTimeout(finish, STDIN_BUDGET_MS).unref();
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (c) => (body += c));
  process.stdin.on("end", finish);
  process.stdin.on("error", finish);
}

// ── Main ──────────────────────────────────────────────────────────────────────

if (require.main === module) {
  readPayload((payload) => {
    try {
      const before = readState();
      const { state, ask } = decide(before, payload, process.env);
      if (state !== before) writeState(state);
      if (ask) process.stdout.write(JSON.stringify({ systemMessage: MESSAGE }));
    } catch {}
    process.exit(0);
  });
}

module.exports = { decide, ASK_AFTER, MESSAGE };
