"use strict";

/**
 * lib/jev/local.js — the key-free default scorer.
 *
 * This is the path every user gets who has not set a Jev API key, which is
 * expected to be almost all of them. It must never throw, never touch the
 * network, and never require a dependency.
 *
 * Method: TF-IDF vector space over the option texts, cosine similarity against
 * the state text. Unigrams plus adjacent bigrams, crude suffix stemming, a
 * small English stopword list. The option set is the corpus, so IDF measures
 * which words actually discriminate between the options the caller supplied —
 * words shared by every option carry almost no weight, which is the property
 * that makes this usable for routing and classification.
 *
 * ── Accuracy ceiling (read this before trusting a number) ──────────────────
 *
 * This is lexical overlap, not comprehension. Concretely, it is good at:
 *
 *   - Routing when the option labels/descriptions share vocabulary with the
 *     state ("billing/refund/invoice" vs "login/password/permissions").
 *   - Ranking a shortlist where one option is topically obvious.
 *   - Producing a stable, reproducible answer for the same input.
 *
 * and it is bad at, or simply blind to:
 *
 *   - Negation. "no errors in the log" and "errors in the log" score alike.
 *   - Synonyms and paraphrase with no shared stem ("cannot sign in" vs
 *     "authentication failure") — there are no embeddings here.
 *   - Any judgement that is not present in the words: intent, sentiment,
 *     severity, truth. `noul` without criteria is the worst case, see below.
 *   - Numeric or temporal reasoning of any kind.
 *
 * Rough expectation from internal spot checks on well-written option
 * descriptions: it agrees with a hosted decision model most of the time on
 * clean topical routing and materially less often on anything subtler. Treat a
 * `source: "local"` answer as a hint that saves a round trip, never as a gate
 * on something destructive. Reported confidence is a distribution-concentration
 * measure, is NOT calibrated against outcomes, and is deliberately capped
 * (see LOCAL_CONFIDENCE_CEILING) so that a caller thresholding at 0.8 can
 * never be fooled into thinking a lexical guess was a confident decision.
 */

// ── Tunables ────────────────────────────────────────────────────────────────

// Confidence is capped so callers thresholding high never mistake lexical
// overlap for a calibrated decision. A local answer can be useful; it is never
// authoritative.
const LOCAL_CONFIDENCE_CEILING = 0.75;

// Softmax temperature applied to the rescaled similarities. Lower = peakier.
const SOFTMAX_TEMPERATURE = 0.3;

// Similarities are rescaled by the best one before the softmax, so the shape of
// the distribution follows the *relative* gap between options rather than the
// absolute cosine value (which is depressed by any long state). The floor stops
// that rescaling from amplifying noise: when the best option only matches
// weakly in absolute terms, the whole distribution stays flat and confidence
// stays low, which is the honest reading of thin evidence.
const RESCALE_FLOOR = 0.25;

// Below this top similarity there is no lexical signal at all: return a uniform
// distribution and zero confidence rather than inventing a winner.
const MIN_SIGNAL = 0.02;

// Adjacent-token bigrams are worth less than unigrams but catch phrases
// ("payment failed") that unigrams scatter.
const BIGRAM_WEIGHT = 0.6;

// Criteria-free `noul` is topical overlap, not truth. Its confidence is held
// well below the normal ceiling to say so numerically.
const NOUL_TOPICAL_CEILING = 0.35;
const NOUL_MIDPOINT = 0.12;
const NOUL_SCALE = 0.18;

const STOPWORDS = new Set(
  (
    "a about above after again against all am an and any are as at be because been " +
    "before being below between both but by can cannot could did do does doing down " +
    "during each few for from further had has have having he her here hers herself " +
    "him himself his how i if in into is it its itself just me more most my myself " +
    "no nor not now of off on once only or other our ours ourselves out over own same " +
    "she should so some such than that the their theirs them themselves then there " +
    "these they this those through to too under until up very was we were what when " +
    "where which while who whom why will with would you your yours yourself yourselves"
  ).split(" "),
);

// Longest first so "izations" wins over "s".
const SUFFIXES = [
  "izations",
  "ization",
  "ational",
  "iveness",
  "fulness",
  "ousness",
  "ements",
  "ations",
  "ements",
  "ances",
  "ences",
  "ation",
  "ement",
  "ments",
  "ingly",
  "ment",
  "ness",
  "able",
  "ible",
  "ance",
  "ence",
  "edly",
  "ings",
  "ing",
  "ers",
  "est",
  "ed",
  "er",
  "ly",
  "es",
  "s",
].sort((a, b) => b.length - a.length);

