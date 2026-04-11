# Color Theory Reference

## Color Wheel Schemes

Every palette starts with a base hue and a scheme. The scheme determines which other hues participate. Choose the scheme before generating any swatches.

| Scheme                  | Construction                                   | Character                                          | Use When                                              |
| ----------------------- | ---------------------------------------------- | -------------------------------------------------- | ----------------------------------------------------- |
| **Monochromatic**       | One hue, vary lightness and chroma             | Unified, calm, sophisticated                       | Brand-heavy surfaces, dashboards, data-dense UI       |
| **Analogous**           | 2–3 adjacent hues (within 60° arc)             | Harmonious, natural, low tension                   | Illustration palettes, editorial, warm/cool moods     |
| **Complementary**       | Opposite hues (180° apart)                     | High contrast, energetic                           | CTAs against backgrounds, accent-on-neutral           |
| **Split-complementary** | Base hue + two hues adjacent to its complement | Contrast with less tension than full complementary | Balanced marketing pages, multi-section layouts       |
| **Triadic**             | Three hues equidistant (120° apart)            | Vibrant, playful, balanced                         | Children's products, creative tools, multi-brand      |
| **Tetradic**            | Two complementary pairs (rectangle on wheel)   | Rich, complex                                      | Editorial, data visualization — hard to balance in UI |

Rules:

- One hue dominates (60% surface). Others support. Never give two hues equal weight.
- Complementary pairs at equal saturation and lightness produce vibration. Always shift one lighter or less saturated.
- Analogous palettes need a neutral anchor — without one they read as muddy.

## Warm and Cool

Warm hues (red → yellow, roughly 0°–60° and 300°–360°) advance — they feel closer, heavier, more urgent.
Cool hues (green → blue → violet, roughly 120°–270°) recede — they feel farther, lighter, calmer.

Application in UI:

- **Primary text:** warm dark tones (dark brown-black, warm charcoal) read as approachable and grounded
- **Secondary text:** cool gray tones create visual distance, reducing prominence without reducing legibility
- **CTAs:** warm accents (orange, red-orange, warm yellow) draw the eye forward against cool backgrounds
- **Backgrounds:** cool tints recede, giving content breathing room

This warm/cool depth relationship is why "black text on white" feels flatter than "warm near-black on cool off-white" — the temperature difference creates subtle spatial depth.

## Hue-Shifted Shadows and Highlights

Pure black shadows (`#000` or `oklch(0 0 0)`) look dead. Real-world shadows shift cooler (toward blue), and highlights shift warmer (toward yellow/orange).

```css
/* Wrong: pure black shadow */
box-shadow: 0 4px 12px oklch(0 0 0 / 0.15);

/* Right: cool-shifted shadow */
box-shadow: 0 4px 12px oklch(0.25 0.03 250 / 0.15);
```

For illustration and decorative elements:

- Shadow regions: shift hue 20–40° toward blue, reduce chroma slightly, drop lightness
- Highlight regions: shift hue 10–20° toward yellow, increase lightness
- Never use pure gray for either — it strips the life from the color

This technique is invisible in isolation but makes surfaces feel "lit" rather than flat.

## Color and Emotion

Color associations are culturally loaded but some physiological responses are consistent:

| Color Region  | Physiological Effect                           | Design Implication                                                                                                                                             |
| ------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Red           | Increases arousal, overloads prefrontal cortex | Avoid in analytical/performance contexts (Elliot & Maier 2007). Use for urgency, errors, destructive actions — not primary brand color unless brand IS urgency |
| Blue          | Lowers heart rate, signals trust               | Default B2B/fintech/enterprise palette for a reason. Overused — differentiate via temperature and saturation                                                   |
| Green         | Associated with safety, growth                 | Positive states, success indicators, financial products. Saturated green is hard to read as text                                                               |
| Yellow/Orange | Attention-grabbing, high energy                | Warnings, highlights, badges. Poor text contrast — use as accent only                                                                                          |
| Purple        | Premium, creative                              | Overused in AI/tech branding 2020–2025. If you're reaching for purple, ask if it's a brand decision or an AI default                                           |

The purple-to-blue gradient is the single most common AI-generated color tell. If your palette includes it, document a specific brand reason.

## Background Color Strategy

The background color sets the entire tonal register of a page.

| Background           | When to Use                                          | Constraints                                                                                       |
| -------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| **White/off-white**  | Content-heavy pages, reading-focused, documentation  | Needs strong typographic hierarchy to avoid flatness                                              |
| **Light tinted**     | Product surfaces, app backgrounds                    | Tint must be subtle (L > 0.95) — too much tint competes with content                              |
| **Dark/near-black**  | Premium positioning, media-rich, night mode          | Text must be off-white (not pure white — too harsh). Elevation via lightness tinting, not shadows |
| **Bright saturated** | Low-content splash, hero sections, marketing moments | Text overlay requires scrim or high contrast. Never for long-form reading                         |
| **Mid-tone**         | Almost never                                         | Fails contrast in both directions — dark text and light text both struggle                        |

Rule: if the page has >500 words of body copy, the background should be white or near-white. Dark backgrounds are for scanning, not reading.
