# Production Hardening — Implementation Reference

## Error Handling

Every API call needs three states: loading, error, success. No exceptions.

- Show user-friendly message — never a raw error object or stack trace
- Include a retry action alongside the error message
- Errors appear near the source (inline), not as a distant toast
- Network errors get a specific "Check your connection" message, not a generic failure
- Log full error context server-side; surface only what helps the user

```tsx
// Pattern: loading/error/success states
const { data, error, isLoading } = useQuery(...)

if (isLoading) return <Skeleton />
if (error) return <ErrorMessage message="Could not load results." onRetry={refetch} />
return <DataView data={data} />
```

## Empty States

Every list or collection needs a designed empty state. An empty `<ul>` is not acceptable in production.

Empty state = onboarding opportunity. The user just arrived at a blank slate — tell them what to do.

Structure:

1. Illustration or icon (optional, keeps it lightweight)
2. Short heading: "No projects yet"
3. One-line explanation: "Create a project to organize your work"
4. CTA button: "Create project"

```tsx
// Pattern
function ProjectList({ projects }) {
  if (projects.length === 0) {
    return (
      <EmptyState
        heading="No projects yet"
        description="Create a project to organize your work."
        action={<Button onClick={handleCreate}>Create project</Button>}
      />
    );
  }
  return <ul>{projects.map(...)}</ul>;
}
```

## Edge Cases to Handle

- **Text overflow** — `text-overflow: ellipsis` + `overflow: hidden` + `white-space: nowrap`, or `line-clamp` for multi-line
- **Long usernames/titles** — test with 80+ character strings
- **Very short content** — single-character names, one-word titles
- **Collection sizes** — 0 items, 1 item, 1000+ items (virtualize above 100)
- **Slow network** — skeleton screens + timeout message after 10s
- **Offline** — detect with `navigator.onLine` + `online`/`offline` events, show persistent banner
- **Concurrent edits** — detect stale data on save, show conflict resolution UI

## i18n Readiness

Even if you're not shipping i18n today, don't make it impossible.

- No hardcoded user-facing strings in JSX — use translation keys or at minimum string constants
- Use `Intl.DateTimeFormat` and `Intl.NumberFormat` — never hand-format dates or currency
- Plan for 30–40% text expansion (German, Finnish) — test layouts with longer strings
- RTL support if there's any chance of Arabic/Hebrew users: use `dir="auto"` on root, use logical CSS properties

```css
/* Use logical properties */
margin-inline-start: 1rem; /* not margin-left */
padding-inline-end: 0.5rem; /* not padding-right */
border-inline-start: 1px solid; /* not border-left */
```

Never concatenate strings to form sentences — word order varies by language. Use interpolation with translation keys.

## Core Web Vitals Targets

| Metric | Target  | What it measures                  |
| ------ | ------- | --------------------------------- |
| LCP    | < 2.5s  | Largest content element load time |
| INP    | < 200ms | Interaction to next paint         |
| CLS    | < 0.1   | Layout shift score                |

## Performance Optimization

- Code-split routes with dynamic import — don't ship the whole app on first load
- Lazy-load below-fold components with `loading="lazy"` (images) or dynamic import
- Optimize images: WebP/AVIF format, proper `width`/`height`, `loading="lazy"` for below-fold
- Minimize main thread work — defer non-critical JS with `defer` or dynamic import
- Prefetch likely next pages (`<link rel="prefetch">` or Next.js `prefetch`)
- Debounce search inputs, throttle scroll handlers
- Virtualize long lists with `@tanstack/virtual` or `react-window` above 100 items

## Bundle Size Discipline

Track bundle size as part of CI. Flag regressions before they ship.

- Target: flag any single dependency >50KB gzipped
- Check tree-shaking: use named exports, set `"sideEffects": false` in package.json
- Banned patterns:
  - `import moment from 'moment'` — use `date-fns` or `Temporal`
  - `import _ from 'lodash'` — use `lodash-es` with named imports or native equivalents
  - `import * as Icons from 'react-icons'` — import individual icons

```bash
# Audit bundle
npx bundlesize
npx size-limit
npx vite-bundle-visualizer  # for Vite projects
```

## Accessibility Hardening

Final a11y pass before shipping:

- [ ] Skip-to-content link as first focusable element
- [ ] `<html lang="en">` (or correct locale code)
- [ ] Meaningful `<title>` on every page (not just "App")
- [ ] All images have `alt` — decorative images use `alt=""`
- [ ] Form errors linked via `aria-describedby`
- [ ] `aria-live` regions for dynamic content updates
- [ ] Color is never the sole indicator (icon or label accompanies color meaning)
- [ ] `prefers-reduced-motion` respected (see motion-design.md)
- [ ] `prefers-color-scheme` respected if dark mode is supported
- [ ] All interactive elements reachable and operable via keyboard
