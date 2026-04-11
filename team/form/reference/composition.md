# Composition Reference

## The Dominant Element Rule

Every layout needs exactly one dominant element — the visual anchor that tells the viewer where to start. This is non-negotiable. A layout with no dominant element feels chaotic. A layout with two dominant elements creates competition.

The dominant element is the largest, highest-contrast, or most visually weighted thing on the page. It's usually (but not always) the primary content or the primary CTA.

Test: squint at the layout. If nothing stands out, there's no dominant element. If two things fight for attention, pick one and subordinate the other.

## Six Composition Principles

### 1. Dominance

Visual weight hierarchy. One element is primary, others are secondary and tertiary. Weight is created through size, color, contrast, position, and isolation (whitespace around an element increases its dominance).

### 2. Similarity

Elements that look alike are perceived as related. Use consistent visual treatment (color, shape, size, spacing) to group related content. Breaking similarity signals "this is different" — use intentionally.

### 3. Rhythm

Repeating visual patterns create unity and predictability. Consistent spacing, repeating component patterns, and regular grid intervals all create rhythm. Breaking rhythm creates emphasis — one irregular element in a regular pattern draws the eye.

### 4. Texture

The visual density of a region. Dense text creates a different texture than an image grid, which differs from whitespace. Vary texture across a layout to create visual interest and guide scanning. Uniform texture across an entire page is monotonous.

### 5. Direction

Lines, shapes, and implied movement guide the eye. Diagonal lines create energy. Horizontal lines create calm. Arrows, pointing gestures in images, and converging lines all direct attention. Use direction to move the viewer from the dominant element to the secondary content to the CTA.

### 6. Contrast

Differences between adjacent elements. High contrast draws attention; low contrast recedes. Contrast operates across every dimension: light/dark, large/small, round/angular, dense/sparse, colored/neutral.

## Eye Recycling

The composition must keep the viewer's eye circulating within the layout — not exiting off an edge. Directional forces (lines, shapes, gaze direction) should form a closed loop:

```
Dominant element
    ↓ (visual flow)
Secondary content
    ↓
CTA / action area
    ↗ (directional force back to top)
```

Common leaks:

- Arrows or lines pointing off the edge of the layout
- Images where the subject looks or moves toward the edge
- Content that trails off without a visual terminus

Fix: add a visual stop (a contrasting element, a container edge, or a directional element that redirects the eye back into the layout).

## The F-Pattern for Web

Eye-tracking research consistently shows that web users scan in an F-shaped pattern on text-heavy pages:

1. **First horizontal scan** across the top of the page (strongest)
2. **Second horizontal scan** slightly below, usually shorter
3. **Vertical scan** down the left edge

Implications:

- Most important content goes in the top-left quadrant
- Headlines, key value propositions, and primary navigation live in the first scan line
- Left-aligned layouts outperform centered layouts for content-heavy pages (the left edge anchors the vertical scan)
- The right side of the page gets the least attention — don't put critical content or CTAs there on text-heavy pages

Exception: highly visual pages (image galleries, portfolios) break the F-pattern because images create their own visual anchors.

## Depth and Layering

Create perceived depth through multiple cues working together:

| Cue                 | Foreground (closer)             | Background (farther)         |
| ------------------- | ------------------------------- | ---------------------------- |
| **Size**            | Larger                          | Smaller                      |
| **Detail**          | More detail, sharper            | Less detail, softer          |
| **Color intensity** | More saturated                  | Less saturated, cooler       |
| **Overlap**         | Overlaps other elements         | Overlapped by other elements |
| **Position**        | Lower on the page               | Higher on the page           |
| **Shadows**         | Casts shadow on elements behind | Receives shadow              |

Use depth sparingly in UI. One or two depth cues are enough to create a sense of layering. Stacking all six produces visual noise.

## Composition Mistakes

- **Symmetrical boredom** — perfectly symmetrical layouts feel static and predictable. Break symmetry in one intentional place.
- **No entry point** — the viewer doesn't know where to start. Add a dominant element.
- **Competing anchors** — two elements of equal weight fight for attention. Subordinate one.
- **Exit leaks** — directional forces push the eye off the layout. Add visual stops.
- **Uniform density** — every region has the same visual weight. Vary texture and whitespace.
- **Arbitrary placement** — elements positioned without relationship to each other. Use a grid and alignment.
