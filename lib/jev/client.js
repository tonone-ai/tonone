"use strict";

/**
 * lib/jev/client.js — the shared Jev decision layer for tonone agents.
 *
 * Four primitives, one contract:
 *
 *   noul(state, question, opts)            -> yes/no with a probability
 *   choice(state, question, options, opts) -> one of N with a distribution
 *   score(state, question, levels, opts)   -> weighted position on a rubric
 *   batch(state, questions, opts)          -> many named questions, ONE request
 *
 * All four are async and all four ALWAYS resolve. There is no error path a
 * caller has to handle: no credentials, no network, a 500, a malformed body or
 * an empty option list all degrade to the local scorer and report how the
 * answer was reached in `source`:
 *
 *   "jev"      — answered by the hosted decision model
 *   "local"    — answered by lib/jev/local.js because no key was configured
 *   "fallback" — a key was configured, the call failed, local answered instead
 *
 * Credentials are opt-in and are read from the environment only. Nothing here
 * ever prompts, ever writes a key anywhere, or ever makes the network a
 * requirement. With no key set the module performs zero network I/O.
 *
 * Provider resolution order:
 *   1. JEV_API_KEY or TYPESAFE_API_KEY -> api.typesafe.ai/v1/systemone (jev-latest)
 *   2. OPENROUTER_API_KEY -> openrouter.ai/api/alpha/decisions (typesafe/jev-1.13)
 *   3. neither -> lib/jev/local.js
 *
 * TONONE_JEV_OFFLINE=1 forces step 3 even when a key is present.
 */

const http = require("http");
const https = require("https");
const { URL } = require("url");

const local = require("./local");
const cache = require("./cache");

// ── Provider configuration ──────────────────────────────────────────────────

const PROVIDERS = {
  typesafe: {
    name: "typesafe",
    endpoint: "https://api.typesafe.ai/v1/systemone",
    model: "jev-latest",
  },
  openrouter: {
    name: "openrouter",
    endpoint: "https://openrouter.ai/api/alpha/decisions",
    model: "typesafe/jev-1.13",
  },
};

const DEFAULT_TIMEOUT_MS = 8000;
const DEFAULT_RETRIES = 1;
const RETRY_DELAY_MS = 200;
const RETRYABLE_STATUS = new Set([429, 500, 502, 503, 504, 520, 529]);

// The API caps these; exceeding them is a 4xx, so clamp instead of failing.
const MAX_CHOICE_OPTIONS = 255;
const MAX_SCORE_LEVELS = 10;

function truthy(value) {
  if (!value) return false;
  const v = String(value).trim().toLowerCase();
  return v !== "" && v !== "0" && v !== "false" && v !== "no";
}

/**
 * Resolve the provider from the environment. Returns null when the local
 * scorer should answer. Never throws, never prompts.
 */
function resolveProvider(env) {
  const e = env || process.env;
  try {
    if (truthy(e.TONONE_JEV_OFFLINE)) return null;
    const typesafeKey = e.JEV_API_KEY || e.TYPESAFE_API_KEY;
    if (typesafeKey) {
      return {
        name: "typesafe",
        endpoint: e.TONONE_JEV_ENDPOINT || PROVIDERS.typesafe.endpoint,
        model: e.TONONE_JEV_MODEL || PROVIDERS.typesafe.model,
        key: typesafeKey,
      };
    }
    if (e.OPENROUTER_API_KEY) {
      return {
        name: "openrouter",
        endpoint: e.TONONE_JEV_ENDPOINT || PROVIDERS.openrouter.endpoint,
        model: e.TONONE_JEV_MODEL || PROVIDERS.openrouter.model,
        key: e.OPENROUTER_API_KEY,
      };
    }
    return null;
  } catch {
    return null;
  }
}

// ── Question specs ──────────────────────────────────────────────────────────

/**
 * A question spec is the portable description of one decision:
 *
 *   { type: "noul",   question: "...", criteria?: { true: "...", false: "..." } }
 *   { type: "choice", question: "...", options: ["a","b"] | { a: "desc", ... } }
 *   { type: "score",  question: "...", levels: ["low", "mid", "high"] }
 *
 * `question` may be a string or an object (the API accepts structured
 * instructions, and structured criteria are the single biggest accuracy lever).
 */
