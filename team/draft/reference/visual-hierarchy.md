# Visual Hierarchy Reference (for UX)

## The Hierarchy Stack

Hierarchy tools in order of power and subtlety:

```
1. White space      ← most powerful, most subtle
2. Weight
3. Size
4. Color
5. Ornamentation    ← least powerful, most obvious
```

For wireframes, this means: don't rely on color or decoration to communicate hierarchy. White space and relative size should establish the structure before any color is applied.

If a wireframe only works when you add color to distinguish sections, the spatial hierarchy is broken.

## White Space as Grouping

The most powerful tool Draft has for organizing information:

**Tight spacing = related.** Elements with small gaps between them are perceived as a group.
**Wide spacing = separate.** Elements with large gaps are perceived as different groups.

This is stronger than labels, borders, or background colors for communicating structure. When wireframing:

```
WRONG (borders for grouping):
┌─────────────────┐   ┌─────────────────┐
│ Section A       │   │ Section B       │
│ Item 1          │   │ Item 3          │
│ Item 2          │   │ Item 4          │
└─────────────────┘   └─────────────────┘

RIGHT (spacing for grouping):
Section A                Section B
Item 1                   Item 3
Item 2                   Item 4


     (generous gap between sections, tight gaps within)
```

## Tufte's 1+1=3

Two visual elements create a third: the space between them. This third element is noise.

In wireframes and layout:

- **Remove borders** when alignment alone defines the structure
- **Remove divider lines** between list items when spacing alone separates them
- **Remove card containers** when content grouping is clear from proximity and alignment
- **Remove background colors** when whitespace alone distinguishes sections

Each visual element removed is cognitive load removed. The user processes the content, not the chrome.

Test: remove one visual separator at a time. If the structure still reads clearly, the separator was noise.

## Cap-Height Spacing

Use the height of a capital letter in the heading as the spacing unit between the heading and its associated body text. This creates a proportional relationship:

- Larger headings → more space before body
- Smaller headings → less space before body

The system scales itself. In wireframe annotations, note "use cap-height spacing" rather than specifying pixel values — the actual values depend on the final type scale (Form's territory).

## Hierarchy Levels in a Layout

Most screens need exactly 3–4 hierarchy levels. More than 4 creates confusion. Fewer than 3 creates flatness.

| Level          | What it contains                                   | How it's distinguished                                     |
| -------------- | -------------------------------------------------- | ---------------------------------------------------------- |
| **Primary**    | The one thing the user came to see or do           | Largest, most space around it, strongest position          |
| **Secondary**  | Supporting content that contextualizes the primary | Clearly smaller than primary, clearly larger than tertiary |
| **Tertiary**   | Metadata, navigation, secondary actions            | Noticeably smaller, less prominent position                |
| **Quaternary** | Footnotes, legal, timestamps                       | Minimal presence, doesn't compete                          |

In wireframes, annotate which level each element belongs to. If an element doesn't fit neatly into one level, either it's doing too much (split it) or the hierarchy needs a level adjustment.
