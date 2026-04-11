# Spatial Design Reference

## 4pt Base Spacing System

Every margin, padding, and gap in the system comes from this scale. No exceptions, no ad hoc values.

```
4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128
```

As CSS tokens:

```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;
--space-20: 80px;
--space-24: 96px;
--space-32: 128px;
```

Rule of thumb for common use:

- `4px` — micro gaps, icon-to-label spacing, intra-component nudges
- `8px` — tight internal padding, list item gaps
- `12px, 16px` — standard internal component padding
- `20px, 24px` — comfortable padding, section sub-groups
- `32px, 40px` — section spacing, card padding at comfortable density
- `48px, 64px` — major section breaks, hero vertical padding
- `80px, 96px, 128px` — page-level structural spacing, above-fold sections

If a value between scale steps is needed, the component probably needs redesigning, not a custom spacing value.

## Self-Adjusting Grid

Don't hardcode column counts. Use CSS Grid with `auto-fill` or `auto-fit` and `minmax()`. Components should reflow gracefully.

```css
/* Card grid that goes from 1 to N columns automatically */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-6); /* 24px */
}

/* Use auto-fit (collapses empty tracks) vs auto-fill (preserves them) */
/* auto-fit: better for centered layouts with few items */
/* auto-fill: better for left-aligned grids */
```

Column count breakpoints, if explicit control is needed:

```css
.grid {
  display: grid;
  grid-template-columns: 1fr; /* mobile */
}

@media (min-width: 640px) {
  .grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

Prefer `auto-fill` + `minmax` over explicit breakpoints wherever possible. Less code, more resilient.

## The Squint Test

Step back from the screen (or literally squint) until all text becomes illegible. What you see is the pure shape language of the hierarchy.

A well-designed layout passes the squint test when:

- The primary action or primary content cluster is visually dominant
- The hierarchy has at least 2–3 distinct visual weights
- Empty areas feel intentional, not empty

A layout fails the squint test when:

- Everything looks the same density and weight
- The eye doesn't know where to start
- Content and controls are indistinguishable in shape

If the squint test fails, the solution is almost never "add more visual elements." It's: increase size differential between levels, increase whitespace around primary content, reduce visual weight of secondary elements.

## Hierarchy Through Multiple Dimensions

Strong visual hierarchy uses at least 3 simultaneous contrast dimensions. Relying on a single dimension produces weak hierarchy.

| Dimension | Examples                                  |
| --------- | ----------------------------------------- |
| Size      | Heading 48px vs body 16px                 |
| Weight    | Bold 700 vs regular 400                   |
| Color     | Brand color vs neutral gray               |
| Space     | 64px above primary vs 8px above secondary |
| Position  | Left-aligned vs indented                  |
| Opacity   | Full vs 60%                               |

Primary headings should use at least 3 of these dimensions of contrast vs body text. If a "heading" is only different from body text in one dimension (usually size), it doesn't carry hierarchy — it's just bigger text.

## Cards

Cards are often overused. Ask before adding a card:

**Use cards when:**

- Content is independently scannable as a complete unit
- Items are being compared side-by-side
- Each item is independently actionable (has its own CTA or navigation)

**Don't use cards when:**

- Items are sequential steps in a process (use numbered layout or timeline)
- Items are attribute pairs of a single entity (use a detail view or table)
- The card is just visual padding around text on a flat background (use whitespace)
- You need to convey a simple list (use a list)

Never nest cards inside cards. A card-in-card creates ambiguous hierarchy and double-borders that feel visually trapped.

Card structure principles:

```
Card padding: --space-6 (24px) standard, --space-4 (16px) compact
Card gap: --space-4 to --space-6 between cards
Card corner radius: consistent with the design system's border-radius token (don't vary per card)
Card border/shadow: one or the other, not both
```

## Container Queries

Prefer `@container` over `@media` for component-level responsiveness. Components should respond to their available container width, not the viewport.

```css
/* Define a containment context */
.card-wrapper {
  container-type: inline-size;
  container-name: card;
}

/* Component adapts to container, not viewport */
@container card (min-width: 400px) {
  .card {
    display: grid;
    grid-template-columns: 120px 1fr;
  }
}
```

When to use `@media` vs `@container`:

- `@media`: global layout changes (sidebar visibility, navigation mode, page-level structure)
- `@container`: component-level adaptation (card layout, form field stacking, sidebar widget density)

## Optical Adjustments

Mathematical alignment is not the same as visual alignment. Always adjust optically after mathematical placement.

Common corrections:

- **Icons next to text**: center the icon mathematically, then nudge 1–2px upward. The visual weight of most icons sits below the geometric center.
- **Rounded shapes vs squares**: a circle at the same mathematical size as a square looks smaller. Increase circle/rounded element size by ~2% to achieve optical parity.
- **Vertical centering with text**: top padding slightly less than bottom padding feels visually centered. Mathematical 50/50 split reads as bottom-heavy.
- **Capital letters**: text starting with a capital letter (especially round ones like O, C, G) optically overshoots the baseline grid. Adjust line by ~1px optically.
- **Icon alignment in buttons**: icons and text in the same button row — the icon bottom should align with text baseline, not the text bounding box center.

These are small. They compound. A UI with careful optical adjustments feels "finished" even before a single animation is added.

## Touch Targets

Minimum sizes are non-negotiable for accessibility. Apply to every interactive element.

| Standard             | Minimum size              | Gap between targets |
| -------------------- | ------------------------- | ------------------- |
| WCAG 2.5.5 (AAA)     | 44×44px                   | —                   |
| WCAG 2.5.8 (AA, 2.2) | 24×24px (with exceptions) | 24px spacing        |
| Material Design      | 48×48dp                   | 8dp                 |
| Apple HIG            | 44×44pt                   | —                   |

Practice: use 44×44px as the hard minimum. Even if the visible element is smaller (an 8px radio button, a 16px icon), the invisible interactive hit area must be at least 44×44px.

```css
/* Small icon button: visible 24px, hit area 44px */
.icon-button {
  width: 24px;
  height: 24px;
  padding: 10px; /* expands hit area to 44px */
  margin: -10px; /* compensates so layout is unaffected */
}
```

## Depth and Elevation

Use sparingly. 3 levels maximum.

| Level   | Use                                | Implementation                      |
| ------- | ---------------------------------- | ----------------------------------- |
| Flat    | Default surfaces, backgrounds      | No shadow, background color only    |
| Raised  | Cards, interactive elements, menus | Subtle shadow or +1 lightness step  |
| Overlay | Modals, dropdowns, tooltips        | Medium shadow or +2 lightness steps |

Modern trend: replace shadows with lightness tinting. On a dark background, a "raised" surface is 5–8 lightness points lighter than the base surface. This is more legible across brightness settings and removes shadow blur artifacts.

```css
/* Lightness-based elevation (dark mode) */
--surface-base: oklch(0.12 0.015 250);
--surface-raised: oklch(0.17 0.015 250);
--surface-overlay: oklch(0.22 0.015 250);

/* Shadow-based elevation (light mode) */
--shadow-raised:
  0 1px 3px 0 oklch(0 0 0 / 0.1), 0 1px 2px -1px oklch(0 0 0 / 0.1);
--shadow-overlay:
  0 10px 15px -3px oklch(0 0 0 / 0.1), 0 4px 6px -4px oklch(0 0 0 / 0.1);
```

Avoid mixing both systems on the same surface. Shadows + lightness tinting together produce visual contradiction.