// ── Text handling ───────────────────────────────────────────────────────────

/**
 * Flatten any JSON-ish value into searchable text. Object keys are kept —
 * in a state blob the field names carry as much signal as the values.
 */
function textOf(value, depth) {
  const d = typeof depth === "number" ? depth : 0;
  if (value === null || value === undefined) return "";
  if (d > 8) return "";
  const t = typeof value;
  if (t === "string") return value;
  if (t === "number" || t === "boolean") return String(value);
  if (Array.isArray(value)) {
    return value.map((v) => textOf(v, d + 1)).join(" ");
  }
  if (t === "object") {
    const parts = [];
    for (const key of Object.keys(value)) {
      parts.push(key, textOf(value[key], d + 1));
    }
    return parts.join(" ");
  }
  return "";
}

function stem(word) {
  let w = word;
  if (w.length <= 3) return w;
  if (w.endsWith("ies") && w.length > 4) return w.slice(0, -3) + "y";
  if (w.endsWith("sses")) return w.slice(0, -2);
  if (w.endsWith("ss")) return w;
  for (let i = 0; i < SUFFIXES.length; i++) {
    const suf = SUFFIXES[i];
    if (w.endsWith(suf) && w.length - suf.length >= 4) {
      return w.slice(0, -suf.length);
    }
  }
  return w;
}

/**
 * Lowercase, split on non-alphanumerics, drop stopwords and 1-char tokens,
 * stem, then append adjacent bigrams of the surviving stems.
 */
function tokenize(text) {
  const raw = String(text || "")
    .toLowerCase()
    .split(/[^a-z0-9]+/);
  const unigrams = [];
  for (let i = 0; i < raw.length; i++) {
    const w = raw[i];
    if (!w || w.length < 2) continue;
    if (STOPWORDS.has(w)) continue;
    unigrams.push(stem(w));
  }
  const tokens = unigrams.slice();
  for (let i = 0; i + 1 < unigrams.length; i++) {
    tokens.push(unigrams[i] + "_" + unigrams[i + 1]);
  }
  return tokens;
}

function isBigram(term) {
  return term.indexOf("_") !== -1;
}

function termFrequencies(tokens) {
  const tf = new Map();
  for (let i = 0; i < tokens.length; i++) {
    tf.set(tokens[i], (tf.get(tokens[i]) || 0) + 1);
  }
  return tf;
}

// ── Vector space ────────────────────────────────────────────────────────────

function buildIdf(documentTermSets, docCount) {
  const df = new Map();
  for (let i = 0; i < documentTermSets.length; i++) {
    documentTermSets[i].forEach((term) => {
      df.set(term, (df.get(term) || 0) + 1);
    });
  }
  const idf = new Map();
  df.forEach((count, term) => {
    // Always positive, larger for terms that appear in fewer options.
    idf.set(term, Math.log((docCount + 1) / (count + 0.5)));
  });
  return idf;
}

/**
 * Sublinear TF weighting, IDF from the option corpus, bigrams discounted.
 * Terms unseen in the corpus keep a max-IDF weight so they still contribute to
 * the query norm — that makes a long, mostly-irrelevant state score lower
 * against every option, which is the honest outcome. It cannot change the
 * ranking, only the absolute similarity (and therefore the confidence).
 */
function weightVector(tf, idf, fallbackIdf) {
  const vec = new Map();
  let sumSquares = 0;
  tf.forEach((count, term) => {
    const base = idf.has(term) ? idf.get(term) : fallbackIdf;
    if (!base) return;
    let w = (1 + Math.log(count)) * base;
    if (isBigram(term)) w *= BIGRAM_WEIGHT;
    if (!isFinite(w) || w <= 0) return;
    vec.set(term, w);
    sumSquares += w * w;
  });
  return { vec: vec, norm: Math.sqrt(sumSquares) };
}

function cosine(a, b) {
  if (!a.norm || !b.norm) return 0;
  // Iterate the smaller map.
  const [small, large] = a.vec.size <= b.vec.size ? [a, b] : [b, a];
  let dot = 0;
  small.vec.forEach((w, term) => {
    const other = large.vec.get(term);
    if (other) dot += w * other;
  });
  const sim = dot / (a.norm * b.norm);
  if (!isFinite(sim) || sim <= 0) return 0;
  return sim > 1 ? 1 : sim;
}

