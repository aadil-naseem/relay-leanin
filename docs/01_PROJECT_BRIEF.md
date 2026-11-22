# Factory Continuity Desk — Final Project Brief (Ideation Frozen)

> **Instruction for any Claude session reading this:** This is the final, locked ideation for a solo hackathon build. Do **not** reopen idea selection or propose alternative projects. Your job is to help plan and build *this* project. Section 13 lists what is open for planning. Everything else is decided.

---

## 1. Context

| Item | Detail |
|---|---|
| Event | **Vihaan X (10th edition)** hackathon, **software track** |
| Format | 24-hour build, starts **Saturday 14 Nov 2026** |
| Team | **Solo builder** (Aadil) |
| Track chosen | **Open Innovation** (also touches Sustainability / Smart City & Civic Tech) |
| Problem statement rule | Organisers confirmed the PS is **self-chosen within the track's domain** |
| Build rule | Organisers confirmed **main project building must happen during the 24 hours**. Research, ideation and preparation beforehand are allowed |
| Judging criteria | Not confirmed. Assume innovation, technical depth, real-world impact and demo quality |

**Preparation allowed before the event:** research, ideation, architecture, data/fixture preparation, sample drawings, API testing, pitch drafting. **Not allowed:** writing the main project code in advance. Treat any scaffolding as a grey area to avoid or keep minimal.

---

## 2. One-paragraph summary

**Factory Continuity Desk** is a production-continuity platform for small precision-component manufacturers in India. It finds where a factory would break *before* a disruption (flood, power or water outage, blocked access) and shows who could cover the work. It reads a part drawing to build a structured **Production Passport**, finds the factory's **single points of failure**, watches live weather, elevation and road data for **exposure**, runs a **what-if stress test** automatically when risk rises, and recommends **risk-aware backup factories** that do not share the same hazard zone. It reports a **computed Recovery Readiness Score**. The pitch: *"Find where your factory breaks before the flood does, then show who can cover it."*

---

## 3. The problem

When a factory cannot produce (flooding, extreme weather, power or water interruption, transport problems), orders slip and customers are lost. Smaller manufacturers rarely have a prepared alternative. Finding a backup under pressure is hard because a candidate may:

- lack the right machine, process, material or tooling;
- be unable to hold the required dimensions or tolerances;
- have no spare capacity or an unsuitable lead time;
- need sample or customer approval before taking over;
- sit in the same disrupted area;
- refuse urgent work without pre-agreed terms.

Most small factories also do not know which single machine, vendor or material their critical orders depend on, so they cannot see the risk until it hits.

**Why this space:** it is far less crowded than consumer or EV ideas, and the pain is a concrete B2B one with a clear buyer (owner / operations / procurement manager).

---

## 4. Target users

- **Primary:** owners and operations/procurement/production managers of small and medium manufacturers.
- **Initial segment:** small **precision-component manufacturers** (CNC machining and similar). Their needs can be described concretely: process, machine capability, material, dimensions, tolerances, tooling, quantity, inspection requirements.
- Later: other manufacturing sectors.

---

## 5. Positioning and USP

**Positioning:** a production recovery network that helps smaller manufacturers **prepare** and **activate** qualified alternative production.

**USP:** the product does not stop at warning "production may stop". It (1) diagnoses the factory's specific weak points, (2) proactively alerts and quantifies the impact, and (3) shows credible, risk-independent backups that are tracked with a readiness status.

**Honesty note on competition (unverified in this project):** manufacturing marketplaces (e.g. Xometry, Fictiv, Zetwerk-style) and supply-chain risk tools (e.g. Resilinc, Everstream, Interos) are believed to overlap with parts of this. These names come from background knowledge and have not been checked. The claim is **not** "nobody does anything similar". The claim is that the **combined workflow** (drawing to passport, single-point-of-failure diagnosis, live exposure, risk-aware backup readiness for small manufacturers) is the opportunity. Verify competitors briefly before pitching.

---

## 6. How the idea was chosen (decision log, do not reopen)

**Eliminated or set aside:**

| Idea | Why it was dropped |
|---|---|
| Bureaucracy translator (Open Innovation) | Two of the builder's classmates already built it |
| Deepfake / fraud detection for the elderly (Security) | Crowded with existing AI tools |
| EV battery second-life marketplace | EV space is saturated; the product would be a plain marketplace with no technical innovation; liability and verification problems |
| Migrant portable digital identity | Root problem is policy, not technology |
| Crowdsourced water-quality monitoring | Data unreliable without hardware; existing government tools |
| Vernacular crop-advisory voice bot | Kisan Call Centre exists; brittle regional-language voice tech; WhatsApp approval wall |
| Phone-as-sensor predictive maintenance (IoT) | Hard to demo without a real machine; lukewarm interest |
| RWA water-tanker delivery audit (Smart City) | Set aside before a full teardown; early research suggested buyers are mostly households rather than RWAs and found no clear verification data source |

