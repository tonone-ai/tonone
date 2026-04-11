# Polish Checklist — Final QA Pass Before Shipping

Run this checklist before marking any UI work done. These are the catches that separate shipped from shipped well.

## Visual Alignment

- [ ] Consistent spacing scale throughout — no ad hoc pixel values, only design tokens
- [ ] Elements align to the layout grid
- [ ] Optical alignment verified — mathematically centered is not always visually centered
- [ ] Consistent `border-radius` — no mix of sharp and rounded without intent
- [ ] Consistent shadow elevation — no random box-shadow values

## Typography

- [ ] Hierarchy clear at every screen: one `<h1>`, logical heading nesting
- [ ] No orphaned words at line breaks — use `text-wrap: balance` for headings
- [ ] Consistent text sizes — no values outside the type scale
- [ ] Links visually distinguishable from body text (not just color — underline or weight)

## Color and Contrast

- [ ] All text passes WCAG AA: 4.5:1 for normal text, 3:1 for large text (18px+ bold or 24px+)
- [ ] All interactive elements have visible `:focus-visible` state
- [ ] Hover states are distinguishable from default
- [ ] Disabled states are visually clear — not invisible, not full opacity either
- [ ] Dark mode tested separately — not assumed to be correct from light mode alone
- [ ] Color is never the sole indicator of meaning

## Interaction States

- [ ] Every button and link has: hover + focus-visible + active + disabled states
- [ ] Forms show validation feedback in real-time (on blur at minimum)
- [ ] Loading states use skeleton screens matching actual layout
- [ ] Success and error feedback is timely (not delayed) and visually clear
- [ ] Disabled controls have `cursor: not-allowed`

## Micro-Interactions

- [ ] Transitions between states are smooth — no instant state changes on 300ms+ operations
- [ ] Route transitions don't flash white/blank
- [ ] Accordion/expand animations are directional (matching the expand direction)
- [ ] Toast notifications don't stack awkwardly (max 3, queued beyond that)
- [ ] `prefers-reduced-motion` reduces or removes all animations

## Content Edge Cases

- [ ] Long text truncates gracefully with ellipsis — no text overflow breaking layout
- [ ] Empty states are designed with heading, context, and CTA (not just "No items")
- [ ] Error messages are actionable — not "Something went wrong"
- [ ] Dates and numbers are locale-aware (`Intl.DateTimeFormat`, `Intl.NumberFormat`)
- [ ] Long usernames and titles tested (80+ characters)
- [ ] Zero, one, and many items tested for every list

## Responsive

- [ ] No horizontal scroll at any viewport width
- [ ] Touch targets are minimum 44×44px on mobile
- [ ] Text is readable without zoom on mobile (base font size ≥ 16px)
- [ ] Images don't break layout at any width
- [ ] Tested at 320px, 375px, 768px, 1024px, 1440px

## Performance

- [ ] No visible layout shifts on load (CLS < 0.1)
- [ ] Above-fold content loads quickly — LCP target < 2.5s
- [ ] Interactions feel instant — no janky response to clicks/taps (INP < 200ms)
- [ ] No janky scroll — no synchronous layout in scroll handlers
- [ ] Images are lazy-loaded below the fold
- [ ] No blocking scripts in `<head>` without `async`/`defer`
