# Visual Hierarchy Reference

## The Hierarchy Stack

Apply hierarchy tools in this order. Each layer is more powerful than the one below it and more subtle than the one above it.

```
1. White space      ← most powerful, most subtle
2. Weight
3. Size
4. Color
5. Ornamentation    ← least powerful, most obvious
```

Most designers reach for color or ornamentation first because they're the most visible changes. But white space and weight do the heaviest lifting with the least visual noise.

A heading separated by generous whitespace and set in bold weight communicates hierarchy before you add size, color, or decoration. If you need ornamentation to establish hierarchy, the earlier layers aren't doing their job.

## White Space as Structure

White space is not empty — it's active. It separates groups, creates relationships, and directs attention.

**Proximity rule:** Items with less space between them are perceived as related. Items with more space are perceived as separate groups. This is more powerful than borders, backgrounds, or labels for communicating structure.

**Hierarchy through isolation:** An element surrounded by generous whitespace gains prominence. The space around it — not the element itself — creates the visual weight.

**Common failure:** Equal spacing everywhere. When every gap is 16px, nothing is grouped, and nothing is separated. Vary spacing deliberately: tight within groups, generous between groups.

## Cap-Height Spacing

Use the cap-height of the text as the spacing unit between closely related elements (e.g., a heading and its body paragraph).

If the heading is set at 24px with a cap-height of roughly 17px, the gap between heading and body should be approximately 17px. This creates a proportional relationship between text size and spacing that scales naturally across the type scale.

Larger headings get more space. Smaller labels get less. The system is self-regulating.

## Tufte's 1+1=3 Principle

Two visual elements (lines, boxes, borders) create a third: the space between them. This third element is visual noise.

A table with cell borders creates a grid of lines that competes with the data inside. Remove the borders. Let alignment and whitespace define the structure. The data becomes the visual, not the grid.

```
NOISY (borders create noise):
┌────────┬────────┬────────┐
│ Name   │ Role   │ Status │
├────────┼────────┼────────┤
│ Alice  │ Eng    │ Active │
│ Bob    │ Design │ Active │
└────────┴────────┴────────┘

CLEAN (alignment does the work):
Name     Role     Status
Alice    Eng      Active
Bob      Design   Active
```

Apply this principle to every visual element: borders, dividers, backgrounds, card outlines. Remove each one and ask: does the structure still hold? If yes, the element was noise.

## Meaningful Type Scale Steps

Adjacent steps in a type scale create weak hierarchy. Skipping steps creates meaningful contrast.

```
WEAK:   Body 16px → Heading 18px    (ratio 1.12 — barely different)
STRONG: Body 16px → Heading 28px    (ratio 1.75 — clearly different level)
```

Rule: heading text should be at least 1.5× the size of body text to register as a different hierarchy level. Below 1.3× the difference reads as a mistake, not a decision.

For three levels of hierarchy, use a minimum ratio progression:

- Body: 16px
- Subheading: 24px (1.5×)
- Heading: 36px (2.25×)

The 3:4 type scale from Design for Hackers provides pre-calculated steps that maintain meaningful contrast: 5, 7, 9, 12, 16, 21, 28, 37, 50, 67px. Use non-adjacent steps for hierarchy levels.

## Multi-Dimensional Hierarchy

Strong hierarchy uses at least 3 simultaneous contrast dimensions (from `spatial-design.md`). This reference adds the ordering principle:

1. **Start with white space** — separate the element from its surroundings
2. **Add weight** — bold or semi-bold for emphasis
3. **Then size** — larger for primary, smaller for secondary
4. **Then color** — brand color or emphasis color, sparingly
5. **Last resort: ornamentation** — underlines, backgrounds, borders, icons

If a hierarchy decision requires ornamentation (step 5) to work, revisit steps 1–4 first. Usually one of the earlier layers is underused.

## Reading Order vs. Visual Order

Visual hierarchy must match the intended reading order. If the most important element is also the first thing the eye encounters (via position, size, or contrast), the layout works. If the eye finds a secondary element first, the hierarchy has failed — regardless of how the primary element is styled.

Test: ask someone unfamiliar with the layout to point at the first thing they see. If it's not the primary element, fix the composition before fixing the styling.
