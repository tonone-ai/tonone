# Color and Contrast Reference

## OKLCH Color Space

Use OKLCH for all palette generation. Unlike HSL, OKLCH is perceptually uniform — equal numeric steps produce equal perceived lightness changes across all hues.

```
oklch(L C H)
  L = lightness, 0 (black) to 1 (white)
  C = chroma (saturation), 0 (gray) to ~0.4 (maximum saturation)
  H = hue, 0–360 degrees
```

Why OKLCH over HSL: Two colors with the same HSL lightness can look dramatically different in perceived brightness (yellow at L=50% looks much lighter than blue at L=50%). OKLCH corrects this. When building a scale, keep L uniform across steps to get true lightness consistency.

CSS support: native in all modern browsers. `color(display-p3 ...)` as fallback for older browsers where needed.

## Tinted Neutrals

Never use pure gray (`oklch(L 0 H)`). Pure grays read as cold, clinical, and cheap against chromatic brand colors.

Rule: add 1–3% chroma from the brand hue to every neutral step.

```css
/* Wrong: pure gray */
--color-neutral-100: oklch(0.97 0 0);

/* Right: tinted neutral using brand hue */
--color-neutral-100: oklch(0.97 0.008 250);
```

The tint is invisible in isolation but produces visual coherence when neutrals and brand colors appear together. This is one of the cheapest quality upgrades available.

## 60-30-10 Rule

Every surface should allocate color across three roles:

- **60% dominant** — surfaces, backgrounds, page canvas. Usually neutral.
- **30% secondary** — containers, secondary text, structural elements. Neutral or low-chroma brand.
- **10% accent** — interactive elements, emphasis, CTAs. Full brand color.

Violations of this ratio produce visual noise (too much accent) or visual flatness (too little). The moment a page looks "too busy," check if accent is consuming more than 10%.

## Palette Scale Structure

For each hue in the system, generate a 50–950 scale with at least 10 stops. Each stop must have a defined use case — no orphan values.

| Scale step | Primary use cases                         |
| ---------- | ----------------------------------------- |
| 50, 100    | Backgrounds, tinted surfaces              |
| 200, 300   | Borders, dividers, disabled states        |
| 400, 500   | Icons, illustrations, inactive states     |
| 600, 700   | Text on light backgrounds                 |
| 800, 900   | Text on dark backgrounds, strong emphasis |
| 950        | Near-black for dark mode surfaces         |

If a step has no use case, remove it. Palette bloat is a maintenance tax.

## WCAG Contrast Requirements

Minimum ratios. These are non-negotiable for shipping.

| Content type                                         | Minimum ratio  | WCAG level |
| ---------------------------------------------------- | -------------- | ---------- |
| Normal text (<18pt, or <14pt bold)                   | 4.5:1          | AA         |
| Large text (≥18pt, or ≥14pt bold)                    | 3:1            | AA         |
| UI components (borders, icons conveying information) | 3:1            | AA         |
| Decorative content (no information)                  | No requirement | —          |
| Enhanced normal text                                 | 7:1            | AAA        |

Tools: browser devtools color picker, `@radix-ui/colors` palette (all steps verified), `culori` JS library for programmatic checks.

Check every text/background combination before shipping. Don't eyeball it — calculate it.

## Dangerous Combinations to Ban

These combinations produce visual vibration or inaccessibility regardless of intent:

- **Pure red on pure blue** (or vice versa): high chromatic contrast at similar lightness produces vibrating edges. Neither passes contrast anyway.
- **Vibrating complementaries at equal lightness**: orange on blue, red on cyan, green on magenta — only safe when one is significantly lighter or darker.
- **Text on gradients without overlay**: a gradient background that passes contrast at one end may fail at the other. Either use a semi-transparent dark/light overlay, or restrict text to a region of proven contrast.
- **Saturated color on saturated color**: two fully-chromatic colors adjacent exhaust attention. One element gets color, the other gets neutral.
- **White text on mid-range colors**: colors in the 400–500 range rarely pass 4.5:1 against white. Test before using.

## Dark Mode

Dark mode is not inverted light mode. Inversion produces unintended results (shadows become glows, light accents become harsh dark blobs). Rebuild intentionally.

Dark mode construction rules:

1. **Surfaces**: use low-lightness, low-to-mid chroma variants. `oklch(0.12 0.015 250)` not `oklch(0.05 0 0)`. Absolute black feels unnatural on screen.
2. **Text**: use high-lightness, low-chroma variants. Off-white (`oklch(0.95 0.008 250)`) reads softer than pure white and still passes contrast.
3. **Accent colors**: shift lighter by 10–15 lightness points compared to light mode. A 600-step color in light mode becomes closer to a 400-step color in dark mode to maintain similar perceived emphasis.
4. **Elevation**: reduce or eliminate shadows (shadows require light). Use lightness tinting instead — raised surfaces are slightly lighter than their container surface.
5. **Borders**: dark mode borders need less contrast than light mode borders. A 200-step border on a 50-step background (light) maps to roughly a 700-step border on a 900-step surface (dark).

Each token must have an explicit dark mode value. Never rely on filter or inversion shortcuts.

## Token Hierarchy

Three layers. Components reference semantic tokens only. Semantic tokens reference primitives only. Never skip layers.

```
Primitive tokens (raw values)
  --color-blue-600: oklch(0.45 0.18 255);

Semantic tokens (use cases)
  --color-interactive: var(--color-blue-600);
  --color-interactive-hover: var(--color-blue-700);

Component tokens (specific bindings)
  --button-primary-bg: var(--color-interactive);
  --button-primary-bg-hover: var(--color-interactive-hover);
```

Components never reference primitives (`--color-blue-600`) directly. If you find a component reaching past the semantic layer, add the missing semantic token.

### Dark Mode Token Pattern

```css
:root {
  --color-surface: oklch(0.98 0.005 250);
  --color-text-primary: oklch(0.15 0.01 250);
}

[data-theme="dark"] {
  --color-surface: oklch(0.12 0.015 250);
  --color-text-primary: oklch(0.92 0.008 250);
}
```

## Alpha as Design Smell

If you're reaching for `rgba()` or `oklch(L C H / 0.5)` to create a tinted surface, you're probably missing a palette step.

Alpha-based tints change appearance depending on what's underneath them — they're not predictable colors. If the design calls for a specific tinted surface, add that exact color as a named primitive. Use alpha intentionally only for overlays and scrim layers where the layering effect is the point.

The exception: 8–16% alpha black or white overlays for hover/pressed states on interactive elements. This is a valid pattern when the base color varies.
