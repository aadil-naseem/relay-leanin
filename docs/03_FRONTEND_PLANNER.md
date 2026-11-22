# RELAY — Frontend Planner

> **Read this first.** This file is the single source of truth for **how the frontend looks, moves and is built**. The *what and why* live in `docs/01_PROJECT_BRIEF.md`; the *backend how* lives in `docs/02_TECHNICAL_BLUEPRINT.md`. Hand an AI coding agent those three files and it can build the whole UI, phase by phase.
>
> **Do not reopen the idea, the palette or the concept.** They are locked here. This planner only decides how to build them.
>
> **Naming.** Product brand in the UI = **RELAY**. Sub-line = *Factory Continuity Desk*. The repo and API keep the original names.

---

## 0. Agent Operating Rules (apply to every frontend phase)

| # | Rule |
|---|---|
| FR1 | Read brief → technical blueprint → this planner → `docs/PROGRESS.md`. Resume at the first frontend phase not marked DONE. |
| FR2 | The backend gate (technical Phase 14) must be green and tagged `backend-v1` before Phase F0. The backend contract is authoritative. Adjust the client, not the API, unless a real bug is found. |
| FR3 | **E: drive only.** All installs, caches, fonts, screenshots and build output stay on E: (technical Phase 0 redirects apply). Use `npm` with the E: cache already configured. |
| FR4 | **Zero cost.** No paid fonts, icon packs, stock footage or image generators. Fonts via `@fontsource` packages (self-hosted, work offline). Verify each package name on npm before installing (same spirit as R5). |
| FR5 | **Palette lock.** Only the 12 hex values in §2.1 may appear in the codebase, and only inside `src/styles/tokens.css` (and `src/scene/palette.js`, which reads the same list). Everything else uses CSS variables. `npm run lint:palette` must pass at the end of every phase. |
| FR6 | **No fake proof.** No invented customer logos, testimonials, user counts or "trusted by" strips. Social proof on the landing page is the real **Cyclone Michaung back-test** only. |
| FR7 | **Honest labelling carries into the UI** (technical R9, R10): every screen shows *SAMPLE / SIMULATED*; risk is a *risk indicator*, never a flood prediction; matches are *candidates*; never write "AI-powered", "agentic", "copilot", "smart". |
| FR8 | **The demo must survive failure.** Every screen has loading, empty, error and degraded states (§9.4). A saved snapshot mode exists for a dead backend. The 3D scene has three quality tiers, including a static one. |
| FR9 | **App first, spectacle second.** Functional screens (F0–F7) are built before the 3D landing (F8–F9). The 3D landing is the riskiest piece; it never blocks the demo path. |
| FR10 | Commit once per phase: `frontend phase Fn: <title>`. Update `docs/PROGRESS.md`. Each phase ends with a screenshot set saved to `docs/screens/Fn/`. |

---

## 1. Concept and Identity

### 1.1 The name: RELAY
A **relay** is an electrical switch that closes when a circuit fails, so power keeps flowing. It is also a **baton hand-off**. Both are exactly what the product does: when one factory goes down, work is handed to a backup. The name drives the visuals: circuits, contacts, traces, hand-offs.

### 1.2 The one big idea: "The Floor is the Interface"
RELAY looks like a **plant control room crossed with an engineering drawing office**, not like a SaaS template.

- **Control room:** dark navy surfaces, lamps, gauges, a stack light, a status strip, a shift clock.
- **Drawing office:** cream sheets, title blocks, dimension lines, tolerance callouts, registration marks, hatching.
- **One glowing thing in a field of dark things.** (From your container-grid inspo.) A single amber-lit factory bay among a grid of dark identical bays *is* the single point of failure. It is the hero image, the logo idea and the recurring visual motif.

### 1.3 Two-axis colour meaning (the system that keeps everything consistent)
| Axis | Colour | Meaning |
|---|---|---|
| **Heat / attention / risk** | **Amber gold** (Sun) | Something needs your eyes: risk, exposure, late, the weak point, the primary action |
| **Coverage / safety / live data** | **Sky blue** | Covered, ready, live feed, selected |
| Structure | Navy family | Everything else: surfaces, panels, lines |
| Paper | Cream | Documents only: drawings, passports, RFQs, handover packs |

If a screen is mostly navy with one gold thing, the gold thing is what matters. That rule replaces red/green and keeps the UI to your palette.

### 1.4 What we are deliberately avoiding (anti-slop list)
- No purple/pink gradients, mesh blobs, glassmorphism on everything, or neon glows on every card.
- No rounded pill-and-shadow "dashboard template" cards. Cards are **square-cornered hairline frames with corner ticks**.
- No emoji, no stock illustrations, no generic gradient hero with a laptop mockup.
- No fake logos, no "10,000+ users", no AI sparkle icons.
- No bouncy spring animations. Motion is **mechanical**: snap, settle, tick.
- No colour that is not in the palette. Ever.

### 1.5 Inspiration decoded (what we take from each reference)
| Reference | Take | Leave |
|---|---|---|
| UnitMove (dark hero, giant condensed letters behind a lit 3D object, floating callout cards with dots) | Letters **behind** the 3D object; leader-line callouts anchored to 3D points; dark navy + amber crane | Fake "Amazon / 450+ trust" proof |
| Container grid with one glowing unit | The hero concept: one lit unit in a dark grid = the SPOF | The marketing copy |
| Hydraoo (calm aerial scene, huge light headline, tiny pill nav) | Restraint, big quiet type, plenty of negative space in the nav and hero | Stock aerial photo |
| "Speculate Responsibly" (serif headline over stacked 3D boxes, warm light raking across) | **Condensed sans + italic serif pairing**, warm raking light on dark forms | The satire copy |
| Palette 1 (Deep Navy, Navy, Warm Gold, Pale Gold, Cream) | Surfaces, paper, text | — |
| Palette 2 (White, Sun, Ocean, Sand, Sky, Midnight, Black + three gradients) | Accent ramp, Sky for coverage, the three gradients | — |

---

## 2. Design System

### 2.1 Palette (locked, 12 values)
These are the only colours. They come straight from your two palette images (you attached two palette boards; this covers both).

| Token | Hex | Source | Role |
|---|---|---|---|
| `--c-void` | `#000000` | Palette 2 Black | Deepest vignette and gradient end only. Never a surface |
| `--c-deep` | `#0A1A40` | Palette 1 Deep Navy | **App background** |
| `--c-midnight` | `#00205B` | Palette 2 Midnight | Raised panels, header, rail |
| `--c-navy` | `#1A3070` | Palette 1 Navy | Inset surfaces, hover, table stripes |
| `--c-ocean` | `#003087` | Palette 2 Ocean | Selected rows, secondary buttons, solid blocks |
| `--c-sky` | `#307FE2` | Palette 2 Sky | Coverage, READY, live data, links, focus ring |
| `--c-sun` | `#F2A900` | Palette 2 Sun | Heat/attention, **primary CTA**, the glowing unit |
| `--c-gold` | `#C8920A` | Palette 1 Warm Gold | Pressed states, gold borders, hatch lines |
| `--c-pale` | `#E8C870` | Palette 1 Pale Gold | MODERATE risk, secondary gold text |
| `--c-sand` | `#FFE264` | Palette 2 Sand | Glow core / glint. **Max one use per screen** |
| `--c-cream` | `#F8F0DC` | Palette 1 Cream | Paper sheets, body text on dark |
| `--c-white` | `#FFFFFF` | Palette 2 White | Max-contrast headlines, text on Ocean |

**Alpha tints** are allowed only as variables defined in `tokens.css` (e.g. `--c-cream-12`, `--c-cream-24`, `--c-sky-16`, `--c-sun-20`, `--c-deep-80`). No ad-hoc `rgba()` anywhere else.

**Gradients (only these three, from palette 2):**
| Name | Stops | Use |
|---|---|---|
| `--g-depth` | Sky → Ocean → Void | Landing sky, deep vignettes |
| `--g-dusk` | Sun → Sky → Midnight | Hero horizon glow, section dividers (sparingly) |
| `--g-paper` | White → Sand → Sun | Title-block accent strip, rare highlight bars |

### 2.2 Contrast rules (computed, not guessed)
| Pair | Approx. contrast | Rule |
|---|---|---|
| Cream on Deep | ≈ 15 : 1 | Default body text |
| Sun on Deep | ≈ 8.5 : 1 | Gold text and numbers allowed at any size |
| **Sky on Deep** | **≈ 4.3 : 1** | **Not for small text.** Use Sky for lines, icons, fills, and text ≥ 18 px bold. Small blue text uses Cream with a Sky marker |
| Deep on Sun | ≈ 8.5 : 1 | Text on gold buttons is always Deep |
| Navy ink on Cream | high | All paper documents use Deep/Midnight ink on Cream |

Never put Sun text on Cream or White. On paper, gold is a fill or stripe only.

### 2.3 Semantic mapping (status is never colour-only: shape or pattern always differs)

