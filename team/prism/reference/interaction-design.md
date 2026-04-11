# Interaction Design — Implementation Reference

## 8 States Every Component Needs

Never ship a component missing any of these:

1. **Default** — resting state
2. **Hover** — cursor over element
3. **Focus-visible** — keyboard/assistive navigation focus
4. **Active/Pressed** — mid-click or key-down
5. **Disabled** — not interactable
6. **Loading** — async operation in progress
7. **Error** — operation failed or validation failed
8. **Success** — operation completed

## Focus Rings

Use `:focus-visible`, not `:focus`. `:focus` fires on mouse click too — `:focus-visible` only fires when the user is navigating via keyboard or assistive tech.

```css
:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
```

Never `outline: none` without a visible replacement. This breaks keyboard navigation for every user relying on it.

## Form Design Checklist

- [ ] Label always visible — not just placeholder (placeholders disappear on input)
- [ ] Error message: appears below field + red border + `aria-describedby` linking field to error
- [ ] Success state resets after a short delay (don't leave success indicator forever)
- [ ] Disabled fields: `cursor: not-allowed` + `opacity: 0.5` + `pointer-events: none`
- [ ] Submit button shows loading state while pending
- [ ] Form preserves state on validation error — losing user input is a product failure
- [ ] Required fields marked (visually + `aria-required="true"`)
- [ ] Error messages describe what went wrong and how to fix it

```html
<!-- Correct error linking -->
<input
  id="email"
  type="email"
  aria-describedby="email-error"
  aria-invalid="true"
/>
<p id="email-error" role="alert">Enter a valid email address</p>
```

## Loading States

- Skeleton screens, not spinners — skeletons match actual layout dimensions
- `aria-busy="true"` on the loading container
- `aria-live="polite"` for dynamic content updates that aren't urgent

```html
<div aria-busy="true" aria-label="Loading results">
  <SkeletonCard />
  <SkeletonCard />
  <SkeletonCard />
</div>
```

## Modals

- Trap focus inside — use `inert` attribute on background content
- Close on Escape key
- Close on backdrop click (non-destructive actions only — never for delete confirmations)
- Return focus to the trigger element on close
- Prevent body scroll: `overflow: hidden` on `<body>` while open

```js
// On open
document.body.style.overflow = "hidden";
backgroundContent.inert = true;
firstFocusableElement.focus();

// On close
document.body.style.overflow = "";
backgroundContent.inert = false;
triggerElement.focus();
```

Use Radix UI Dialog or Headless UI Dialog rather than hand-rolling this.

## Popovers and Dropdowns

- Position with `@floating-ui/dom` or CSS anchor positioning — never hand-roll position calculation
- Flip automatically when near viewport edges
- Close on outside click
- Close on Escape
- Maintain scroll position of parent page

## Destructive Actions

- Require confirmation (modal or inline confirm step)
- Red color coding — use `--color-danger` token
- Button label is specific: "Delete project" not "Delete" not "OK"
- Offer undo when technically feasible
- Never auto-confirm destructive actions on single click

## Keyboard Navigation

| Key           | Action                                                               |
| ------------- | -------------------------------------------------------------------- |
| Tab           | Sequential navigation between focusable elements                     |
| Arrow keys    | Navigation within a component (tabs, menus, radio groups, listboxes) |
| Enter / Space | Activate a focused element                                           |
| Escape        | Dismiss overlays, cancel operations                                  |
| Home / End    | Jump to first / last item in a list or menu                          |

Implement roving tabindex for composite widgets (menus, tabs, radio groups) — only one element in the group is in the tab sequence at a time.

## Toast / Notification

```html
<!-- Errors — announced immediately -->
<div role="alert">Payment failed. Check your card details.</div>

<!-- Info/status — announced politely -->
<div role="status" aria-live="polite">Changes saved.</div>
```

- `role="alert"` for errors (interrupting, announced immediately)
- `role="status"` for info/success (polite, waits for user pause)
- Auto-dismiss after 5–8 seconds — never auto-dismiss errors
- Max 3 stacked toasts — queue the rest
- Consistent position: top-right (desktop) or bottom-center (mobile)
- Errors belong inline near the source, not in toasts
