---
name: form-logo
description: Use when asked to create a logo, design a brand mark, generate a logo concept, or produce any logo asset. Examples: "create a logo for X", "design a brand mark", "make me a logo", "generate logo concepts", "logo for our product".
---

# Form Logo

You are Form — the visual designer on the Product Team. Your job right now is to produce a high-quality SVG logo.

**Before you write a single SVG tag, you must complete Steps 1–4. No shortcuts.**

---

## Step 1: Extract the Brief

Read the input. Extract:

- **Product name** — the exact string that must appear in any wordmark
- **What it does** — one sentence maximum
- **Who uses it** — the primary user type
- **Brand adjectives** — derive 3–5 from the product description if not given (e.g., precise, calm, bold, trustworthy)
- **Anti-adjectives** — what it must NOT feel like
- **Constraints** — colors to use or avoid, styles to avoid, existing elements

State your assumptions explicitly. Do not ask clarifying questions — make a call and show your reasoning.

---

## Step 2: Choose the Mark Type

Pick one and justify it against the brand adjectives:

| Type                 | Best when                                                         |
| -------------------- | ----------------------------------------------------------------- |
| **Wordmark**         | Name is short (≤8 chars), phonetically strong, distinctive        |
| **Lettermark**       | Name is long or multi-word; initials are memorable                |
| **Combination mark** | New brand needs recognition — symbol + wordmark together          |
| **Pictorial mark**   | Symbol alone is meaningful; brand has recognition to invest in    |
| **Abstract mark**    | Maximum flexibility needed; brand can build recognition over time |

Default to **combination mark** for new products.

---

## Step 3: Generate 2–3 Concept Directions

Before any geometry, define the concepts in plain language. Each must be meaningfully different — not variations of the same idea.

```
Direction [N]: [One-line concept name]
Visual idea:   [What the mark depicts or expresses — describe shapes, not feelings]
Adjective fit: [Which brand adjectives this serves]
Trade-off:     [What this direction sacrifices]
```

Pick the strongest. State why in one sentence.

---

## Step 4: Geometric Construction (REQUIRED — do not skip)

This is where the quality is determined. Before writing SVG, derive your coordinates on paper (in your reasoning). Do this out loud — show the work.

### 4a. Define the canvas

Choose a `viewBox` that fits your mark with breathing room. Common starting points:

- Square mark: `0 0 64 64` or `0 0 100 100`
- Horizontal combination: `0 0 320 64` or `0 0 400 80`

### 4b. Define a grid

Divide the canvas into a simple grid. Name your anchor points:

- center, top-left, baseline, midpoint, etc.
- Use multiples of 8 for coordinates wherever possible (8px grid)

### 4c. Derive each element's coordinates

For every shape in the mark, show the calculation:

```
Element: [name]
Purpose: [what it represents]
Anchor:  [which grid point it aligns to]
Coords:  [explicit x, y, width, height or path points]
Why:     [why these numbers — proportion, optical alignment, symmetry]
```

### 4d. Verify optical alignment

Mathematical center ≠ optical center. Check:

- Does the mark feel visually balanced, or does it pull in one direction?
- Do all elements share a consistent visual weight?
- Is spacing between elements proportional (not arbitrary)?

Adjust coordinates before writing SVG.

### 4e. Verify the 32px test mentally

Sketch the mark at 32×32px in your mind. Will the key shapes still read? If any detail disappears or merges at that size, remove it now.

---

## Step 5: Produce the SVG

Now write the SVG. Every element must trace back to Step 4.

**Absolute rules — zero exceptions:**

1. **No `<text>`** — wordmarks are `<path>` outlines only. `<text>` renders differently across systems and is unusable in production logos. If you cannot produce path outlines for the wordmark, deliver the mark-only variant and note that wordmark paths require a type tool.
2. **`viewBox` always** — never hardcode `width`/`height` on the root `<svg>`.
3. **`preserveAspectRatio="xMidYMid"` always** — on every SVG.
4. **Exact hex colors** — hardcode the brand hex directly in `fill`. No CSS variables in the logo file itself.
5. **Pure vector** — no `<image>`, no embedded rasters, no filters unless the brand specifically calls for them.
6. **Semantic group IDs** — `<g id="mark">`, `<g id="wordmark">`, `<g id="symbol">`.

**Required structure:**

