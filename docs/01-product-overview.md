# 01 · Product overview

## The problem (our framing, from the Designathon submission)
> **Waypoint doesn't have a capacity problem, it has a planning-accuracy problem.** Plans assume empty roads. Reality runs 1.7× slower and the delay compounds stop by stop, so one Fresh delivery in five is late. On peak days refrigerated space is the hard limit, and nobody sees any of it until a store calls.

### Evidence (computed from the competition data; training 2024-01-01 → 2026-02-14, scenario S1)
| Finding | Number | What we built because of it |
|---|---|---|
| Actual travel vs planned free-flow time | **1.72×** | Two clocks: plan time for the rules, a likely window for people |
| Late rate by stop position | **7% → 68%** (stop 1 → 8) | Late risk per stop at plan time |
| Fresh deliveries after the window closes | **20.4%** | Exceptions ranked by impact; Fresh first |
| S1 chilled demand vs reefer space | **181.6 vs 172.4 m³** | Bottleneck strip; deferrals with reasons; unavoidable vs our choice |
| Outlets at 5 days since last served (S1) | 5 | Repeat-skip protection |
| Van-only chilled orders vs the one reefer van | **1,096 kg vs 1,040 kg** | Live rule messages explain why a trip splits |
| Fresh outlet-days with a dry and a chilled order | **66.6%** | Two orders, two vans, shown as two lines |

## Scale (real world)
- About **140 orders per operating day** (Peliyagoda about 86, Kandy about 54); p95 is 152.
- About **38 routes** and **139 stops** a day, using about **29 of 60 vehicles**.
- About **200 users**: ~60 drivers, a handful of loaders, 2–3 dispatchers, ~120 store managers.
- **1–2k events a day.**

This is a **correctness, reliability and offline** problem, not a throughput problem. See [03-architecture.md §Scale](03-architecture.md#scale-and-growth).

## Principles
1. **Decide · Predict · Check · Communicate.** Optimisation decides; models predict; rules and gates check; plain-language, multilingual messages communicate.
2. **Minimise business loss**, not "orders served".
3. **A person always decides.** The engine proposes, and every output explains itself.
4. **Two clocks:** the published planning standard (the rules) beside a realistic likely window.
5. **Offline is a normal working state** for drivers and loaders.
6. **One source of truth:** immutable plan versions and an append-only event log.

## Roles and screens in scope (Hackathon)
Screen codes follow the Figma file.

| Role | Screens | Degradation (⭐) |
|---|---|---|
| Shared | X1 Sign in | |
| Dispatcher (desktop) | D1 Plan workspace (Timeline · Deferred tab D3 · Fleet tab · Edit trips · Publish dialog D4) · D5 Live ops · D6 Resolve shortfall · D10 Review store report · D13 Reconcile offline record | D6, D13 |
| Loader (phone + dock tablet) | L1 Loading trips · L2 Load trip · L3 Report shortfall · L4 On hold (result of L3) · L5 Review revised load | L3, L4 |
| Driver (phone) | R1 Today's trip · R2 Stop detail · R3 Record outcome · R4 Saved offline · R5 Uploaded · R7 Needs review | R4, R7 |
| Store manager (phone/desktop) | S1 Home + tracking · S2 New order · S5 Confirm receipt · S6 Report a problem · S8 Delivery deferred | S8 |

**Out of scope (as stated in the design):** live GPS map, vision AI on photos, voice for drivers, policy sliders, learning from overrides. **P1 if time allows:** D7 Capacity outlook.

## The demo story (peak-day scenario S1)
Peliyagoda · **Tue 7 Apr 2026**, one week before New Year · 85 orders, closing Mon 6 Apr at 16:00.
1. **Mon 14:50.** OUT001 orders from its usual items. A 3× quantity is questioned.
2. **16:00.** Orders close. **16:12** the dispatcher generates the plan: the limit is reefer space. VEH036 needs 2 trips (1,096 kg vs 1,040 kg). OUT074 (5 days unserved) is protected on VEH007. Deferrals carry reasons. Publish v1.
3. **16:25.** OUT054 gets a deferral notice (Sinhala, Tamil or English).
4. **Tue 04:17.** The loader finds OUT003 is 2 cases short, and VEH036 goes on hold. **04:26** the dispatcher applies option A (40 now + 2 on trip 2) and v2 is published. The loader acknowledges, and the van is released.
5. **04:36.** The driver acknowledges v2 and delivers OUT001 and OUT003, with two clocks per stop.
6. **05:40.** OUT001 confirms receipt and reports 2 damaged yoghurt and 1 missing fish, which goes to D10 for a decision.
7. **06:52.** VEH007 delivers OUT074 offline (Puttalam). It syncs at 07:48. The store counted 200 against the driver's 205, so the record goes to D13 for reconciliation.
