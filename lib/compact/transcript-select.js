"use strict";

/**
 * lib/compact/transcript-select.js — verbatim transcript selection.
 *
 * Decides which tool calls and tool results in a Claude Code transcript are
 * still worth carrying, and reports that decision as a plan. It never
 * summarizes, never paraphrases and never rewrites: every entry it keeps is
 * kept byte-for-byte, and every entry it drops is dropped whole. The only
 * lossy operation it will perform is a middle elision on a very large result,
 * and both the head and the tail of that elision are exact substrings of the
 * original.
 *
 * Three rules, and they are the whole design:
 *
 * 1. **Keeping too much is the cheap mistake.** Losing a file path, an exact
 *    error string or a stated constraint is expensive and silent. Every rule
 *    here is written so that the failure mode is "we kept something we did not
 *    need", never "we lost something we did".
 * 2. **Nothing here throws and nothing here requires credentials.** The
 *    deterministic heuristic is the primary path and always runs with zero
 *    network I/O. lib/jev is consulted only when a provider is already
 *    configured in the environment, and lib/jev itself degrades to a local
 *    scorer with no key.
 * 3. **User and assistant prose is never touched.** Only `tool_use` /
 *    `tool_result` pairs are candidates. Text, thinking, system records,
 *    attachments and every other record type are copied through untouched.
 *
 * Jev is a veto, not a proposer. The heuristic decides; a hosted Jev answer
 * may move an entry *toward keeping* freely, and may move a `keep` down to
 * `truncate` — but nothing Jev says can turn a `keep` into a `drop`. A
 * confidently wrong decision model can therefore cost tokens. It cannot cost
 * information. Non-hosted answers (`source !== "jev"`) are ignored entirely,
 * per lib/jev/README.md § Reading `confidence`.
 *
 * API:
 *   parse(text)                  -> entries[]            (never throws)
 *   buildExchanges(entries)      -> exchanges[]
 *   planSync(entries, opts)      -> plan                 (deterministic, no I/O)
 *   plan(entries, opts)          -> Promise<plan>        (adds the Jev veto)
 *   emit(entries, plan)          -> string               (filtered JSONL)
 *   render(plan)                 -> string               (human summary)
 */

const MODULE_VERSION = 1;

// docs/output-kit.md: CLI output must not exceed 40 lines.
const RENDER_MAX_LINES = 40;

// ── Tunables ────────────────────────────────────────────────────────────────

const DEFAULTS = {
  // Exchanges this close to the end of the transcript are always kept. Recency
  // is the single most reliable proxy for "the model is still using this".
  keepRecent: 30,
  // A result smaller than this is never worth touching: the bookkeeping costs
  // more than the tokens saved, and small results are where exact strings live.
  smallBytes: 2000,
  // Above this, an old result with no later supersession gets a middle elision.
  hugeBytes: 20000,
  // Verbatim head and tail retained by a truncation.
  keepHeadBytes: 1200,
  keepTailBytes: 600,
  // Bounds on the optional Jev call.
  maxJevQuestions: 80,
  maxDigestChars: 60000,
  perEntryDigestChars: 500,
  jevTimeoutMs: 8000,
};

// Tools whose result records what changed on disk. Never dropped: they are the
// audit trail of the session's own edits.
const MUTATING_TOOLS = new Set([
  "Write",
  "Edit",
  "MultiEdit",
  "NotebookEdit",
  "ArtifactData",
  "Artifact",
]);

// Tools whose result is a snapshot of something that can be looked at again.
// Only these are eligible for a full drop, and only when superseded.
const READ_SHAPED_TOOLS = new Set([
  "Read",
  "Bash",
  "Glob",
  "Grep",
  "LS",
  "WebFetch",
  "WebSearch",
  "NotebookRead",
  "ListAgents",
  "ToolSearch",
]);

// ── Parsing ─────────────────────────────────────────────────────────────────

/**
 * Parse a transcript. Input is either JSONL text or an array of already
 * parsed records. Unparseable lines are preserved as opaque entries so that
 * emit() can copy them through byte-for-byte.
 *
 * Returns entries: { i, raw, json, type, role, blocks }
 */