function normalizeSpec(spec) {
  if (!spec || typeof spec !== "object") return null;
  const type = String(spec.type || "").toLowerCase();
  const question =
    spec.question !== undefined ? spec.question : spec.instructions;

  if (type === "noul") {
    return {
      type: "noul",
      question: question,
      criteria: spec.criteria || null,
    };
  }
  if (type === "choice") {
    const norm = local.normalizeOptions(spec.options);
    return {
      type: "choice",
      question: question,
      options: spec.options,
      keys: norm.keys.slice(0, MAX_CHOICE_OPTIONS),
      texts: norm.texts.slice(0, MAX_CHOICE_OPTIONS),
    };
  }
  if (type === "score") {
    const levels = Array.isArray(spec.levels)
      ? spec.levels.slice(0, MAX_SCORE_LEVELS)
      : [];
    return { type: "score", question: question, levels: levels };
  }
  return null;
}

/** Build the API `questions` entry for one normalized spec. */
function apiQuestion(spec) {
  if (spec.type === "noul") {
    const q = { type: "noul", instructions: spec.question };
    if (spec.criteria && typeof spec.criteria === "object") {
      q.criteria = {
        true:
          spec.criteria.true !== undefined
            ? spec.criteria.true
            : "The statement holds for this state.",
        false:
          spec.criteria.false !== undefined
            ? spec.criteria.false
            : "The statement does not hold for this state.",
      };
    }
    return q;
  }
  if (spec.type === "choice") {
    const criteria = {};
    if (
      spec.options &&
      !Array.isArray(spec.options) &&
      typeof spec.options === "object"
    ) {
      for (let i = 0; i < spec.keys.length; i++) {
        criteria[spec.keys[i]] = spec.options[spec.keys[i]];
      }
    } else {
      for (let i = 0; i < spec.keys.length; i++) {
        criteria[spec.keys[i]] = spec.texts[i];
      }
    }
    return { type: "choice", instructions: spec.question, criteria: criteria };
  }
  return {
    type: "score",
    instructions: spec.question,
    criteria: spec.levels.map((l) =>
      typeof l === "string" ? l : local.textOf(l),
    ),
  };
}

/** Answer the spec with the local scorer. */
function answerLocally(state, spec, source) {
  let result;
  if (spec.type === "noul") {
    result = local.localNoul(state, spec.question, spec.criteria);
  } else if (spec.type === "choice") {
    result = local.localChoice(state, spec.question, spec.options);
  } else {
    result = local.localScore(state, spec.question, spec.levels);
  }
  if (source) result.source = source;
  return result;
}

/**
 * Convert one API answer into the module's own result shape.
 * Returns null when the payload is not usable, which sends the caller to the
 * local fallback rather than to an exception.
 */
function fromApiAnswer(answer, spec) {
  if (!answer || typeof answer !== "object") return null;

  if (spec.type === "noul") {
    const p = answer.noul;
    if (typeof p !== "number" || !isFinite(p) || p < 0 || p > 1) return null;
    return {
      type: "noul",
      answer: p >= 0.5,
      probability: p,
      // noul returns no confidence of its own: distance from a coin flip is
      // the only concentration the single probability can express.
      confidence: Math.round(Math.abs(p - 0.5) * 2 * 1000) / 1000,
      source: "jev",
    };
  }

  if (spec.type === "choice") {
    const winner = answer.choice;
    if (typeof winner !== "string" || winner === "") return null;
    if (spec.keys.length && spec.keys.indexOf(winner) === -1) return null;
    return {
      type: "choice",
      answer: winner,
      confidence: typeof answer.confidence === "number" ? answer.confidence : 0,
      probabilities:
        answer.probabilities && typeof answer.probabilities === "object"
          ? answer.probabilities
          : {},
      source: "jev",
    };
  }

  const value = answer.score;
  if (typeof value !== "number" || !isFinite(value)) return null;
  return {
    type: "score",
    answer: value,
    confidence: typeof answer.confidence === "number" ? answer.confidence : 0,
    probabilities:
      answer.probabilities && typeof answer.probabilities === "object"
        ? answer.probabilities
        : {},
    legend:
      answer.legend && typeof answer.legend === "object" ? answer.legend : {},
    source: "jev",
  };
}

// ── Transport ───────────────────────────────────────────────────────────────

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * One POST. Resolves to { ok, status, body } and never rejects: transport
 * errors come back as { ok: false, error }.
 */
