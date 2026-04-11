# Design Simplification Reference

Sourced from impeccable design system. For reducing complexity and clarifying flows.

## Core Question

"What's the ONE thing this should accomplish?"

Every element must justify its existence against this answer.

## The 20/80 Rule

Identify the 20% of features delivering 80% of value. Everything else is a candidate for removal or progressive disclosure.

## Information Architecture

- Remove secondary actions from primary view
- Progressive disclosure: hide complexity behind clear entry points
- Combine related actions (merge similar buttons, consolidate forms)
- ONE primary action, few secondary, everything else tertiary or hidden
- If it's said elsewhere, don't repeat it

## Interaction Simplification

- Fewer choices = clearer path (paradox of choice)
- Smart defaults: make common choices automatic
- Inline actions over modal flows where possible
- Remove steps: can it be fewer steps?
- ONE obvious next step, not five competing actions

## Content Simplification

- Cut every sentence in half, then do it again
- Active voice: "Save changes" not "Changes will be saved"
- Plain language over jargon
- Scannable: short paragraphs, bullets, clear headings
- Say it once, say it well — no redundant copy

## What NOT to Simplify

- Necessary functionality (simple ≠ feature-less)
- Accessibility requirements (labels/ARIA still required)
- Information users need for decisions
- Error recovery paths
- Complex domains that ARE inherently complex

## Verification

After simplifying, check:

- Faster task completion?
- Reduced cognitive load?
- Still functionally complete?
- Clearer hierarchy?