function parse(input) {
  const entries = [];
  try {
    if (Array.isArray(input)) {
      input.forEach((rec, i) => entries.push(makeEntry(i, null, rec)));
      return entries;
    }
    const text = String(input == null ? "" : input);
    const lines = text.split("\n");
    for (let i = 0; i < lines.length; i++) {
      const raw = lines[i];
      if (raw.trim() === "") continue;
      let json = null;
      try {
        json = JSON.parse(raw);
      } catch {
        json = null;
      }
      entries.push(makeEntry(entries.length, raw, json));
    }
  } catch {
    return entries;
  }
  return entries;
}

function makeEntry(i, raw, json) {
  const rec = json && typeof json === "object" ? json : null;
  const msg =
    rec && rec.message && typeof rec.message === "object" ? rec.message : null;
  const content = msg ? msg.content : null;
  const blocks = Array.isArray(content)
    ? content.filter((b) => b && typeof b === "object")
    : [];
  return {
    i: i,
    raw: raw,
    json: rec,
    type: rec ? String(rec.type || "") : "",
    role: msg ? String(msg.role || "") : "",
    blocks: blocks,
  };
}

// ── Exchange building ───────────────────────────────────────────────────────

/**
 * Pair every tool_use with its tool_result by tool_use_id. An unpaired
 * tool_use (still running, or the transcript ends mid-call) yields an exchange
 * with no result, which is always kept.
 */
function buildExchanges(entries) {
  const byId = new Map();
  const order = [];
  for (const e of entries) {
    for (const b of e.blocks) {
      if (b.type === "tool_use" && typeof b.id === "string") {
        if (byId.has(b.id)) continue;
        const ex = {
          id: b.id,
          useEntry: e.i,
          resultEntry: null,
          name: String(b.name || "unknown"),
          input: b.input && typeof b.input === "object" ? b.input : {},
          text: null,
          bytes: 0,
          inlineBytes: 0,
          sidecarBytes: 0,
          hasSidecar: false,
          isError: false,
          idx: order.length,
        };
        ex.target = targetOf(ex.name, ex.input);
        byId.set(b.id, ex);
        order.push(ex);
      } else if (
        b.type === "tool_result" &&
        typeof b.tool_use_id === "string"
      ) {
        const ex = byId.get(b.tool_use_id);
        if (!ex || ex.resultEntry !== null) continue;
        ex.resultEntry = e.i;
        ex.text = resultText(b.content);
        ex.inlineBytes = byteLength(ex.text);
        const side = sidecarOf(e);
        ex.hasSidecar = side !== null;
        ex.sidecarBytes = side ? side.bytes : 0;
        ex.bytes = ex.inlineBytes + ex.sidecarBytes;
        ex.isError = b.is_error === true;
      }
    }
  }
  return order;
}

function resultText(content) {
  try {
    if (typeof content === "string") return content;
    if (Array.isArray(content)) {
      const parts = [];
      for (const b of content) {
        if (!b || typeof b !== "object") continue;
        if (typeof b.text === "string") parts.push(b.text);
      }
      return parts.join("\n");
    }
    if (content == null) return "";
    return JSON.stringify(content);
  } catch {
    return "";
  }
}

/**
 * Claude Code writes a tool result twice: once as a `tool_result` block inside
 * `message.content`, and again as a structured top-level `toolUseResult` field
 * on the same record. On real transcripts the sidecar is the larger of the two
 * — on a 2.3 MB session here, 609 KB of `toolUseResult` against 238 KB of
 * inline blocks. Measuring or rewriting only the inline copy would report
 * savings against a tenth of the file and leave every "dropped" payload sitting
 * in the emitted output verbatim.
 *
 * The sidecar belongs to the record's tool_result block. A record carrying more
 * than one block gives no way to say which, so it is left alone and unmeasured:
 * the failure mode is "we kept something", never "we lost something".
 *
 * Returns { value, bytes } or null.
 */
