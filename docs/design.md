# Design (R0.5)

Figma file: [Fix with Me — Design System & Prototype](https://www.figma.com/design/aq3OJwtmk5r6PMIlp8XMKD)

To tap through the screens, open the **Prototype** page and press **Present**. The flow starts on **00 Welcome**, where Fixy waves and says hi, then moves on to Home by itself after 1.8 s.

## What's in the file

| Page | Contents |
|---|---|
| Foundations | Colour swatches and the type ramp, all bound to variables |
| Components | **Fixy the robot** (7 moods), 32 Lucide icons (ISC licence), Button (5 styles × 2 sizes), Icon Button, Tier Badge, Chip, Status Bar, App Bar, Tab Bar, Cause Row, Offer Card |
| Prototype | 8 minimal, linked screens at 390×844: Welcome, Home, Camera, Chat, Guide, STOP, Parts, Cart |

**Tokens (Figma variables):**
- `Primitives`: 43 raw colours.
- `Color`: 28 semantic tokens for the light theme.
- `Color · Dark`: the same 28 names with dark-theme values.
- `Dimension`: spacing 2–48 px and radius 8–999 px.

Every variable carries web code syntax (e.g. `var(--color-brand-primary)`), so CSS custom properties in `apps/web` should use the same names.

**Type:** Inter for Latin text, Noto Sans Devanagari for Hindi (`Body/Hindi`, 16/26).

## Fixy, the robot companion

The robot is the centre of the UI. It is a component set, `Robot · Fixy`, with these moods:

| Mood | Used on | Animation in Present mode |
|---|---|---|
| Wave A / Wave B | Welcome, Home | Loops between the two every 0.35 s with Smart Animate, so the arm waves |
| Idle / Blink | Camera, chat avatar, Guide, Parts | Blinks every ~2.6 s |
| Thinking | While the engine works (not drawn yet) | None |
| Worried | STOP | None |
| Cheer | Cart; also for "Repair verified" | None |

Each arm sits in a pivot frame at the shoulder, so Smart Animate rotates it naturally. Sizes are set with `rescale()`: ~1.2–1.5 for heroes, ~0.25–0.3 for the chat avatar.

**UI rules after the simplification pass:**
- Show one short line per screen, with Fixy saying it.
- Home has no category grid and no tab bar: just Fixy and Scan (the big button), Talk and Type, plus History and the language toggle.
- Trust signals stay but shrink to badges ("Label read", "Likely: capacitor · 72%", "Fits", "Stock unknown").

## Prototype links

```
Welcome ─(after 1.8 s)─▶ Home
Home ─ Scan ─▶ Camera ─ shutter ─▶ Chat          Camera ✕ ─▶ Home
Home ─ Talk / Type ─▶ Chat
Chat ─ "Yes" ─▶ Guide ─ Next ─▶ Parts ─ Cart (1) ─▶ Cart
Chat ─ message box (demo of "I smell burning") ─▶ STOP ─ Go back ─▶ Chat
Back buttons: Chat→Home, Guide→Chat, Parts→Guide, Cart→Parts
```

## Figma free-plan constraints we hit

- **3 pages per file:** foundations, components and screens each get one page.
- **1 mode per variable collection:** dark values live in a separate `Color · Dark` collection, not as a mode. In code, map them to a `[data-theme="dark"]` / `prefers-color-scheme` override.
- **About 20 MCP tool calls a month:** design edits through Claude are batched. Leave feedback as Figma comments so fixes can go out in one pass.

## Known gaps in the prototype

- The camera feed and step illustrations are placeholders (an icon on a tinted panel); real illustrations come later.
- The full cause list (`Cause Row`) is now collapsed into one "Likely" badge in the chat. Tapping it should open the full ranked list; that sheet is not drawn yet.
- The Tier Badge variants share one default label. Always set the `Label` property; labelled examples sit on the Components page.
- Prices, product names and model numbers on the screens are illustrative copy, not real listings.
- Only the light theme is drawn.

## Copy and UX rules shown in the prototype

- Every claim carries a tier badge: Verified, Likely, AI suggestion, Caution or Stop.
- A price always shows its source and when it was checked. Amazon shows "See price on Amazon" until the Creators API is available.
- Affiliate commission is disclosed on Parts and Cart, together with the promise that it never affects ranking.
- Safety copy comes before the action (e.g. "Switch off at the wall first").
