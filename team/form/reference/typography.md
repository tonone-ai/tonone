# Typography Reference

## Vertical Rhythm

Establish a 4px baseline grid. Every line-height must be a multiple of 4px. This produces visual rhythm across a page — elements feel like they belong to the same system.

```
Base: 4px grid
Body (16px text): line-height 24px (6 units)
Small (14px text): line-height 20px (5 units)
Heading LG (30px): line-height 36px (9 units)
Heading XL (48px): line-height 56px (14 units)
```

When line-heights don't land on the grid, paragraphs and headings fall out of rhythm when stacked. It's invisible until you stack 10 sections — then the page looks wrong and nobody knows why.

## Modular Type Scale

Pick one ratio. Apply it consistently to all size steps. Never add a font size outside the scale.

Common ratios:

- **1.25 (major third)** — compact, dense UI, data-heavy products
- **1.333 (perfect fourth)** — balanced, works for most products
- **1.5 (perfect fifth)** — editorial, expressive, large screens

Example scale with 1.333 ratio, 16px base:

| Step | Size | Role                           |
| ---- | ---- | ------------------------------ |
| xs   | 10px | Labels, captions, legal        |
| sm   | 12px | Secondary labels, metadata     |
| base | 14px | UI text, secondary body        |
| md   | 16px | Body copy (base)               |
| lg   | 18px | Large body, lead paragraphs    |
| xl   | 21px | Small headings, section labels |
| 2xl  | 28px | Subheadings, card titles       |
| 3xl  | 37px | Page headings                  |
| 4xl  | 50px | Hero headings                  |
| 5xl  | 67px | Display, marketing             |

Snap to whole pixels or half-pixels for screen rendering. The ratio gives you starting points, not final values.

Practical scale used in most products: `12 / 14 / 16 / 18 / 20 / 24 / 30 / 36 / 48 / 60 / 72`

## Font Selection Process

In order. Don't skip steps.

1. **Define brand adjectives** — "precise and confident" leads to different type choices than "warm and approachable." Type without brand adjectives is guessing.
2. **Shortlist 3–5 families** that match the adjectives. Consider: geometric sans, humanist sans, transitional serif, contemporary serif, monospace. Each has a personality.
3. **Test at body size first (16px)** — not at 48px in a mockup. If it doesn't read well at body size, it fails for most of the product.
4. **Check x-height** — larger x-height means better screen readability at small sizes. Compare by setting "x" in multiple families at 16px.
5. **Verify character set** — covers all languages needed, including extended Latin for European markets at minimum.
6. **Check OpenType features** — tabular figures for numbers, old-style figures for body, ligatures. Missing tabular figures breaks data tables.
7. **Test light/dark** — thin weights and low-contrast letter forms fall apart on dark backgrounds. Test the actual rendering, not the font specimen.
8. **Pair: contrast in structure, harmony in proportion** — pair a geometric sans with a humanist serif, or a wide sans with a condensed serif. Don't pair two fonts that look almost identical or two fonts that feel from completely different eras.

## Fonts to Reject (AI Default Markers)

These fonts signal "I didn't think about typography." If you're choosing one, document a specific reason — or choose something else.

- **Inter** — overused to the point of invisibility. Fine technically, but carries zero brand signal in 2024+. Justification required.
- **Poppins** — geometric, even, generic. Popular in no-design-budget contexts. Almost never the right choice.
- **Montserrat** — geometric sans with no distinguishing character. Used on every startup landing page 2015–2020.
- **Roboto** — Google's system font. Correct for Android products. Wrong for anything else.
- **Open Sans** — overly neutral. Designed for maximum inoffensiveness, which is also maximum forgettability.
- **Lato** — same category as Open Sans. Humanist but characterless.
- **Nunito** — rounded, friendly, used for every "approachable" product. The roundness reads as amateur without careful use.

If the brand adjectives genuinely point to one of these, document it. "We use Inter because our users are developers who distrust visual flourish and expect GitHub-adjacent aesthetics" is a valid reason. "We use Inter because it's the default" is not.

Better alternatives by archetype:

