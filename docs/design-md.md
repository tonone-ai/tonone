# DESIGN.md format

One format for every skill that reads or writes `DESIGN.md` (repo root). Base: the platform layout (YAML frontmatter + fixed sections). `/form-brief` and `/form-document` both write it; `/form-lint` parses it.

## Frontmatter

Platform keys (do not rename): `name`, `description`, `colors`, `typography`, `rounded`, `spacing`, `components`.
Additive extensions: `elevation`, `motion` (written by `/form-document`).
Brief keys (written by `/form-brief`, all optional): `form_kind` (software | gaming | tech | product | service | place), `visitor_mode` (Persuade | Operate | Read | Experience), `mood`, `direction` (name chosen via `/form-direction`).

Values are literal CSS (`"#1a2b3c"`, `"0.875rem"`). Components reference tokens as `{colors.x}`.

## Sections (this order; omit rather than invent)

| #   | Heading             | Notes                                                                        |
| --- | ------------------- | ---------------------------------------------------------------------------- |
| 1   | Overview            | North star, feel, references, form_kind/visitor_mode prose, **Design dials** |
| 2   | Colors              | Primary / Neutral / Semantic with role and use rule                          |
| 3   | Typography          | Families, scale, hierarchy                                                   |
| 4   | Layout              | Spacing base, grid, max width, density                                       |
| 5   | Elevation & Depth   | Shadow vocabulary or "flat"                                                  |
| 6   | Shapes              | Radius vocabulary                                                            |
| 7   | Components          | One short block per recurring component                                      |
| 8   | Do's and Don'ts     | Rules plus exclusions                                                        |
| 9   | Responsive Behavior | Optional. Breakpoints and per-size behavior                                  |
| 10  | Agent Prompt Guide  | Optional. Hard rules for downstream agents                                   |
| 11  | Drift Candidates    | Optional. `/form-document` only; written without `#` or units (see skill)    |

Design dials live in Overview as the block below (prism-ui and move-animate read it by that text, wherever the heading is):

```
Design dials
  DESIGN_VARIANCE   4  — <rationale>
  MOTION_INTENSITY  3  — <rationale>
  VISUAL_DENSITY    7  — <rationale>
```

## Who writes what

| Skill                                                         | Writes                                                                                                                                |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `/form-brief`                                                 | Frontmatter incl. brief keys; sections 1-10 from resolved tokens (greenfield). Dials, Do's and Don'ts exclusions, Agent Prompt Guide. |
| `/form-document`                                              | Frontmatter + sections 1-8 and 11 from shipped code (diff, never overwrite). Preserves hand-written Overview and Do's and Don'ts.     |
| `/form-direction`                                             | Nothing directly; its chosen direction name goes in `direction` when DESIGN.md is next written.                                       |
| `/form-lint`                                                  | Reads only. Every `#hex`, `rgb()`/`hsl()` color and `px`/`rem` number anywhere in the file is the sanctioned allow-list.              |
| `/prism-ui`, `/move-animate`, `/form-critique`, `/form-audit` | Read only.                                                                                                                            |

## Legacy headings (tolerate and migrate)

Files written before this spec use `/form-brief`'s headings and no frontmatter. Readers MUST accept them; the lint ignores headings entirely. Writers migrate on next write (show the diff, apply on approval):

| Legacy                                                   | Unified           |
| -------------------------------------------------------- | ----------------- |
| Visual Theme & Atmosphere                                | Overview          |
| Color Palette & Roles                                    | Colors            |
| Typography Rules                                         | Typography        |
| Component Stylings                                       | Components        |
| Layout Principles                                        | Layout            |
| Depth & Elevation                                        | Elevation & Depth |
| Responsive Behavior, Agent Prompt Guide, Do's and Don'ts | unchanged         |

Legacy `Background:` / `Accent:` bullet values become `colors` frontmatter entries; `form_kind` and `visitor_mode` bullets become frontmatter keys.

## Minimal example

```markdown
---
name: Acme
description: Invoicing for freelancers
form_kind: software
visitor_mode: Operate
mood: professional_minimal
colors:
  background: { value: "#faf9f7" }
  text: { value: "#1c1b1a" }
  accent: { value: "#2d5be3" }
typography:
  body:
    {
      fontFamily: "Source Sans 3",
      fontSize: "1rem",
      fontWeight: 400,
      lineHeight: 1.5,
    }
rounded: { md: "6px" }
spacing: { md: "16px" }
components:
  button-primary:
    {
      backgroundColor: "{colors.accent}",
      textColor: "{colors.background}",
      rounded: "{rounded.md}",
    }
---

# Design System: Acme

## Overview

Calm, exact, quick. Design dials
DESIGN_VARIANCE 2 — convention wins in a finance tool
MOTION_INTENSITY 2 — motion confirms, never performs
VISUAL_DENSITY 7 — daily use

## Colors

Accent #2d5be3 for primary actions only.

## Do's and Don'ts

- DO use only the tokens above.
- DON'T add gradients.
```