function sidecarOf(entry) {
  try {
    if (!entry || !entry.json || typeof entry.json !== "object") return null;
    if (!Object.prototype.hasOwnProperty.call(entry.json, "toolUseResult"))
      return null;
    const v = entry.json.toolUseResult;
    if (v === null || v === undefined) return null;
    let n = 0;
    for (const b of entry.blocks) {
      if (b && b.type === "tool_result") n++;
    }
    if (n !== 1) return null;
    const text = typeof v === "string" ? v : JSON.stringify(v);
    if (typeof text !== "string") return null;
    return { value: v, bytes: byteLength(text) };
  } catch {
    return null;
  }
}

function byteLength(s) {
  try {
    return Buffer.byteLength(String(s || ""), "utf8");
  } catch {
    return String(s || "").length;
  }
}

// Input fields that are a human label for the call rather than part of what it
// looked at. Everything else narrows the view and therefore narrows the target.
const TARGET_IGNORED_INPUT_FIELDS = new Set(["description"]);

// Longest target fragment kept literally before it is bounded by a hash.
const TARGET_MAX_CHARS = 400;

/**
 * A stable identity for "what this call looked at". Two calls with the same
 * target are looking at the same thing, so the later one supersedes the
 * earlier one.
 *
 * The identity is the primary subject of the call (a path, a command, a URL, a
 * pattern) *plus every other input field*. That second half is not decoration:
 * `Read(file_path, offset: 1, limit: 100)` and `Read(file_path, offset: 900)`
 * name the same file and return disjoint regions of it, and so do
 * `Grep(output_mode: "content")` versus `Grep(output_mode: "files_with_matches")`
 * and two `WebFetch` calls on one URL with different prompts. Folding those
 * onto one target lets a later partial read supersede — and drop — an earlier
 * one that holds bytes the later one never saw, which is exactly the loss this
 * module promises never to cause.
 */
function targetOf(name, input) {
  try {
    if (!input || typeof input !== "object") return "";
    const primary = primaryTarget(name, input);
    const rest = {};
    let restCount = 0;
    for (const k of Object.keys(input)) {
      if (primary.consumed.indexOf(k) !== -1) continue;
      if (TARGET_IGNORED_INPUT_FIELDS.has(k)) continue;
      const v = input[k];
      if (v === undefined || v === null || v === "") continue;
      rest[k] = v;
      restCount++;
    }
    if (restCount === 0) return primary.key;
    return (
      primary.key + "\u0002" + bound(canonicalize(rest, 0), TARGET_MAX_CHARS)
    );
  } catch {
    return "";
  }
}

/** The subject of the call, and which input fields that subject consumed. */
function primaryTarget(name, input) {
  if (typeof input.file_path === "string") {
    return { key: input.file_path, consumed: ["file_path"] };
  }
  if (typeof input.notebook_path === "string") {
    return { key: input.notebook_path, consumed: ["notebook_path"] };
  }
  if (name === "Bash" && typeof input.command === "string") {
    return {
      key: input.command.replace(/\s+/g, " ").trim(),
      consumed: ["command"],
    };
  }
  if (name === "Grep" || name === "Glob") {
    const pat = typeof input.pattern === "string" ? input.pattern : "";
    const p = typeof input.path === "string" ? input.path : "";
    const g = typeof input.glob === "string" ? input.glob : "";
    return {
      key: pat + "\u0001" + p + "\u0001" + g,
      consumed: ["pattern", "path", "glob"],
    };
  }
  if (typeof input.url === "string")
    return { key: input.url, consumed: ["url"] };
  if (typeof input.query === "string")
    return { key: input.query, consumed: ["query"] };
  return { key: "", consumed: [] };
}