- Developer/technical precision: **Berkeley Mono**, **Geist**, **JetBrains Mono**
- Clean/modern/professional: **Instrument Sans**, **DM Sans**, **Plus Jakarta Sans**
- Humanist/warm: **Figtree**, **Outfit**, **Bricolage Grotesque**
- Editorial/expressive: **Fraunces**, **Newsreader**, **Playfair Display**
- Geometric/confident: **Cabinet Grotesk**, **Clash Grotesk**, **Satoshi**

## Web Font Loading

Performance and stability. Both matter.

```html
<!-- 1. Preload critical fonts -->
<link
  rel="preload"
  href="/fonts/primary-regular.woff2"
  as="font"
  type="font/woff2"
  crossorigin
/>

<!-- 2. Font face declaration -->
<style>
  @font-face {
    font-family: "PrimaryFont";
    src: url("/fonts/primary-regular.woff2") format("woff2");
    font-weight: 400;
    font-style: normal;
    font-display: swap;
    /* Metric-matched fallback to reduce layout shift */
    ascent-override: 90%;
    descent-override: 22%;
    line-gap-override: 0%;
    size-adjust: 103%;
  }
</style>
```

Rules:

- `font-display: swap` always — prevents invisible text during load
- Self-host via [fontsource](https://fontsource.org/) — removes Google Fonts dependency, improves privacy, allows font subsetting
- Metric-matched fallback with `size-adjust`, `ascent-override`, `descent-override` — reduces cumulative layout shift when font loads
- Max 2 font families — each family with 2–3 weights. More than this is a performance and maintenance problem.
- Subset to used character ranges — saves 60–80% of file size for Latin-only products

## Fluid Typography

Use `clamp()` for sizes that need to respond to viewport. Apply sparingly — only heading and body, not every scale step.

```css
/* Heading: 30px at mobile, scales to 48px at large viewport */
font-size: clamp(1.875rem, 1.2rem + 2.5vw, 3rem);

/* Body: 15px at mobile, 17px at large viewport */
font-size: clamp(0.9375rem, 0.75rem + 0.8vw, 1.0625rem);
```

Formula to derive: `clamp(MIN, PREFERRED, MAX)` where `PREFERRED = MIN_REM + (MAX_PX - MIN_PX) / (MAX_VIEWPORT - MIN_VIEWPORT) * 100vw`. Use [utopia.fyi](https://utopia.fyi/) to calculate values automatically.

Don't apply fluid sizing to every type step — it makes the scale unpredictable across breakpoints. Fluid for the 2–3 sizes that matter most.

## OpenType Features

Enable these in CSS for quality typography. Most quality web fonts support them.

```css
/* Always on */
font-kerning: normal;
font-feature-settings:
  "liga" 1,
  "kern" 1;

/* Body text with old-style figures */
.body-text {
  font-feature-settings:
    "liga" 1,
    "onum" 1,
    "kern" 1;
}

/* Data tables, code, financial figures */
.tabular-data {
  font-feature-settings:
    "tnum" 1,
    "kern" 1;
  font-variant-numeric: tabular-nums;
}

/* Small caps headings or labels */
.label-caps {
  font-variant-caps: small-caps;
  font-feature-settings: "smcp" 1;
}
```

- **liga**: standard ligatures (fi, fl, ff) — prevents awkward letter collisions
- **onum**: old-style figures — numbers that descend below baseline, better for running text
- **tnum**: tabular figures — equal-width numbers, essential for columns and data
- **kern**: kerning — letter pair spacing, should always be on
- **smcp**: small caps — for uppercase labels that don't shout

## Letter-Spacing

Counterintuitive but important rules.

| Context                         | Value              | Reason                                                        |
| ------------------------------- | ------------------ | ------------------------------------------------------------- |
| Body text                       | 0 (never add)      | Typeface already optically spaced for reading                 |
| Large headings (>36px)          | -0.01em to -0.03em | Optical tightening; wide spacing looks wrong at display sizes |
| All-caps labels                 | +0.05em to +0.1em  | Caps need spacing to breathe and remain legible               |
| Small caps                      | +0.03em to +0.06em | Same reason as all-caps                                       |
| Numeric codes, tracking numbers | 0.02em to 0.05em   | Aids scanability                                              |

Adding letter-spacing to body text is one of the most common typography mistakes. It slows reading speed and signals unfamiliarity with typography basics.

## Line-Height

| Context               | Value   |
| --------------------- | ------- |
| Body text             | 1.5–1.6 |
| Large headings        | 1.1–1.2 |
| Medium headings       | 1.2–1.3 |
| UI labels and buttons | 1.2–1.4 |
| Code blocks           | 1.6–1.8 |
| Captions              | 1.4–1.5 |

Tighter line-height on larger text, looser on smaller text. Large text at 1.5 line-height looks like a list. Small text at 1.1 line-height is unreadable.

## Measure (Line Length)

Optimal reading measure: 45–75 characters per line for body text. At 16px with a typical sans-serif, this is approximately 480–680px container width.

Token:

```css
--prose-max-width: 68ch;
```

Use `ch` units — they scale with the actual font in use, unlike fixed px widths.

UI components (cards, sidebar items, form fields) are not prose and don't follow this rule. Apply measure constraints to body copy and long-form content only.

## Medium-Form Relationship

Typefaces are designed for specific media. A font that excels in print may fail on screen, and vice versa.

**Print-optimized faces** (Garamond, Caslon, Bembo): designed for high-resolution offset printing. Thin strokes, subtle serifs, delicate details. At screen resolution (72–144 DPI), these features blur or disappear.

**Screen-optimized faces** (Georgia, Verdana, and most post-2010 type): designed for pixel grids. Larger x-height, sharper serif terminals, stronger stroke contrast, wider letterforms. These features maintain clarity at low resolution and small sizes.

Rule: when choosing a serif for screen, prefer faces designed for digital: Georgia, Newsreader, Source Serif, Literata. Reserve Garamond and its kin for print or large display sizes (32px+).

## Letter Structure Categories

Typefaces fall into structural families. Understanding the structure helps with pairing and avoids the "uncanny valley" of two fonts that are almost identical.

| Category      | Structure                                                | Examples                          | Character                           |
| ------------- | -------------------------------------------------------- | --------------------------------- | ----------------------------------- |
| **Humanist**  | Calligraphic origins, varied stroke width, organic forms | Gill Sans, Frutiger, Figtree      | Warm, approachable, human           |
| **Geometric** | Built from circles and lines, uniform stroke width       | Futura, Century Gothic, DM Sans   | Modern, precise, designed           |
| **Realist**   | Neutral, no obvious calligraphic or geometric origin     | Helvetica, Arial, Instrument Sans | Professional, invisible, functional |

**The "n" test:** set a lowercase "n" in each candidate font at body size. Humanist "n" has visible stroke variation and a calligraphic arch. Geometric "n" has uniform strokes and a circular arch. Realist "n" sits between — functional, not expressive.

Pairing rule: pair fonts from different structural categories for contrast (humanist sans + geometric serif), or the same category for harmony (two humanists with different proportions). Never pair two fonts from the same category with similar proportions — the subtle differences read as a mistake.

## Typographic Etiquette

Rules that distinguish intentional typography from uncontrolled text:

| Rule                      | Wrong                                          | Right                                                          |
| ------------------------- | ---------------------------------------------- | -------------------------------------------------------------- |
| **Quotes**                | "straight quotes"                              | "smart quotes" (curly)                                         |
| **Apostrophes**           | it's (tick mark)                               | it's (true apostrophe)                                         |
| **Dashes**                | hyphen for ranges (1-10)                       | en dash for ranges (1–10), em dash for breaks (—)              |
| **Spaces after periods**  | Two spaces.                                    | One space.                                                     |
| **Justified text on web** | Justified paragraphs with rivers of whitespace | Left-aligned (ragged right) — browsers lack proper hyphenation |
| **Bold and italic**       | Browser-synthesized (faux bold/italic)         | Load the actual bold and italic font weights                   |
| **Small caps**            | Scaled-down capitals (FAKE)                    | True small caps via OpenType (`font-variant-caps: small-caps`) |

Fake bold, fake italic, and fake small caps are **critical failures** — they are visible quality indicators that signal "this was not designed." Browsers synthesize these by algorithmically stretching or slanting the regular weight, producing muddy, distorted letterforms.

Always load the specific font weights and styles you use. If a weight doesn't exist in the family, choose a different family rather than faking it.