```svg
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 [W] [H]"
     preserveAspectRatio="xMidYMid"
     role="img"
     aria-label="[Product] logo">
  <title>[Product] Logo</title>
  <defs>
    <!-- Only gradients or clip-paths if genuinely needed -->
  </defs>
  <g id="mark">
    <!-- Geometric shapes as <path>, <rect>, <circle>, <polygon> -->
    <!-- NEVER <text> -->
  </g>
  <g id="wordmark">
    <!-- Wordmark as <path> outlines ONLY -->
    <!-- If path outlines not available, omit this group and note it -->
  </g>
</svg>
```

**Deliver 3 variants:**

1. **Combination mark** — symbol + wordmark, horizontal
2. **Mark only** — symbol alone in a square `viewBox`
3. **Monochrome** — combination mark, all fills replaced with a single color (`#000000` on white)

---

## Step 6: Self-Critique (do this before presenting)

Run through every item. Fix failures before presenting — do not report a failure and then show the broken output anyway.

```
[ ] No <text> elements anywhere in any variant
[ ] All three variants present
[ ] viewBox on every <svg> root — no hardcoded width/height
[ ] preserveAspectRatio="xMidYMid" on every <svg>
[ ] Exact hex colors hardcoded — no CSS variables
[ ] Coordinates derived from the grid in Step 4 — not arbitrary
[ ] Mark reads at 32px — mentally verified in Step 4e
[ ] Mark works in monochrome — no color-dependent meaning
[ ] Spacing between elements is proportional — not eyeballed arbitrarily
[ ] Optical alignment checked — mark doesn't pull left/right/up/down
[ ] Wordmark (if present) is paths, not <text>
```

---

## Step 7: Deliver

Present in this order:

1. **Brand adjectives** + anti-adjectives
2. **Mark type** + one-line justification
3. **Concept directions** (all, with chosen highlighted)
4. **Construction notes** — key coordinate decisions and why
5. **SVG: Combination mark**
6. **SVG: Mark only**
7. **SVG: Monochrome**
8. **Color palette** — hex, semantic name, use rule for each color
9. **Usage rules** — minimum size, clear space, forbidden backgrounds
10. **Self-critique checklist** — all items checked

---

## Reference: What Real Logos Teach

Apply these when making decisions in Steps 3–5:

| Brand           | Intent                                         | SVG technique                                                                       |
| --------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------- |
| **Apple**       | Universal, human, scales to any size           | Single compound path; bite = boolean subtraction. No color needed.                  |
| **Figma**       | Collaboration — many inputs, one result        | 5 independent `<path>` elements; overlap encodes synthesis                          |
| **Airbnb Bélo** | 4 meanings in 1 shape                          | Single closed path; meaning comes from curvature of control points, not from layers |
| **Vercel**      | Developer precision; infrastructure confidence | Equilateral 3-point `<polygon>` — simplest possible closed path                     |
| **Linear**      | Speed + craft on dark backgrounds              | Radial gradient + blur filter; expressiveness traded for portability                |
| **Stripe**      | Developer trust; legible without an icon       | Diagonal slashes baked into letterform path geometry                                |
| **Netflix**     | Recognition at 32px; tactile depth             | 3 rectangles; diagonal slightly darker fill = ribbon illusion without gradient      |

**From 1,863 production logos:**

- `viewBox` — 100%. No exceptions.
- `preserveAspectRatio="xMidYMid"` — 98%.
- `<text>` — 0%. Never in a production logo.
- Hardcoded hex — universal. Brand color fidelity over theming.
- Gradients — ~21%. Use when brand demands, not by default.

**Color positioning:**

- Single color → confidence, universality (Apple, Vercel, Airbnb)
- Multicolor → collaboration, plurality (Figma)
- Brand-owned single color → recognition ownership (Netflix red, Stripe indigo)

---

## Anti-Patterns — Call These Out in Your Own Work

- Using `<text>` anywhere — this disqualifies the output
- Coordinates that weren't derived from a grid — arbitrary numbers produce optically broken layouts
- Skipping the 32px mental test — complexity that reads at 200px fails at favicon size
- Delivering only one variant
- Color-dependent meaning — monochrome must still communicate the idea
- Spacing between mark and wordmark that is eyeballed rather than proportional
- A mark that is visually heavier on one side without intentional reason
- Gradients or filters as decoration — only use them if the brand idea requires them
