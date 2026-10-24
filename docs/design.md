# Design (R0.5)

Figma file: [Fix with Me — Design System & Prototype](https://www.figma.com/design/aq3OJwtmk5r6PMIlp8XMKD)

To tap through the screens, open the **Prototype** page and press **Present**. The flow starts on **01 Home**.

## What's in the file

| Page | Contents |
|---|---|
| Foundations | Colour swatches and the type ramp, all bound to variables |
| Components | 31 Lucide icons (ISC licence), Button (5 styles × 2 sizes), Icon Button, Tier Badge, Chip, Status Bar, App Bar, Tab Bar, Cause Row, Offer Card |
| Prototype | 7 linked screens at 390×844: Home, Live camera, Diagnosis, Guide, STOP, Parts, Cart |

**Tokens (Figma variables):**
- `Primitives`: 43 raw colours.
- `Color`: 28 semantic tokens for the light theme.
- `Color · Dark`: the same 28 names with dark-theme values.
- `Dimension`: spacing 2–48 px and radius 8–999 px.

Every variable carries web code syntax (e.g. `var(--color-brand-primary)`), so CSS custom properties in `apps/web` should use the same names.

**Type:** Inter for Latin text, Noto Sans Devanagari for Hindi (`Body/Hindi`, 16/26).

## Prototype links

```
Home ─ Scan with camera ─▶ Live camera ─ Looks right ─▶ Diagnosis
Home ─ Send ──────────────────────────────────────────▶ Diagnosis
Home ─ Continue your repair ─▶ Guide
Diagnosis ─ "Yes, it turns freely" ─▶ Guide ─ Next step ─▶ Parts ─ View cart ─▶ Cart
Diagnosis ─ composer ("Try: I smell burning") ─▶ STOP ─ go back ─▶ Diagnosis
Back buttons return to the previous screen; Camera ✕ returns to Home.
```

## Figma free-plan constraints we hit

- **3 pages per file:** foundations, components and screens each get one page.
- **1 mode per variable collection:** dark values live in a separate `Color · Dark` collection, not as a mode. In code, map them to a `[data-theme="dark"]` / `prefers-color-scheme` override.
- **About 20 MCP tool calls a month:** design edits through Claude are batched. Leave feedback as Figma comments so fixes can go out in one pass.

## Known gaps in the prototype

- The camera feed and step illustrations are placeholders (an icon on a tinted panel); real illustrations come later.
- The Diagnosis cause rows were detached from the `Cause Row` component, because Figma doesn't allow resizing a bar inside a component instance. In code, the bar width is simply the probability.
- The Tier Badge variants share one default label. Always set the `Label` property; labelled examples sit on the Components page.
- Prices, product names and model numbers on the screens are illustrative copy, not real listings.
- Only the light theme is drawn.

## Copy and UX rules shown in the prototype

- Every claim carries a tier badge: Verified, Likely, AI suggestion, Caution or Stop.
- A price always shows its source and when it was checked. Amazon shows "See price on Amazon" until the Creators API is available.
- Affiliate commission is disclosed on Parts and Cart, together with the promise that it never affects ranking.
- Safety copy comes before the action (e.g. "Switch off at the wall first").