function postJson(endpoint, headers, payload, timeoutMs) {
  return new Promise((resolve) => {
    let url;
    try {
      url = new URL(endpoint);
    } catch {
      resolve({ ok: false, error: "invalid endpoint" });
      return;
    }
    const transport = url.protocol === "http:" ? http : https;
    const data = Buffer.from(JSON.stringify(payload), "utf8");
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      resolve(value);
    };

    let req;
    try {
      req = transport.request(
        {
          protocol: url.protocol,
          hostname: url.hostname,
          port: url.port || (url.protocol === "http:" ? 80 : 443),
          path: url.pathname + url.search,
          method: "POST",
          headers: Object.assign(
            {
              "Content-Type": "application/json",
              "Content-Length": data.length,
              Accept: "application/json",
            },
            headers,
          ),
          timeout: timeoutMs,
        },
        (res) => {
          let body = "";
          res.setEncoding("utf8");
          res.on("data", (chunk) => {
            // Guard against an endpoint that streams forever.
            if (body.length < 4 * 1024 * 1024) body += chunk;
          });
          res.on("end", () => {
            finish({ ok: true, status: res.statusCode || 0, body: body });
          });
          res.on("error", () => finish({ ok: false, error: "response error" }));
        },
      );
    } catch {
      finish({ ok: false, error: "request failed" });
      return;
    }

    req.on("error", (err) => {
      finish({ ok: false, error: (err && err.code) || "network error" });
    });
    req.on("timeout", () => {
      try {
        req.destroy();
      } catch {}
      finish({ ok: false, error: "timeout" });
    });
    try {
      req.write(data);
      req.end();
    } catch {
      finish({ ok: false, error: "write failed" });
    }
  });
}

/**
 * Call the provider with retries for the transient statuses only.
 * Resolves to { body } on success or { error } on any failure.
 */
async function callProvider(provider, payload, opts) {
  const timeoutMs = opts.timeoutMs;
  const retries = opts.retries;
  const headers = { Authorization: "Bearer " + provider.key };
  if (provider.name === "openrouter") {
    headers["HTTP-Referer"] = "https://github.com/tonone-ai/tonone";
    headers["X-Title"] = "tonone";
  }

  let lastError = "unknown error";
  for (let attempt = 0; attempt <= retries; attempt++) {
    const res = await postJson(provider.endpoint, headers, payload, timeoutMs);
    if (!res.ok) {
      lastError = res.error || "network error";
      if (attempt < retries) {
        await sleep(RETRY_DELAY_MS);
        continue;
      }
      break;
    }
    if (res.status >= 200 && res.status < 300) {
      try {
        const parsed = JSON.parse(res.body);
        if (!parsed || typeof parsed !== "object") {
          return { error: "malformed response" };
        }
        return { body: parsed };
      } catch {
        return { error: "unparseable response" };
      }
    }
    lastError = "http " + res.status;
    if (RETRYABLE_STATUS.has(res.status) && attempt < retries) {
      await sleep(RETRY_DELAY_MS);
      continue;
    }
    break;
  }
  return { error: lastError };
}

// ── Core batch path ─────────────────────────────────────────────────────────

function resolveOptions(opts) {
  const o = opts && typeof opts === "object" ? opts : {};
  const envTimeout = parseInt(process.env.TONONE_JEV_TIMEOUT_MS || "", 10);
  return {
    timeoutMs:
      typeof o.timeoutMs === "number" && o.timeoutMs > 0
        ? o.timeoutMs
        : isFinite(envTimeout) && envTimeout > 0
          ? envTimeout
          : DEFAULT_TIMEOUT_MS,
    retries:
      typeof o.retries === "number" && o.retries >= 0
        ? o.retries
        : DEFAULT_RETRIES,
    cache: o.cache === false ? false : true,
    env: o.env || process.env,
    sessionId: o.sessionId || null,
    provider: o.provider || null, // injected for tests
  };
}

/**
 * Send several named questions about one state in a single request.
 *
 * `questions` is { name: spec }. Every name in the input appears in the output,
 * whatever happened. Batching matters: one call carries the state once, where
 * N sequential calls re-send it N times.
 *
 * Resolves to:
 *   { answers: { name: result }, source, provider, cached, usage, error }
 * where `source` is the weakest source among the answers, so a caller can gate
 * on the batch as a whole.
 */