**Why Factory Continuity Desk won:** real B2B pain, a low-competition space, no hardware, no government API access and no policy change required, and a pitch story judges can follow. The original brief was a workflow/marketplace app with a matching filter (low technical novelty), so it was **restructured** to put a technical core at the centre: drawing extraction, graph analysis, live hazard data, simulation, and risk-aware optimisation.

**Self-assessed scores (1 to 10):** original brief: innovation 4, solo-buildable 6, impact 6. Final version: innovation 8, solo-buildable 6, impact 7. The main risk is scope.

---

## 7. Final scope

### 7.1 BUILD (core)

1. M1. Simple form onboarding
2. M2. Drawing to Production Passport, plus redacted RFQ
3. M3. Single-point-of-failure finder
4. M4. Live exposure engine (auto-run, alert banner)
5. M5. What-if stress test (auto-run on alert and manual)
6. M6. Risk-aware backup matching
7. M7. Production Recovery Request (prefilled from the alert)
8. M8. Recovery Readiness Score with a light status field and preparedness review

### 7.2 MOCKED (thin UI, simulated state)

- M9. Production Handover pack
- M10. Recovery tracking (milestone stepper)

### 7.3 NOT BUILT (if-time-allows list only)

- Local incident reporting (explicitly kept as a not-built item)
- WhatsApp-forward incident parsing
- Cluster response dashboard / shared incident feed
- Downloadable PDF passport and recovery reports
- Notifications for partner responses and milestones
- Photo/voice onboarding (**rejected**: adds an unnecessary vision layer)

---

## 8. Module specifications

### M1. Simple form onboarding
Plain forms to create a factory or partner profile. No vision or voice input.
- **Fields:** name, location (latitude/longitude), industrial cluster, processes, machines (type, count), materials, capacity (hours/week or units/week), typical lead time, contact roles.
- **Partner factories:** same fields plus a readiness status (see M8).
- **Demo data:** all factories are **fictional sample data, clearly labelled as simulated**.

### M2. Drawing to Production Passport (the hero feature)
A **Production Passport** is a structured record of a product or job so a backup partner can judge whether it can take over.
- **Input:** an image or PDF of a part drawing.
- **Processing:** a multimodal LLM extracts structured JSON: part description, manufacturing process, material and specification, key dimensions, tolerances, surface finish, tooling/fixture hints, quantity and deadline (if present), inspection notes.
- **Reliability:** every field carries a confidence level; missing or ambiguous fields are flagged; the user reviews and edits before saving.
- **Fallback:** if extraction fails, the passport can be filled by hand (protects the live demo).
- **Redacted RFQ:** a second view that strips customer name, title-block identifiers, part numbers and branding, keeping only process, material, tolerances, quantity and deadline, and generates an anonymised request for backup partners. This addresses the objection that factories will not share drawings.
- Drawings and customer details are shared only with explicit permission in any real use.

### M3. Single-point-of-failure (SPOF) finder
- **Model:** orders to parts to required processes to machines, vendors and materials, as a graph.
- **Output:** a ranked list of nodes (one CNC machine, one heat-treatment vendor, one material supplier) whose loss breaks critical orders that have no in-house alternative, with the orders affected and revenue at risk.
- **Demo:** uses a sample bill of processes.

### M4. Live exposure engine
- **Inputs (free public data, to be verified during planning):** weather forecast (Open-Meteo), elevation data, road network (OpenStreetMap).
- **Output:** a risk score per factory and per access route over the next 72 hours (flood, waterlogging, isolation).
- **Proactive behaviour:** the engine **runs automatically** on every dashboard load. When risk crosses a threshold it triggers M5 and shows a banner on the landing page, e.g. *"Heavy rain in 36h: 2 orders at risk, ₹X exposed, 1 order has no fallback"*, with a one-click **Start Recovery Request** button.
- **Demo realism:** exposure uses **real data** for a real flood-prone industrial cluster location; the factories themselves are fictional. Keep cached fallback data in case an API is down.

### M5. What-if stress test
- **Manual:** the user selects a hazard, zone and duration (for example, "flood in this zone for 72 hours").
- **Automatic:** runs on its own when M4 raises an alert, so the user never has to find it.
- **Output:** which factories are affected, which orders miss their deadlines (simple schedule model), revenue at risk, and which orders have a fallback.
- Feeds the readiness score (M8).

### M6. Risk-aware backup matching
- **Hard filters:** process, material, tolerance capability, available capacity, lead time.
- **Correlated-risk exclusion:** exclude or down-rank backups in the same hazard zone, industrial cluster or power grid as the affected factory. Where several backups are chosen, prefer a set whose failure modes are not correlated.
- **Transparency:** each match shows which requirements were **checked** and which remain **unverified**. A match is a candidate, not an approved backup.

### M7. Production Recovery Request
- Created manually, or **prefilled from the M4/M5 alert** with one click.
- Records the disruption, the order or product, quantity, deadline and passport. Shows ranked backup options (M6), their readiness status, capacity and outstanding approvals. The factory selects a partner and requests activation, subject to the human, customer and contractual approvals that remain outside the software.