function softmax(values, temperature) {
  const max = Math.max.apply(null, values);
  const exps = values.map((v) => Math.exp((v - max) / temperature));
  const total = exps.reduce((a, b) => a + b, 0);
  if (!isFinite(total) || total <= 0) {
    return values.map(() => 1 / values.length);
  }
  return exps.map((e) => e / total);
}

/**
 * Distribution concentration in [0, 1]: the margin between the best and the
 * runner-up. A uniform distribution scores 0, a decisive one approaches 1.
 * This matches how the hosted model's `confidence` behaves closely enough to
 * be interchangeable at a threshold, and unlike normalized entropy it does not
 * collapse toward 0 as the number of options grows.
 */
function concentration(probabilities) {
  const n = probabilities.length;
  if (n === 0) return 0;
  if (n === 1) return 1;
  const sorted = probabilities.slice().sort((a, b) => b - a);
  const margin = sorted[0] - sorted[1];
  if (!isFinite(margin) || margin <= 0) return 0;
  return margin > 1 ? 1 : margin;
}

function capConfidence(value, ceiling) {
  const c = ceiling === undefined ? LOCAL_CONFIDENCE_CEILING : ceiling;
  if (!isFinite(value) || value <= 0) return 0;
  return Math.round(Math.min(value, c) * 1000) / 1000;
}

// ── Option normalization ────────────────────────────────────────────────────

/**
 * Accepts ["a", "b"] or {key: "description"} or {key: {nested: "..."}} and
 * returns parallel arrays of stable keys and searchable texts. The key itself
 * is folded into the text because a well-named key is signal.
 */
function normalizeOptions(options) {
  const keys = [];
  const texts = [];
  if (Array.isArray(options)) {
    for (let i = 0; i < options.length; i++) {
      const opt = options[i];
      if (opt && typeof opt === "object" && !Array.isArray(opt)) {
        const key = String(opt.key !== undefined ? opt.key : i);
        keys.push(key);
        texts.push(key + " " + textOf(opt.text !== undefined ? opt.text : opt));
      } else {
        const key = String(opt === undefined || opt === null ? "" : opt);
        keys.push(key);
        texts.push(key);
      }
    }
  } else if (options && typeof options === "object") {
    const objKeys = Object.keys(options);
    for (let i = 0; i < objKeys.length; i++) {
      keys.push(objKeys[i]);
      texts.push(objKeys[i] + " " + textOf(options[objKeys[i]]));
    }
  }
  return { keys: keys, texts: texts };
}

// ── Core ranking ────────────────────────────────────────────────────────────

/**
 * Rank option texts against the query text.
 * Returns { similarities, probabilities, winner, confidence, signal }.
 * Ties break toward the lowest index — the caller's own ordering — so the same
 * input always produces the same answer.
 */
function rank(queryText, optionTexts) {
  const n = optionTexts.length;
  if (n === 0) {
    return {
      similarities: [],
      probabilities: [],
      winner: -1,
      confidence: 0,
      signal: 0,
    };
  }
  if (n === 1) {
    return {
      similarities: [1],
      probabilities: [1],
      winner: 0,
      confidence: 1,
      signal: 1,
    };
  }

  const optionTfs = optionTexts.map((t) => termFrequencies(tokenize(t)));
  const termSets = optionTfs.map((tf) => new Set(tf.keys()));
  const idf = buildIdf(termSets, n);
  const fallbackIdf = Math.log((n + 1) / 0.5);

  const queryVec = weightVector(
    termFrequencies(tokenize(queryText)),
    idf,
    fallbackIdf,
  );
  const similarities = optionTfs.map((tf) =>
    cosine(queryVec, weightVector(tf, idf, fallbackIdf)),
  );

  const signal = Math.max.apply(null, similarities);
  if (signal < MIN_SIGNAL) {
    // No lexical evidence. Uniform distribution, zero confidence, first option
    // as a deterministic placeholder the caller can detect via confidence === 0.
    return {
      similarities: similarities,
      probabilities: similarities.map(() => 1 / n),
      winner: 0,
      confidence: 0,
      signal: signal,
    };
  }

  const scale = Math.max(signal, RESCALE_FLOOR);
  const rescaled = similarities.map((s) => s / scale);
  const probabilities = softmax(rescaled, SOFTMAX_TEMPERATURE);
  let winner = 0;
  for (let i = 1; i < n; i++) {
    // Strictly greater keeps the earliest index on a tie.
    if (similarities[i] > similarities[winner]) winner = i;
  }
  return {
    similarities: similarities,
    probabilities: probabilities,
    winner: winner,
    confidence: capConfidence(concentration(probabilities)),
    signal: signal,
  };
}