| Concept | LOW / good → bad | Encoding |
|---|---|---|
| **RiskLevel** | LOW | Sky hairline chip, "Low" |
| | MODERATE | Pale Gold chip |
| | HIGH | Sun solid chip |
| | SEVERE | Sun solid + hazard chevron edge + slow pulse ring |
| **OrderState** | ON_TRACK / AT_RISK / LATE | Sky tick / Pale clock / Sun solid flag |
| **FallbackLevel** | READY | Sky solid shield |
| | POTENTIAL_ONLY | Pale outline shield |
| | NONE | **Hatched Sun** "NO COVER" stamp |
| **BackupStatus** | READY | Sky solid, check, "closed contact" glyph |
| | READY but STALE | Sky **dashed** outline + clock glyph, "Reconfirm needed" |
| | APPROVAL_PENDING | Pale outline, half-filled |
| | ASSESSMENT_IN_PROGRESS | Navy-light outline, three-dot glyph |
| | POTENTIAL_MATCH | Ghost (hairline only) |
| | UNAVAILABLE_EXPIRED | Struck through, Navy |
| | **EXCLUDED** (correlated risk) | **Diagonal hatch** + reason chip (`SAME_HAZARD_ZONE`) |
| **Confidence** | HIGH / MEDIUM / LOW / MISSING / CONFIRMED | Signal bars: 3 Sky / 2 Pale / 1 Sun / empty dashed / cream "CONFIRMED" stamp |
| **Weather source** | live / cache / replay / synthetic | Pulsing Sky dot / Pale dot / reel glyph "REPLAY" / hatched; `degraded` adds a Sun sliver |
| **Readiness gauge** | | Covered share filled **Sky**; the uncovered **gap is hatched Sun** |

**Hazard chevron stripes (Sun/Deep diagonal)** are reserved for SEVERE alerts, the NO COVER stamp and EXCLUDED hatching. Because they are rare, they read as important.

### 2.4 Typography (all free, self-hosted via `@fontsource`)
| Role | Font | Use |
|---|---|---|
| **Display** | **Big Shoulders Display** (700/800/900), uppercase, tight tracking | Hero giant letters, screen titles, KPI numerals. Industrial signage feel, close to your UnitMove reference |
| **Accent serif** | **Instrument Serif** (italic) | The one emphasised phrase in a headline ("*before the flood does.*"), pull quotes. Max one per view |
| **UI / body** | **IBM Plex Sans** (400/500/600) | Everything readable. Engineering heritage, not the default-SaaS look |
| **Data / log / IDs** | **IBM Plex Mono** (400/500) | Calculation log, IDs, coordinates, tolerances, tags |

Scale (px): 12 / 14 / 16 / 20 / 28 / 40 / 64 / 96 / 180 (hero). Line-height 1.45 body, 0.9 display. Numerals in KPIs use tabular figures. Letter-spacing on small uppercase labels: +0.08em.

### 2.5 Grid, shape, line
- 8 px base grid; 12-column layout, max content width 1600 px; rail 72 px collapsed / 224 px expanded.
- **Corners are square (0 px).** Inputs 2 px. Only lamps and dots are circular.
- **Hairlines:** 1 px at `--c-cream-24` (raise to 36 % in High-contrast/projector mode).
- **Corner ticks:** every card has 8 px L-shaped ticks in its four corners (drawing registration marks) instead of a shadow.
- **No box shadows.** Depth comes from surface step (`deep → midnight → navy`) and hairlines. The only glow allowed is around the amber unit and gold primary CTA on hover.
- Texture: a faint **blueprint grid** (24 px, `--c-cream-12`) on the app background; a very light film-grain overlay (1–2 %) on the landing only.

### 2.5.1 Patterns (SVG `<pattern>` defs, reusable)
`hatch-sun` (45°, Gold lines), `hatch-navy`, `chevron-sun` (hazard stripes), `dots-sky` (halftone for gap fills), `grid-24`.

### 2.6 Iconography
Single stroke family: 1.5 px stroke, square caps, 24 px grid.
- **Custom machine glyphs (draw these as inline SVG, ~12):** lathe (TURN), vertical mill (MILL), drill/tap, cylindrical grinder, surface grinder, wire EDM, furnace (HEAT_TREAT), plating tank (SURFACE_TREAT), flood, power, water, road-blocked, shed (factory), supplier crate.
- Generic UI icons (arrows, close, upload, check, clock): `lucide-react` at `strokeWidth 1.5`, optional; if not installed, draw them inline. Do not mix any other family.

### 2.7 Motion language: "mechanical, never bouncy"
| Token | Value | Use |
|---|---|---|
| `--ease-snap` | `cubic-bezier(.2,.8,.2,1)` | Most UI |
| `--ease-settle` | `cubic-bezier(.16,1,.3,1)` | Panels, drawers |
| `--ease-tick` | `steps(6, end)` | Odometer digits, ticker |
| Durations | 120 / 240 / 400 / 800 ms | micro / standard / panel / sequence |

Signature motions (reused everywhere):
1. **Stamp-in:** element drops in 6 % scale-down with a 1-frame flash of Sand on the border (used for the alert banner, NO COVER, CONFIRMED).
2. **Odometer:** numbers roll digit by digit with `--ease-tick`.
3. **Trace draw:** SVG paths draw with `stroke-dashoffset` (dependency lines, relay circuit, routes).
4. **Contact close:** a relay glyph's gap closes and the trace beyond it lights Sky (a backup becoming READY).
5. **Shutter:** two navy panels with chevron edges close and open for route changes (§6).
6. **Scan line:** a thin Sky line sweeps the drawing while extraction is *pending* (only while a request is in flight; never fakes completion).
7. **Redaction bars:** black-navy bars slide over identifying fields in the RFQ view, driven by the real `redaction_report`.

`prefers-reduced-motion`: replace 3, 5, 6 with fades; stop all looping animations; the landing falls back to the static tier.

### 2.6.1 Optional sound
A single soft relay "click" when a backup becomes READY and a low tick on odometers. **Off by default**, toggle in Stage Controls. Free-licence or self-synthesised with WebAudio (no files needed).

### 2.8 Accessibility
Focus ring: 2 px Sky + 2 px Deep gap. Min target 40 px. All icons have labels. Status is shape + text + colour. Keyboard path for the entire demo (§7.9). High-contrast toggle (projector mode) raises hairlines, font weight and gold saturation use. Landing is fully usable without 3D (static tier).

### 2.9 Voice and microcopy
Plain, foreman-to-owner, short. Examples in Appendix C. Banned words: *AI-powered, smart, intelligent, seamless, revolutionary, leverage.* Say "reads your drawing", "where your factory breaks", "checked / unverified", "reconfirm needed".

---

## 3. Signature UI Elements (what makes it unmistakably RELAY)

| # | Element | Spec | Where |
|---|---|---|---|
| 1 | **Title block** | Bottom-right engineering title block on every screen: `DWG: RELAY-S2 · REV: 14 NOV 04:53 IST (data snapshot) · SCALE: 1:1 · SHEET 2/8 · SAMPLE / SIMULATED`. Doubles as the mandatory data label | All app screens |
| 2 | **Stack light** | Three-lamp tower in the header: top = exposure (Sun when alert), middle = readiness (Sky if ≥ 60, Pale if 30–59, Sun if < 30), bottom = data freshness (Sky live, Pale cache, hatched replay). Hover shows the numbers | Header |
| 3 | **Dimension-line callouts** | Key numbers wrapped in `├── 148 mm ──┤` style dimension lines with tick ends. Used for rain mm, distances, lead-time slack | Exposure, Matching |
| 4 | **Nameplate chips** | IDs and machine tags as riveted metal-plate chips (two dots + mono text) | Tables, graph nodes |
| 5 | **Shift clock** | IST clock + "T+00…T+72" horizon bar in the header; the hour marker where heavy rain begins is a Sun notch | Header, What-if, Exposure |
| 6 | **Relay circuit schematic** | Partner network drawn as an electrical diagram: owner bus on the left, each partner a relay symbol, trace style by status (solid Sky = ready, dashed Pale = pending, hatched/open = excluded, ghost = potential) | Partners, Recovery, landing |
| 7 | **Hatched gap gauge** | Readiness ring where the *missing* coverage is visibly hatched; hovering a Next Best Action previews a ghost arc of the uplift | Desk, Partners |
| 8 | **Gantt "shift chart"** | Stress test as a machine-shop schedule: baseline bar vs stressed bar, downtime windows as hatched vertical bands, due-date flags | What-if |
| 9 | **Pull the plug** | In Weak Points, "Simulate loss" dims one resource and animates the orders that break turning hatched | Weak Points |
| 10 | **Job-card calc log** | "How was this calculated?" slides out like a perforated job-card printout in mono, with `step / detail / inputs / output` rows | Everywhere a `trace` exists |
| 11 | **Paper sheets** | Drawings, passports, RFQs and handover packs sit on **Cream paper** with Deep ink inside the navy app, so "documents" feel physical | Passports, Recovery |
| 12 | **Redaction bars** | Slide over customer name / drawing no. / revision / title block on the RFQ | Passports |
| 13 | **Leader-line callouts** | Floating labels connected by hairline to dots on 3D objects (landing) and on map markers (app) | Landing, Map |
| 14 | **Hazard chevrons** | Only for SEVERE, NO COVER, EXCLUDED | Rare, so meaningful |

---

## 4. Sitemap and Navigation