/** Key-order-independent serialization, depth-bounded so a cycle terminates. */
function canonicalize(v, depth) {
  if (depth > 6) return '"…"';
  if (v === null) return "null";
  const t = typeof v;
  if (t === "number") return isFinite(v) ? String(v) : "null";
  if (t === "boolean") return String(v);
  if (t === "string") return JSON.stringify(v);
  if (Array.isArray(v))
    return "[" + v.map((x) => canonicalize(x, depth + 1)).join(",") + "]";
  if (t === "object") {
    const keys = Object.keys(v).sort();
    const parts = [];
    for (const k of keys) {
      const child = canonicalize(v[k], depth + 1);
      if (child === undefined) continue;
      parts.push(JSON.stringify(k) + ":" + child);
    }
    return "{" + parts.join(",") + "}";
  }
  return "null";
}

/**
 * Bound a target fragment without letting two different inputs collide. A bare
 * slice would make any two calls that agree on their first `max` characters
 * supersede each other, so the tail is replaced by the length and a hash.
 */
function bound(s, max) {
  const str = String(s);
  if (str.length <= max) return str;
  return str.slice(0, max) + "\u0003" + str.length + "\u0003" + fnv1a(str);
}

function fnv1a(s) {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i) & 0xff;
    h = (h + ((h << 1) + (h << 4) + (h << 7) + (h << 8) + (h << 24))) >>> 0;
    h ^= s.charCodeAt(i) >>> 8;
    h = h >>> 0;
  }
  return h.toString(16);
}

// ── The deterministic heuristic ─────────────────────────────────────────────

/**
 * Decide an action for every exchange with no network I/O and no credentials.
 * This is the default path and it always runs; the Jev layer only adjusts what
 * this produced.
 *
 * Actions: "keep" | "truncate" | "drop".
 */
function planSync(entries, opts) {
  const o = withDefaults(opts);
  const exchanges = buildExchanges(entries);
  const total = exchanges.length;

  // Index the last occurrence of each read-shaped target, so an earlier call
  // can tell whether a later one looked at exactly the same thing.
  const lastSeen = new Map();
  for (const ex of exchanges) {
    if (!READ_SHAPED_TOOLS.has(ex.name)) continue;
    if (ex.resultEntry === null || ex.isError) continue;
    lastSeen.set(ex.name + "\u0000" + ex.target, ex.idx);
  }

  const items = [];
  for (const ex of exchanges) {
    const fromEnd = total - 1 - ex.idx;
    const item = {
      idx: ex.idx,
      id: ex.id,
      name: ex.name,
      target: ex.target,
      useEntry: ex.useEntry,
      resultEntry: ex.resultEntry,
      bytes: ex.bytes,
      inlineBytes: ex.inlineBytes,
      sidecarBytes: ex.sidecarBytes,
      hasSidecar: ex.hasSidecar,
      isError: ex.isError,
      fromEnd: fromEnd,
      action: "keep",
      reason: "no-rule-fires",
      supersededBy: null,
      jev: null,
    };

    const supersededBy = lastSeen.get(ex.name + "\u0000" + ex.target);
    if (supersededBy !== undefined && supersededBy > ex.idx) {
      item.supersededBy = supersededBy;
    }

    if (ex.resultEntry === null) {
      item.reason = "unpaired-tool-call";
    } else if (fromEnd < o.keepRecent) {
      item.reason = "recent";
    } else if (ex.isError) {
      item.reason = "error-result";
    } else if (MUTATING_TOOLS.has(ex.name)) {
      item.reason = "mutating-tool";
    } else if (ex.bytes < o.smallBytes) {
      item.reason = "small";
    } else if (item.supersededBy !== null && READ_SHAPED_TOOLS.has(ex.name)) {
      item.action = "drop";
      item.reason = "superseded-by-#" + item.supersededBy;
    } else if (ex.bytes >= o.hugeBytes) {
      item.action = "truncate";
      item.reason = "large-and-old";
    }

    items.push(item);
  }

  return finalize(items, o, "heuristic", null, transcriptBytes(entries));
}

/** Total size of the transcript itself, so "freed" can be stated against it. */
function transcriptBytes(entries) {
  let n = 0;
  try {
    for (const e of entries) {
      const raw =
        e.raw !== null && e.raw !== undefined ? e.raw : safeStringify(e.json);
      n += byteLength(raw) + 1;
    }
  } catch {
    return n;
  }
  return n;
}

