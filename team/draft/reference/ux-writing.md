# UX Writing Reference

Sourced from impeccable design system. For use in flow annotation, wireframe copy, and UX review.

## Button Labels

NEVER use "OK", "Submit", or "Yes/No". Use verb + object pattern:

| Bad        | Good           | Why                         |
| ---------- | -------------- | --------------------------- |
| OK         | Save changes   | Says what will happen       |
| Submit     | Create account | Outcome-focused             |
| Yes        | Delete message | Confirms the action         |
| Cancel     | Keep editing   | Clarifies what cancel means |
| Click here | Download PDF   | Describes the destination   |

For destructive actions, name the destruction: "Delete" not "Remove" (delete = permanent, remove = recoverable). Show count: "Delete 5 items" not "Delete selected".

## Error Message Formula

Every error answers: (1) What happened? (2) Why? (3) How to fix it?

| Situation         | Template                                                                       |
| ----------------- | ------------------------------------------------------------------------------ |
| Format error      | "[Field] needs to be [format]. Example: [example]"                             |
| Missing required  | "Please enter [what's missing]"                                                |
| Permission denied | "You don't have access to [thing]. [What to do instead]"                       |
| Network error     | "We couldn't reach [thing]. Check your connection and [action]"                |
| Server error      | "Something went wrong on our end. We're looking into it. [Alternative action]" |

Don't blame users: "Please enter a date in MM/DD/YYYY format" not "You entered an invalid date".

## Empty States

Empty states are onboarding moments, not dead ends:

1. Acknowledge briefly
2. Explain the value of filling it
3. Provide a clear action

"No projects yet. Create your first one to get started." — not "No items".

## Voice vs Tone

**Voice** = brand personality, consistent everywhere.
**Tone** adapts to moment:

| Moment              | Tone                                                           |
| ------------------- | -------------------------------------------------------------- |
| Success             | Celebratory, brief: "Done! Your changes are live."             |
| Error               | Empathetic, helpful: "That didn't work. Here's what to try..." |
| Loading             | Reassuring: "Saving your work..."                              |
| Destructive confirm | Serious, clear: "Delete this project? This can't be undone."   |

NEVER use humor for errors. Users are already frustrated.

## Accessibility

- Link text must have standalone meaning — "View pricing plans" not "Click here"
- Alt text describes information, not the image — "Revenue increased 40% in Q4" not "Chart"
- Icon buttons need `aria-label`
- Use `alt=""` for decorative images

## Translation Planning

| Language | Expansion vs English       |
| -------- | -------------------------- |
| German   | +30%                       |
| French   | +20%                       |
| Finnish  | +30-40%                    |
| Chinese  | -30% chars (similar width) |

Keep numbers separate, use full sentences as single strings, avoid abbreviations.

## Terminology Consistency

Pick ONE term, use it everywhere:

| Inconsistent                     | Pick One |
| -------------------------------- | -------- |
| Delete / Remove / Trash          | Delete   |
| Settings / Preferences / Options | Settings |
| Sign in / Log in / Enter         | Sign in  |
| Create / Add / New               | Create   |

## Loading States

Be specific: "Saving your draft..." not "Loading...". For long waits: "This usually takes 30 seconds".

## Confirmation Dialogs

Most confirmation dialogs are design failures — consider undo instead. When necessary: name the action, explain consequences, use specific labels ("Delete project" / "Keep project" — not "Yes" / "No").