### 4.1 Routes
| Route | Screen | Backend |
|---|---|---|
| `/` | **S0 Landing** — 3D scroll story | `/dashboard/{id}` (numbers), with baked fallback |
| `/app` | **S1 Desk** (dashboard) | `/dashboard/{id}`, `/exposure/map` |
| `/app/weak-points` | **S2 Weak Points** (SPOF) | `/factories/{id}/spof` |
| `/app/exposure` | **S3 Exposure** (map + horizon) | `/factories/{id}/exposure`, `/exposure/map` |
| `/app/passports` (+ `/:id`) | **S4 Passports** | `/passports/*` |
| `/app/what-if` (+ `/:id`) | **S5 What-if** | `/stress-tests` |
| `/app/recovery` (+ `/:id`) | **S6 Recovery** (request, options, handover, tracking) | `/recovery-requests/*`, `/matching/search` |
| `/app/partners` | **S7 Partners & Readiness** | `/factories/{id}/relationships`, `/readiness/*` |
| `/app/proof` | **S8 Proof & Method** | static back-test JSON + docs |
| drawer (`` ` `` key) | **S9 Stage Controls** | `/demo/*`, `/health` |
| `*` | **S10 System screens** (404, backend down, snapshot mode) | — |

### 4.2 Landing navigation
- **Transparent bar, 64 px**, hairline underneath only after scrolling. Left: RELAY mark + wordmark. Centre: `Story · How it works · Proof`. Right: **Open the desk** (Sun button). Condenses to a 48 px bar after the hero.
- **Chapter rail (right edge):** five small tick marks with labels that appear on hover (`01 Diagnose · 02 Threat · 03 Relay · 04 Ready`). The active tick is Sun. During chapter 02 it also shows the live `T+nn h` readout.
- Scroll hint at the bottom of the hero: a thin line with a travelling dot and "Scroll = time".

### 4.3 App navigation
- **Left rail (72 px, expands to 224 px on hover/pin).** Items in demo order, each with a custom glyph and a one-line label:
  1. Desk · 2. Weak points · 3. Exposure · 4. Passports · 5. What-if · 6. Recovery · 7. Partners · 8. Proof
  Active item: Sun marker bar + Cream label. Number hints `1`–`8` shown in mono for keyboard use.
- **Top status strip (48 px):** RELAY mark (click = back to landing with reverse transition) · factory nameplate "Sample Precision Components · Ambattur" · shift clock · `SAMPLE / SIMULATED` stamp · weather-source badge · stack light · Stage Controls button.
- **Breadcrumb line** under the strip only on detail routes.
- **Command palette (`/` or `Ctrl+K`):** jump to any screen or action ("Start recovery request", "Reset demo", "Switch to replay"). Small, mono, fast.
- Mobile/tablet: rail becomes a bottom bar with 5 items + "More".

---

## 5. Landing Experience (S0): "Scroll is time"

### 5.1 Structure
One page, three zones:
1. **Pinned 3D story stage** (≈ 700 vh of scroll) with five chapters.
2. **How it works** (static, 4 job cards).
3. **Proof + honest limits + CTA + footer.**

### 5.2 Hero (Chapter 0) — layered parallax
**Visual:** dusk. A dark grid of identical factory bays recedes into fog. **One bay is lit amber.** Container stacks and a gantry crane silhouette sit in the yard (nod to UnitMove and the container-grid inspo). The crane hook hangs above the lit bay with a leader line to a callout.

**Headline (the layered-letters trick, as in UnitMove):**
- Giant **FIND WHERE YOU BREAK** in Big Shoulders 900, ~180 px, Cream→Pale vertical gradient fill, spanning the width, **behind** the 3D canvas.
- The lit bay and crane **overlap the letters**, so the 3D object visibly sits in front of the type.
- Over the letters, in front: *before the flood does.* in Instrument Serif italic, White, ~64 px, left-aligned under the first line. This is the single serif phrase on the page.

**Z-stack (back to front):**
| z | Layer | Parallax factor (scroll / pointer) |
|---|---|---|
| 0 | Sky gradient `--g-depth` + dusk glow `--g-dusk` at the horizon | 0.05 / 0.01 |
| 1 | Far skyline SVG (sawtooth roofs, chimneys, pylons) | 0.15 / 0.02 |
| 2 | **Giant headline letters** | 0.30 / 0.03 |
| 3 | **R3F canvas** (transparent background, `alpha: true`): bays, yard, crane, lit unit, fog | camera-driven |
| 4 | Rain particle layer (canvas or points, starts faint, grows with scroll) | 0.6 / 0.04 |
| 5 | Foreground UI: nav, callout cards, CTA, scroll hint | 1.0 / 0 |

The canvas ground must fade to transparent at the bottom (alpha gradient in the ground shader) so letters and sky show through.

**Pointer parallax:** camera sways ±2° with eased follow (lerp 0.06), letters shift opposite by up to 14 px. Disabled on touch and reduced-motion.

**Foreground cards (tracked to 3D anchors, UnitMove-style dots):**
- *Left card:* "The only grinder you have. ±0.005 mm. **4 orders** wait on it." + buttons **Open the desk** (Sun) and **Watch the story** (ghost, scrolls to chapter 1).
- *Right card:* "**₹21.5 L** exposed if the north phase floods in 36 h" with a `SAMPLE / SIMULATED` micro-stamp.
- Numbers come from `GET /dashboard/{id}` in replay mode; if it fails, from `src/data/story.fallback.json`.

### 5.3 Story chapters (scroll-pinned)

Scroll progress `p` ∈ [0,1] across the pinned stage. Camera and scene values are **starting points; tune visually**.

| Ch | `p` range | What the viewer sees | Camera (pos → target) | Scene state | Copy |
|---|---|---|---|---|---|
| **00 Hero** | 0.00–0.08 | Lit bay, letters, calm dusk | `[16,7,20] → [0,1,0]`, fov 34 | Rain 0, units dim, one amber unit pulsing slowly | *Find where you break* / *before the flood does.* |
| **01 Diagnose** | 0.08–0.34 | Camera dollies down into the grid. Amber dependency lines **draw** from order tags → part → step → machine, all converging on the lit bay. Every other bay dims to 30 %. A leader callout names the weak point | `[16,7,20] → [4,3,8] → [2,2.2,3]` | Trace-draw lines (Sun), other units opacity 0.3, nameplate chips appear | *One grinder. Four orders. If it stops, they all stop.* |
| **02 Threat** | 0.34–0.60 | Camera rises to a three-quarter view. Rain thickens. A translucent Sky water plane rises over the low zone. **Scroll scrubs the 72-hour forecast** (`T+00 → T+72`): bays in the flood zone switch off in sequence; the ₹ exposed counter rolls up; the stack light turns Sun | `[2,2.2,3] → [12,9,14]` | Rain density ∝ p, water plane y from −0.2 to +0.8, zone bays emissive → 0 | *Heavy rain in 36 h. Your zone is the low ground.* |
| **03 Relay** | 0.60–0.86 | Bays **shrink into nodes** and the ground becomes a graticule: the cluster becomes a map of Tamil Nadu and Karnataka. Amber pulses leave the dead nodes and arc to distant ones. The neighbour in the same zone is struck out (hatched). Oragadam lights Sky ("contact closes"); Hosur stays Pale (approval pending); Peenya dashed (stale) | `[12,9,14] → [0,38,6]` (top-down, nodes positioned from real lat/lon) | Instance scale → 0.18, arcs as animated tubes, amber→Sky colour shift on arrival | *Cover that isn't standing in the same water.* |
| **04 Ready** | 0.86–1.00 | The readiness ring closes from the hatched gap: **42 → 71**. Camera pulls back to a wide shot. Primary CTA appears | `[0,38,6] → [18,10,24]` | Score odometer, ring fill | *Know your cover before you need it.* **Open the desk** |

**Node map projection (chapter 03):** `x = (lon − lon0) · cos(lat0) · k`, `z = −(lat − lat0) · k`, with `lat0 = 12.4`, `lon0 = 78.4`, `k ≈ 1.1` per degree (tune so Coimbatore stays in frame). Sites: Ambattur 13.100/80.155, Guindy 13.010/80.212, Oragadam 12.842/79.952, Hosur 12.740/77.830, Peenya 13.028/77.520, Coimbatore 10.950/76.970.

**Pinned-section chapter UI:** each chapter shows a numbered label (`01 / DIAGNOSE`), a 2-line headline (Big Shoulders), a one-line body (Plex Sans), and a small data chip (e.g. `replay · Cyclone Michaung rainfall, Dec 2023, time-shifted`).

### 5.4 After the story
1. **How it works** — four horizontal "job cards" on a blueprint grid, connected by a trace that draws on scroll: **① Read the drawing** → **② Find the break** → **③ Watch the sky** → **④ Line up cover**. One-line promise each. Under it, the line: *"Our software reads the drawing. Our maths tells you where you break."*
2. **Proof** — a compact version of the Michaung back-test: ranked table of back-test sites with flooded sites marked by a Sun dot. Headline: *"Tested on a real storm."* Caption states it is a risk indicator, not a flood model.
3. **Honest limits** — three plain statements: *Matches are candidates, not approved backups. Risk is an indicator, not a prediction. All factories shown are fictional samples.*
4. **Final CTA** band with the glowing bay icon + **Open the desk**.
5. **Footer:** attributions ("Weather data by Open-Meteo.com", "© OpenStreetMap contributors"), hackathon line, repo link.

### 5.5 3D scene specification (`src/scene/`)
All geometry is procedural. No GLTF downloads are required.

| Object | Build | Notes |
|---|---|---|
| **Bay** | `InstancedMesh`: box body + sawtooth roof (`ExtrudeGeometry` from a saw-profile `Shape`) + roller door inset + small chimney on some | Palette colours only; Deep body, Midnight roof, `--c-cream-24` edge lines via a thin edges geometry |
| **Lit bay** | Separate mesh, same shape, `emissive = Sun`, emissive intensity animated 0.8–1.3 | Window strip and door glow Sand; one point light (Sun) + faint volumetric cone (cheap additive cone) |
| **Grid layout** | 14 × 14 cells, 2 gaps for roads, a 5 × 4 block flagged as **flood zone** | Same positions drive chapter-03 node scale-down |
| **Yard dressing** | A few container stacks (instanced boxes with a procedural corrugation bump texture from `CanvasTexture`) + gantry crane silhouette (thin boxes) | Crane hook sways ±3 cm |
| **Ground** | Large plane, `grid-24` shader, radial alpha fade | Becomes graticule in ch. 03 (uniform switch) |
| **Rain** | `LineSegments` or `Points` stretched in y, one draw call, ~4–6 k drops | Density uniform ∝ `rain(p)` |
| **Water** | Transparent plane (Sky, 35 % alpha) with slow normal ripple (scrolling noise texture) | Rises only over the zone (mask) |
| **Dependency lines** | `TubeGeometry` or `Line2` with `dashOffset` driven by scroll | Sun |
| **Relay arcs** | Quadratic Béziers lifted in y, travelling pulse via shader | Sun → Sky on arrival |
| **Fog** | `Fog(--c-deep, 30, 90)` | Hides the far edge |
| **Glow** | Default: fake glow (additive sprite + emissive). Optional high tier: `@react-three/postprocessing` Bloom, threshold-gated | High tier only |

**Scroll → scene wiring:** a single `storyStore` (zustand) holds `progress`, `chapter`, `pointer`. GSAP `ScrollTrigger` (pinned container, `scrub: 0.6`) writes `progress`; R3F reads it every frame. Lenis provides smooth scroll and is synced with ScrollTrigger (`lenis.on('scroll', ScrollTrigger.update)`; drive Lenis from `gsap.ticker`). **Never create timelines inside R3F `useFrame`.**

### 5.6 Quality tiers and fallbacks
| Tier | Condition | Behaviour |
|---|---|---|
| `full` | Desktop GPU, ≥ 8 logical cores, no reduced-motion | Full scene, DPR ≤ 1.75, bloom optional |
| `lite` | `<PerformanceMonitor>` drops below ~40 fps, or ≤ 4 cores | DPR 1.0, rain 1 k, no bloom, no yard dressing, simpler water |
| `static` | WebGL missing, reduced-motion, mobile, or `?tier=static` | **CSS/SVG parallax**: pre-rendered poster of the hero (`public/poster-hero.webp`, captured from the scene), layered skyline + rain via CSS, chapters become simple scroll-reveal sections with SVG illustrations |

Budgets: ≤ 150 draw calls, ≤ 250 k triangles, textures ≤ 1024 px, first interaction < 2.5 s on the demo laptop, scene chunk lazy-loaded (`React.lazy`) so `/app` does not pay for `three` unless the backdrop is enabled.

---

## 6. Cross-Page 3D Transition System

Goal: the whole product feels like **one continuous world**, not a stack of separate pages.

### 6.1 Persistent scene
A single `<WorldCanvas>` is mounted at the app root, **behind** all routes. The same bay grid exists on every route. Each route declares a **station**: a camera pose plus a scene mode. Route changes fly the camera to the new station (600–900 ms, `--ease-settle`) while the shutter wipes the DOM.

| Route | Station (what the backdrop shows) | Backdrop opacity |
|---|---|---|
| `/` | Story stage (landing) | 100 % |
| `/app` Desk | Wide three-quarter, lit bay pulsing | 18 % |
| `/app/weak-points` | Close on the lit bay, dependency lines drawn | 25 % |
| `/app/exposure` | Top-down, water plane visible | 20 % |
| `/app/what-if` | Low flood view, water plane animated by scenario | 20 % |
| `/app/recovery` | Map mode, arcs to the chosen partner | 25 % |
| `/app/partners` | Map mode, all partner nodes with status colours | 25 % |
| `/app/passports` | Backdrop dims to 8 % (paper-heavy screen) | 8 % |

The backdrop sits behind a Deep overlay at the opacity above, uses `frameloop="demand"` (renders only on camera moves or state change) and pauses when the tab is hidden. In `static` tier it is replaced by a CSS blueprint grid.

### 6.2 Named transitions
| Name | Trigger | Sequence (≈ ms) |
|---|---|---|
| **Dive** | Landing → `/app` | Camera flies into the lit bay (500), Sand → Sun flash (120), cut to Deep, Desk stamps in (300) |
| **Pull-out** | `/app` → `/` via logo | Reverse of Dive |
| **Shutter** | Any app route change | Chevron-edged navy panels close (240) → route swap → open (320); camera glide runs underneath |
| **Stamp** | Alert appears, CONFIRMED, NO COVER | Stamp-in motion (§2.7) |
| **Relay close** | Backup becomes READY | Contact glyph closes, trace lights Sky, score odometer rolls, stack-light middle lamp changes |

Implementation: `useRelayNavigate()` wraps React Router's `navigate`, plays the shutter-in, navigates, then shutter-out. If the tier is `static` or reduced-motion, it does a 160 ms crossfade instead. `viewTransition` from React Router may be used as a progressive enhancement only.

### 6.3 Scroll inside app pages
App pages scroll normally (no hijacking). The only scroll-scrubbed element in the app is the **Exposure horizon scrubber** (an explicit drag/scroll control, never implicit).

---

## 7. Screens

> Wireframes are schematic. All screens carry the **title block** (§3) bottom-right and obey §9.4 states.

### 7.1 S1 Desk (`/app`) — the control room
**Purpose:** the first thing a judge sees after the landing. Shows alert, score, weak points, exposure and the next action in one glance.

```
┌ status strip ─────────────────────────────────────────────────────────────────────────┐
│ RELAY │ Sample Precision Components · Ambattur │ IST 04:53 │ SAMPLE/SIMULATED │ ●replay │ ▮▮▮ │
├────┬──────────────────────────────────────────────────────────────────────────────────┤
│ R  │ ▓▓ ALERT  Heavy rain in 36h: 3 orders at risk, ₹21.5 L exposed, 1 order has no     │
│ A  │ ▓▓ fallback        ONSET T+36h     [ Start recovery request ]  [ See the test ]   │
│ I  ├─────────────────────────┬────────────────────────────┬───────────────────────────┤
│ L  │ READINESS   [24|48|72]  │ KPIs (odometers)           │ NEXT BEST ACTIONS         │
│    │   ◜ ring, hatched gap ◝ │ ₹ exposed │ at risk │ no   │ Reconfirm Peenya  +14 pts │
│    │      42  / 100          │ cover │ stale partners     │ Finish Hosur checks +12   │
│    │   weighted 38           ├────────────────────────────┤ …                         │
│    ├─────────────────────────┤ 72h RAIN (bar strip)       │                           │
│    │ WEAK POINTS (top 3)     │ ▁▂▃▅█▇▅▃▂ onset notch      ├───────────────────────────┤
│    │ ▪ Cyl. grinder  ₹21.5L  ├────────────────────────────┤ EXPOSURE MAP (mini)       │
│    │ ▪ Heat-treat vendor     │ calc log ▸                 │ markers by risk, zone     │
│    │ ▪ EN24 supplier         │                            │ hatch, 1 route polyline   │
└────┴─────────────────────────┴────────────────────────────┴───────────────────────────┘
                                                                  [title block]
```

- **Alert banner:** full-width, left edge chevron (SEVERE) or Sun bar (HIGH). Headline in Big Shoulders 40 px from `alert.headline`. Primary CTA **Start recovery request** calls `POST /recovery-requests {from_stress_test_id, order_id}` for the worst order, then Shutter → `/app/recovery/:id`. Secondary opens What-if with the auto test.
- **Readiness ring:** Sky fill = covered, hatched Sun = gap. 24/48/72 segmented switch changes the headline value (data from `readiness.windows`). Click opens the breakdown drawer (per-part reasons).
- **KPI strip:** four odometers (`revenue_exposed_inr` as ₹ lakh, `orders_at_risk`, `orders_no_fallback`, `stale_partners`).
- **Weak points:** top 3 from `spof_top` as nameplate rows with revenue at risk and an `exposed` Sun dot; click → Weak Points with that node selected.
- **Rain strip:** hourly bars (Recharts) with onset notch and `max_24h_mm` dimension line. Needs `hourly_mm` (see §9.5 backend ask). Without it, show a single dimension-line callout.
- **Mini map:** Leaflet, same styling as S3.
- **Cold-open sequence (once per session or after Reset, ≤ 1.2 s):** banner stamps in → ring sweeps → odometers roll → markers drop in by risk order. Subsequent visits render instantly.
- **Empty state (no alert):** banner replaced by a calm Sky line "No heavy rain forecast in the next 72 h. Readiness is the main job today."

### 7.2 S2 Weak Points (`/app/weak-points`)
**Purpose:** show *why* the factory breaks.

```
┌ RANKED WEAK POINTS ───────────┬ DEPENDENCY DRAWING ────────────────────────────────┐
│ 1 ▣ Cylindrical grinder  ● exp │  ORDERS     PARTS      STEPS       RESOURCES       │
│   ₹21.5 L · 4 orders          │  ord_107 ─┐                                         │
│ 2 ▣ Heat-treat vendor    ● exp │  ord_112 ─┼─ PRT-A ─ TURN ─────── Lathe ×3          │
│ 3 ▣ EN24 supplier             │  ord_118 ─┘          HEAT_TREAT ── Vendor ◄ SPOF     │
│ …                             │             PRT-B ─ GRIND_CYL ─── Grinder ◄ SPOF    │
│ [ Simulate loss ]  [ Stress   │                                                      │
│   this resource → What-if ]   │  legend: Sun = SPOF · Sky = has alternative         │
└───────────────────────────────┴────────────────────────────────────────────────────┘
```
- Layered **custom SVG graph** (four columns: Orders → Parts → Steps → Resources); no graph library needed. Edges from `nodes/edges`. SPOF nodes are Sun-outlined; resources with alternatives are Sky.
- **Pull the plug:** selecting a row + **Simulate loss** dims the resource, edges retract, and the orders in `orders_broken` turn hatched Sun with a stamp "BREAKS". "Reset" restores.
- Row expand shows `steps_broken`, orders affected, `exposed` reason (zone name or risk score).
- **Stress this resource** deep-links to What-if with hazard `RESOURCE_DOWN` prefilled.
- Honesty line under the graph: "Three lathes never appear here, because losing one still leaves two."

### 7.3 S3 Exposure (`/app/exposure`)
**Purpose:** show what the sky and the ground are doing to every site.

- **Full-bleed map** (Leaflet, OSM tiles restyled to navy, see §8.3) with: site markers sized and coloured by `site_risk` (Sky→Pale→Sun, SEVERE = chevron ring), hatched **historic zone circles**, **route polylines** coloured by `route_risk`, isolation sites flagged "all exit routes exposed".
- **Left panel — site list:** ranked by risk; each row has the **drivers[]** sentences ("148 mm forecast in 24 h; 2.4 m below surroundings; 380 m from water; in a historically flooded zone") and a dimension-line callout for the key number.
- **Bottom — horizon scrubber:** `T+00 → T+72` rail with an explicit draggable playhead. Moves rain intensity overlay and highlights onset. Works fully if `hourly_mm` is available; otherwise the scrubber is hidden and the panel shows the single max-24h callout.
- **Legend + honesty chip:** "Risk indicator from forecast rain and site conditions. Not a flood model."
- **Calc log** per site (job-card drawer).
- **Source badge** large: live / cache / replay / synthetic.

### 7.4 S4 Passports (`/app/passports`)
**Purpose:** the hero feature. Drawing in, reviewed passport out, redacted RFQ out.

Stepper (top): **① Drawing → ② Review → ③ Confirm → ④ Redacted RFQ → ⑤ Share**

```
┌ DRAWING TABLE (cream sheet) ─┬ PRODUCTION PASSPORT (editable) ──────────┬ RFQ ──────────┐
│  [ drawing preview, zoom ]   │ Part name      Pump shaft        ▮▮▮      │ (step 4)      │
│  ~~~ scan line while pending │ Material       EN8 · IS 5517     ▮▮▮      │               │
│                              │ Tightest tol.  ±0.02 mm          ▮▮       │               │
│  Samples: [Pump shaft]       │ Process route  TURN → MILL       ▮▮▮      │               │
│   [Piston rod] [Valve flange]│ Surface finish Ra 1.6            ▮        │               │
│  or drop a file              │ ⚠ NEEDS REVIEW: tolerance — rules 0.02 vs reading 0.05 │
│  provider: cache             │ [ Confirm passport ]  (disabled: 1 field missing)       │
└──────────────────────────────┴──────────────────────────────────────────┴───────────────┘
```
- **Sample tray first:** three clickable sample drawings (pump shaft, piston rod, valve flange) so the stage demo never depends on a file picker. A drop zone styled as a drawing table sits next to it.
- **Extraction states:** *pending* (scan line + "Reading your drawing…"), *done* (fields **stamp in** top to bottom, 60 ms stagger, purely visual after data has arrived), *rules-only* (banner: "Reading service unavailable. Draft built from printed text only. Check every field."), *manual* (empty form).
- **Provider chip:** `Read from saved result` / `Read by Gemini free tier` / `Printed-text rules only` / `Entered by hand`, with latency.
- **Each field:** value (editable inline), **confidence signal bars**, source chip (`rules`, `reading`, `both agree`). **Disagreements** show both candidates as two small cards; the default (rules) is pre-selected; picking one marks the field CONFIRMED.
- **Dimensions table** with nominal ± tolerances in mono and a `critical` flag toggle.
- **Confirm gating:** the button lists exactly what is missing (process route, material grade, quantity, tolerance or general standard). Confirm → **CONFIRMED stamp**, then creates/updates the part and steps; shows a toast with a link to the part.
- **Cycle-time note:** "Cycle times are planner estimates from defaults. A drawing does not contain them." with an inline edit.
- **RFQ step:** two sheets side by side, **Original** and **Redacted**. On entering the step, **redaction bars** slide over customer name, drawing no., revision, title block and any scrubbed free text (positions from `redaction_report`). Under the sheets: "Removed: customer name, drawing number, part number, revision, title block, branding." `rfq_ref` shown as an opaque ID nameplate.
- **Share step:** two options, **Share redacted RFQ** (default) and **Share full passport** (requires an explicit consent dialog: "The partner will see the full drawing details. Only do this with the customer's permission."). Calls `POST /passports/{id}/share`.
- Right-hand paper uses Cream with Deep ink; gold only as stripes/stamps.

### 7.5 S5 What-if (`/app/what-if`)
**Purpose:** simulate a disruption and see who misses a deadline.

```
┌ SCENARIO ────────────┬ SHIFT CHART (T+00 ───────────────── T+168h) ─────────────────────┐
│ Hazard  [≋][⚡][💧][⛔][▣]│ ord_107  base ▓▓▓▓▓▓    stressed ▓▓▓▓░░░░░░▓▓▓▓▓  ⚑ due  LATE 3.2d │
│ (flood, power, water, │ ord_112  …                                                        │
│  access, resource)    │ ░ hatched bands = downtime windows (T+24 → T+96)                  │
│ Scope  zone/cluster/  ├───────────────────────────────────────────────────────────────────┤
│        grid/sites     │ SUMMARY  at risk 3 · ₹21.5 L · no fallback 1 · no READY fallback 2 │
│ Start  ─●───── 24 h   │ ORDER TABLE: state · days late · value · fallback · best backup   │
│ Length ───●─── 72 h   │ [ Open recovery for this order ]                                  │
│ [ Run test ]          │ calc log ▸                                                        │
└──────────────────────┴───────────────────────────────────────────────────────────────────┘
```
(The hazard buttons use the custom glyphs, not emoji; the characters above are placeholders.)
- Scope picker lists zones/clusters/grids from the API with a mini map for `zone`; `exposure_alert` appears as **"Use the current alert"**.
- **Auto test** opens read-only with a tag "Auto-run from alert at 04:53".
- **Shift chart:** SVG Gantt; rows per order; **baseline** bar (Cream hairline outline) vs **stressed** bar (Sun fill); downtime windows are hatched bands spanning all rows; due flags; late overflow in solid Sun with "+3.2 d". Hover shows the schedule steps.
- **Result table:** order state shape-coded; `fallback_level` shield; `best_backup` nameplate; row action **Open recovery**.
- Running animates the window bands "falling" onto the chart (400 ms) after the result arrives.

### 7.6 S6 Recovery (`/app/recovery/:id`)
**Purpose:** the payoff. Prefilled request, ranked options, handover, tracking.

```
┌ REQUEST (prefilled from alert) ────────────────────────────────────────────────────────┐
│ Disruption: Flood · north phase · T+24→T+96   Order ord_107  Pump shaft ×400  Due 21 Nov│
│ Passport: PRT-B ✔ confirmed                                  Window [24|48|72]          │
├ OPTIONS ───────────────────────────────────────────────────────────────────────────────┤
│ ┌ READY ───────────┐ ┌ APPROVAL PENDING ┐ ┌ EXCLUDED ─────────────┐                     │
│ │ Sample Components│ │ Sample Engineering│ │ ░ Sample Precision    │                     │
│ │ Oragadam  ✔ fresh│ │ Hosur             │ │ ░ Works (Ambattur)    │                     │
│ │ CHECKED  ✓ process│ │ CHECKED ✓ process │ │ ░ SAME_HAZARD_ZONE    │                     │
│ │ ✓ material ✓ tol. │ │ ✓ … ○ capacity   │ │ ░ technically suitable│                     │
│ │ UNVERIFIED ○ sample│ │ UNVERIFIED ○ cust.│ │ ░ but sits in the same│                     │
│ │ ├ lead slack 18 h ┤│ │ approval          │ │ ░ flood zone          │                     │
│ │ [ Select partner ]│ │ [ Select partner ]│ │ [ Cannot select ]     │                     │
│ └──────────────────┘ └───────────────────┘ └───────────────────────┘                     │
│ Recommended set: Oragadam + Hosur (different cluster, zone and grid)                      │
├ HANDOVER PACK (SIMULATED, cream sheet)  │  ROUTE CARD (tracking stepper)  [Advance step ▸] │
└────────────────────────────────────────────────────────────────────────────────────────┘
```
- **Three columns by outcome** (Ready / Approval pending / Excluded). Excluded cards are hatched and always show the **reason chip**; their button is disabled with a tooltip explaining why (409 prevention).
- **Checked vs unverified:** a two-block list per card. **CHECKED** items show a ✓ and a basis chip (`declared profile`); **UNVERIFIED** items show ○ and the check that would close them. Copy under the list: "A match is a candidate, not an approved backup."
- **Lead-time slack** shown as a dimension line (`├─ 18 h slack ─┤`).
- **Select partner** → confirm sheet: "Request activation from Sample Components. Activation is subject to human, customer and contractual approvals outside this software." → `POST …/select-partner`.
- **Handover pack:** cream sheet with a diagonal **SIMULATED** watermark; sections: job requirements, authorised documents, quantity and deadline, inspection checklist, responsibilities and contacts, required approvals, milestones.
- **Route card:** horizontal rail with seven stations (Request sent → Partner response → Technical and customer approvals → Production scheduled → Production started → Quality inspection → Dispatch and delivery). **Advance step (simulation)** moves a Sky marker along the rail; completed stations get a stamp. Label: "Simulated tracking".
- After selection, the relay schematic strip at the top shows the contact closing from owner to the chosen partner.

### 7.7 S7 Partners & Readiness (`/app/partners`)
**Purpose:** show the score is earned and decays; the place where it visibly rises at the end of the demo.

```
┌ RELAY CIRCUIT ─────────────────────────────────────────────────────────────────────────┐
│ OWNER ━━┯━━━━━━━━━◯ Oragadam  READY ✔ 40 d       trace solid Sky                        │
│ (bus)   ┠ ─ ─ ─ ─ ◯ Hosur     APPROVAL PENDING   trace dashed Pale                      │
│         ┠ ─ ─ ⏱ ─ ◯ Peenya    READY · STALE      trace dashed Sky + clock               │
│         ┠ ░░░░░░░░ ◯ Ambattur neighbour  EXCLUDED hatched / open contact                │
│         ┖ · · · · · ◯ Coimbatore POTENTIAL        ghost                                  │
├ READINESS ───────────────┬ PREPAREDNESS REVIEW ─────────┬ HISTORY ─────────────────────┤
│ ring 42 (24: 30 · 72: 55)│ ⏱ Peenya stale — Reconfirm   │ stepped line chart, markers  │
│ NEXT BEST ACTIONS        │ ⏳ Hosur expiring in 9 d      │ at status changes            │
│ ▸ Finish Hosur +12  [Do] │                              │                              │
└──────────────────────────┴──────────────────────────────┴──────────────────────────────┘
```
- **Relay circuit** is the centrepiece (SVG, trace-draw on load). Clicking a relay opens the **partner drawer**.
- **Partner drawer:** profile summary, status pill, the five **checks** as toggles-with-confirm (`TECH_ASSESSMENT_DONE`, `SAMPLE_APPROVED`, `TERMS_AGREED`, `CAPACITY_RECONFIRMED`, `CUSTOMER_APPROVED`), **Reconfirm** button, **Set status** control. A blocked transition (409) shows a stamp "CANNOT SET READY" with `missing_checks` listed.
- **Next best actions:** hover previews a **ghost arc** of the uplift on the ring; **Do it** executes the action (e.g. reconfirm) and the ring animates to the real new value; the predicted and actual uplift must match (backend test).
- **The closing demo moment:** completing Hosur's two missing checks → set READY → **Relay close** motion → score odometer rises ≥ 10 points → middle stack-light lamp changes → history chart gets a new marker.
- **Preparedness review:** stale and expiring-within-14-days lists with Reconfirm.
- **History chart:** stepped line from `/readiness/{id}/history`; markers carry the `reason`.

### 7.8 S8 Proof & Method (`/app/proof`)
- **Back-test table:** the Michaung ranking (sites, flooded yes/no, score), copied at Phase 14 into `src/data/backtest.json` (no live call). A bar chart with flooded sites marked by a Sun dot.
- **How numbers are made:** four short cards (Exposure, Weak points, Matching, Readiness) with the formula in one line each and a link to the live calc log.
- **Where AI is used:** one card: "Reading drawings only. Cross-checked against a text parser. A person confirms before anything is saved."
- **Limits and data sources:** the honesty statements, Open-Meteo and OSM attributions.
- **Glossary** of the six brief terms.

### 7.9 S9 Stage Controls (drawer, `` ` `` key)
Not a page; a right-side drawer available everywhere.
- **Weather mode:** `live | replay | synthetic` (segmented, with the current source/degraded status). Default replay.
- **Reset demo** (confirm) → `POST /demo/reset`, clears session flags (cold-open replays).
- **State readout:** `GET /demo/state` and `GET /health` as chips (DB, weather, vision chain).
- **Presenter mode** toggle (below) · **High-contrast / projector** toggle · **Reduce motion** override · **3D quality** (auto / full / lite / static) · **Backdrop** on/off · **Sound** on/off · **Snapshot mode** toggle.
- **Presenter mode:** a slim step strip at the bottom with the 7 demo steps and a timer. `→` / `←` jump between steps with the Shutter + camera flight; `R` resets; `H` hides the strip. Mapping in Appendix D.

### 7.10 S10 System screens
- **404 "Line not found":** a single relay glyph with an open contact and a button back to the Desk.
- **Backend unreachable:** full-page "Can't reach the server" with **Retry** and **Open saved snapshot**. Snapshot mode loads `src/data/snapshot.*.json` (captured from replay at Phase 17), disables write actions, and shows a Pale ribbon "Saved snapshot, not live".
- **Offline map tiles:** map keeps working on the blueprint grid with vector overlays only; badge "Map tiles unavailable".

---

## 8. Component Library

### 8.1 Primitives (`components/primitives/`)
`Frame` (hairline card with corner ticks) · `Button` (primary Sun / secondary Ocean / ghost; sizes; loading) · `Segmented` · `Chip` · `Nameplate` · `Stamp` · `Tooltip` · `Drawer` · `Dialog` · `Tabs` · `Toggle` · `Slider` · `Field`/`Input` · `Table` (sticky head, striped Navy) · `Skeleton` (blueprint-grid shimmer) · `Toast` · `Kbd` · `Icon` (inline SVG set).

### 8.2 Domain components (`components/domain/`)
| Component | Notes |
|---|---|
| `RiskPill`, `OrderStatePill`, `FallbackShield`, `StatusPill` (effective status incl. STALE), `ConfidenceBars`, `ExcludedReason` | The §2.3 encoding table, one component each. Single source of truth |
| `DataLabelBadge` | "SAMPLE / SIMULATED" stamp |
| `WeatherSourceBadge` | live / cache / replay / synthetic + degraded |
| `Money` | ₹ lakh / crore formatting (`2150000 → ₹21.5 L`) |
| `Odometer` | digit-roll number, `--ease-tick`, respects reduced-motion |
| `StackLight` | 3 lamps with tooltip |
| `ShiftClock`, `HorizonBar` | IST clock, T+00…T+72 |
| `ReadinessRing` | hatched gap, ghost-arc preview, 24/48/72 |
| `AlertBanner` | stamp-in, chevron edge, CTA |
| `DimensionLine` | wraps a value with end ticks |
| `CalcLog` | job-card drawer rendering `trace[]` |
| `TitleBlock` | per-screen drawing block |
| `PaperSheet` | cream sheet with Deep ink, optional watermark |
| `RelayCircuit` | schematic of owner + partners |
| `ShiftChart` | Gantt |
| `DependencyGraph` | custom layered SVG |
| `ExposureMap` | Leaflet wrapper, navy tile filter, markers/zones/routes |
| `CandidateCard` | match card with checked/unverified |
| `RouteCard` | tracking stepper |
| `RedactionSheet` | original vs redacted with bars |

### 8.3 Map styling (keep OSM, make it navy)
Leaflet OSM tiles are light. Apply a CSS filter on the tile pane: `filter: grayscale(1) invert(1) brightness(0.55) contrast(1.1)`, then overlay a `--c-deep` layer with `mix-blend-mode: multiply` at ~70 % and a faint Sky-tinted layer with `mix-blend-mode: screen` at ~8 % so it lands near Midnight/Navy. Verify visually; adjust the numbers, never add new colours. Attribution stays visible ("© OpenStreetMap contributors"). Light tile use only.

---

## 9. State, Data and Resilience

### 9.1 Client stack
React 19 + Vite (JS), React Router, **TanStack Query** (all server state), **zustand** (UI/story state only), Leaflet/react-leaflet, Recharts (rain strip, history, back-test only), GSAP + ScrollTrigger + **Lenis** (landing), three + R3F + drei (scene). No UI kit, no Tailwind: plain CSS with variables and CSS Modules.

### 9.2 Query conventions
| Query | Key | Refetch |
|---|---|---|
| Dashboard | `['dashboard', factoryId]` | on mount, then every 5 min, manual button |
| Exposure map | `['exposure','map']` | with dashboard |
| SPOF, relationships, readiness, passports | per id | on mutation invalidate |
| Mutations | status change, check complete, reconfirm, select partner, confirm passport | invalidate `dashboard`, `readiness`, `relationships` |

Defaults: `staleTime 30 s`, `retry 1`, request timeout 8 s, error normaliser reading the backend shape `{error:{code,message,details}}`. The 409 `details.missing_checks` is surfaced verbatim in the UI.

### 9.3 Session state (zustand)
`ui` (rail pinned, drawer open, presenter on/step, high-contrast, reduce-motion, tier, backdrop), `story` (progress, chapter, pointer), `session` (cold-open played, snapshot mode). Persist only UI prefs to `localStorage` (wrapped in try/catch).

### 9.4 The four states (every screen)
| State | Treatment |
|---|---|
| **Loading** | Blueprint-grid skeletons shaped like the final layout; never a spinner alone |
| **Empty** | One plain sentence + one action (e.g. Passports: "No passports yet. Use a sample drawing or drop your own.") |
| **Error** | Inline Frame with the normalised message, **Retry**, and the request ID/code in mono |
| **Degraded** | A Pale ribbon at the top of the affected panel using `degraded`/`source` flags ("Using last good forecast from 04:10") |

### 9.5 Backend asks (small, additive; raise in Phase F0)
1. `GET /factories/{id}/exposure` and `/exposure/map` include `hourly_mm[72]` per site (already computed inside the engine) for the rain strip and the horizon scrubber.
2. `/dashboard/{id}` includes `worst_order_id` for the banner CTA (else the client picks the highest-value LATE order from the stress result).
3. `/demo/state` returns whether `replay` is active and the replay label text.
If these are not done, the UI degrades as described in §7.1 and §7.3; nothing else is blocked.

### 9.6 Snapshot safety net
At Phase 17, capture `dashboard`, `spof`, `exposure/map`, `relationships`, `readiness`, one `stress-test`, one `recovery-request` and one `passport` into `src/data/snapshot.*.json`. Snapshot mode serves these read-only so the demo can still be *shown* if the backend dies.

---

## 10. Project Structure and Dependencies

### 10.1 Structure (inside `frontend/`)
```
frontend/
├── index.html
├── public/ (poster-hero.webp, favicon.svg, og.png)
├── scripts/ check_palette.mjs  capture_poster.mjs
├── src/
│   ├── main.jsx  routes.jsx
│   ├── api/ (client.js, hooks/, schemas.js)
│   ├── app/ (AppShell, Rail, StatusStrip, CommandPalette, StageControls, PresenterStrip, TransitionLayer)
│   ├── pages/ (Landing/, Desk/, WeakPoints/, Exposure/, Passports/, WhatIf/, Recovery/, Partners/, Proof/, System/)
│   ├── components/ (primitives/, domain/, drawing/ (PaperSheet, RedactionSheet), charts/)
│   ├── scene/ (WorldCanvas, Bay, LitBay, Yard, Rain, Water, Lines, Arcs, Ground, cameraStations.js, palette.js, tiers.js)
│   ├── styles/ (tokens.css, base.css, patterns.svg.jsx, motion.css)
│   ├── store/ (ui.js, story.js, session.js)
│   ├── hooks/ (useRelayNavigate, useSceneTier, useReducedMotion, useHotkeys)
│   ├── lib/ (format.js, money.js, time.js, status.js)
│   └── data/ (story.fallback.json, backtest.json, snapshot.*.json, copy.js)
```

### 10.2 Extra installs (on top of technical Phase 0; verify names on npm first)
```powershell
cd E:\Projects\factory-continuity-desk\frontend
npm install lenis zustand
npm install @fontsource/big-shoulders-display @fontsource/instrument-serif @fontsource/ibm-plex-sans @fontsource/ibm-plex-mono
npm install lucide-react            # optional, generic icons only
npm install @react-three/postprocessing   # optional, high tier bloom only
```
React/R3F pairing from the technical blueprint still applies (R3F v9 ↔ React 19; v8 ↔ React 18). GSAP's ScrollTrigger ships inside the `gsap` package; register it with `gsap.registerPlugin(ScrollTrigger)` after verifying current import paths in the docs (log in `docs/VERIFIED_FACTS.md`).

### 10.3 Palette lint (`scripts/check_palette.mjs`)
Scans `src/**/*.{css,js,jsx,svg}` for hex literals and `rgb()/hsl()` calls. Passes only if every match is inside `tokens.css` or `scene/palette.js` and is one of the 12 allowed hex values. Wired as `npm run lint:palette` and run at the end of every phase.

---

## 11. Build Phases

Mapped to the technical blueprint (Phases 15–18). **Order is deliberate: the demo path first, the spectacle second.**

| Phase | Title | Est. | Tech phase |
|---|---|---|---|
| F0 | Foundations: tokens, fonts, shell, API client, lint | 0:40 | 15 |
| F1 | Component library | 1:00 | 16 |
| F2 | App shell, navigation, shutter transition | 0:45 | 16 |
| F3 | Desk + Exposure | 1:15 | 16 |
| F4 | Weak Points + What-if | 1:15 | 16 |
| F5 | Recovery + Partners (relay circuit) | 1:30 | 16 |
| F6 | Passports + RFQ | 1:15 | 16 |
| F7 | Stage Controls, Presenter mode, Proof, system screens | 0:50 | 16 |
| F8 | Landing: hero parallax | 1:30 | 15–16 |
| F9 | Landing: scroll story + Dive transition | 1:30 | 15–16 |
| F10 | Persistent world backdrop and stations (stretch) | 1:00 | — |
| F11 | Integration, performance, rehearsal, freeze | 1:00 | 17–18 |

**Cut order if behind:** F10 → chapter 03 map morph (keep chapters 00–02, 04) → landing 3D (ship the `static` tier landing) → sound → command palette → Proof page extras. **Never cut:** F0–F7 and the snapshot safety net.

---

### PHASE F0 — Foundations
**Tasks**
1. Install §10.2 packages; confirm nothing landed on C: (run the technical `check_c_drive_leaks.ps1`).
2. `styles/tokens.css` (Appendix A), `base.css` (reset, blueprint-grid background, focus ring, type scale), SVG `patterns`.
3. Import fonts from `@fontsource` (weights only as listed).
4. `src/api/client.js` (base URL `VITE_API_URL`, timeout, error normaliser), health hook, Query provider.
5. Routes skeleton for every §4.1 route rendering a titled placeholder + `TitleBlock`.
6. `scripts/check_palette.mjs` and `npm run lint:palette`.
7. Raise the §9.5 backend asks (note any that are refused).
**Done when:** `npm run dev` shows the shell on all routes, fonts load offline, `GET /health` appears in a chip, `lint:palette` passes.

### PHASE F1 — Component Library
**Tasks:** build §8.1 primitives and §8.2 domain components that do not need page data. Add a hidden `/app/_kit` route showing every component and every status/state variant side by side (this is the visual regression page).
**Tests:** unit tests for `Money`, status-to-style mapping (every enum value has a distinct shape/pattern + text), `Odometer` final value, `ConfidenceBars`.
**Done when:** `_kit` shows all variants in the palette only; status mapping tests pass; `lint:palette` passes.

### PHASE F2 — App Shell, Navigation, Shutter
**Tasks:** `AppShell`, `Rail` (collapse/expand, hotkeys 1–8), `StatusStrip` (clock, stamp, source badge, stack light placeholder), `useRelayNavigate` + `TransitionLayer` (shutter with chevron edge; 160 ms crossfade when reduced-motion), `CommandPalette`, breadcrumbs.
**Done when:** all routes reachable by rail, hotkeys and palette; shutter plays on every change without layout jank; reduced-motion respected.

### PHASE F3 — Desk and Exposure
**Tasks:** S1 Desk per §7.1 and S3 Exposure per §7.3: `AlertBanner`, `ReadinessRing`, KPI odometers, weak-point list, rain strip, `ExposureMap` (navy tile filter, zones, routes, markers), site list with drivers, calc log drawer, cold-open sequence, all four states.
**Done when:** with the backend in `replay`, the Desk shows the banner, ring and top 3 weak points; **Start recovery request** creates a request (even before S6 exists, it must reach the route); map works with tiles blocked.

### PHASE F4 — Weak Points and What-if
**Tasks:** S2 with `DependencyGraph` and **Pull the plug**; S5 with scenario form, `ShiftChart`, result table, deep links (Desk → What-if auto test, Weak Points → What-if resource).
**Done when:** a manual FLOOD test renders LATE orders with correct dates on the chart; the auto test opens read-only; pull-the-plug animates and matches `orders_broken`.

### PHASE F5 — Recovery and Partners
**Tasks:** S6 per §7.6 (`CandidateCard` columns, select flow, handover sheet, route card) and S7 per §7.7 (`RelayCircuit`, partner drawer with guarded transitions, next-best actions with ghost arc, history chart, **Relay close** motion).
**Done when:** demo steps 5–7 work in the browser: Ready / Approval pending / Excluded cards show; selecting an excluded partner is impossible; completing Hosur's checks and setting READY raises the score ≥ 10 points with the animation.

### PHASE F6 — Passports and RFQ
**Tasks:** S4 per §7.4: sample tray, drop zone, extraction states with scan line, fields with confidence bars and candidate picking, confirm gating, `RedactionSheet` with bars from `redaction_report`, share dialog with consent copy.
**Done when:** all three sample drawings go from tray → confirmed passport → redacted RFQ; manual path works with the reading service disabled; a leak check by eye finds no customer name or drawing number in the redacted sheet.

### PHASE F7 — Stage Controls, Presenter, Proof, System
**Tasks:** S9 drawer and Presenter strip (Appendix D mapping and shortcuts), S8 Proof page (`backtest.json` copied from the Phase 14 report), S10 screens, snapshot mode and snapshot capture script.
**Done when:** the full 3–4 minute story can be driven with only `→`/`←`; snapshot mode shows a read-only demo with the server stopped.

### PHASE F8 — Landing: Hero Parallax
**Tasks:**
1. Build the **static tier first** (CSS/SVG parallax hero, layered headline, skyline, rain, callout cards, nav, chapter rail). This is the guaranteed fallback.
2. `WorldCanvas` (transparent), `Bay` instances, `LitBay`, `Ground` shader with alpha fade, `Yard`, fog, pointer sway.
3. Tracked leader-line callouts anchored to 3D points.
4. `useSceneTier` with `PerformanceMonitor`; `capture_poster.mjs` (or a manual screenshot) to produce `public/poster-hero.webp`.
**Done when:** the hero holds 50+ fps on the demo laptop; letters sit behind the lit bay; `?tier=static` and reduced-motion show the static hero; scene chunk is lazy-loaded.

### PHASE F9 — Landing: Scroll Story and Dive
**Tasks:** Lenis + ScrollTrigger pin (700 vh), `storyStore`, chapters 01–04 per §5.3 (dependency lines, rain/water/zone shutdown with scrubbed `T+hh`, map morph and arcs, ring close), "How it works", "Proof", "Honest limits", CTA, footer; **Dive** transition into `/app`; data from `/dashboard` with `story.fallback.json`.
**Done when:** scrolling back and forth is smooth and reversible at any speed; chapter UI and counters match the scene; the Dive lands on the Desk with its cold-open; static tier tells the same story without 3D.

### PHASE F10 — Persistent World Backdrop (stretch)
**Tasks:** mount `WorldCanvas` at the app root behind routes with `cameraStations.js` per §6.1, `frameloop="demand"`, route-driven camera flights under the shutter, backdrop opacity per route, Passports dim, tier-aware fallback to the CSS grid.
**Done when:** route changes show a camera flight with no dropped frames and no readability loss; turning the backdrop off in Stage Controls is instant.

### PHASE F11 — Integration, Performance, Rehearsal, Freeze
**Tasks:**
1. Run the 7-step story three times, resetting between, in `replay` mode, then once with `live`, then once with the server killed (snapshot mode).
2. Performance pass against §12 budgets; fix long tasks; verify lazy chunks.
3. Accessibility pass: keyboard-only run of the demo, focus order, contrast spot-checks, high-contrast mode on a projector-like screen.
4. Screens at 1920×1080 and 1366×768; confirm nothing clips in the title block or rail.
5. Capture `src/data/snapshot.*.json` and final screenshots to `docs/screens/final/`.
6. Update README (frontend section), tag `v1.0`.
**Done when:** three clean runs with zero console errors; palette lint green; two timed rehearsals under 4 minutes.

---

## 12. QA, Performance Budgets, Risks

### 12.1 Budgets
| Item | Target |
|---|---|
| App (non-landing) JS | ≤ 350 KB gzip initial (three/R3F excluded, lazy) |
| Landing first paint (static layer) | < 1.5 s; scene interactive < 2.5 s |
| Scene frame rate | ≥ 50 fps `full`, ≥ 30 fps `lite` |
| Route transition | ≤ 700 ms total, no layout shift |
| Dashboard render after data | < 300 ms (excluding the cold-open sequence) |

### 12.2 Visual QA checklist (per phase screenshot set)
- Only palette colours; no pure grey; no shadows; corners square; ticks present on every Frame.
- Gold means attention; Sky means coverage. Nothing violates it.
- Every status has a shape or pattern, not just colour.
- Title block present and says SAMPLE / SIMULATED.
- No banned words; no fake social proof.
- Degraded and empty states reviewed on every screen.

### 12.3 Risks and mitigations
| Risk | Mitigation |
|---|---|
| 3D landing eats the schedule | Static tier built first (F8.1) and it is shippable; F9/F10 are explicit stretch work |
| WebGL fails on the demo machine or projector | Three tiers, `?tier=static`, poster image, reduced-motion path |
| Scroll jank (Lenis/ScrollTrigger fights) | Single ticker (`gsap.ticker` drives Lenis); no timelines in `useFrame`; test on the real laptop early |
| Letters-behind-object effect looks flat | Make the ground alpha-fade and keep the canvas transparent; fall back to a larger parallax offset on the letters |
| Navy map tiles look muddy | Tune the filter numbers (§8.3); fallback to blueprint grid with vector overlays |
| Palette drift as components multiply | `lint:palette` every phase; one `status.js` mapping |
| Backend missing `hourly_mm` | Degrade to a single dimension-line callout (§7.1, §7.3) |
| Projector washes out hairlines | High-contrast toggle (hairlines 36 %, weight 600) |
| Backend dies on stage | Snapshot mode + pre-opened tabs per screen |
| Time overrun | §11 cut order; F0–F7 are protected |

---

## Appendix A — `src/styles/tokens.css` (starting file)

```css
:root {
  /* palette: the only 12 colours */
  --c-void:#000000; --c-deep:#0A1A40; --c-midnight:#00205B; --c-navy:#1A3070;
  --c-ocean:#003087; --c-sky:#307FE2; --c-sun:#F2A900; --c-gold:#C8920A;
  --c-pale:#E8C870; --c-sand:#FFE264; --c-cream:#F8F0DC; --c-white:#FFFFFF;

  /* alpha tints (derived, defined only here) */
  --c-cream-12: rgb(248 240 220 / .12);
  --c-cream-24: rgb(248 240 220 / .24);
  --c-cream-36: rgb(248 240 220 / .36);
  --c-sky-16:   rgb(48 127 226 / .16);
  --c-sun-20:   rgb(242 169 0 / .20);
  --c-deep-80:  rgb(10 26 64 / .80);

  /* gradients (palette 2) */
  --g-depth: linear-gradient(180deg, var(--c-sky), var(--c-ocean) 45%, var(--c-void));
  --g-dusk:  linear-gradient(0deg, var(--c-sun), var(--c-sky) 55%, var(--c-midnight));
  --g-paper: linear-gradient(90deg, var(--c-white), var(--c-sand) 55%, var(--c-sun));

  /* surfaces and text */
  --bg: var(--c-deep); --panel: var(--c-midnight); --inset: var(--c-navy);
  --text: var(--c-cream); --text-strong: var(--c-white); --hair: var(--c-cream-24);
  --focus: var(--c-sky);

  /* type */
  --f-display: "Big Shoulders Display", sans-serif;
  --f-serif: "Instrument Serif", serif;
  --f-ui: "IBM Plex Sans", system-ui, sans-serif;
  --f-mono: "IBM Plex Mono", ui-monospace, monospace;

  /* motion */
  --ease-snap: cubic-bezier(.2,.8,.2,1);
  --ease-settle: cubic-bezier(.16,1,.3,1);
  --ease-tick: steps(6, end);
  --t-micro:120ms; --t-std:240ms; --t-panel:400ms; --t-seq:800ms;

  /* layout */
  --u: 8px; --rail: 72px; --rail-open: 224px; --strip: 48px;
}
[data-contrast="high"] { --hair: var(--c-cream-36); }
```

## Appendix B — Status encoding quick table (implement once in `lib/status.js`)

| Enum value | Fill | Stroke / pattern | Glyph | Label |
|---|---|---|---|---|
| RiskLevel.LOW | none | Sky | dot | Low |
| RiskLevel.MODERATE | Pale | — | dot | Moderate |
| RiskLevel.HIGH | Sun | — | triangle | High |
| RiskLevel.SEVERE | Sun | chevron-sun + pulse | triangle ! | Severe |
| OrderState.ON_TRACK | none | Sky | tick | On track |
| OrderState.AT_RISK | Pale | — | clock | At risk |
| OrderState.LATE | Sun | — | flag | Late |
| FallbackLevel.READY | Sky | — | shield solid | Ready cover |
| FallbackLevel.POTENTIAL_ONLY | none | Pale | shield outline | Candidate only |
| FallbackLevel.NONE | hatch-sun | Gold | shield cross | No cover |
| BackupStatus.READY | Sky | — | closed contact | Ready |
| EffectiveStatus.STALE | none | Sky dashed | clock | Reconfirm needed |
| BackupStatus.APPROVAL_PENDING | half Pale | Pale | half circle | Approval pending |
| BackupStatus.ASSESSMENT_IN_PROGRESS | none | Navy-light | three dots | Assessing |
| BackupStatus.POTENTIAL_MATCH | none | hairline | ring | Potential |
| BackupStatus.UNAVAILABLE_EXPIRED | none | Navy, strikethrough | open contact | Unavailable |
| Excluded (any reason) | hatch-navy | Gold | open contact | Excluded: *reason* |

## Appendix C — Copy deck (plain language)

| Where | Copy |
|---|---|
| Hero headline | **FIND WHERE YOU BREAK** / *before the flood does.* |
| Hero left card | The only grinder you have. ±0.005 mm. 4 orders wait on it. |
| Chapter 01 | One grinder. Four orders. If it stops, they all stop. |
| Chapter 02 | Heavy rain in 36 hours. Your zone is the low ground. |
| Chapter 03 | Cover that isn't standing in the same water. |
| Chapter 04 | Know your cover before you need it. |
| Tagline (footer) | Our software reads the drawing. Our maths tells you where you break. |
| Alert banner | Heavy rain in 36h: 3 orders at risk, ₹21.5 L exposed, 1 order has no fallback |
| Risk disclaimer | Risk indicator from forecast rain and site conditions. Not a flood model. |
| Match disclaimer | A match is a candidate, not an approved backup. |
| Select partner | Activation is subject to human, customer and contractual approvals outside this software. |
| Extraction pending | Reading your drawing… |
| Rules-only fallback | Reading service unavailable. Draft built from printed text only. Check every field. |
| Confirm blocked | Can't confirm yet: material grade, quantity. |
| Redaction note | Removed: customer name, drawing number, part number, revision, title block, branding. |
| Full-share consent | The partner will see the full drawing details. Only do this with the customer's permission. |
| Stale | Reconfirm needed |
| Sample stamp | SAMPLE / SIMULATED |
| Replay label | Replay of Cyclone Michaung rainfall (Dec 2023), time-shifted to now |
| Snapshot ribbon | Saved snapshot, not live |
| 404 | Line not found. |

## Appendix D — Presenter script mapping (3–4 minutes)

| Step | ≈ Time | Screen | What to say / do | Key |
|---|---|---|---|---|
| 0 | 0:00 | Landing (scroll 20 s, or skip with **Open the desk**) | "Find where your factory breaks before the flood does." | `→` |
| 1 | 0:25 | Desk | Alert banner, readiness 42, "one order has no fallback" | `→` |
| 2 | 0:50 | What-if (auto test) | Orders at risk, ₹ exposed, shift chart | `→` |
| 3 | 1:15 | Weak points | Pull the plug on the grinder: four orders break | `→` |
| 4 | 1:45 | Passports | Sample drawing → passport → redacted RFQ. "Our software reads the drawing." | `→` |
| 5 | 2:25 | Recovery | Start request; Ready / Approval pending / Excluded (same flood zone) | `→` |
| 6 | 3:00 | Recovery | Select the Ready partner; handover pack; advance the route card | `→` |
| 7 | 3:20 | Partners | Complete Hosur's checks → READY → relay closes → score up. "Our maths tells you where you break." | `R` to reset |

Keyboard: `→/←` step, `R` reset, `H` hide presenter strip, `` ` `` Stage Controls, `/` command palette, `1–8` screens.

## Appendix E — Quick resume index
- **F0–F2:** foundations, library, shell and transitions.
- **F3–F7:** the full working app (demo path), Stage Controls and Presenter, snapshot net.
- **F8–F9:** the landing (static tier first, then 3D scroll story and Dive).
- **F10:** persistent 3D world behind the app (stretch).
- **F11:** integration, performance, rehearsal, freeze.
