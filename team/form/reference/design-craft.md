# Design Craft Reference

## 5-Step Craft Flow

The sequence matters. Skipping steps produces rework.

### 1. Shape

Understand the feature before designing anything. What problem does it solve? Who uses it? What's the happy path and what are the edge cases? If a wireframe or flow exists from Draft, read it. If not, sketch the content structure on paper first.

Questions to answer before touching visual design:

- What is the primary action on this surface?
- What does the user need to know before they can act?
- What happens when there's no data (empty state)?
- What happens with too much data (overflow state)?
- What happens when an action fails?

### 2. Load References

Read the relevant design documentation before designing:

- Active brand adjectives
- Color token set and use rules
- Type scale and semantic roles
- Spacing system
- Existing components that should be reused or extended

Don't design from memory. The reference check takes 2 minutes and prevents an hour of rework.

### 3. Build

Sequence matters within the build step:

1. **Structure** — semantic HTML/component hierarchy first. Get the content structure right before applying any visual treatment.
2. **Layout** — position elements in space. Grid, spacing, alignment.
3. **Typography** — apply type scale, weights, line-heights.
4. **Color** — apply color tokens. Surfaces first, then text, then interactive, then accent.
5. **States** — design all interactive states: default, hover, focus, active, disabled, error, loading.
6. **Motion** — only after states are correct. Motion amplifies interaction; it doesn't substitute for missing states.
7. **Responsive** — adapt from the designed viewport to the full range. Container queries first, viewport breakpoints second.

### 4. Visual Iteration

Don't ship the first pass.

- Test at multiple sizes: 375px mobile, 768px tablet, 1280px desktop, 1920px wide
- Run the squint test (see `spatial-design.md`)
- Check all interactive states
- Verify contrast on all text/background pairs
- Run the AI slop check (see next section)
- Get a second set of eyes when possible

### 5. Present

Show work with rationale. The design decision is incomplete without its justification.

Format: "I chose [X] because [brand adjective/constraint/user need]. I considered [Y] but rejected it because [reason]."

This trains the team to evaluate design decisions on criteria, not taste. It also forces the designer to verify their own reasoning before presenting.

---

## AI Slop Detection

Run this checklist before delivering any visual work. Each item below is a signal of low-effort or unintentional design — the kind of output that emerges when tools make decisions instead of designers.

### The 24 Anti-Patterns

**Typography**

- [ ] Using Inter, Poppins, Montserrat, Roboto, Open Sans, Lato, or Nunito without a documented reason
- [ ] All text centered with no hierarchy rationale
- [ ] Letter-spacing added to body text
- [ ] No variation in font weight across the hierarchy

**Color**

