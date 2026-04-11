# Heuristics and Personas Reference

## Nielsen's 10 Heuristics — Scoring Rubric

Use this rubric for structured design critiques. Score each heuristic 0–4. Total is out of 40.

### Severity Scale

| Score | Meaning                                 | Action          |
| ----- | --------------------------------------- | --------------- |
| 0     | No issue                                | —               |
| 1     | Cosmetic — doesn't affect usability     | Polish pass     |
| 2     | Minor — causes confusion, user recovers | Fix soon        |
| 3     | Major — impairs key flow                | Fix this sprint |
| 4     | Catastrophe — blocks usage              | Fix now         |

### Score Bands

| Total | Rating                                    |
| ----- | ----------------------------------------- |
| 36–40 | Excellent — ship with polish pass         |
| 28–35 | Good — fix 3s before shipping             |
| 20–27 | Needs work — significant usability issues |
| < 20  | Critical — do not ship                    |

### The 10 Heuristics

**H1: Visibility of System Status**
The system keeps users informed about what's happening through appropriate feedback within reasonable time.

- Score 4: No feedback on any action. Loading states missing. User doesn't know if their action registered.
- Score 2: Some feedback, but delayed or incomplete (spinner with no label, success toast that disappears too fast).
- Score 0: All states communicate clearly. Loading, success, error, empty all designed and implemented.

**H2: Match Between System and Real World**
The system speaks the user's language — words, phrases, and concepts familiar to the user, not system-oriented jargon.

- Score 4: Technical jargon throughout. Error codes exposed. Metaphors from system internals, not user context.
- Score 2: Mostly clear, but a few specialist terms without explanation.
- Score 0: All labels, messages, and empty states use user-familiar language.

**H3: User Control and Freedom**
Users make mistakes. They need clearly marked "emergency exits" without having to go through extended dialogue.

- Score 4: Destructive actions with no confirmation. No undo. Navigation traps. Back button breaks state.
- Score 2: Undo available but hard to find. Confirmation dialogs present but not for all destructive actions.
- Score 0: Undo/redo available. Confirmations for destructive actions. Easy exit from any state.

**H4: Consistency and Standards**
Users shouldn't have to wonder whether different words, situations, or actions mean the same thing.

- Score 4: Same action has different labels in different contexts. Component behavior varies arbitrarily. Platform conventions broken.
- Score 2: Mostly consistent, with a few unexplained variations.
- Score 0: Consistent terminology, visual language, and behavior across the product. Follows platform conventions.

**H5: Error Prevention**
Better than good error messages: design carefully to prevent problems from occurring in the first place.

- Score 4: Users can easily enter invalid states. Forms accept invalid input and fail late. Irreversible actions have no safeguards.
- Score 2: Some validation present, but not comprehensive. Constraints communicated after failure, not before.
- Score 0: Input constraints shown before interaction. Inline validation. Dangerous actions require confirmation. Defaults are safe.

**H6: Recognition Rather Than Recall**
Minimize user memory load. Make objects, actions, and options visible. Instructions visible or easily retrievable.

- Score 4: Users must memorize sequences, codes, or states. Critical information not visible at decision points.
- Score 2: Most information available, but some requires navigating away or remembering from earlier.
- Score 0: All information needed for decisions is visible at the decision point. No memory required for core flows.

**H7: Flexibility and Efficiency of Use**
Accelerators — unseen by novices — allow experts to work faster. The system should serve both inexperienced and experienced users.

- Score 4: Single path for all users. No shortcuts. No way for experts to move faster.
- Score 2: Some shortcuts exist but undiscoverable or incomplete.
- Score 0: Keyboard shortcuts for common actions. Bulk operations available. Progressive disclosure allows expert-mode access.

**H8: Aesthetic and Minimalist Design**
Dialogues should not contain irrelevant or rarely needed information. Every extra unit of information competes with relevant information.

- Score 4: Pages cluttered with options, labels, icons, and metadata. No clear hierarchy. Everything equally prominent.
- Score 2: Mostly clean, but some screens have low-value information at high visual weight.
- Score 0: Every element earns its place. Hierarchy clear. Secondary information de-emphasized. Visual noise minimized.

**H9: Help Users Recognize, Diagnose, and Recover from Errors**
Error messages should be expressed in plain language (no codes), precisely indicate the problem, and constructively suggest a solution.

- Score 4: Error codes exposed. No explanation. No path forward. Red banner with "Something went wrong."
- Score 2: Errors explained but solution not offered. Generic messages for specific problems.
- Score 0: Every error message: explains what happened, why it happened, and what to do next. In plain language.

**H10: Help and Documentation**
Even though it is better if the system can be used without documentation, it may be necessary to provide help. Help should be easy to search, focused on the user's task, and not too large.

- Score 4: No help available anywhere. No tooltips, no onboarding, no documentation links.
- Score 2: Help exists but not contextual. Generic documentation not linked from the place it's needed.
- Score 0: Contextual help at decision points. Tooltips on non-obvious controls. Documentation linked from error states and empty states.

---

## Issue Severity Framework

For tracking and prioritizing found issues separate from heuristic scoring.

| Priority | Definition                                                                      | SLA                        |
| -------- | ------------------------------------------------------------------------------- | -------------------------- |
| **P0**   | Blocks core usage. User cannot complete primary flow.                           | Fix now, before this ships |
| **P1**   | Impairs key flow. User can complete but with significant friction or confusion. | Fix this sprint            |
| **P2**   | Annoyance. User notices but works around it.                                    | Fix soon                   |
| **P3**   | Polish. User unlikely to notice. Matters for craft and consistency.             | Backlog                    |

