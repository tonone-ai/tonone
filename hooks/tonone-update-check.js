#!/usr/bin/env node
"use strict";

// tonone-update-check — SessionStart hook
// Checks for plugin updates once per 24 h. When a newer version exists it asks
// once per version whether to update. Exits silently if offline, rate-limited,
// or up to date.
//
// A hook cannot prompt, so the ask goes to Claude as SessionStart context:
// Claude asks the user, and runs `claude plugin update` only on "Update now".
// Opt out: TONONE_NO_UPDATE_CHECK=1. Skipped when CI is set.

const https = require("https");
const fs = require("fs");
const os = require("os");
const path = require("path");

// ── Config ────────────────────────────────────────────────────────────────────

const PLUGIN_ROOT =
  process.env.CLAUDE_PLUGIN_ROOT || path.join(__dirname, "..");
const PLUGIN_JSON = path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json");
const CACHE_DIR =
  process.env.TONONE_CONFIG_DIR || path.join(os.homedir(), ".config", "tonone");
const CACHE_FILE = path.join(CACHE_DIR, "update-cache.json");
const INTERVAL_MS = 24 * 60 * 60 * 1000; // 24 h
const MARKETPLACE = "tonone-ai";
const RAW_URL =
  "https://raw.githubusercontent.com/tonone-ai/tonone/main/.claude-plugin/plugin.json";

// ── Helpers ───────────────────────────────────────────────────────────────────

function readManifest() {
  try {
    return JSON.parse(fs.readFileSync(PLUGIN_JSON, "utf8"));
  } catch {
    return {};
  }
}

function readCache() {
  try {
    return JSON.parse(fs.readFileSync(CACHE_FILE, "utf8"));
  } catch {
    return {};
  }
}

function writeCache(data) {
  try {
    fs.mkdirSync(CACHE_DIR, { recursive: true });
    fs.writeFileSync(CACHE_FILE, JSON.stringify(data));
  } catch {}
}

// Versions and names reach Claude's context, and `latest` comes from a remote
// response, so only plain x.y.z versions and plugin-name characters pass.
const VERSION_RE = /^\d+\.\d+\.\d+$/;
const NAME_RE = /^[a-z0-9][a-z0-9-]*$/;

// Returns -1 if a < b, 0 if equal, 1 if a > b.
function semverCmp(a, b) {
  const pa = a.split(".").map(Number);
  const pb = b.split(".").map(Number);
  for (let i = 0; i < 3; i++) {
    const d = (pa[i] || 0) - (pb[i] || 0);
    if (d !== 0) return d < 0 ? -1 : 1;
  }
  return 0;
}

function fetchLatestVersion(cb) {
  const req = https.get(RAW_URL, { timeout: 5000 }, (res) => {
    let body = "";
    res.on("data", (chunk) => (body += chunk));
    res.on("end", () => {
      try {
        cb(null, JSON.parse(body).version || null);
      } catch {
        cb(new Error("parse error"));
      }
    });
  });
  req.on("error", cb);
  req.on("timeout", () => {
    req.destroy();
    cb(new Error("timeout"));
  });
}

function askText(name, current, latest) {
  const cmd = `claude plugin update ${name}@${MARKETPLACE}`;
  return (
    `tonone update (ask once): ${name} v${latest} is available, the user has ` +
    `v${current}. Ask the user with AskUserQuestion whether to update now, ` +
    `options "Update now" and "Not now". If they pick "Update now" run: ` +
    `${cmd} , then tell them to restart Claude Code to apply it. If they pick ` +
    `"Not now" do nothing; they will not be asked again for v${latest}. ` +
    `Do not mention this otherwise.`
  );
}

// Ask at most once per version. Returns the JSON to print, or "".
function decide(manifest, cache, env) {
  if (env.CI || env.TONONE_NO_UPDATE_CHECK === "1") return "";
  const { name, version: current } = manifest;
  const latest = cache.latestVersion;
  if (!VERSION_RE.test(current || "") || !VERSION_RE.test(latest || ""))
    return "";
  if (!NAME_RE.test(name || "")) return "";
  if (semverCmp(current, latest) >= 0) return "";
  if (cache.askedVersion === latest) return "";
  return JSON.stringify({
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext: askText(name, current, latest),
    },
  });
}

function emit(cache) {
  const out = decide(readManifest(), cache, process.env);
  if (!out) return;
  writeCache({ ...cache, askedVersion: cache.latestVersion });
  process.stdout.write(out);
}

// ── Main ──────────────────────────────────────────────────────────────────────

if (require.main === module) {
  const cache = readCache();
  const now = Date.now();

  // Cache fresh enough: no network call.
  if (cache.checkedAt && now - cache.checkedAt < INTERVAL_MS) {
    emit(cache);
    process.exit(0);
  }

  // Cache stale: fetch from GitHub.
  fetchLatestVersion((err, latest) => {
    if (err || !latest) process.exit(0);
    const next = { ...cache, checkedAt: now, latestVersion: latest };
    writeCache(next);
    emit(next);
  });
}

module.exports = { decide, semverCmp, askText };
