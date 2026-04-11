# Responsive Design — Implementation Reference

## Mobile-First Approach

Write base styles for mobile (375px baseline). Add complexity upward with `min-width` queries.

```css
/* Base: mobile */
.component {
  padding: 1rem;
}

/* Tablet and up */
@media (min-width: 768px) {
  .component {
    padding: 2rem;
  }
}

/* Desktop and up */
@media (min-width: 1024px) {
  .component {
    padding: 3rem;
  }
}
```

In Tailwind: unprefixed class = mobile, then `md:`, `lg:`, `xl:` stack up.

## Breakpoint Strategy

Use Tailwind defaults. Don't add custom breakpoints without a strong reason — every custom breakpoint is maintenance cost.

| Prefix | Min-width |
| ------ | --------- |
| `sm`   | 640px     |
| `md`   | 768px     |
| `lg`   | 1024px    |
| `xl`   | 1280px    |
| `2xl`  | 1536px    |

## Input Detection

Use capability queries, not screen width, for interaction pattern differences.

```css
/* Hover-capable devices (mouse, trackpad) */
@media (hover: hover) {
  .button:hover {
    background: var(--color-primary-hover);
  }
}

/* Touch primary input (phones, tablets) */
@media (pointer: coarse) {
  .touch-target {
    min-height: 44px;
    min-width: 44px;
  }
}

/* Precise pointer (mouse) */
@media (pointer: fine) {
  .drag-handle {
    cursor: grab;
  }
}
```

## Safe Areas (Notched Devices)

Required for fixed headers, footers, and floating action buttons.

```css
.fixed-header {
  padding-top: max(1rem, env(safe-area-inset-top));
}

.fixed-footer {
  padding-bottom: max(1rem, env(safe-area-inset-bottom));
}

.floating-button {
  bottom: max(1.5rem, env(safe-area-inset-bottom));
  right: max(1.5rem, env(safe-area-inset-right));
}
```

## Responsive Images

```html
<!-- Art direction: different crop per breakpoint -->
<picture>
  <source media="(min-width: 768px)" srcset="hero-wide.webp" />
  <source media="(min-width: 480px)" srcset="hero-medium.webp" />
  <img
    src="hero-mobile.webp"
    alt="Descriptive alt text"
    width="800"
    height="600"
    loading="lazy"
  />
</picture>

<!-- Resolution switching: same image, different sizes -->
<img
  src="photo-800.webp"
  srcset="photo-400.webp 400w, photo-800.webp 800w, photo-1600.webp 1600w"
  sizes="(min-width: 1024px) 800px, (min-width: 768px) 600px, 100vw"
  alt="Descriptive alt text"
  width="800"
  height="600"
  loading="lazy"
/>
```

Always provide explicit `width` and `height` to prevent CLS. Use `aspect-ratio` in CSS as a fallback for dynamic content.

## Container Queries

Prefer over media queries for component-level responsive behavior. A card doesn't care about the viewport — it cares about its container.

```css
/* Parent opts into container query context */
.card-grid {
  container-type: inline-size;
  container-name: card-grid;
}

/* Child responds to parent width */
@container card-grid (min-width: 400px) {
  .card {
    flex-direction: row;
  }
}
```

Use container queries when the same component appears in multiple layout contexts (sidebar, main column, modal).

## Touch Targets

- Minimum 44×44px for all interactive elements
- 8px minimum gap between adjacent targets
- Primary actions in bottom 60% of screen on mobile (thumb zone)

```css
.touch-target {
  min-height: 44px;
  min-width: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
```

Small visual elements (icons, badges) can be visually smaller than 44px if the clickable area is padded to meet the minimum.

## Testing Checklist

Test at these viewports — in this order, on real devices when possible:

| Width  | Device                      |
| ------ | --------------------------- |
| 320px  | iPhone SE (smallest common) |
| 375px  | Standard mobile baseline    |
| 768px  | Tablet portrait             |
| 1024px | Laptop / tablet landscape   |
| 1440px | Desktop                     |
| 1920px | Large monitor               |

Browser resize alone is insufficient — test on a real iPhone and Android device before shipping. Simulator covers layout but misses touch target feel, safe areas, and font rendering.

## Content-Driven Breakpoints

Device-based breakpoints (768px, 1024px) are an antipattern. They assume specific devices and break when new devices appear.

Content-driven breakpoints: set breakpoints where the **content** breaks — where a line becomes too long, a grid column becomes too narrow, or a component becomes unreadable.

```css
/* WRONG: device-based */
@media (min-width: 768px) {
  /* "tablet" */
}
@media (min-width: 1024px) {
  /* "desktop" */
}

/* RIGHT: content-driven */
@media (min-width: 45em) {
  /* prose column gets uncomfortably wide */
}
@media (min-width: 64em) {
  /* sidebar + main content both fit comfortably */
}
```

How to find content breakpoints:

1. Start at the smallest viewport (320px)
2. Slowly widen the viewport
3. When the layout starts to look wrong (lines too long, gaps too wide, elements too stretched), that's your breakpoint
4. Express it in `em` or `rem` (scales with font size)

Tailwind's default breakpoints (640/768/1024/1280/1536) are starting points. Override them when the content demands it — but document why.

## The clamp() Formula

Fluid typography and spacing without media queries:

```css
font-size: clamp(MIN, PREFERRED, MAX);
```

Derivation formula:

```
PREFERRED = MIN_REM + (MAX_PX - MIN_PX) / (MAX_VP - MIN_VP) * 100vw

Example: 16px at 375px viewport → 20px at 1280px viewport
PREFERRED = 1rem + (20 - 16) / (1280 - 375) * 100vw
         = 1rem + 0.442vw

font-size: clamp(1rem, 1rem + 0.442vw, 1.25rem);
```

Use [utopia.fyi](https://utopia.fyi/) to calculate automatically. Apply fluid sizing to the 2–3 sizes that matter most (body, primary heading). Don't make every type step fluid — it makes the scale unpredictable across viewports.