- [ ] Purple-to-blue gradient as the default accent (the #1 AI color tell)
- [ ] Pure grays with no brand hue tinting
- [ ] Saturated accent color used at more than 10% of visual surface area
- [ ] Color-only state indicators (no icon or text backup for colorblind users)

**Layout and Spacing**

- [ ] Identical padding on every element (`padding: 16px` everywhere)
- [ ] Card grids when a simple list or table would work better
- [ ] Nested cards
- [ ] No empty state designed
- [ ] Hamburger menu on a desktop layout

**Components**

- [ ] Identical rounded corners on every element regardless of role
- [ ] Shadows on every card, panel, and container
- [ ] Icons mixed from 3+ different icon sets or styles
- [ ] No hover, focus, or active states on interactive elements
- [ ] Decorative elements that don't serve visual hierarchy

**Content**

- [ ] Lorem ipsum or placeholder text shipped
- [ ] Stock photo hero sections
- [ ] "Welcome to our platform" heading (no specificity)

**Motion and Accessibility**

- [ ] Animations without `prefers-reduced-motion` query
- [ ] Focus styles removed (`outline: none` without replacement)
- [ ] Interactive elements below 44×44px touch target

**Scoring**: 0 items checked = ship. 1–3 items = fix before shipping. 4+ items = rebuild pass required.

### The AI Direction Test

Before any visual decision, state a specific aesthetic direction in 2–3 words (e.g., "brutalist editorial", "warm minimalism", "dense precision"). Then ask:

> **"Would a different AI, given the same brief, make this exact same choice?"**

If the answer is yes, the choice is a default, not a decision. Defaults converge — that's how AI slop happens. A specific aesthetic direction produces divergent, intentional choices.

"Clean and modern" is the absence of direction, not a direction. It produces the same output regardless of brand, audience, or positioning. Replace it with words that actually constrain choices.

Examples:

- "Clean and modern" → every AI produces Inter, blue palette, rounded cards, centered layout
- "Dense precision" → tabular data, monospace accents, tight spacing, minimal decoration
- "Warm editorial" → serif headings, warm neutrals, generous whitespace, asymmetric layout
- "Industrial utility" → dark backgrounds, high contrast, system fonts, raw structural elements

The direction words become a filter: for every font, color, spacing, and layout choice, ask "does this serve [direction words]?" If it doesn't, cut it.

---

## Bolder Principles

When a design reads as too safe, too generic, or visually indistinguishable from competitors, push in these directions:

1. **Push typography contrast** — increase the size differential between heading and body. If heading is 1.5× body, try 2.5×. If regular weight is used, try black (900) weight.
2. **Add asymmetry** — break the grid in one intentional place. A full-bleed element, an offset column, a large pull quote that breaks the text margin.
3. **Use more saturated colors** — if the palette feels washed out, increase chroma on the accent. `oklch(0.55 0.18 250)` vs `oklch(0.55 0.08 250)` — the chroma does the work.
4. **Increase size differentials** — the largest element on the page should feel large. If the biggest thing is 32px and the body is 16px, try 48px or 60px for the dominant element.
5. **Add one signature visual element** — a distinctive pattern, texture, or shape used consistently. One. Not five.

The goal is intentional distinctiveness. Each push should be traceable to a brand adjective.

## Quieter Principles

When a design is overstimulating, visually noisy, or exhausting to look at:

1. **Reduce to 2–3 colors + neutrals** — strip everything back to primary, secondary, and neutral. If it still works with 3 colors, the rest were noise.
2. **Remove decorative elements** — anything that doesn't carry information or reinforce hierarchy. Dividers, ornaments, background patterns — remove them one at a time until something is missed.
3. **Increase whitespace** — double the padding on sections and containers. The first draft is almost always too dense.
4. **Reduce shadows and borders** — eliminate shadows first. Then reduce borders to only where containment is functionally needed.
5. **Simplify animation** — remove all transitions. Add back only the one or two that orient the user (a panel sliding in, a button acknowledging a press). Everything else is noise.

The goal is clarity. The user came to do something. Make the path to that action shorter by removing everything else.

---

## Critique Framework

Evaluate designs across 6 dimensions. Score each 1–5. Total ÷ 6 = design readiness score.

| Dimension                    | 1 (Failing)                                      | 5 (Excellent)                                           |
| ---------------------------- | ------------------------------------------------ | ------------------------------------------------------- |
| **Visual hierarchy**         | Can't identify primary action or content         | Clear dominant element, obvious reading path            |
| **Information architecture** | Content organization is unclear or arbitrary     | Structure matches user mental model                     |
| **Emotional resonance**      | Design contradicts brand adjectives              | Design embodies adjectives; creates intended feeling    |
| **Cognitive load**           | Multiple simultaneous decisions; memory required | Progressive disclosure; one primary decision per screen |
| **Accessibility**            | Fails contrast, missing states, keyboard broken  | Passes AA, all states designed, keyboard complete       |
| **Consistency**              | Elements break system rules throughout           | Every element references the token layer                |

Score ≥ 4.0: ready to ship. Score 3.0–3.9: fix the lowest dimension. Score < 3.0: needs significant rework before engineering handoff.
