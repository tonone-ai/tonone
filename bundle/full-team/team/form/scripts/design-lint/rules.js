"use strict";
// design-lint/rules.js — the rule table.
//
// Rule shape: { id, tier, severity, fileTypes, message, fix, detect(ctx) }
//   tier "immediate" = mechanical, high-precision, safe to surface from a hook.
//   tier "advisory"  = taste. Reported by the CLI only. Humans/Form decide.
//   severity: "warning" | "info" (output-kit levels; the linter never says critical).
//   detect returns [{line, message?}]; message overrides the rule default.
// ids line up with team/form/reference/craft-floor.md where an item exists.

const {
  MARKUP,
  STYLE,
  parseColor,
  contrast,
  chroma,
  toPx,
  splitTop,
} = require("./parse");

const MK = [...MARKUP];
const ALL = [...MARKUP, ...STYLE];
const hasCls = (n, re) => n.classes.some((c) => re.test(c));
const sel = (n) =>
  `${n.tag} ${n.selector} ${n.classes.join(" ")}`.toLowerCase();
const NEUTRAL =
  "gray|slate|zinc|neutral|stone|white|black|transparent|current|inherit";
const SEMANTIC =
  /accent|primary|brand|secondary|success|warning|danger|error|info|blue|red|green|purple|indigo|violet|orange|amber|yellow|teal|cyan|pink|rose|emerald|lime|sky|fuchsia/i;

function pure(c, v) {
  return c && c.a === 1 && c.r === v && c.g === v && c.b === v;
}