### M8. Recovery Readiness Score and light status field
- **Backup status (per partner relationship):** `Potential Match`, `Assessment in Progress`, `Approval Pending`, `Ready`, `Unavailable / Expired`, plus a **last-confirmed date**.
- **Score:** the share of a factory's critical parts (optionally revenue-weighted) that have at least one **Ready, non-stale, non-correlated** backup able to deliver within a chosen recovery window (**24, 48 or 72 hours**).
- **Only `Ready` and not-stale backups count.** Staleness window is a configurable default (planning to set a value, for example 90 days).
- **Preparedness review (light):** stale or expired partners are flagged with a "reconfirm" prompt, which lowers the score until confirmed. The status field therefore changes the score rather than decorating it.
- A software status must never be shown as proof of quality unless the checks were actually completed.

### M9 and M10. Mocked handover and tracking
- **Handover pack (static):** product and job requirements, authorised documents, quantity and deadline, inspection checklist, responsibilities and contacts, required approvals, agreed milestones.
- **Tracking (simulated):** stepper through Request sent, Partner response, Technical and customer approvals, Production scheduled, Production started, Quality inspection, Dispatch and delivery.

---

## 9. Demo scenario (3 to 4 minute story)

1. Landing page shows the factory's **Readiness Score** and a **live risk banner** from real forecast data: heavy rain approaching a flood-prone cluster.
2. The banner shows the auto-run stress test: orders at risk, revenue exposed, and the one order with no fallback.
3. Open the **SPOF finder** and show why: one CNC machine or one vendor everything depends on.
4. Show a part drawing turned into a **Production Passport** in seconds, then its **redacted RFQ**.
5. Click **Start Recovery Request** (prefilled). Backup options appear: one **Ready** with the right process and capacity; one technically suitable but **Approval Pending**; one **excluded** because it sits in the same flood zone.
6. Select the Ready backup, show the (mock) handover pack and tracking stepper.
7. Close on the score going up once a backup is confirmed `Ready`.

All factories, capacities and approvals are labelled **sample / simulated**.

---

## 10. Suggested 24-hour build order (initial, to be refined in planning)

- **Hours 0 to 8:** M2 drawing extraction, M3 SPOF graph.
- **Hours 8 to 16:** M4 exposure engine, M6 risk-aware matching.
- **Hours 16 to 21:** M5 what-if and auto-run, M8 readiness score and status field, M7 recovery request, redacted RFQ.
- **Hours 21 to 24:** M9/M10 mocks, polish, pitch rehearsal.
- **Build the demo flow first:** SPOF, exposure, what-if and the score work together as one story, so they come before polish.
- **Riskiest piece:** drawing extraction. Test it on 2 or 3 sample drawings before the event.

---

## 11. Product boundaries and assumptions

- The platform **supports decisions and coordination**. It does not manufacture, guarantee quality, transfer orders automatically, or bypass customer and contractual approvals.
- Technical matching is an aid to assessment, not certification.
- Technical drawings, customer information and commercial terms are shared only with explicit permission and access controls.
- Capacity and readiness change over time; partners must reconfirm.
- A geographically separate factory is not automatically safe from the same disruption; location and infrastructure exposure are considered explicitly (M4, M6).
- Real-world adoption depends on manufacturers being willing to share capability information and form backup arrangements. **No customer interviews have been done**, so willingness to pay and to share data is unvalidated.
- The "pre-qualified" part of the USP (sample inspection, customer sign-off) happens in the real world; the software tracks it but cannot perform it.

---

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Scope too large for solo 24h | Strict build order; M9/M10 are mocks; stretch list is not built |
| Drawing extraction fails on stage | Manual passport fallback; pre-tested sample drawings |
| Free APIs unavailable or rate-limited | Cached forecast, elevation and road data for the demo cluster |
| Looks like "just another marketplace" | Lead the pitch with diagnosis (SPOF, exposure, what-if, score), not matching |
| Judges ask about adoption and cold start | Be upfront: pilot with one cluster; the value stands alone through diagnosis even before backups join |
| Judges ask about data sharing and IP | Redacted RFQ; permissioned sharing |
| Competitor overlap | Present the combined workflow as the opportunity; verify competitors beforehand |

---

## 13. Open items for planning (the only things still undecided)

- Tech stack, hosting and repository layout
- Data model and APIs between modules
- Which LLM/vision provider and cost limits
- Which real flood-prone cluster location to use for the demo
- Sample drawings, fictional factory fixtures and bill-of-process data
- Staleness window default and the readiness-score formula details
- Pitch deck and demo script wording
- Pre-event preparation that stays within the organisers' rule

---

## 14. Glossary

- **Production Passport:** structured description of a part or job that lets a backup factory assess fit.
- **Redacted RFQ:** anonymised request derived from a passport, with customer-identifying details removed.
- **SPOF (single point of failure):** a machine, vendor or material whose loss stops critical orders with no alternative.
- **Exposure:** how likely a factory or its access routes are to be hit by a hazard within a time window.
- **Recovery Readiness Score:** share of critical production with a viable, ready, non-correlated fallback within a chosen recovery window.
- **Correlated risk:** two sites likely to fail together because they share a hazard zone, cluster or power grid.
