# Checklists Reference

## Red Flags Table

Fast lookup: if any of these appear in a design, they need either a documented justification or a fix.

### Typography Red Flags

| Red Flag                                               | Severity | Root Cause                                          | Fix                                                                                    |
| ------------------------------------------------------ | -------- | --------------------------------------------------- | -------------------------------------------------------------------------------------- |
| No defined type scale (ad hoc font sizes)              | Major    | Missing design system foundation                    | Define a modular scale from `typography.md` and use only its steps                     |
| Body text with added letter-spacing                    | Major    | Misunderstanding of typographic fundamentals        | Remove. Body text letter-spacing slows reading. Only all-caps labels get added spacing |
| Fake bold (browser-synthesized, no bold weight loaded) | Critical | Missing font weight in @font-face                   | Load the actual bold weight. Synthetic bold looks muddy and breaks metrics             |
| Fake italic (oblique, not true italic)                 | Critical | Same as fake bold                                   | Load the actual italic variant                                                         |
| Fake small caps (scaled-down capitals)                 | Major    | Using `text-transform: uppercase` + small font size | Use `font-variant-caps: small-caps` or true small caps from OpenType                   |
| Justified text on web                                  | Major    | Print convention misapplied to screen               | Left-align. Web browsers lack the hyphenation needed for good justification            |
| More than 2 font families                              | Minor    | Scope creep in typography                           | Reduce to 2 max: one for identity, one for reading                                     |
| Body text below 14px                                   | Major    | Prioritizing density over readability               | 16px minimum for body copy, 14px minimum for UI text                                   |
| No font loading strategy                               | Major    | Performance blindspot                               | Add `font-display: swap`, preload critical weights, metric-match fallbacks             |

### Color Red Flags

| Red Flag                                  | Severity | Root Cause                  | Fix                                                                                           |
| ----------------------------------------- | -------- | --------------------------- | --------------------------------------------------------------------------------------------- |
| Purple-to-blue gradient as default accent | Major    | AI default pattern          | Derive accent from brand adjectives via `color-theory.md`. If purple is correct, document why |
| Pure gray neutrals (zero chroma)          | Minor    | Missing brand hue tinting   | Add 1–3% chroma from brand hue per `color-and-contrast.md`                                    |
| Accent color >10% of visual surface       | Major    | 60-30-10 rule violation     | Reduce accent to interactive elements and emphasis only                                       |
| Color-only state indicators               | Critical | Accessibility failure       | Add icon, text, or pattern as redundant cue — ~10% of males are colorblind                    |
| No semantic color naming                  | Major    | Tokens reference raw values | Map every color use to a semantic token: `--color-interactive`, not `--color-blue-600`        |
| Gradient without purpose                  | Minor    | Decorative impulse          | Gradient must serve hierarchy (e.g., depth cue) or be cut                                     |
| Text on gradient without contrast check   | Critical | Accessibility failure       | Add semi-transparent overlay or restrict text to proven contrast region                       |

### Layout Red Flags

| Red Flag                                 | Severity | Root Cause                     | Fix                                                                           |
| ---------------------------------------- | -------- | ------------------------------ | ----------------------------------------------------------------------------- |
| No dominant element                      | Major    | Missing composition foundation | Apply `composition.md`: one element must be visually largest/strongest        |
| Everything same visual weight            | Major    | Hierarchy failure              | Use 3+ contrast dimensions from `visual-hierarchy.md`                         |
| Inconsistent spacing (non-system values) | Major    | Missing spacing system         | Use 4pt grid from `spatial-design.md`. No ad hoc values                       |
| Card-in-card nesting                     | Minor    | Over-componentization          | Flatten. Cards group independent units — nesting creates ambiguous hierarchy  |
| Hamburger menu on desktop                | Minor    | Mobile pattern misapplied      | Desktop has room for visible navigation. Show it                              |
| All-centered text layout                 | Major    | Lazy alignment choice          | Left-align body text and content. Center only single-line headings and CTAs   |
| No empty state designed                  | Major    | Happy-path-only thinking       | Every list, table, and data view needs a first-run empty state                |
| Identical padding everywhere             | Minor    | Lazy spacing                   | Vary spacing by context: tighter within components, generous between sections |

### Component Red Flags

