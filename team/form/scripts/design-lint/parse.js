"use strict";
// design-lint/parse.js — light tokenizing helpers. Regex only, no AST, no deps.

const MARKUP = new Set([".tsx", ".jsx", ".vue", ".svelte", ".html"]);
const STYLE = new Set([".css", ".scss"]);
const EXTS = new Set([...MARKUP, ...STYLE]);
const VOID = new Set(
  "area base br col embed hr img input link meta source track wbr".split(" "),
);

const blank = (s) => s.replace(/[^\n]/g, " ");

// Replace comments with spaces (same length, newlines kept) so offsets/lines survive.
function stripComments(src, ext) {
  let out = src
    .replace(/\/\*[\s\S]*?\*\//g, blank)
    .replace(/<!--[\s\S]*?-->/g, blank);
  if (ext !== ".css") {
    out = out.replace(
      /(^|[^:"'`\w\\(])(\/\/[^\n]*)/g,
      (m, a, b) => a + blank(b),
    );
  }
  return out;
}

// Split on `sep` outside parens/brackets/braces/quotes. Returns [{text,start}].
function splitTop(s, sep) {
  const out = [];
  let depth = 0;
  let q = null;
  let cur = "";
  let start = 0;
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (q) {
      cur += ch;
      if (ch === q) q = null;
      continue;
    }
    if (ch === '"' || ch === "'") {
      q = ch;
      cur += ch;
      continue;
    }
    if (ch === "(" || ch === "[" || ch === "{") depth++;
    else if (ch === ")" || ch === "]" || ch === "}") depth--;
    if (ch === sep && depth <= 0) {
      out.push({ text: cur, start });
      cur = "";
      start = i + 1;
      continue;
    }
    cur += ch;
  }
  if (cur.trim()) out.push({ text: cur, start });
  return out;
}

const kebab = (k) => k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
const UNITLESS =
  /^(line-height|opacity|z-index|flex|flex-grow|flex-shrink|font-weight|order|zoom|aspect-ratio|scale)$/;

// body: "a: b; c: d". Returns {map, list:[{prop,value,line}]}.
function parseDecls(body, baseIdx, lineAt, fallbackLine) {
  const map = Object.create(null);
  const list = [];
  for (const { text, start } of splitTop(body, ";")) {
    const i = text.indexOf(":");
    if (i < 1) continue;
    const prop = text.slice(0, i).trim().toLowerCase();
    if (!/^-{0,2}[a-z][a-z0-9-]*$/.test(prop)) continue;
    const value = text
      .slice(i + 1)
      .replace(/!important/i, "")
      .trim();
    const lead = text.length - text.trimStart().length;
    const line =
      lineAt && baseIdx != null ? lineAt(baseIdx + start + lead) : fallbackLine;
    map[prop] = value;
    list.push({ prop, value, line });
  }
  return { map, list };
}

// JSX/Vue object style: `{{ fontSize: 12, color: '#000' }}` or `{ 'font-size': '12px' }`.
function parseStyleObject(expr, line) {
  let inner = expr.trim();
  while (inner.startsWith("{") && inner.endsWith("}"))
    inner = inner.slice(1, -1).trim();
  const map = Object.create(null);
  const list = [];
  for (const { text } of splitTop(inner, ",")) {
    const i = text.indexOf(":");
    if (i < 1) continue;
    const prop = kebab(
      text
        .slice(0, i)
        .trim()
        .replace(/^['"]|['"]$/g, ""),
    );
    let value = text
      .slice(i + 1)
      .trim()
      .replace(/^(['"`])([\s\S]*)\1$/, "$2");
    if (/^-?\d+(\.\d+)?$/.test(value) && value !== "0" && !UNITLESS.test(prop))
      value += "px";
    if (!/^-{0,2}[a-z][a-z0-9-]*$/.test(prop)) continue;
    map[prop] = value;
    list.push({ prop, value, line });
  }
  return { map, list };
}

function makeLineAt(src) {
  const starts = [0];
  for (let i = 0; i < src.length; i++)
    if (src.charCodeAt(i) === 10) starts.push(i + 1);
  return (idx) => {
    let lo = 0;
    let hi = starts.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (starts[mid] <= idx) lo = mid;
      else hi = mid - 1;
    }
    return lo + 1;
  };
}

// ── colors ──────────────────────────────────────────────────────────────────
const NAMED = {
  white: [255, 255, 255, 1],
  black: [0, 0, 0, 1],
  transparent: [0, 0, 0, 0],
  red: [255, 0, 0, 1],
  blue: [0, 0, 255, 1],
  green: [0, 128, 0, 1],
  purple: [128, 0, 128, 1],
  orange: [255, 165, 0, 1],
  yellow: [255, 255, 0, 1],
  pink: [255, 192, 203, 1],
  teal: [0, 128, 128, 1],
  gray: [128, 128, 128, 1],
  grey: [128, 128, 128, 1],
};

function hslToRgb(h, s, l) {
  h = ((h % 360) + 360) % 360;
  const k = (n) => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = (n) =>
    l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
  return [
    Math.round(f(0) * 255),
    Math.round(f(8) * 255),
    Math.round(f(4) * 255),
  ];
}

// → {r,g,b,a} or null. Hex, rgb[a], hsl[a], a few names. Never throws.
function parseColor(raw) {
  if (!raw) return null;
  const s = String(raw).trim().toLowerCase();
  let m = /^#([0-9a-f]{3,8})$/.exec(s);
  if (m) {
    let h = m[1];
    if (h.length === 3 || h.length === 4) h = h.replace(/./g, (c) => c + c);
    if (h.length !== 6 && h.length !== 8) return null;
    return {
      r: parseInt(h.slice(0, 2), 16),
      g: parseInt(h.slice(2, 4), 16),
      b: parseInt(h.slice(4, 6), 16),
      a: h.length === 8 ? parseInt(h.slice(6, 8), 16) / 255 : 1,
    };
  }
  m = /^(rgba?|hsla?)\(([^)]*)\)$/.exec(s);
  if (m) {
    const nums = m[2].match(/-?\d*\.?\d+%?/g);
    if (!nums || nums.length < 3) return null;
    const n = nums.map((x) =>
      x.endsWith("%") ? parseFloat(x) / 100 : parseFloat(x),
    );
    const alpha = nums.length > 3 ? n[3] : 1;
    if (m[1].startsWith("rgb")) {
      const sc = (i) => (nums[i].endsWith("%") ? n[i] * 255 : n[i]);
      return {
        r: Math.round(sc(0)),
        g: Math.round(sc(1)),
        b: Math.round(sc(2)),
        a: alpha,
      };
    }
    const [r, g, b] = hslToRgb(n[0], n[1], n[2]);
    return { r, g, b, a: alpha };
  }
  if (NAMED[s]) {
    const [r, g, b, a] = NAMED[s];
    return { r, g, b, a };
  }
  return null;
}

function luminance({ r, g, b }) {
  const f = (v) => {
    v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
}

function contrast(a, b) {
  const la = luminance(a);
  const lb = luminance(b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

const chroma = (c) => (Math.max(c.r, c.g, c.b) - Math.min(c.r, c.g, c.b)) / 255;

// px value from "12px" / "0.75rem" / "1em"(=16). null if not a plain length.
function toPx(v) {
  const m = /^(-?\d*\.?\d+)(px|rem|em)?$/.exec(String(v).trim());
  if (!m) return null;
  const n = parseFloat(m[1]);
  return m[2] === "rem" || m[2] === "em" ? n * 16 : n;
}

// ── class tokens ─────────────────────────────────────────────────────────────
const BR0 = "[^{}]*";
const BR1 = `(?:[^{}]|\\{${BR0}\\})*`;
const BR2 = `(?:[^{}]|\\{${BR1}\\})*`;
const BRACE = `\\{${BR2}\\}`;
const ATTR_PIECE = `"[^"]*"|'[^']*'|${BRACE}|[^>"'{}]`;
const TAG_RE_SRC = `<(\\/?)([A-Za-z][\\w.:-]*)((?:${ATTR_PIECE}){0,4000})>`;
const CLASS_ATTR = new RegExp(
  `(?:^|\\s)(?::?class(?:Name)?|class:list)\\s*=\\s*("[^"]*"|'[^']*'|${BRACE})`,
  "g",
);
const STYLE_ATTR = new RegExp(
  `(?:^|\\s):?style\\s*=\\s*("[^"]*"|'[^']*'|${BRACE})`,
);

function isVariant(c) {
  return c.replace(/\[[^\]]*\]/g, "").includes(":");
}

function extractClasses(attrs) {
  const all = [];
  CLASS_ATTR.lastIndex = 0;
  let m;
  while ((m = CLASS_ATTR.exec(attrs))) {
    const v = m[1];
    let text = "";
    if (v[0] === "{") {
      const lits = v.match(/"[^"]*"|'[^']*'|`[^`]*`/g) || [];
      text = lits
        .map((l) => l.slice(1, -1).replace(/\$\{[^}]*\}/g, " "))
        .join(" ");
    } else {
      text = v.slice(1, -1);
    }
    for (const c of text.split(/\s+/)) if (c) all.push(c);
  }
  return { base: all.filter((c) => !isVariant(c)), all };
}

function stripTags(s) {
  return s
    .replace(/<[^>]*>/g, " ")
    .replace(/\{[^{}]*\}/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

// ── context ─────────────────────────────────────────────────────────────────
function buildContext(file, src, ext) {
  const clean = stripComments(src, ext);
  const lineAt = makeLineAt(src);
  const nodes = [];
  const elements = [];

  const addCss = (text, base) => {
    const re = /([^{}]*)\{([^{}]*)\}/g;
    let m;
    while ((m = re.exec(text))) {
      let sel = m[1];
      const cut = sel.lastIndexOf(";") + 1;
      sel = sel.slice(cut);
      const selector = sel.trim();
      if (!selector || /^@(font-face|keyframes|page|property)/i.test(selector))
        continue;
      const lead = sel.length - sel.trimStart().length;
      const idx = base + m.index + cut + lead;
      const bodyIdx = base + m.index + m[1].length + 1;
      const d = parseDecls(m[2], bodyIdx, lineAt);
      nodes.push({
        kind: "css",
        tag: "",
        selector,
        classes: (selector.match(/\.[\w-]+/g) || []).map((c) => c.slice(1)),
        decls: d.map,
        declList: d.list,
        idx,
        line: lineAt(idx),
      });
    }
  };

  let markup = clean;
  if (STYLE.has(ext)) {
    addCss(clean, 0);
    markup = "";
  } else {
    if (ext !== ".tsx" && ext !== ".jsx") {
      markup = markup.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, blank);
    }
    markup = markup.replace(
      /(<style\b[^>]*>)([\s\S]*?)(<\/style>)/gi,
      (m, a, body, c, off) => {
        addCss(body, off + a.length);
        return a + blank(body) + c;
      },
    );
  }

  if (markup) {
    const re = new RegExp(TAG_RE_SRC, "g");
    const stack = [];
    let m;
    while ((m = re.exec(markup))) {
      const [full, closing, name, attrs] = m;
      const lname = name.toLowerCase();
      if (closing) {
        for (let i = stack.length - 1; i >= 0; i--) {
          if (stack[i].lname === lname) {
            stack.length = i;
            break;
          }
        }
        continue;
      }
      const selfClosing = attrs.trimEnd().endsWith("/");
      const { base, all } = extractClasses(attrs);
      const sm = STYLE_ATTR.exec(attrs);
      const line = lineAt(m.index);
      let d = { map: Object.create(null), list: [] };
      if (sm) {
        const v = sm[1];
        d =
          v[0] === "{"
            ? parseStyleObject(v, line)
            : parseDecls(v.slice(1, -1), null, null, line);
        if (v[0] === '"' || v[0] === "'") {
          if (/^\s*\{/.test(v.slice(1)))
            d = parseStyleObject(v.slice(1, -1), line);
        }
      }
      const el = {
        kind: "tag",
        tag: lname,
        rawTag: name,
        selector: lname + (base.length ? "." + base.join(".") : ""),
        classes: base,
        allClasses: all,
        decls: d.map,
        declList: d.list,
        attrs,
        idx: m.index,
        end: m.index + full.length,
        line,
        ancestors: stack.slice(),
        lname,
        text() {
          const close = markup.indexOf("</" + name, this.end);
          const stop =
            close < 0 ? this.end + 400 : Math.min(close, this.end + 4000);
          return stripTags(markup.slice(this.end, stop));
        },
      };
      elements.push(el);
      nodes.push(el);
      if (!selfClosing && !VOID.has(lname)) stack.push(el);
    }
  }

  return { file, ext, src, clean, markup, lineAt, nodes, elements };
}

module.exports = {
  MARKUP,
  STYLE,
  EXTS,
  stripComments,
  splitTop,
  parseDecls,
  parseColor,
  luminance,
  contrast,
  chroma,
  toPx,
  makeLineAt,
  buildContext,
  stripTags,
};