function roundProbabilities(keys, probabilities) {
  const out = {};
  for (let i = 0; i < keys.length; i++) {
    out[keys[i]] = Math.round((probabilities[i] || 0) * 10000) / 10000;
  }
  return out;
}

// ── Public primitives ───────────────────────────────────────────────────────

/**
 * Local `choice`. Returns the same shape the API path returns, with
 * source "local".
 */
function localChoice(state, question, options) {
  const norm = normalizeOptions(options);
  if (norm.keys.length === 0) {
    return {
      type: "choice",
      answer: null,
      confidence: 0,
      probabilities: {},
      source: "local",
      method: "tfidf",
      note: "no options supplied",
    };
  }
  const query = textOf(state) + " \n " + textOf(question);
  const r = rank(query, norm.texts);
  return {
    type: "choice",
    answer: norm.keys[r.winner],
    confidence: r.confidence,
    probabilities: roundProbabilities(norm.keys, r.probabilities),
    source: "local",
    method: "tfidf",
  };
}

/**
 * Local `noul`.
 *
 * With criteria ({ true: "...", false: "..." }) this is a two-way choice and
 * behaves as well as any other two-option routing call. Without criteria it is
 * only topical overlap between the state and the question — it answers "does
 * the state talk about this", not "is this true" — so its confidence is held
 * under NOUL_TOPICAL_CEILING. Always pass criteria when the answer matters.
 */
function localNoul(state, question, criteria) {
  const hasCriteria =
    criteria &&
    typeof criteria === "object" &&
    (criteria.true !== undefined || criteria.false !== undefined);

  if (hasCriteria) {
    const r = rank(textOf(state) + " \n " + textOf(question), [
      textOf(criteria.true !== undefined ? criteria.true : question),
      textOf(
        criteria.false !== undefined
          ? criteria.false
          : "not " + textOf(question),
      ),
    ]);
    const pTrue = Math.round((r.probabilities[0] || 0.5) * 10000) / 10000;
    return {
      type: "noul",
      answer: pTrue >= 0.5,
      probability: pTrue,
      confidence: r.confidence,
      source: "local",
      method: "tfidf-criteria",
    };
  }

  // Topical-overlap fallback. Map similarity through a smooth curve centered on
  // NOUL_MIDPOINT so a state that never mentions the topic lands below 0.5.
  const r = rank(textOf(state), [textOf(question), ""]);
  const sim = r.similarities.length ? r.similarities[0] : 0;
  const shaped = 0.5 + 0.5 * Math.tanh((sim - NOUL_MIDPOINT) / NOUL_SCALE);
  const pTrue = Math.round(shaped * 10000) / 10000;
  return {
    type: "noul",
    answer: pTrue >= 0.5,
    probability: pTrue,
    confidence: capConfidence(Math.abs(pTrue - 0.5) * 2, NOUL_TOPICAL_CEILING),
    source: "local",
    method: "tfidf-topical",
    note: "no criteria supplied — topical overlap only, not a truth judgement",
  };
}

/**
 * Local `score`. Levels are an ordered array; the answer is the
 * probability-weighted mean of the level indices, exactly like the API.
 */
function localScore(state, question, levels) {
  const list = Array.isArray(levels) ? levels : [];
  if (list.length === 0) {
    return {
      type: "score",
      answer: null,
      confidence: 0,
      probabilities: {},
      legend: {},
      source: "local",
      method: "tfidf",
      note: "no levels supplied",
    };
  }
  const texts = list.map((l) => textOf(l));
  const keys = list.map((_, i) => String(i));
  const r = rank(textOf(state) + " \n " + textOf(question), texts);

  let mean = 0;
  for (let i = 0; i < list.length; i++) mean += i * (r.probabilities[i] || 0);

  const legend = {};
  for (let i = 0; i < list.length; i++) legend[String(i)] = texts[i];

  return {
    type: "score",
    answer: Math.round(mean * 1000) / 1000,
    confidence: r.confidence,
    probabilities: roundProbabilities(keys, r.probabilities),
    legend: legend,
    source: "local",
    method: "tfidf",
  };
}

module.exports = {
  localChoice: localChoice,
  localNoul: localNoul,
  localScore: localScore,
  // Exported for tests and for callers who want the raw vector-space layer.
  rank: rank,
  tokenize: tokenize,
  stem: stem,
  textOf: textOf,
  normalizeOptions: normalizeOptions,
  LOCAL_CONFIDENCE_CEILING: LOCAL_CONFIDENCE_CEILING,
};