When running a design review, log every issue as P0–P3. P0s and P1s block shipping. P2s and P3s get triaged.

---

## Cognitive Load Assessment

Three types of cognitive load. Good design minimizes extraneous, supports germane, accepts intrinsic.

| Type           | What it is                             | Design goal                        |
| -------------- | -------------------------------------- | ---------------------------------- |
| **Intrinsic**  | Complexity inherent to the task itself | Accept it — can't be designed away |
| **Extraneous** | Load added by poor design              | Eliminate it                       |
| **Germane**    | Load that builds useful mental models  | Support and reinforce it           |

### Working Memory Rule

Users can hold approximately 4 items in working memory at one decision point. Design for this limit.

Violation: a form field with 12 options, no default, no grouping, and no indication of which options are most common. User must hold all 12 options in mind simultaneously.

Correction: group options, provide a smart default, show the 3 most common first, hide the rest behind "More options."

### Common Extraneous Load Violations

- **Too many choices without defaults** — decision paralysis. Add a recommended default, group by frequency of use, or use progressive disclosure.
- **Inconsistent patterns forcing relearning** — users build a mental model from the first 3 interactions. If the 4th interaction breaks that model, they have to re-learn. Cost: frustration + errors.
- **Hidden information requiring recall** — information needed to make a decision that isn't shown at the decision point. Solution: surface the information, or restructure the flow.
- **Complex forms without progressive disclosure** — show fields as they become relevant. A form with 20 fields shown simultaneously creates extraneous load even if only 5 are required.
- **Navigation requiring memorization** — if a user has to remember where a feature is rather than find it by logic, the information architecture has failed.
- **Error messages without context** — errors shown after a multi-step form that don't point to the specific problem. User has to diagnose without evidence.
- **Multi-step processes without progress indication** — user doesn't know how many steps remain. Each step increases uncertainty. Show step X of N or a progress bar.
- **Jargon requiring translation** — every domain term or acronym requires translation effort. Budget: 0 unexplained jargon in onboarding flows.

---

## 5 Test Personas

Use these personas when evaluating designs. Each persona stress-tests a different dimension. A design that works for all 5 is production-ready.

### Alex — Power User

Background: Uses the product daily for their core job. Has been using similar tools for years. Optimizes for speed.

Evaluates:

- Keyboard shortcut availability and discoverability
- Bulk action and multi-select capabilities
- Customization and saved configurations
- Density options (can they see more on screen?)
- Import/export and integration access

Failures that frustrate Alex: required confirmation dialogs for low-stakes actions, no keyboard shortcuts on repetitive tasks, pagination where filtering would serve better, clicks required for actions that should be automatic.

### Jordan — First-Timer

Background: Just signed up. No prior knowledge of the product. Following a recommendation from a colleague. Has 15 minutes to evaluate whether this is worth their time.

Evaluates:

- Empty states (are they helpful or blank voids?)
- Onboarding flow (does it reach the first value moment fast?)
- Labels and descriptions (are they self-explanatory?)
- CTAs (is the next action always obvious?)
- Error recovery (when they make a wrong move, can they easily get back?)

Failures that lose Jordan: a dashboard with no data and no guidance, form errors without explanation, navigation that requires learning before using, features that require setup before providing value.

### Sam — Accessibility User

Background: Uses a screen reader and keyboard-only navigation. May have low vision and use high-contrast mode.

Evaluates:

- Screen reader flow (do headings create logical document structure? Do images have alt text? Do icons have labels?)
- Keyboard navigation (tab order logical? Focus visible? No keyboard traps?)
- Color contrast (does all text pass WCAG AA 4.5:1?)
- Color-only information (is color-only state also communicated via text or icon?)
- Motion (does `prefers-reduced-motion` disable or reduce animations?)
- Touch vs keyboard (are all interactive elements reachable without pointer?)

Failures that block Sam: focus outlines removed with `outline: none`, information conveyed only by color, unlabeled icon buttons, modal dialogs that don't trap focus, skip-navigation links missing, animation that cannot be disabled.

### Riley — Stress Tester

Background: Uses the product in difficult conditions — slow network connection, on an older device, while multitasking, after receiving unexpected data.

Evaluates:

- Performance degradation behavior (loading states, skeleton screens, timeout handling)
- Error states (what happens when an API call fails? when a file upload fails?)
- Edge content (long strings, empty strings, special characters, RTL text)
- Interruption resilience (form state preserved across page refresh? session timeout handled gracefully?)
- Offline or partial connectivity behavior

Failures that surface under stress: spinners with no timeout or retry, white screens on API failure, form data lost on navigation, truncation that breaks layout instead of wrapping, optimistic updates that don't handle server rejection.

### Casey — Mobile/Distracted User

Background: Uses the product on a phone, one-handed, while commuting or in a busy environment. Glances at the screen rather than reading carefully.

Evaluates:

- Thumb zones (primary actions in the bottom 60% of screen? or buried in top corners?)
- Touch target sizes (all interactive elements ≥ 44×44px?)
- Scanning over reading (headings and labels provide sufficient context without body copy?)
- One-handed usability (can the core flow be completed without two hands?)
- Notification response (can the user take the right action from a notification without opening the full app?)

Failures that frustrate Casey: primary action in top-right corner, small touch targets with large gaps between them, multi-column layouts that require scrolling sideways, destructive actions next to primary actions with no spacing, critical information below the fold without indication there's more.
