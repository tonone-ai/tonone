# Craft Floor

The non-negotiable floor every UI ships with. Not taste, not direction: the baseline below which work is unfinished. Each line has one concrete check. Run it after the build, before handoff.

For anti-patterns and AI-slop direction see `design-craft.md`. This file does not repeat that list; items already there (Inter defaults, purple gradients, nested cards, lorem ipsum as a slop signal, missing focus styles, `prefers-reduced-motion`) stay there.

## The brief wins

If the brief or brand explicitly calls for something on the REFUSE list (a deliberate pure-black-on-white brutalist page, a gradient headline in an established identity), the brief wins. Do it, and note the deviation in the handoff: `Deviation: <item> — <why the brief requires it>`. Silent deviation is a failure; documented deviation is a decision. The VERIFY list has no override, except where a platform makes an item impossible; note that too.

---

## VERIFY (must exist before ship)

**States**

- [ ] Empty, error, and loading states exist for every data view. Check: force each (no rows, failed request, pending request) and screenshot all three. Empty state says what is missing and offers the next action.
- [ ] Loading holds layout. Check: skeleton or reserved height matches final content; throttle network and watch for jump.
- [ ] Errors say what happened and what to do, next to the thing that failed. Check: no bare "Something went wrong".

**Layout and viewport**

- [ ] Full-height mobile sections use `dvh` or `svh`, never raw `vh`. Check: grep for `100vh`; open on a phone with the URL bar visible and collapsed.
- [ ] No horizontal scroll at 320px. Check: resize to 320px and scroll sideways.
- [ ] Images and embeds reserve space (`width`/`height` or `aspect-ratio`). Check: Lighthouse CLS under 0.1.

**Color and depth**

- [ ] Shadows are tinted: hue-shifted toward the surface or brand hue, not `rgba(0,0,0,x)`. Check: grep `box-shadow` for pure black; shadow tokens use the neutral hue at low alpha.
- [ ] Light vs dark is chosen by use scene (who looks, where, ambient light, session length), not by fashion or category. Check: the brief or DESIGN.md names the scene in one line.
- [ ] Dark mode has explicit token values, not inverted light values. Check: both themes defined in the token file.

**Type**

- [ ] Tabular numerals on figures that align or update: tables, prices, counters, timers, charts. Check: `font-variant-numeric: tabular-nums` on those elements; digits do not jitter when values change.
- [ ] `text-wrap: balance` on headings, `text-wrap: pretty` on body copy. Check: no one-word last lines on headings; no orphans in paragraphs at three widths.
- [ ] Body line length 45-75 characters. Check: measure at desktop width.

**Browser surfaces**

- [ ] `::selection` themed with brand colors that keep text contrast. Check: select text in both themes.
- [ ] `caret-color` set to the accent on inputs and editable regions. Check: click into a field.
- [ ] Scrollbars themed (`scrollbar-color`, `scrollbar-width`) on custom scroll regions, in both themes. Check: scroll a panel in each theme.
- [ ] `color-scheme` declared so native controls and scrollbars follow the theme. Check: a native select and date input match the theme.

**Interaction**

- [ ] `:focus-visible` ring on every interactive element, 3:1 against its surroundings, offset from the element. Check: tab through the page; the ring is never clipped by `overflow: hidden`.
- [ ] Touch targets at least 44x44px (24px minimum on dense desktop-only tools, with spacing). Check: measure the smallest control on a 375px viewport.
- [ ] Hover-only affordances have a touch and keyboard equivalent. Check: tooltips and reveal menus work without a pointer.
- [ ] Disabled and busy controls explain themselves. Check: a disabled submit shows why, or the reason is reachable by tooltip or inline text.

**Content**

- [ ] Real copy and real data in every state, including long names, long numbers, and non-Latin text. Check: paste a 60-character name and a 9-digit figure; nothing clips unintentionally.
- [ ] Every icon-only button has an accessible name. Check: screen reader or `aria-label` grep.

---

## REFUSE (do not ship)

- [ ] Emoji used as icons, bullets, or status. Check: scan source for emoji code points; icons come from one drawn set at one stroke weight.
- [ ] Pure `#000` text on pure `#fff` for body copy. Check: body color is a tinted near-black on a tinted near-white; contrast stays above AA without the harshness.
- [ ] Gradient text on body copy or long runs. Check: `background-clip: text` appears nowhere outside a deliberate single display moment.
- [ ] Placeholder as the only label. Check: every input has a visible, persistent `<label>`; placeholder shows format examples only.
- [ ] Lorem ipsum, "Test", "Untitled", or fake round numbers shipped. Check: grep for `lorem`, `ipsum`, `TODO`, `foo`.
- [ ] Layout shift on load: late fonts, late images, late banners pushing content. Check: `font-display` set with a metric-matched fallback; no banner inserts above existing content.
- [ ] Color as the only carrier of state (error red, success green). Check: grayscale screenshot still reads; each state has an icon or text.
- [ ] Positive `tabindex`, or `outline: none` with no replacement. Check: grep `tabindex="[1-9]"` and `outline: none`.
- [ ] Autoplaying sound, or autoplaying video without a pause control. Check: media mutes by default and pause is reachable.
- [ ] Modal on page load, or a modal that traps focus with no Escape and no visible close. Check: open it by keyboard; Escape closes it; focus returns to the trigger.
- [ ] Text over images without a scrim or measured contrast. Check: sample the worst-case pixel behind each text block and compute the ratio.
- [ ] Truncated text with no way to read the full value. Check: every ellipsis has a tooltip, expand, or detail view.
- [ ] Animation on `width`, `height`, `top`, or `left`. Check: motion uses `transform` and `opacity`; grep `transition: all`.
- [ ] Disabled zoom (`user-scalable=no`, `maximum-scale=1`). Check: pinch-zoom works on a phone.

---

## Scoring

Count unchecked VERIFY items and tripped REFUSE items. Zero: ship. Any VERIFY gap on states or focus: stop. Report severity with the unified indicators: states and focus gaps are CRITICAL, browser-surface and type details are WARNING, anything else is INFO.
