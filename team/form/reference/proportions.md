# Proportions Reference

## Ratio Selection

The golden ratio (1.618) is one of several aesthetically pleasing ratios — not a magic number. Simpler ratios produce equally harmonious results and are easier to work with in code.

| Ratio  | Value  | Character                   | Common Use                                             |
| ------ | ------ | --------------------------- | ------------------------------------------------------ |
| 1:1    | 1.0    | Square, stable, equal       | Avatars, icons, grid cells                             |
| 2:3    | 0.666  | Tall, elegant, photographic | Card images, phone screens, book pages                 |
| 3:4    | 0.75   | Balanced, natural           | Presentation slides, traditional photos, content cards |
| 4:5    | 0.80   | Nearly square, comfortable  | Instagram posts, compact cards                         |
| 16:9   | 0.5625 | Wide, cinematic             | Hero images, video embeds, banner sections             |
| Golden | 0.618  | Classic proportion          | Sidebar/content splits, image crops                    |

Rule: pick one ratio for the primary layout relationship and use it consistently. Don't mix ratios arbitrarily — the visual coherence comes from repetition of the same proportional relationship across different elements.

## Varied Scale

Start with the largest element and multiply by a consistent factor to derive smaller related sizes. The factor 0.75 (3:4) produces a natural, harmonious progression.

```
Starting point: 400px (hero image width)
× 0.75 = 300px (secondary image)
× 0.75 = 225px (card width)
× 0.75 = 169px (thumbnail)
× 0.75 = 127px (small thumbnail)
```

This creates visual harmony because all sizes share a proportional relationship. Ad hoc sizes (400px, 280px, 150px, 90px) lack this coherence even when they "look fine" individually.

The same principle applies to spacing: if section padding is 96px, sub-section padding might be 72px (96 × 0.75), and component padding might be 54px (72 × 0.75). The 4pt grid snaps these to practical values: 96, 72, 56.

## The 3:4 Type Scale

A type scale built on the 3:4 ratio (perfect fourth), rounded to whole pixels:

```
5 → 7 → 9 → 12 → 16 → 21 → 28 → 37 → 50 → 67 (px)
```

Each step is approximately 1.333× the previous. This scale provides enough steps for complex interfaces while maintaining clear contrast between non-adjacent steps.

Usage mapping:
| Size | Role |
|------|------|
| 67px | Display / hero heading |
| 50px | Page title |
| 37px | Section heading |
| 28px | Subsection heading |
| 21px | Large body / lead paragraph |
| 16px | Body text (base) |
| 12px | Small text / captions |
| 9px | Micro text / legal (minimum for readability) |

Never use adjacent steps for different hierarchy levels — the contrast is too weak. Skip at least one step: body at 16px pairs with headings at 28px or 37px, not 21px.

## Tschichold Margin Method

A classical method for positioning a content block within a page or screen so that the content area has the same aspect ratio as its container.

Construction:

1. Draw the diagonal of the full page (corner to corner)
2. Draw the diagonal of the facing page (or mirrored for a single page)
3. The intersection of these diagonals with horizontal/vertical lines defines the content margins

The result: inner margins are smaller than outer margins, and top margins are smaller than bottom margins. This creates a natural "optical center" slightly above the mathematical center — which is where the eye expects the content to be.

For screen design, the principle translates to:

- Content blocks should not be mathematically centered — shift them slightly upward
- Side margins should be unequal if the layout has a sidebar (content gets the larger margin on the open side)
- The content area's aspect ratio should relate to the screen's aspect ratio

## Proportion as Visual Interest

Uniform proportions create monotony. Varied proportions create visual interest.

```
MONOTONOUS: Three equal columns (1:1:1)
    ┌──────┐ ┌──────┐ ┌──────┐
    │      │ │      │ │      │
    └──────┘ └──────┘ └──────┘

INTERESTING: Varied columns (2:3:1)
    ┌──────────┐ ┌────────────────┐ ┌────┐
    │          │ │                │ │    │
    └──────────┘ └────────────────┘ └────┘
```

This applies to:

- Column widths in grid layouts
- Image sizes in a gallery
- Section heights on a landing page
- Card widths in a mixed content layout

The dominant element should be the largest (matching the composition principle). Supporting elements should be visibly smaller, not slightly smaller.