function withDefaults(opts) {
  const o = Object.assign({}, DEFAULTS);
  if (opts && typeof opts === "object") {
    for (const k of Object.keys(DEFAULTS)) {
      const v = opts[k];
      if (typeof v === "number" && isFinite(v) && v >= 0) o[k] = v;
    }
  }
  return o;
}

function finalize(items, o, source, jevError, bytesTranscript) {
  let bytesTotal = 0;
  let bytesKept = 0;
  let bytesSidecar = 0;
  const counts = { keep: 0, truncate: 0, drop: 0 };
  for (const it of items) {
    const inline =
      typeof it.inlineBytes === "number" ? it.inlineBytes : it.bytes;
    bytesTotal += it.bytes;
    bytesSidecar += typeof it.sidecarBytes === "number" ? it.sidecarBytes : 0;
    counts[it.action] += 1;
    if (it.action === "keep") bytesKept += it.bytes;
    else if (it.action === "truncate") {
      // A truncation keeps a verbatim head and tail of the inline block. The
      // structured sidecar is a duplicate of that same payload and is replaced
      // by a marker, so none of it survives.
      bytesKept += Math.min(inline, o.keepHeadBytes + o.keepTailBytes);
    }
  }
  const total =
    typeof bytesTranscript === "number" && bytesTranscript >= 0
      ? bytesTranscript
      : 0;
  return {
    version: MODULE_VERSION,
    source: source,
    jevError: jevError,
    options: o,
    items: items,
    totals: {
      exchanges: items.length,
      kept: counts.keep,
      truncated: counts.truncate,
      dropped: counts.drop,
      bytesTotal: bytesTotal,
      bytesInline: bytesTotal - bytesSidecar,
      bytesSidecar: bytesSidecar,
      bytesKept: bytesKept,
      bytesFreed: Math.max(0, bytesTotal - bytesKept),
      bytesTranscript: total,
    },
  };
}

// ── The optional Jev veto ───────────────────────────────────────────────────

/**
 * Deterministic plan first, then one batched Jev request that may adjust it.
 *
 * Monotonicity, which is the safety property of this whole module:
 *   jev says "still needed"     -> drop becomes truncate, truncate becomes keep
 *   jev says "no longer needed" -> keep becomes truncate; a drop stays a drop
 *   jev is unavailable/local    -> the heuristic plan is returned unchanged
 *
 * Nothing Jev can say promotes an entry to `drop`. The worst a wrong answer
 * costs is tokens.
 *
 * opts.jev injects the decision layer (tests). Omit it and lib/jev/client is
 * required lazily; if that require fails, the heuristic plan is returned.
 */
