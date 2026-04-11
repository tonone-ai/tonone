# Cognitive Load Reference

Sourced from impeccable design system. For evaluating screen complexity and flow decisions.

## Three Load Types

| Type           | Description                                                  | Design Goal                 |
| -------------- | ------------------------------------------------------------ | --------------------------- |
| **Intrinsic**  | Inherent task complexity (choosing insurance IS complex)     | Can't reduce — support it   |
| **Extraneous** | Load from poor design (confusing nav, inconsistent patterns) | MUST reduce — eliminate it  |
| **Germane**    | Useful learning (building mental models of the system)       | WANT to support — enable it |

## Working Memory Rule

Humans hold 4±1 items in working memory.

**Design implications:**

- Max 4 visible choices per decision point without grouping
- Progressive disclosure for complex forms (show fields in groups)
- Provide context at point of decision (don't require recall from earlier screens)
- Group related items visually

## 8 Common Violations

| Violation                                    | Fix                                                 |
| -------------------------------------------- | --------------------------------------------------- |
| Too many choices without defaults            | Smart defaults, group into categories               |
| Inconsistent patterns forcing relearning     | Standardize interaction patterns across screens     |
| Hidden information requiring recall          | Show context at decision points                     |
| Complex forms without progressive disclosure | Break into logical steps with progress indicator    |
| Navigation requiring memorization            | Clear wayfinding, breadcrumbs, landmarks            |
| Error messages without context               | Inline errors near the source with fix instructions |
| Multi-step processes without progress        | Stepper/progress bar, "Step 2 of 4"                 |
| Jargon requiring mental translation          | Plain language, tooltips for technical terms        |

## Assessment Checklist

For each screen or flow, ask:

1. How many things compete for attention?
2. Does user need to remember anything from a previous screen?
3. Are patterns consistent with what they've seen before?
4. Can they recover from mistakes without starting over?

If any answer is concerning, you've found extraneous load to eliminate.
