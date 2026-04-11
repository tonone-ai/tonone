# Composition for Layout Reference

## F-Pattern for Web

Eye-tracking research shows web users scan text-heavy pages in an F-shaped pattern:

1. **Top horizontal scan** — strongest attention. The first line of content gets the most reading.
2. **Second horizontal scan** — shorter, lower. Users scan a sub-heading or the start of the second paragraph.
3. **Left-edge vertical scan** — users scan down the left margin, reading the first words of each line/section.

### Layout implications for wireframes

- **Top-left quadrant** is prime real estate — place the primary heading, value prop, or key action here
- **Left-align content** on text-heavy pages — centered layouts break the left-edge vertical scan
- **Front-load paragraphs** — the most important word in each paragraph should come first (users only read the first 2–3 words per line in scan mode)
- **Sub-headings matter more than body text** — they're the anchors for the second horizontal scan
- **Right-column content gets low attention** — don't place critical actions or information there on content pages

### When F-pattern doesn't apply

- **Visual-heavy pages** (image galleries, portfolios) — images create their own scan points
- **Single-action pages** (checkout, login) — the layout funnels toward one CTA
- **Mobile** — single column eliminates the F-pattern; vertical scan dominates

## The Dominant Element

Every screen needs one dominant element — the visual anchor that answers "where do I start?"

In wireframe terms, this means:

- One element is noticeably larger, bolder, or more prominent than everything else
- If two elements compete for dominance, pick one and subordinate the other
- The dominant element should be the primary content or primary action (not a decorative image or logo)

**Squint test:** blur your eyes until text is illegible. Can you still identify the primary element? If not, the hierarchy needs work.

## Eye Recycling

Directional forces in the layout should keep the user's eye circulating through the content — not exiting off an edge.

Design a visual flow loop:

```
Primary element (start here)
    ↓
Supporting content (context, evidence)
    ↓
Call to action (what to do next)
    ↗ (navigation, related content → back to primary)
```

Wireframe check: trace the likely eye path through the layout. If it exits at any point (hits an edge with no redirect), add a visual element to bring the eye back in.

## Foreground and Background

Create perceived depth in layouts through layering cues:

| Closer (foreground)        | Farther (background)    |
| -------------------------- | ----------------------- |
| Larger elements            | Smaller elements        |
| More detailed / sharper    | Less detailed / muted   |
| More saturated color       | Less saturated / grayer |
| Overlapping other elements | Behind other elements   |

For wireframes: indicate depth with annotation rather than attempting to render it. Note which elements should "sit above" others, and which should recede. Form and Prism handle the visual implementation.

## Composition Principles for Layout Decisions

When placing elements on a wireframe, these principles resolve "where does this go?":

| Principle      | What it means for placement                                               |
| -------------- | ------------------------------------------------------------------------- |
| **Dominance**  | The most important element gets the most space and the strongest position |
| **Similarity** | Related items should look alike (same indentation, same layout pattern)   |
| **Rhythm**     | Repeating consistent spacing and patterns aids scanning                   |
| **Direction**  | Arrows, lines, and visual flow guide the eye toward the CTA               |
| **Contrast**   | The CTA or primary action should contrast with surrounding content        |

These are annotation notes on wireframes — Draft defines the structure, Form applies the visual treatment.