async function plan(entries, opts) {
  const o = withDefaults(opts);
  const base = planSync(entries, o);
  const options = opts && typeof opts === "object" ? opts : {};

  if (options.useJev === false) return base;

  let jev = options.jev;
  if (!jev) {
    try {
      jev = require("../jev/client");
    } catch {
      return finalize(
        base.items,
        o,
        "heuristic",
        "lib/jev unavailable",
        base.totals.bytesTranscript,
      );
    }
  }

  let provider = null;
  try {
    provider = jev.resolveProvider(options.env);
  } catch {
    provider = null;
  }
  if (!provider) {
    return finalize(
      base.items,
      o,
      "heuristic",
      "no Jev provider configured",
      base.totals.bytesTranscript,
    );
  }

  const candidates = base.items
    .filter(
      (it) =>
        it.resultEntry !== null &&
        it.fromEnd >= o.keepRecent &&
        it.bytes >= o.smallBytes,
    )
    .slice(0, o.maxJevQuestions);

  if (candidates.length === 0) {
    return finalize(
      base.items,
      o,
      "heuristic",
      "no entries eligible for review",
      base.totals.bytesTranscript,
    );
  }

  const state = digest(candidates, entries, o);
  const questions = {};
  for (const it of candidates) {
    questions["x" + it.idx] = {
      type: "noul",
      question:
        "Is entry #" +
        it.idx +
        " in the transcript digest still needed for the rest of this session?",
      criteria: {
        true:
          "Entry #" +
          it.idx +
          " holds information that is not recoverable from later entries: an exact error string, a file path, a configuration value, a stated constraint or requirement, a command that must be repeated, or content the assistant has not yet acted on.",
        false:
          "Entry #" +
          it.idx +
          " is superseded by a later entry that looked at the same thing, or is a routine listing, search hit set or bulk file dump whose conclusions already appear in later assistant messages.",
      },
    };
  }

  let result = null;
  try {
    result = await jev.batch(state, questions, {
      timeoutMs: o.jevTimeoutMs,
      sessionId: options.sessionId,
      env: options.env,
    });
  } catch {
    // lib/jev promises never to reject; this is belt and braces.
    result = null;
  }

  if (!result || !result.answers || result.source !== "jev") {
    const why = !result
      ? "Jev call produced no result"
      : "Jev answered from " +
        String(result.source) +
        "; a non-hosted answer is not trusted";
    return finalize(
      base.items,
      o,
      "heuristic",
      why,
      base.totals.bytesTranscript,
    );
  }

  const byIdx = new Map(base.items.map((it) => [it.idx, it]));
  for (const it of candidates) {
    const ans = result.answers["x" + it.idx];
    if (!ans || typeof ans.answer !== "boolean") continue;
    const target = byIdx.get(it.idx);
    if (!target) continue;
    target.jev = {
      needed: ans.answer,
      probability: ans.probability,
      confidence: ans.confidence,
    };
    if (ans.answer === true) {
      // Still needed: move one step toward keeping.
      if (target.action === "drop") {
        target.action = "truncate";
        target.reason = target.reason + " +jev-still-needed";
      } else if (target.action === "truncate") {
        target.action = "keep";
        target.reason = target.reason + " +jev-still-needed";
      }
    } else if (target.action === "keep" && target.reason === "no-rule-fires") {
      // No longer needed: the strongest demotion allowed is a middle elision.
      target.action = "truncate";
      target.reason = "jev-not-needed";
    }
  }

  return finalize(base.items, o, "jev", null, base.totals.bytesTranscript);
}

/**
 * The transcript as bounded prose, for use as a lib/jev `state`. One numbered
 * block per candidate, each capped, and the whole thing capped again.
 */
function digest(candidates, entries, o) {
  const parts = [];
  let used = 0;
  for (const it of candidates) {
    const body = sliceResult(entries, it, o.perEntryDigestChars);
    const block =
      "#" +
      it.idx +
      " tool=" +
      it.name +
      " target=" +
      String(it.target).slice(0, 160) +
      " bytes=" +
      it.bytes +
      " age=" +
      it.fromEnd +
      (it.isError ? " ERROR" : "") +
      "\n" +
      body;
    if (used + block.length > o.maxDigestChars) break;
    used += block.length;
    parts.push(block);
  }
  return parts.join("\n\n");
}

function sliceResult(entries, item, max) {
  try {
    const e = entries[item.resultEntry];
    if (!e) return "";
    for (const b of e.blocks) {
      if (b.type === "tool_result" && b.tool_use_id === item.id) {
        const t = resultText(b.content);
        return t.length > max ? t.slice(0, max) + " ..." : t;
      }
    }
  } catch {
    return "";
  }
  return "";
}

// ── Emission ────────────────────────────────────────────────────────────────

/**
 * Render the plan as a filtered JSONL transcript.
 *
 * Every line that the plan does not touch is written out byte-for-byte from
 * the input, including lines that failed to parse. Only tool_result records
 * whose action is `drop` or `truncate` are re-serialized, and even then the
 * retained text is an exact substring of the original.
 *
 * A rewritten record has its top-level `toolUseResult` sidecar replaced too.
 * That field is Claude Code's structured duplicate of the very payload being
 * dropped, and on real transcripts it is the larger copy: leaving it in place
 * would mean a "dropped" secret is still sitting in the emitted file, and would
 * make the file shrink by far less than the plan reports. Only tools that can
 * be dropped or elided at all are affected, and for those the sidecar carries
 * nothing the inline block does not.
 *
 * This is a preview artifact. Claude Code compacts its in-memory message list,
 * not this file — see docs/adr/0001-verbatim-context-compaction.md.
 */
