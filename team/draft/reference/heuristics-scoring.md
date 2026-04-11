# Nielsen Heuristics Scoring Reference

Sourced from impeccable design system. For structured UX critique and usability scoring.

## The 10 Heuristics

### 1. Visibility of System Status

System keeps user informed through timely feedback.

- Loading indicators present?
- Save confirmations shown?
- State changes visible?
- Form validation real-time?

### 2. Match Between System and Real World

Speaks user's language, follows real-world conventions.

- No jargon?
- Logical order?
- Familiar metaphors?

### 3. User Control and Freedom

Easy to undo, redo, escape.

- Undo available?
- Cancel paths clear?
- Multi-step can go back?
- Exit always accessible?

### 4. Consistency and Standards

Same words/actions mean the same thing.

- Terminology consistent?
- Interaction patterns uniform?
- Visual conventions followed?

### 5. Error Prevention

Eliminate error-prone conditions.

- Confirmation before destructive?
- Constraints prevent invalid input?
- Clear formatting guidance?

### 6. Recognition Rather Than Recall

Minimize memory load.

- Options visible?
- Context provided?
- Recent items shown?

### 7. Flexibility and Efficiency of Use

Accelerators for expert users.

- Keyboard shortcuts?
- Bulk actions?
- Customization available?

### 8. Aesthetic and Minimalist Design

No irrelevant information.

- Each element serves purpose?
- Visual hierarchy clear?
- Progressive disclosure used?

### 9. Help Users Recover from Errors

Error messages in plain language with solutions.

- Specific error messages?
- Recovery actions suggested?
- No raw error codes?

### 10. Help and Documentation

Easy to search, focused on task.

- Contextual help?
- Searchable docs?
- Feature onboarding?

## Scoring

**Per heuristic:** 0 = no issue, 1 = cosmetic, 2 = minor, 3 = major, 4 = catastrophe

**Score bands (total 0-40):**

- 36-40: Excellent
- 28-35: Good
- 20-27: Needs work
- <20: Critical redesign needed

## Issue Severity

| Level | Meaning          | Action          |
| ----- | ---------------- | --------------- |
| P0    | Blocks usage     | Fix immediately |
| P1    | Impairs key flow | Fix this sprint |
| P2    | Annoyance        | Fix soon        |
| P3    | Polish           | Backlog         |