async function batch(state, questions, opts) {
  const options = resolveOptions(opts);
  const specs = {};
  const names = [];

  const input = questions && typeof questions === "object" ? questions : {};
  for (const name of Object.keys(input)) {
    const spec = normalizeSpec(input[name]);
    if (spec) {
      specs[name] = spec;
      names.push(name);
    }
  }

  if (names.length === 0) {
    return {
      answers: {},
      source: "local",
      provider: null,
      cached: false,
      usage: null,
      error: "no valid questions",
    };
  }

  // Specs the API cannot answer at all (an empty option list is a 4xx there,
  // and a degenerate one needs no model) stay local and are never sent.
  const sendable = names.filter((name) => {
    const s = specs[name];
    if (s.type === "choice") return s.keys.length >= 2;
    if (s.type === "score") return s.levels.length >= 2;
    return true;
  });

  const provider = options.provider || resolveProvider(options.env);
  const answers = {};
  let cached = false;
  let usage = null;
  let error = null;

  // Nothing to send: either no credentials, or every question is degenerate
  // (an empty option list is a 4xx at the API and needs no model here).
  if (!provider || sendable.length === 0) {
    for (const name of names) answers[name] = answerLocally(state, specs[name]);
    return {
      answers: answers,
      source: "local",
      provider: null,
      cached: false,
      usage: null,
      error: null,
    };
  }

  const payload = { model: provider.model, state: state, questions: {} };
  for (const name of sendable)
    payload.questions[name] = apiQuestion(specs[name]);
  if (options.sessionId)
    payload.session_id = String(options.sessionId).slice(0, 256);

  let body = null;
  const cacheKey = options.cache
    ? cache.keyFor({ endpoint: provider.endpoint, payload: payload })
    : null;
  if (cacheKey) {
    const hit = cache.get(cacheKey);
    if (hit) {
      body = hit;
      cached = true;
    }
  }

  if (!body) {
    const res = await callProvider(provider, payload, options);
    if (res.body) {
      body = res.body;
      if (cacheKey) cache.set(cacheKey, body);
    } else {
      error = res.error;
    }
  }

  const apiAnswers =
    body && body.answers && typeof body.answers === "object"
      ? body.answers
      : {};
  if (body && !Object.keys(apiAnswers).length && !error) {
    error = "malformed response";
  }
  if (body && body.usage && typeof body.usage === "object") usage = body.usage;

  for (const name of names) {
    const spec = specs[name];
    if (sendable.indexOf(name) === -1) {
      answers[name] = answerLocally(state, spec);
      continue;
    }
    const parsed = body ? fromApiAnswer(apiAnswers[name], spec) : null;
    answers[name] = parsed || answerLocally(state, spec, "fallback");
  }

  // The batch is only as trustworthy as its weakest answer.
  let source = "jev";
  for (const name of names) {
    const s = answers[name].source;
    if (s === "fallback") {
      source = "fallback";
      break;
    }
    if (s === "local") source = source === "jev" ? "local" : source;
  }

  return {
    answers: answers,
    source: source,
    provider: provider.name,
    cached: cached,
    usage: usage,
    model: body && typeof body.model === "string" ? body.model : null,
    error: error,
  };
}

/** Run a single-question batch and unwrap it. */
async function single(state, spec, opts) {
  try {
    const result = await batch(state, { q: spec }, opts);
    const answer =
      result.answers.q || answerLocally(state, normalizeSpec(spec));
    if (result.cached) answer.cached = true;
    if (result.provider && answer.source === "jev")
      answer.provider = result.provider;
    return answer;
  } catch {
    // Belt and braces: a primitive must never reject.
    const normalized = normalizeSpec(spec);
    return normalized
      ? answerLocally(state, normalized, "fallback")
      : {
          type: spec && spec.type,
          answer: null,
          confidence: 0,
          source: "fallback",
        };
  }
}

// ── Public primitives ───────────────────────────────────────────────────────

/**
 * Yes/no gate. Resolves to
 *   { type:"noul", answer:<boolean>, probability:<0..1>, confidence, source }
 *
 * `answer` applies a 0.5 threshold to `probability`; read `probability` and
 * pick your own threshold when the decision has teeth.
 * Pass opts.criteria = { true: "...", false: "..." } — it is what makes both
 * the hosted model and the local scorer accurate.
 */
function noul(state, question, opts) {
  const options = opts && typeof opts === "object" ? opts : {};
  return single(
    state,
    { type: "noul", question: question, criteria: options.criteria || null },
    options,
  );
}

/**
 * Pick one of N. `options` is ["a","b"] or { key: "description" }.
 * Resolves to { type:"choice", answer:<key|null>, confidence, probabilities, source }.
 * An empty option list resolves to answer null with confidence 0 — it never throws.
 */
function choice(state, question, options, opts) {
  return single(
    state,
    { type: "choice", question: question, options: options },
    opts,
  );
}

/**
 * Grade on an ordered rubric. `levels` is an ordered array; index 0 is the
 * bottom of the scale. Resolves to
 *   { type:"score", answer:<weighted mean>, confidence, probabilities, legend, source }
 * `answer` lands between levels on purpose — 1.4 and 1.6 are different answers.
 */
function score(state, question, levels, opts) {
  return single(
    state,
    { type: "score", question: question, levels: levels },
    opts,
  );
}

module.exports = {
  noul: noul,
  choice: choice,
  score: score,
  batch: batch,
  resolveProvider: resolveProvider,
  normalizeSpec: normalizeSpec,
  PROVIDERS: PROVIDERS,
  DEFAULT_TIMEOUT_MS: DEFAULT_TIMEOUT_MS,
};