function emit(entries, planResult) {
  const o = withDefaults(planResult && planResult.options);
  const actions = new Map();
  for (const it of (planResult && planResult.items) || []) {
    if (it.action === "keep" || it.resultEntry === null) continue;
    actions.set(it.resultEntry + "\u0000" + it.id, it);
  }

  const out = [];
  for (const e of entries) {
    let touched = false;
    let sidecarItem = null;
    if (e.json && e.blocks.length > 0) {
      for (const b of e.blocks) {
        if (b.type !== "tool_result" || typeof b.tool_use_id !== "string")
          continue;
        const it = actions.get(e.i + "\u0000" + b.tool_use_id);
        if (!it) continue;
        touched = true;
        sidecarItem = it;
        b.content =
          it.action === "drop"
            ? dropMarker(it)
            : elide(resultText(b.content), it, o);
      }
      // The sidecar is only attributable when the record holds exactly one
      // tool_result block; sidecarOf() enforces that and returns null otherwise,
      // in which case the field is left untouched.
      if (touched && sidecarItem && sidecarOf(e)) {
        e.json.toolUseResult = sidecarMarker(sidecarItem);
      }
    }
    if (!touched) {
      out.push(
        e.raw !== null && e.raw !== undefined ? e.raw : safeStringify(e.json),
      );
    } else {
      out.push(safeStringify(e.json));
    }
  }
  return out.join("\n") + (out.length ? "\n" : "");
}

function dropMarker(it) {
  return (
    "[tonone-compact] dropped " +
    it.bytes +
    " bytes of " +
    it.name +
    " output verbatim (" +
    it.reason +
    "). Target: " +
    String(it.target).slice(0, 200)
  );
}

/**
 * What replaces a rewritten record's `toolUseResult`. It is a duplicate of the
 * payload the tool_result block now carries in dropped or elided form, so the
 * marker states what happened rather than restating any of the content.
 */
function sidecarMarker(it) {
  return {
    tonone_compact: it.action === "drop" ? "dropped" : "elided",
    note:
      "[tonone-compact] " +
      (it.action === "drop" ? "dropped " : "elided ") +
      (typeof it.sidecarBytes === "number" ? it.sidecarBytes : 0) +
      " bytes of duplicated " +
      it.name +
      " output from toolUseResult (" +
      it.reason +
      ")" +
      (it.action === "drop"
        ? ""
        : "; the verbatim head and tail are retained in the tool_result block"),
    bytes: typeof it.sidecarBytes === "number" ? it.sidecarBytes : 0,
    tool: it.name,
    target: String(it.target).slice(0, 200),
  };
}

function elide(text, it, o) {
  const s = String(text || "");
  const head = o.keepHeadBytes;
  const tail = o.keepTailBytes;
  if (s.length <= head + tail) return s;
  const removed = s.length - head - tail;
  return (
    s.slice(0, head) +
    "\n[tonone-compact] elided " +
    removed +
    " characters verbatim from the middle (" +
    it.reason +
    ")\n" +
    s.slice(s.length - tail)
  );
}

function safeStringify(json) {
  try {
    return JSON.stringify(json);
  } catch {
    return "";
  }
}

// ── Rendering ───────────────────────────────────────────────────────────────