| Red Flag                                       | Severity | Root Cause                | Fix                                                                       |
| ---------------------------------------------- | -------- | ------------------------- | ------------------------------------------------------------------------- |
| Missing interactive states                     | Critical | Incomplete implementation | Every interactive element needs all 8 states from `interaction-design.md` |
| Identical corner radius everywhere             | Minor    | Thoughtless defaults      | Vary radius by component role: buttons, cards, inputs may differ          |
| Shadows on every container                     | Minor    | Overuse of depth          | Use 3 elevation levels max from `spatial-design.md`                       |
| Mixed icon styles (3+ sets)                    | Minor    | No icon standard defined  | Choose one icon set. Match weight to type weight                          |
| Decorative elements without hierarchy function | Minor    | Visual noise              | Remove anything that doesn't support scanning, grouping, or emphasis      |

### Content Red Flags

| Red Flag                          | Severity | Root Cause               | Fix                                                                                       |
| --------------------------------- | -------- | ------------------------ | ----------------------------------------------------------------------------------------- |
| Lorem ipsum shipped               | Critical | Incomplete content       | Real content or realistic placeholder. Lorem hides layout failures                        |
| Stock photo hero section          | Minor    | Lazy visual storytelling | Product screenshots, illustrations, or custom photography. Stock photos erode credibility |
| "Welcome to our platform" heading | Major    | No value proposition     | Lead with what the user can accomplish, not what the product is called                    |

---

## Decision Trees

### 1. Choose Colors

```
Start: What mood should the palette convey?
  ├─ Energetic/Bold → warm base hue (red/orange/yellow range)
  ├─ Calm/Trustworthy → cool base hue (blue/teal range)
  ├─ Premium/Sophisticated → low-chroma, dark values
  └─ Playful/Creative → high-chroma, varied hues
        │
        ▼
Select color wheel scheme (see color-theory.md)
  ├─ Need simplicity? → Monochromatic
  ├─ Need harmony? → Analogous
  ├─ Need pop? → Complementary or split-complementary
  └─ Need richness? → Triadic (use with caution)
        │
        ▼
Generate tints/shades: 50–950 scale per hue
        │
        ▼
Check: every text/background pair passes WCAG AA
        │
        ▼
Assign semantic roles: --color-interactive, --color-danger, etc.
        │
        ▼
Apply 60-30-10 rule: dominant (neutral), secondary, accent
```

### 2. Pick Fonts

```
Start: Define 3–5 brand adjectives
        │
        ▼
Categorize needed personality:
  ├─ Technical/precise → geometric sans, monospace
  ├─ Professional/clean → realist/neo-grotesque sans
  ├─ Warm/approachable → humanist sans
  ├─ Editorial/expressive → transitional or contemporary serif
  └─ Bold/distinctive → display face for headings only
        │
        ▼
Shortlist 3–5 families → test at 16px body size (NOT display size)
        │
        ▼
Check x-height (larger = better screen readability)
        │
        ▼
Verify: character set covers needed languages
        │
        ▼
Check: tabular figures available? Old-style figures? Small caps?
        │
        ▼
Pair: contrast in structure, harmony in proportion
  Rule: geometric sans + humanist serif ✓
        two similar sans ✗ (uncanny valley)
```

### 3. Diagnose Layout Problems

```
Start: Run the squint test
  ├─ Can identify primary element? → Dominance OK
  │   └─ Can identify 3 hierarchy levels? → Hierarchy OK
  │       └─ Spacing feels grouped? → Rhythm OK
  │           └─ Eye flows naturally? → Direction OK → Layout passes
  │
  └─ Everything looks same weight? → Hierarchy failure
      ├─ Fix: increase size differential (1.5×+ between levels)
      ├─ Fix: add whitespace separation between groups
      ├─ Fix: increase weight contrast (400 vs 700)
      └─ Fix: reduce visual weight of secondary elements
```

### 4. Establish Hierarchy

```
Start: Define information priority (what matters most?)
        │
        ▼
Layer 1: White space — separate primary from secondary with generous gaps
        │
        ▼
Layer 2: Weight — bold for primary, regular for body
        │
        ▼
Layer 3: Size — skip type scale steps for meaningful contrast
        │
        ▼
Layer 4: Color — brand color on primary, neutral on secondary (sparingly)
        │
        ▼
Layer 5: Ornamentation — only if layers 1–4 aren't sufficient (rarely)
        │
        ▼
Test: does the squint test reveal 3 clear hierarchy levels?
  ├─ Yes → Ship
  └─ No → Return to the weakest layer and strengthen it
```