function colorOf(n, kind) {
  // kind: "fg" | "bg". Literal color from decls or Tailwind arbitrary/keyword classes.
  if (kind === "fg") {
    const c = parseColor(n.decls.color);
    if (c) return c;
    for (const k of n.classes) {
      const m = /^text-(?:\[(#[0-9a-fA-F]{3,8})\]|(white|black))$/.exec(k);
      if (m) return parseColor(m[1] || m[2]);
    }
    return null;
  }
  const c =
    parseColor(n.decls["background-color"]) || parseColor(n.decls.background);
  if (c) return c;
  for (const k of n.classes) {
    const m = /^bg-(?:\[(#[0-9a-fA-F]{3,8})\]|(white|black))$/.exec(k);
    if (m) return parseColor(m[1] || m[2]);
  }
  return null;
}

function fontPx(n) {
  const v = n.decls["font-size"];
  if (v) return toPx(v);
  for (const k of n.classes) {
    const m = /^text-\[(\d*\.?\d+)(px|rem)\]$/.exec(k);
    if (m) return toPx(m[1] + m[2]);
  }
  return null;
}

const CAPTIONY =
  /badge|caption|legal|footnote|fine-?print|copyright|\btag\b|chip|kbd|meta|eyebrow|label|sup\b|sub\b|timestamp|hint|helper|pill/;
const CARDISH =
  /card|callout|alert|notice|banner|toast|\btip\b|\bnote\b|panel|message|tile|stat|admonition/;
const SIDE_EXEMPT =
  /quote|\bnav|menu|sidebar|tabs?\b|toc|breadcrumb|timeline|stepper|prose|\bcode\b|\bpre\b|\bli\b|details|summary/;

function hasRadius(n) {
  const r = n.decls["border-radius"];
  if (r && !/^0(px|rem)?$/.test(r.trim())) return true;
  return hasCls(n, /^rounded(?!-none)(-|$)/);
}

function colorIsAccent(tok) {
  const c = parseColor(tok);
  if (c) return c.a > 0.3 && chroma(c) >= 0.15;
  const v = /^var\(\s*--([\w-]+)/.exec(tok);
  if (v)
    return (
      SEMANTIC.test(v[1]) && !/border|muted|neutral|gray|grey|subtle/.test(v[1])
    );
  return false;
}

function sideTabWidth(n) {
  // returns {w, accent} for a left/start border, or null.
  for (const p of ["border-left", "border-inline-start"]) {
    const v = n.decls[p];
    if (!v) continue;
    const toks = splitTop(v, " ")
      .map((t) => t.text.trim())
      .filter(Boolean);
    const w = toks.map(toPx).find((x) => x != null);
    const accent = toks.some((t) => colorIsAccent(t));
    if (w != null) return { w, accent };
  }
  for (const [pw, pc] of [
    ["border-left-width", "border-left-color"],
    ["border-inline-start-width", "border-inline-start-color"],
  ]) {
    if (n.decls[pw])
      return {
        w: toPx(n.decls[pw]) || 0,
        accent: colorIsAccent(n.decls[pc] || ""),
      };
  }
  let w = null;
  let accent = false;
  for (const k of n.classes) {
    let m =
      /^border-[ls]-(\d+)$/.exec(k) || /^border-[ls]-\[(\d+)px\]$/.exec(k);
    if (m) w = +m[1];
    if (
      new RegExp(
        `^border-(?:[ls]-)?(?!(?:${NEUTRAL})\\b)([a-z]+)-\\d{2,3}(?:/\\d+)?$`,
      ).test(k)
    )
      accent = true;
    if (
      /^border-(?:[ls]-)?(primary|accent|brand|secondary|success|warning|danger|error|info)(?:-\d+)?$/.test(
        k,
      )
    )
      accent = true;
  }
  return w != null ? { w, accent } : null;
}

function shadowGlow(value) {
  // true if any non-inset shadow has blur >= 20px and a saturated color.
  for (const { text } of splitTop(value, ",")) {
    if (/\binset\b/.test(text)) continue;
    const toks = splitTop(text.trim(), " ")
      .map((t) => t.text.trim())
      .filter(Boolean);
    const lens = toks.map(toPx).filter((x) => x != null);
    const colorTok = toks.find((t) => parseColor(t));
    const c = colorTok && parseColor(colorTok);
    if (
      lens.length >= 3 &&
      lens[2] >= 20 &&
      c &&
      c.a >= 0.2 &&
      chroma(c) >= 0.35
    )
      return true;
  }
  return false;
}

function isDarkFile(ctx) {
  if (ctx._dark != null) return ctx._dark;
  let dark = /color-scheme\s*:\s*dark/.test(ctx.clean);
  for (const n of ctx.nodes) {
    if (dark) break;
    const bg = colorOf(n, "bg");
    if (bg && bg.a === 1 && Math.max(bg.r, bg.g, bg.b) < 40) dark = true;
    if (hasCls(n, /^bg-(black|(slate|gray|zinc|neutral|stone)-(900|950))$/))
      dark = true;
  }
  ctx._dark = dark;
  return dark;
}

const FONTS =
  /^(inter|roboto|arial|open sans|poppins|montserrat|lato)(?: var| variable)?$/i;
const FONT_IMPORT =
  /import\s*\{[^}]*\b(Inter|Roboto|Poppins|Open_Sans|Montserrat|Lato)\b[^}]*\}\s*from\s*["']next\/font\/google["']/;

function firstFamily(v) {
  const f = splitTop(v, ",")[0];
  return f ? f.text.trim().replace(/^["']|["']$/g, "") : "";
}

function hexNorm(h) {
  const c = parseColor(h);
  if (!c) return null;
  const x = (v) => v.toString(16).padStart(2, "0");
  return x(c.r) + x(c.g) + x(c.b);
}

const TOKEN_FILE =
  /(^|\/)(tokens?|theme|variables|palette|colors?|design-tokens)[^/]*\.(css|scss)$|tailwind\.config/i;

const rules = [
  {
    id: "gradient-text",
    tier: "immediate",
    severity: "warning",
    fileTypes: ALL,
    message:
      "Gradient text (background-clip:text over a gradient). Craft floor REFUSE.",
    fix: "Use a solid token color; keep emphasis in weight/size. Brief-mandated? note the deviation.",
    detect(ctx) {
      const out = [];
      for (const n of ctx.nodes) {
        const clip = /\btext\b/.test(
          n.decls["background-clip"] ||
            n.decls["-webkit-background-clip"] ||
            "",
        );
        const grad = /gradient\(/.test(
          n.decls["background-image"] || n.decls.background || "",
        );
        const twClip = hasCls(n, /^bg-clip-text$/);
        const twGrad =
          hasCls(n, /^(bg-gradient-|bg-linear-|bg-radial|bg-conic)/) ||
          (hasCls(n, /^from-/) && hasCls(n, /^to-/));
        if (
          (clip && grad) ||
          (twClip && twGrad) ||
          (clip && twGrad) ||
          (twClip && grad)
        )
          out.push({ line: n.line });
      }
      return out;
    },
  },
  {
    id: "side-tab",
    tier: "immediate",
    severity: "warning",
    fileTypes: ALL,
    message: "Thick colored left border on a card/callout (side-tab accent).",
    fix: "Use a full hairline border, a tinted background, or an icon. Reserve left rules for blockquotes.",
    detect(ctx) {
      const out = [];
      for (const n of ctx.nodes) {
        if (/^(blockquote|pre|code|li|nav|details|summary|td|th)$/.test(n.tag))
          continue;
        const s = sel(n);
        if (SIDE_EXEMPT.test(s)) continue;
        const b = sideTabWidth(n);
        if (!b || b.w <= 1 || !b.accent) continue;
        if (CARDISH.test(s) || hasRadius(n)) out.push({ line: n.line });
      }
      return out;
    },
  },
  {
    id: "nested-cards",
    tier: "advisory",
    severity: "info",
    fileTypes: MK,
    message: "Card inside a card (stacked radius + shadow/border surfaces).",
    fix: "Flatten the inner surface: drop its border/shadow, use spacing or a divider.",
    detect(ctx) {
      const card = (n) =>
        n.kind === "tag" &&
        (hasCls(n, /(^|-)card$/) ||
          (hasCls(n, /^rounded(-(md|lg|xl|2xl|3xl))?$/) &&
            hasCls(n, /^(shadow|border)(-|$)/) &&
            hasCls(n, /^bg-/)));
      const out = [];
      for (const n of ctx.elements) {
        if (card(n) && n.ancestors.some(card)) out.push({ line: n.line });
      }
      return out;
    },
  },
  {
    id: "icon-tile-stack",
    tier: "advisory",
    severity: "info",
    fileTypes: MK,
    message:
      "Repeated rounded icon tile above a heading (3+ in one file) — template feature-grid look.",
    fix: "Vary the treatment; let one item lead, or drop the tiles and use type + spacing.",
    detect(ctx) {
      const hits = [];
      for (const n of ctx.elements) {
        const tile =
          hasCls(n, /^(size|w|h)-\d/) &&
          hasCls(n, /^rounded(-(md|lg|xl|2xl|3xl|full))$/) &&
          hasCls(n, /^bg-/) &&
          hasCls(n, /^(inline-)?flex$|^grid$/) &&
          hasCls(n, /^(items|place-items)-center$/);
        if (tile && /<h[2-4]\b/.test(ctx.markup.slice(n.end, n.end + 450)))
          hits.push(n);
      }
      return hits.length >= 3
        ? [
            {
              line: hits[0].line,
              message: `${hits.length} icon tiles stacked above headings — template feature-grid look.`,
            },
          ]
        : [];
    },
  },
  {
    id: "hero-eyebrow-chip",
    tier: "advisory",
    severity: "info",
    fileTypes: MK,
    message: "Pill/badge chip directly above the hero h1.",
    fix: "Cut the chip, or fold the claim into the headline/subhead.",
    detect(ctx) {
      const h1 = ctx.elements.find((e) => e.tag === "h1");
      if (!h1) return [];
      const prev = ctx.elements.filter(
        (e) =>
          e.idx < h1.idx && h1.idx - e.idx < 500 && !/^h[1-6]$/.test(e.tag),
      );
      for (const e of prev.reverse()) {
        const tw =
          hasCls(e, /^rounded-full$/) &&
          hasCls(e, /^px-/) &&
          hasCls(e, /^(text-(xs|sm)|uppercase|tracking-|border|bg-)/);
        const named =
          /^(span|div|p|a)$/.test(e.tag) &&
          hasCls(e, /^(eyebrow|pill|badge|chip|kicker)([-_]|$)/);
        if (tw || named) return [{ line: e.line }];
      }
      return [];
    },
  },
  {
    id: "dark-glow",
    tier: "advisory",
    severity: "info",
    fileTypes: ALL,
    message: "Colored glow (large blurred saturated shadow) on a dark surface.",
    fix: "Use a tinted, low-alpha elevation shadow or a border; skip neon halos.",
    detect(ctx) {
      if (!isDarkFile(ctx)) return [];
      const out = [];
      for (const n of ctx.nodes) {
        const v = (n.decls["box-shadow"] || "") + "," + (n.decls.filter || "");
        let hit =
          v.length > 1 &&
          shadowGlow(
            v.replace(/drop-shadow\(([^)]*(?:\([^)]*\))?[^)]*)\)/g, "$1"),
          );
        for (const k of n.classes) {
          const m = /^(?:drop-)?shadow-\[(.+)\]$/.exec(k);
          if (m && shadowGlow(m[1].replace(/_/g, " "))) hit = true;
          if (
            new RegExp(
              `^shadow-(?!(?:${NEUTRAL})\\b)[a-z]+-\\d{2,3}(/\\d+)?$`,
            ).test(k)
          )
            hit = true;
        }
        if (hit) out.push({ line: n.line });
      }
      return out;
    },
  },
  {
    id: "bounce-easing",
    tier: "immediate",
    severity: "warning",
    fileTypes: ALL,
    message:
      "Overshooting/bouncy easing (cubic-bezier y outside 0..1, or bounce/elastic).",
    fix: "Use an ease-out curve (e.g. cubic-bezier(0.22, 1, 0.36, 1)); 100-300ms.",
    detect(ctx) {
      const out = [];
      const re = /cubic-bezier\(([^)]*)\)/g;
      let m;
      while ((m = re.exec(ctx.clean))) {
        const n = m[1].split(",").map((x) => parseFloat(x));
        if (
          n.length === 4 &&
          n.every((x) => !Number.isNaN(x)) &&
          (n[1] > 1 || n[1] < 0 || n[3] > 1 || n[3] < 0)
        ) {
          out.push({ line: ctx.lineAt(m.index) });
        }
      }
      for (const n of ctx.nodes) {
        for (const d of n.declList) {
          if (
            /^(transition|animation)/.test(d.prop) &&
            /\b(bounce|elastic|overshoot)\b/i.test(d.value)
          )
            out.push({ line: d.line });
        }
        if (hasCls(n, /^ease-(bounce|elastic)/)) out.push({ line: n.line });
      }
      return out;
    },
  },
  {
    id: "overused-font",
    tier: "advisory",
    severity: "info",
    fileTypes: ALL,
    message:
      "Default-stack primary font (Inter/Roboto/Arial/Open Sans/Poppins...).",
    fix: "Pick a typeface with intent via /form-direction; keep the default only if DESIGN.md says so.",
    detect(ctx) {
      const out = [];
      const claimed = (name) =>
        ctx.designMd &&
        ctx.designMd.text.includes(name.toLowerCase().replace(/_/g, " "));
      for (const n of ctx.nodes) {
        for (const d of n.declList) {
          if (d.prop !== "font-family") continue;
          const f = firstFamily(d.value);
          if (FONTS.test(f) && !claimed(f.replace(/ var(iable)?$/i, "")))
            out.push({
              line: d.line,
              message: `Primary font "${f}" is a default-stack choice.`,
            });
        }
        for (const k of n.classes) {
          const m = /^font-\[['"]?([A-Za-z ]+?)['"]?(?:,.*)?\]$/.exec(
            k.replace(/_/g, " "),
          );
          if (m && FONTS.test(m[1]) && !claimed(m[1]))
            out.push({ line: n.line });
        }
      }
      const im = FONT_IMPORT.exec(ctx.clean);
      if (im && !claimed(im[1]))
        out.push({
          line: ctx.lineAt(im.index),
          message: `next/font imports "${im[1].replace(/_/g, " ")}" — default-stack choice.`,
        });
      return out;
    },
  },
  {
    id: "gray-on-color",
    tier: "advisory",
    severity: "info",
    fileTypes: MK,
    message: "Gray text on a saturated colored background.",
    fix: "Use a tinted/white text token chosen for that surface; check AA contrast.",
    detect(ctx) {
      const out = [];
      for (const n of ctx.nodes) {
        if (n.kind !== "tag") continue;
        const bgc = n.classes.find((k) =>
          new RegExp(`^bg-(?!(?:${NEUTRAL})\\b)[a-z]+-[4-8]00$`).test(k),
        );
        const gray = n.classes.find((k) =>
          /^text-(gray|slate|zinc|neutral|stone)-[3-6]00$/.test(k),
        );
        if (bgc && gray)
          out.push({
            line: n.line,
            message: `${gray} on ${bgc} — gray text on a colored surface.`,
          });
      }
      return out;
    },
  },
  {
    id: "low-contrast",
    tier: "immediate",
    severity: "warning",
    fileTypes: ALL,
    message: "Text/background contrast below WCAG AA.",
    fix: "Pick a text token that reaches 4.5:1 (3:1 for large text) on that surface.",
    detect(ctx) {
      const out = [];
      for (const n of ctx.nodes) {
        if (/disabled|placeholder|selection|aria-disabled/i.test(n.selector))
          continue;
        const fg = colorOf(n, "fg");
        const bg = colorOf(n, "bg");
        if (!fg || !bg || fg.a < 1 || bg.a < 1) continue;
        const px = fontPx(n);
        const large =
          (px != null && px >= 24) ||
          hasCls(n, /^text-(2xl|3xl|4xl|5xl|6xl|7xl|8xl|9xl)$/);
        const need = large ? 3 : 4.5;
        const r = contrast(fg, bg);
        if (r < need)
          out.push({
            line: n.line,
            message: `Contrast ${r.toFixed(2)}:1 < ${need}:1 (WCAG AA).`,
          });
      }
      return out;
    },
  },
  {
    id: "tiny-text",
    tier: "immediate",
    severity: "warning",
    fileTypes: ALL,
    message: "Font size under 10px — illegible.",
    fix: "Use 12px+ (14-16px for body); 11-12px only for captions.",
    detect(ctx) {
      const out = [];
      for (const n of ctx.nodes) {
        const px = fontPx(n);
        if (px != null && px > 0 && px < 10 && !/^(sup|sub)$/.test(n.tag)) {
          out.push({
            line: n.line,
            message: `Font size ${+px.toFixed(1)}px — illegible.`,
          });
        }
      }
      return out;
    },
  },
  {
    id: "tiny-text-body",
    tier: "advisory",
    severity: "info",
    fileTypes: ALL,
    message: "Small text (10-11px, or text-xs) on what looks like body copy.",
    fix: "Body copy 14-16px. Keep 11-12px for badges, captions, legal.",
    detect(ctx) {
      const out = [];
      for (const n of ctx.nodes) {
        if (CAPTIONY.test(sel(n))) continue;
        const px = fontPx(n);
        if (px != null && px >= 10 && px < 12) {
          out.push({
            line: n.line,
            message: `Font size ${+px.toFixed(1)}px on non-caption element.`,
          });
        } else if (
          n.kind === "tag" &&
          n.tag === "p" &&
          hasCls(n, /^text-xs$/) &&
          n.text().length > 120
        ) {
          out.push({ line: n.line, message: "text-xs on a long paragraph." });
        }
      }
      return out;
    },
  },
  {
    id: "line-length",
    tier: "advisory",
    severity: "info",
    fileTypes: ALL,
    message: "Prose measure too wide (>80ch).",
    fix: "Cap body text at 45-75ch (max-width: 65ch / max-w-prose).",
    detect(ctx) {
      const out = [];
      const prosey =
        /(^|[\s.#>])(p|article)\b|prose|content|lead|copy|paragraph|description|body-text/;
      for (const n of ctx.nodes) {
        const mw = n.decls["max-width"];
        const ch = mw && /^(\d*\.?\d+)ch$/.exec(mw.trim());
        if (ch && +ch[1] > 80)
          out.push({
            line: n.line,
            message: `max-width ${mw} — measure over 80ch.`,
          });
        else if (
          mw &&
          prosey.test(sel(n)) &&
          toPx(mw) != null &&
          /px|rem/.test(mw) &&
          toPx(mw) >= 900
        )
          out.push({ line: n.line, message: `max-width ${mw} on prose.` });
        for (const k of n.classes) {
          const m = /^max-w-\[(\d*\.?\d+)ch\]$/.exec(k);
          if (m && +m[1] > 80) out.push({ line: n.line });
          if (
            /^max-w-(4xl|5xl|6xl|7xl)$/.test(k) &&
            (n.tag === "p" || hasCls(n, /^prose$/))
          )
            out.push({ line: n.line });
        }
        if (hasCls(n, /^prose$/) && hasCls(n, /^max-w-none$/))
          out.push({
            line: n.line,
            message: "prose with max-w-none — unbounded measure.",
          });
      }
      return out;
    },
  },
  {
    id: "skipped-heading",
    tier: "advisory",
    severity: "info",
    fileTypes: MK,
    message: "Heading level skipped.",
    fix: "Step one level at a time; restyle with classes instead of picking a different level.",
    detect(ctx) {
      const out = [];
      let prev = 0;
      for (const e of ctx.elements) {
        const m = /^h([1-6])$/.exec(e.tag);
        if (!m) continue;
        const lvl = +m[1];
        if (prev && lvl > prev + 1)
          out.push({
            line: e.line,
            message: `Heading jumps h${prev} -> h${lvl}.`,
          });
        prev = lvl;
      }
      return out;
    },
  },
  {
    id: "cramped-padding",
    tier: "advisory",
    severity: "info",
    fileTypes: ALL,
    message: "Buttons/cards with under 8px of horizontal padding.",
    fix: "Use the spacing scale: 12-16px horizontal on buttons, 16-24px on cards.",
    detect(ctx) {
      const out = [];
      for (const n of ctx.nodes) {
        const s = sel(n);
        if (!(n.tag === "button" || /\bbtn\b|button|card/.test(s))) continue;
        if (
          /icon|reset|unstyled|link|close|toggle/.test(s) ||
          hasCls(n, /^(size|w)-\d/) ||
          hasCls(n, /^sr-only$/)
        )
          continue;
        if (hasCls(n, /^(p|px)-(0\.5|1|1\.5)$/)) {
          out.push({ line: n.line });
          continue;
        }
        const p =
          n.decls["padding-inline"] ||
          n.decls["padding-left"] ||
          n.decls.padding;
        if (p) {
          const parts = p.trim().split(/\s+/);
          const h = toPx(parts.length >= 2 ? parts[1] : parts[0]);
          if (h != null && h > 0 && h < 8)
            out.push({
              line: n.line,
              message: `Horizontal padding ${p} — under 8px.`,
            });
        }
      }
      return out;
    },
  },
  {
    id: "all-caps-body",
    tier: "advisory",
    severity: "info",
    fileTypes: ALL,
    message: "All-caps on body copy.",
    fix: "Reserve uppercase for short labels (tracking-wide); set paragraphs in sentence case.",
    detect(ctx) {
      const out = [];
      const bodyish =
        /(^|[\s.#>,])(p|li|article|blockquote)\b|prose|paragraph|description|lede|\bcopy\b/;
      const labelish =
        /label|btn|button|eyebrow|badge|tag|title|heading|caption|nav|th\b|chip/;
      for (const n of ctx.nodes) {
        const up =
          /^uppercase$/.test(n.decls["text-transform"] || "") ||
          hasCls(n, /^uppercase$/);
        if (!up) continue;
        if (n.kind === "css") {
          if (
            bodyish.test(n.selector.toLowerCase()) &&
            !labelish.test(n.selector.toLowerCase())
          )
            out.push({ line: n.line });
        } else if (
          /^(p|li|blockquote|dd)$/.test(n.tag) ||
          n.text().length > 80
        ) {
          out.push({ line: n.line });
        }
      }
      return out;
    },
  },
  {
    id: "emoji-as-icon",
    tier: "advisory",
    severity: "info",
    fileTypes: ALL,
    message: "Emoji used as an icon/bullet. Craft floor REFUSE.",
    fix: "Use one drawn icon set at one stroke weight.",
    detect(ctx) {
      const out = [];
      const isEmoji = (cp) =>
        cp >= 0x1f000 ||
        (cp >= 0x2600 &&
          cp <= 0x27bf &&
          ![
            0x2605, 0x2606, 0x2713, 0x2714, 0x2715, 0x2716, 0x2717, 0x2718,
          ].includes(cp));
      const leadingEmoji = (s) => {
        const cp = s.trim().codePointAt(0);
        return (
          cp != null &&
          isEmoji(cp) &&
          /\p{Extended_Pictographic}/u.test(String.fromCodePoint(cp))
        );
      };
      const re = />([^<>{}]+)</g;
      let m;
      while ((m = re.exec(ctx.markup || ""))) {
        if (leadingEmoji(m[1]))
          out.push({
            line: ctx.lineAt(
              m.index + 1 + (m[1].length - m[1].trimStart().length),
            ),
          });
      }
      const prop = /\bicon\w*\s*[=:]\s*\{?\s*["'`]([^"'`]{1,8})["'`]/g;
      while ((m = prop.exec(ctx.clean)))
        if (leadingEmoji(m[1])) out.push({ line: ctx.lineAt(m.index) });
      const content = /content\s*:\s*["']([^"']{1,8})["']/g;
      while ((m = content.exec(ctx.clean)))
        if (leadingEmoji(m[1])) out.push({ line: ctx.lineAt(m.index) });
      return out;
    },
  },
  {
    id: "pure-black-white",
    tier: "immediate",
    severity: "warning",
    fileTypes: ALL,
    message: "Pure #000 text on pure #fff. Craft floor REFUSE.",
    fix: "Tinted near-black on tinted near-white from the tokens; contrast stays AA without the glare.",
    detect(ctx) {
      const out = [];
      for (const n of ctx.nodes) {
        const fg = colorOf(n, "fg");
        const bg = colorOf(n, "bg");
        if (pure(fg, 0) && pure(bg, 255)) out.push({ line: n.line });
        else if (
          n.kind === "css" &&
          /^(html|body|:root)$/.test(n.selector) &&
          pure(fg, 0)
        )
          out.push({
            line: n.line,
            message: "Pure #000 body text. Craft floor REFUSE.",
          });
      }
      return out;
    },
  },
  {
    id: "design-system-drift",
    tier: "immediate",
    severity: "warning",
    fileTypes: ALL,
    message: "Hex color not defined in DESIGN.md tokens.",
    fix: "Use the token (var(--color-*)) or add the color to DESIGN.md via /form-tokens first.",
    detect(ctx) {
      const t = ctx.designMd;
      if (
        !t ||
        !t.hex ||
        t.hex.size < 3 ||
        TOKEN_FILE.test(ctx.file.replace(/\\/g, "/"))
      )
        return [];
      const out = [];
      const re = /#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3,4}\b/g;
      const check = (text, line) => {
        let m;
        re.lastIndex = 0;
        while ((m = re.exec(text))) {
          const h = hexNorm(m[0]);
          if (!h || h === "ffffff" || h === "000000" || t.hex.has(h)) continue;
          out.push({ line, message: `${m[0]} is not in DESIGN.md tokens.` });
        }
      };
      for (const n of ctx.nodes) {
        for (const d of n.declList)
          if (!d.prop.startsWith("--")) check(d.value, d.line);
        for (const k of n.classes) if (/\[#/.test(k)) check(k, n.line);
      }
      return out;
    },
  },
  {
    id: "design-system-drift-scale",
    tier: "advisory",
    severity: "info",
    fileTypes: ALL,
    message: "Font size or radius not on the DESIGN.md scale.",
    fix: "Use a scale step from DESIGN.md or add it via /form-tokens.",
    detect(ctx) {
      const t = ctx.designMd;
      if (
        !t ||
        !t.scale ||
        t.scale.size < 3 ||
        TOKEN_FILE.test(ctx.file.replace(/\\/g, "/"))
      )
        return [];
      const out = [];
      const off = (v) => {
        const px = toPx(v);
        return (
          px != null &&
          px > 1 &&
          px < 100 &&
          !t.scale.has(Math.round(px * 100) / 100)
        );
      };
      for (const n of ctx.nodes) {
        for (const d of n.declList) {
          if (
            (d.prop === "font-size" || d.prop === "border-radius") &&
            !/\s/.test(d.value.trim()) &&
            off(d.value)
          ) {
            out.push({
              line: d.line,
              message: `${d.prop}: ${d.value} is not in the DESIGN.md scale.`,
            });
          }
        }
        for (const k of n.classes) {
          const m = /^(?:text|rounded)-\[(\d*\.?\d+(?:px|rem))\]$/.exec(k);
          if (m && off(m[1]))
            out.push({
              line: n.line,
              message: `${k} is not in the DESIGN.md scale.`,
            });
        }
      }
      return out;
    },
  },
];

module.exports = { rules };
