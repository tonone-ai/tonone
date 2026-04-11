# Discovery Interview Reference

Sourced from impeccable design system. For structured UX planning before implementation.

## Philosophy

Most AI-generated UIs fail from skipped thinking, not bad code. They jump to "card grid" without asking "what is the user trying to accomplish?" Understand deeply first, implement precisely after.

## Interview Structure

Ask conversationally — adapt based on answers, don't dump all at once.

### Purpose & Context

- What is this feature for? What problem does it solve?
- Who specifically will use it? (Role, context, frequency — not "users")
- What does success look like?
- What's user's state of mind when they reach this? (Rushed? Exploring? Anxious?)

### Content & Data

- What content is displayed or collected?
- Realistic ranges? (0 items, 5 items, 500 items)
- Edge cases? (Empty, error, first-time, power user)
- Dynamic content — what changes, how often?

### Design Goals

- Single most important thing user should do or understand?
- What should this feel like? (Fast? Calm? Fun? Premium?)
- Existing patterns to be consistent with?
- Examples (inside or outside product) that capture the goal?

### Constraints

- Technical? (Framework, performance, browser support)
- Content? (Localization, dynamic text, UGC)
- Mobile/responsive requirements?
- Accessibility beyond WCAG AA?

### Anti-Goals

- What should this NOT be?
- Biggest risk of getting this wrong?

## Design Brief Output

After discovery, synthesize into:

1. **Feature Summary** — 2-3 sentences: what, who, purpose
2. **Primary User Action** — the ONE thing
3. **Design Direction** — how it should feel, aesthetic approach
4. **Layout Strategy** — visual hierarchy and flow (not CSS)
5. **Key States** — default, empty, loading, error, success, edge cases
6. **Interaction Model** — clicks, hovers, scrolls, feedback, flow
7. **Content Requirements** — copy, labels, messages, dynamic ranges
8. **Open Questions** — unresolved items for implementer

Get explicit confirmation before considering brief complete.
