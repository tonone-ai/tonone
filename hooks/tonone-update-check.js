#!/usr/bin/env node
"use strict";

// tonone-update-check — SessionStart hook
// Checks for plugin updates once per 24 h and notifies the user when a newer
// version is available. Exits silently if offline, rate-limited, or up to date.

const https = require("https");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawnSync } = require("child_process");

// ── Config ────────────────────────────────────────────────────────────────────

const PLUGIN_ROOT =
  process.env.CLAUDE_PLUGIN_ROOT || path.join(__dirname, "..");
const PLUGIN_JSON = path.join(PLUGIN_ROOT, ".claude-plugin", "plugin.json");
const CACHE_DIR = path.join(os.homedir(), ".config", "tonone");
const CACHE_FILE = path.join(CACHE_DIR, "update-cache.json");
const INTERVAL_MS = 24 * 60 * 60 * 1000; // 24 h
const RAW_URL =
  "https://raw.githubusercontent.com/tonone-ai/tonone/main/.claude-plugin/plugin.json";

// ── Helpers ───────────────────────────────────────────────────────────────────

function currentVersion() {
  try {
    return JSON.parse(fs.readFileSync(PLUGIN_JSON, "utf8")).version || null;
  } catch {
    return null;
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

function notify(current, latest) {
  const body = `Update available: v${current} \u2192 v${latest}`;
  const hint = "claude plugin update tonone";
  const script = [
    `display notification "${body}"`,
    `with title "tonone"`,
    `subtitle "${hint}"`,
  ].join(" ");
  spawnSync("osascript", ["-e", script], { timeout: 3000 });
  process.stderr.write(`\n[tonone] ${body}\n  Run: ${hint}\n\n`);
}

// ── Main ──────────────────────────────────────────────────────────────────────

const current = currentVersion();
if (!current) process.exit(0);

const cache = readCache();
const now = Date.now();

// If the cache is fresh enough, use it — no network call.
if (cache.checkedAt && now - cache.checkedAt < INTERVAL_MS) {
  if (cache.latestVersion && semverCmp(current, cache.latestVersion) < 0) {
    notify(current, cache.latestVersion);
  }
  process.exit(0);
}

// Cache stale — fetch from GitHub.
fetchLatestVersion((err, latest) => {
  if (err || !latest) process.exit(0);
  writeCache({ checkedAt: now, latestVersion: latest });
  if (semverCmp(current, latest) < 0) {
    notify(current, latest);
  }
});
