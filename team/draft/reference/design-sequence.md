# Design Sequence Reference

## The Correct Order

Design work follows a strict sequence. Each step constrains the next. Skipping ahead produces rework.

```
1. Personas       → Who? What context, constraints, goals?
2. Use cases      → What tasks? What does "done" look like?
3. Wireframes     → What structure serves those tasks?
4. Visual design  → What treatment makes it trustworthy and clear?
```

**Visual design is last, not first.** Choosing colors and fonts before understanding user tasks produces decoration, not design. A wireframe built on clear use cases is more useful than a polished mockup built on assumptions.

## Why This Order Matters for UX

Each step produces the inputs the next step needs:

| Step       | Produces                                            | Consumed By                                       |
| ---------- | --------------------------------------------------- | ------------------------------------------------- |
| Personas   | User goals, constraints, mental models              | Use cases — which tasks to support                |
| Use cases  | Task descriptions, success criteria, frequency      | Wireframes — what content and actions appear      |
| Wireframes | Information hierarchy, screen structure, flow logic | Visual design — what to emphasize and subordinate |

Skipping personas → use cases built on assumptions about who the user is.
Skipping use cases → wireframes that serve the feature list, not the user's job.
Skipping wireframes → visual design that looks good but has broken information hierarchy.

## Right-Sizing Design Investment

Not every screen needs the same depth of design work. Use the hammer vs. shoe test:

- **Shoe (right investment):** This signup flow has a 60% drop-off rate — let's understand why and redesign it.
- **Hammer (over-investment):** Let's redesign every settings page with the full persona → wireframe → visual pipeline.

For Draft's work specifically:

- **Full sequence (persona → wireframe):** Core task flows (the things users do daily), onboarding, any flow with conversion or retention impact
- **Abbreviated (use case → quick wireframe):** Settings pages, admin screens, low-traffic secondary flows
- **Skip wireframe:** Simple CRUD lists, standard form pages with no novel interaction — use established patterns directly

## Credibility and Trust

The Fogg credibility study found that ~75% of credibility judgment comes from design (46% visual design, 28% information design/structure).

For Draft, the information design component (28%) is directly in scope: navigation that makes sense, information organized logically, clear labeling, predictable interaction patterns. Poor information architecture erodes trust even when the visual layer is polished.

This is why Draft's structural work matters early — not as an afterthought after visual design.