function render(planResult) {
  const t = planResult.totals;
  const lines = [];
  lines.push("tonone-compact — transcript selection plan");
  lines.push(
    "  source=" +
      planResult.source +
      (planResult.jevError ? " (" + planResult.jevError + ")" : ""),
  );
  lines.push(
    "  exchanges=" +
      t.exchanges +
      " keep=" +
      t.kept +
      " truncate=" +
      t.truncated +
      " drop=" +
      t.dropped,
  );
  lines.push(
    "  tool-result payload " +
      t.bytesTotal +
      " -> " +
      t.bytesKept +
      " (" +
      pct(t.bytesFreed, t.bytesTotal) +
      " freed; inline " +
      t.bytesInline +
      " + toolUseResult " +
      t.bytesSidecar +
      ")",
  );
  lines.push(
    "  transcript " +
      t.bytesTranscript +
      " bytes — " +
      pct(t.bytesFreed, t.bytesTranscript) +
      " of the file",
  );
  const touched = planResult.items.filter((i) => i.action !== "keep");
  if (touched.length) {
    lines.push("");
    lines.push("  #     action    bytes  tool         reason");
    // docs/output-kit.md caps CLI output at 40 lines, header and footer
    // included. Reserve one line for the overflow notice when it is needed.
    const free = RENDER_MAX_LINES - lines.length;
    const rows = touched.length <= free ? free : Math.max(0, free - 1);
    for (const it of touched.slice(0, rows)) {
      lines.push(
        "  " +
          pad(String(it.idx), 5) +
          pad(it.action, 10) +
          pad(String(it.bytes), 8) +
          pad(it.name, 13) +
          it.reason,
      );
    }
    if (touched.length > rows) {
      lines.push("  ... and " + (touched.length - rows) + " more");
    }
  }
  return lines.join("\n");
}

function pad(s, n) {
  s = String(s);
  return s.length >= n ? s.slice(0, n - 1) + " " : s + " ".repeat(n - s.length);
}

function pct(part, whole) {
  if (!whole) return "0%";
  return Math.round((part / whole) * 100) + "%";
}

// ── CLI ─────────────────────────────────────────────────────────────────────

function parseArgv(argv) {
  const out = { format: "text" };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--json") out.format = "json";
    else if (a === "--text") out.format = "text";
    else if (a === "--emit") out.format = "emit";
    else if (a === "--no-jev") out.useJev = false;
    else if (a.startsWith("--") && a.includes("=")) {
      const k = a.slice(2, a.indexOf("="));
      const v = a.slice(a.indexOf("=") + 1);
      out[camel(k)] = isNaN(Number(v)) ? v : Number(v);
    } else if (a.startsWith("--")) {
      const k = camel(a.slice(2));
      const v = argv[i + 1];
      if (v !== undefined && !v.startsWith("--")) {
        out[k] = isNaN(Number(v)) ? v : Number(v);
        i++;
      } else out[k] = true;
    }
  }
  return out;
}

function camel(s) {
  return String(s).replace(/-([a-z])/g, (_, c) => c.toUpperCase());
}

function readStdin() {
  try {
    return require("fs").readFileSync(0, "utf8");
  } catch {
    return "";
  }
}

function main(argv) {
  const opts = parseArgv(argv);
  let text = "";
  try {
    const src = opts.transcript;
    if (!src || src === "-") text = readStdin();
    else text = require("fs").readFileSync(src, "utf8");
  } catch (err) {
    process.stdout.write(
      JSON.stringify({
        ok: false,
        error: String((err && err.message) || err),
      }) + "\n",
    );
    process.exit(0);
    return;
  }

  const entries = parse(text);
  plan(entries, opts)
    .then((p) => {
      if (opts.format === "json") {
        process.stdout.write(
          JSON.stringify(Object.assign({ ok: true }, p)) + "\n",
        );
      } else if (opts.format === "emit") {
        process.stdout.write(emit(entries, p));
      } else {
        process.stdout.write(render(p) + "\n");
      }
      process.exit(0);
    })
    .catch((err) => {
      process.stdout.write(
        JSON.stringify({
          ok: false,
          error: String((err && err.message) || err),
        }) + "\n",
      );
      process.exit(0);
    });
}

if (require.main === module) main(process.argv.slice(2));

module.exports = {
  parse: parse,
  buildExchanges: buildExchanges,
  planSync: planSync,
  plan: plan,
  emit: emit,
  render: render,
  targetOf: targetOf,
  DEFAULTS: DEFAULTS,
  MUTATING_TOOLS: MUTATING_TOOLS,
  READ_SHAPED_TOOLS: READ_SHAPED_TOOLS,
  MODULE_VERSION: MODULE_VERSION,
};
