# Motion Design — Implementation Reference

## Duration Rules

| Use Case                                                      | Duration |
| ------------------------------------------------------------- | -------- |
| Micro-interactions (button press, toggle)                     | 100ms    |
| Standard transitions (expand, slide, fade)                    | 300ms    |
| Complex animations (page transitions, orchestrated sequences) | 500ms    |
| Hard ceiling for any UI animation                             | 700ms    |

Never exceed 700ms. Animations that outlast the user's patience become friction.

## Easing Curves

| Curve         | Use For                                           |
| ------------- | ------------------------------------------------- |
| `ease-out`    | Entrances — elements arriving into view           |
| `ease-in`     | Exits — elements leaving the view                 |
| `ease-in-out` | Position changes — elements moving between states |
| `linear`      | Progress bars only                                |

Custom springs:

```css
/* Bouncy — springy confirm, badge pop */
cubic-bezier(0.34, 1.56, 0.64, 1)

/* Smooth deceleration — drawers, sheets, menus */
cubic-bezier(0.22, 1, 0.36, 1)
```

## GPU Acceleration

Animate only composited properties. These trigger no layout:

- `transform` (translate, scale, rotate)
- `opacity`

Never animate these — they trigger layout (expensive):

- `width`, `height`
- `top`, `left`, `bottom`, `right`
- `margin`, `padding`

Use `will-change` sparingly — it promotes an element to its own layer and uses memory. Apply before animation starts, remove after it ends. Never set `will-change: all`.

```css
/* Before animation */
.element {
  will-change: transform, opacity;
}

/* After animation completes — remove via JS or animation end event */
.element {
  will-change: auto;
}
```

## Staggered Animations

For list items, grid cards, menu items: 50–80ms delay between siblings.

```
delay = index * 50ms
```

Cap total stagger at 400ms. Beyond that it reads as slow, not elegant.

```css
/* CSS custom property approach */
.item {
  transition-delay: calc(var(--index) * 50ms);
}

/* Set --index in template */
```

```jsx
// React example
items.map((item, i) => <Item key={item.id} style={{ "--index": i }} />);
```

## prefers-reduced-motion — NON-NEGOTIABLE

Every project ships this. No exceptions.

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

For users who prefer reduced motion but still benefit from state feedback, replace motion with opacity-only crossfade:

```css
@media (prefers-reduced-motion: reduce) {
  .animated-element {
    transition: opacity 150ms ease-out;
    /* No transform, no movement */
  }
}
```

In JS, check before starting animations:

```js
const prefersReducedMotion = window.matchMedia(
  "(prefers-reduced-motion: reduce)",
).matches;

if (!prefersReducedMotion) {
  // run animation
}
```

## Perceived Performance

- Use skeleton screens, not spinners — skeletons show layout structure, reduce perceived wait
- Start transitions instantly — don't wait for data before beginning the transition
- Stagger content appearance to show progress, not a wall of content arriving at once

## Animation Layers — Implement in This Order

Ship lower layers before higher ones. Layer 4 without layer 1 is noise.

| Layer | Category    | Examples                                       |
| ----- | ----------- | ---------------------------------------------- |
| 1     | Feedback    | Button press, toggle, hover states             |
| 2     | Transitions | Route changes, expand/collapse, show/hide      |
| 3     | Guidance    | Attention direction, tutorial highlights       |
| 4     | Delight     | Personality moments, celebrations, easter eggs |

## Production Easing Curves

Specific curves for common UI transitions:

```css
/* Entry (elements arriving into view) — fast deceleration */
--ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);

/* Exit (elements leaving view) — fast start, slow departure */
--ease-in-expo: cubic-bezier(0.7, 0, 0.84, 0);

/* State toggle (expand/collapse, switch) — smooth both ends */
--ease-in-out: cubic-bezier(0.45, 0, 0.55, 1);
```

## Bounce and Elastic Easing: Avoid in Production UI

Bounce (`cubic-bezier(0.34, 1.56, 0.64, 1)`) and elastic easing are personality moments, not standard transitions. Reserve them for:

- Celebration animations (confetti, achievement badges)
- Empty state illustrations
- Marketing hero sections

Never use bounce/elastic for:

- Button presses, toggles, or form interactions
- Navigation transitions
- Loading states
- Any element the user interacts with repeatedly

Repeated bounce animations become irritating within 3 uses. Standard UI transitions use `ease-out` for entries and `ease-in` for exits — no overshoot, no bounce.
