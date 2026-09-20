"use strict";

/**
 * lib/jev/cache.js — content-addressed cache for Jev API responses.
 *
 * Layout:  ~/.cache/tonone/jev/<first two hex chars>/<sha256>.json
 * TTL:     7 days
 * Entry:   {"v":1,"createdAt":<epoch ms>,"key":"<sha256>","value":<any JSON>}
 *
 * Only API responses are cached. Local scorer results are cheap and
 * deterministic, so caching them would only add failure modes.
 *
 * Every function here is failure-tolerant by construction: a read that cannot
 * happen is a miss, a write that cannot happen is a no-op, and neither ever
 * throws. A corrupt or truncated entry is treated as a miss and removed, which
 * is what makes concurrent use safe together with the atomic write below —
 * writes go to a unique temporary file in the same directory and are moved into
 * place with rename(2), so a reader sees either the previous complete file or
 * the new complete file, never a partial one.
 */

const crypto = require("crypto");
const fs = require("fs");
const os = require("os");
const path = require("path");

const SCHEMA = 1;
const TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 days

/** Cache root. Overridable for tests and for sandboxes with no writable home. */
function cacheDir() {
  if (process.env.TONONE_JEV_CACHE_DIR) {
    return process.env.TONONE_JEV_CACHE_DIR;
  }
  const base =
    process.env.XDG_CACHE_HOME && path.isAbsolute(process.env.XDG_CACHE_HOME)
      ? process.env.XDG_CACHE_HOME
      : path.join(os.homedir() || os.tmpdir(), ".cache");
  return path.join(base, "tonone", "jev");
}

/**
 * Stable stringify: object keys sorted at every depth so that two structurally
 * identical requests always hash the same regardless of key insertion order.
 */
function canonical(value) {
  if (value === null || value === undefined) return "null";
  const t = typeof value;
  if (t === "number") return isFinite(value) ? JSON.stringify(value) : "null";
  if (t === "boolean" || t === "string") return JSON.stringify(value);
  if (Array.isArray(value)) {
    return "[" + value.map(canonical).join(",") + "]";
  }
  if (t === "object") {
    const keys = Object.keys(value).sort();
    const parts = [];
    for (let i = 0; i < keys.length; i++) {
      if (value[keys[i]] === undefined) continue;
      parts.push(JSON.stringify(keys[i]) + ":" + canonical(value[keys[i]]));
    }
    return "{" + parts.join(",") + "}";
  }
  return "null";
}

/** Content address for any JSON-ish request descriptor. */
function keyFor(descriptor) {
  try {
    return crypto
      .createHash("sha256")
      .update(canonical(descriptor))
      .digest("hex");
  } catch {
    return null;
  }
}

function entryPath(key) {
  if (typeof key !== "string" || !/^[0-9a-f]{64}$/.test(key)) return null;
  return path.join(cacheDir(), key.slice(0, 2), key + ".json");
}

function unlinkQuiet(file) {
  try {
    fs.unlinkSync(file);
  } catch {}
}

/**
 * Read an entry. Returns null on miss, expiry, corruption, or any I/O error.
 * Corrupt and expired entries are removed opportunistically; failing to remove
 * one is not an error either.
 */
function get(key, ttlMs) {
  const file = entryPath(key);
  if (!file) return null;
  let raw;
  try {
    raw = fs.readFileSync(file, "utf8");
  } catch {
    return null; // miss, unreadable, or gone
  }
  let entry;
  try {
    entry = JSON.parse(raw);
  } catch {
    unlinkQuiet(file); // corrupt or half-written by a non-atomic writer
    return null;
  }
  if (
    !entry ||
    typeof entry !== "object" ||
    entry.v !== SCHEMA ||
    typeof entry.createdAt !== "number" ||
    !isFinite(entry.createdAt) ||
    !("value" in entry)
  ) {
    unlinkQuiet(file);
    return null;
  }
  const ttl = typeof ttlMs === "number" && ttlMs > 0 ? ttlMs : TTL_MS;
  const age = Date.now() - entry.createdAt;
  // A negative age means a clock jump, not a valid entry.
  if (age < 0 || age > ttl) {
    unlinkQuiet(file);
    return null;
  }
  return entry.value;
}

/**
 * Write an entry atomically. Returns true when the value is durably in place,
 * false when anything at all went wrong (read-only home, full disk, bad key).
 */
function set(key, value) {
  const file = entryPath(key);
  if (!file) return false;
  const dir = path.dirname(file);
  const tmp = path.join(
    dir,
    "." +
      path.basename(file) +
      "." +
      process.pid +
      "." +
      crypto.randomBytes(6).toString("hex") +
      ".tmp",
  );
  try {
    fs.mkdirSync(dir, { recursive: true });
    const entry = {
      v: SCHEMA,
      createdAt: Date.now(),
      key: key,
      value: value,
    };
    fs.writeFileSync(tmp, JSON.stringify(entry), { mode: 0o600 });
    // rename(2) within one directory is atomic: concurrent writers of the same
    // key simply produce last-writer-wins, and no reader ever sees a partial file.
    fs.renameSync(tmp, file);
    return true;
  } catch {
    unlinkQuiet(tmp);
    return false;
  }
}

/**
 * Delete every expired entry. Returns the number removed. Never throws; a
 * directory it cannot read is skipped.
 */
function purge(ttlMs) {
  const root = cacheDir();
  const ttl = typeof ttlMs === "number" && ttlMs > 0 ? ttlMs : TTL_MS;
  let removed = 0;
  let shards;
  try {
    shards = fs.readdirSync(root);
  } catch {
    return 0;
  }
  for (let i = 0; i < shards.length; i++) {
    const shardDir = path.join(root, shards[i]);
    let files;
    try {
      files = fs.readdirSync(shardDir);
    } catch {
      continue;
    }
    for (let j = 0; j < files.length; j++) {
      const file = path.join(shardDir, files[j]);
      try {
        const stat = fs.statSync(file);
        if (Date.now() - stat.mtimeMs > ttl) {
          fs.unlinkSync(file);
          removed++;
        }
      } catch {}
    }
  }
  return removed;
}

module.exports = {
  get: get,
  set: set,
  purge: purge,
  keyFor: keyFor,
  canonical: canonical,
  cacheDir: cacheDir,
  entryPath: entryPath,
  TTL_MS: TTL_MS,
  SCHEMA: SCHEMA,
};
