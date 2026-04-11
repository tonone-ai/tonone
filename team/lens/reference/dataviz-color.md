# Data Visualization Color Reference

## HSB/HSL Brightness ≠ Perceptual Lightness

The most common color mistake in data visualization: assuming HSB brightness or HSL lightness corresponds to how humans perceive lightness. It doesn't.

Two colors with identical HSL lightness values can look dramatically different in perceived brightness:

- Yellow at HSL `hsl(60, 100%, 50%)` looks very bright
- Blue at HSL `hsl(240, 100%, 50%)` looks very dark

For sequential color scales (light → dark), HSL rotation produces uneven perceived steps. The solution:

**Use Lab/OKLCH lightness (L) for perceptual uniformity.** In Lab color space, equal numeric steps in L produce equal perceived lightness changes regardless of hue.

```css
/* WRONG: HSL rotation for a sequential scale */
--step-1: hsl(210, 80%, 90%);
--step-2: hsl(210, 80%, 70%);
--step-3: hsl(210, 80%, 50%); /* perceived jump is uneven */

/* RIGHT: OKLCH with uniform L steps */
--step-1: oklch(0.9 0.08 250);
--step-2: oklch(0.7 0.12 250);
--step-3: oklch(0.5 0.16 250); /* perceived steps are even */
```

## Colorblindness in Data Viz

~8% of males and ~0.5% of females have some form of color vision deficiency. The most common form (deuteranopia/protanopia) makes red and green indistinguishable.

**Rule: never encode meaning in color alone.** Always add a redundant cue:

| Color-only (fails)                   | Color + redundant cue (accessible)              |
| ------------------------------------ | ----------------------------------------------- |
| Red dot = error, green dot = success | Red dot + ✗ icon, green dot + ✓ icon            |
| Red line vs green line on chart      | Solid line vs dashed line, plus labels          |
| Heat map with only color             | Heat map with value labels or pattern overlay   |
| Red/green traffic light indicator    | Indicator + text label ("Critical" / "Healthy") |

For categorical color palettes, use Colorbrewer palettes (colorbrewer2.org) — they're specifically designed and tested for colorblind safety, print safety, and screen safety.

## Colorbrewer Palettes

Colorbrewer provides three palette types designed for data visualization:

| Type            | Use                             | Example                                       |
| --------------- | ------------------------------- | --------------------------------------------- |
| **Sequential**  | Ordered data (low → high)       | Light blue → dark blue for population density |
| **Diverging**   | Data with a meaningful midpoint | Red ← neutral → blue for profit/loss          |
| **Qualitative** | Categorical data (no order)     | Distinct hues for product categories          |

Rules:

- **Sequential:** 3–7 classes. More than 7 becomes hard to distinguish
- **Diverging:** Always center on the meaningful midpoint (zero, average, threshold)
- **Qualitative:** Maximum 8–10 colors before they become indistinguishable. For more categories, group or use other encoding (shape, position)
- **Never use rainbow palettes** for sequential data — rainbow has no perceptual order

## Chart-Specific Color Rules

| Chart Type       | Color Strategy                                                                         |
| ---------------- | -------------------------------------------------------------------------------------- |
| **Line chart**   | Max 5–6 lines. Use hue for categories. Highlight the important line, gray out the rest |
| **Bar chart**    | Single color for comparison. Multiple colors only for categorical grouping             |
| **Pie/donut**    | Max 5 segments. Remainder goes in "Other". Use sequential lightness within one hue     |
| **Heat map**     | Sequential palette always. Never qualitative. Consider diverging if there's a midpoint |
| **Scatter plot** | Hue for category, size for magnitude. Max 4 categories before it becomes noise         |

## Visual Hierarchy for Dashboards

Dashboards are scanning surfaces, not reading surfaces. Apply visual hierarchy:

1. **The most important metric** should be the largest, highest-contrast element — usually a single number with a trend indicator
2. **Supporting charts** should be smaller and visually subordinate
3. **Filters and controls** should be visually quiet — they support the data, they're not the data
4. **Comparison data** (previous period, benchmark) should be visually lighter than current data

Common dashboard hierarchy failure: every chart is the same size, same visual weight. The user doesn't know where to look first. Fix: one chart dominates (the north star metric), others support.

## Color Contrast for Data Labels

Text overlaid on colored chart elements (bar labels, map annotations) must pass contrast requirements:

- Dark text on light fills: minimum 4.5:1 contrast ratio
- Light text on dark fills: minimum 4.5:1 contrast ratio
- If the fill color varies (heat map), use an adaptive strategy: dark text below a lightness threshold, light text above it

```
if (fillLightness > 0.55) → use dark text
if (fillLightness ≤ 0.55) → use light text
```

Never rely on the user's ability to match a legend color to a chart element across a large distance. Label directly when possible.
