# AI tool disclosure (Hackathon)

The brief requires us to explain which work was AI-assisted, which wasn't, and how we used the tools. **Log entries as you go**, then the final version is written from this log before submission.

| Date | Area | Tool | What the AI did | What we did |
|---|---|---|---|---|
| 2026-10-04 | Docs / architecture | Claude Code (Anthropic), with the Figma connector | Read the submitted Figma file and video transcript; extracted business rules; drafted the architecture, data model, API contract, engine spec, ADRs and work breakdown | Chose the stack and architecture after comparing options; set scope and team split; reviewed and approved every doc |

| 2026-10-04 | Local workspace setup | Codex (OpenAI) | Read repository instructions and core docs; downloaded the project; copied the organiser pack from waypoint into gitignored datasets/ and verified file hashes and required paths | Requested setup; next implementation scope pending |

## Dev 2 implementation log (4 Oct 2026)

| Date | Area | Tool | What the AI did | What we did |
|---|---|---|---|---|
| 2026-10-04 | Dev 2 engine, tasks 2.1–2.2 | Codex (OpenAI) | Implemented pure dataclasses, shared BR-01–12 predicates, validation, time examples, greedy planning, explanations, KPIs and Task 2B export; added unit/property tests and ran the local S1 checker | Set business rules, weights, library constraints and acceptance criteria; lead reviews and merges PRs #11–12 |
| 2026-10-04 | Dev 2 planning API, task 2.3 | Codex (OpenAI) | Reused database models, Clock, role dependencies and errors; added adapters, generate/publish gates, immutable snapshots, fleet switches, scoped SSE, synthetic tests and generated contracts | Specified the API and M1 milestone; lead reviews PR #13 and integrates field applications |
| 2026-10-04 | Dev 2 dispatcher UI, task 2.4 | Codex (OpenAI), Figma connector | Read the exact frames/rationales; built D1, Deferred, Fleet and Publish using existing tokens/primitives; added serve-instead and locks; compared browser captures with Figma | Approved disabled editing/Orders controls, actual windows instead of probability, and English-only notices; lead reviews PR #14 |
| 2026-10-04 | Dev 2 shortfall repair, task 2.5 | Codex (OpenAI), Figma connector | Built A/B/C repairs with shared rules and case conservation, stale quotes, linked top-ups/next-run orders, v2 publication and D6; tested real S1 repair plus synthetic API/browser flows | Approved the disabled dock-call control and existing probability departure; lead reviews PR #15 and connects loader acknowledgement |
| 2026-10-04 | Dev 2 handover | Codex (OpenAI) | Recorded task status, PR merge order, verified checks, S1 results, integration gaps, departures and local verification commands | Requested the report and final documentation PR; retains merge and submission decisions |

## Not AI-assisted
- _To be completed by the team (e.g. the original wireframes and flows from the Designathon, decisions made in review)._

## Rules we keep
- No competition data was published. The AI read the dataset locally for analysis only.
- Numbers shown in the product are computed by our engine from the data, not invented.

## Dev 3 implementation log (4 Oct 2026)

| Date | Area | Tool | What the AI did | What we did |
|---|---|---|---|---|
| 2026-10-04 | Store API, task 3.1 | Codex (OpenAI), Figma connector | Read Store frames/rationales and repository contracts; implemented scoped draft submission, cutoff/calendar checks, quantity confirmation, read-only tracking, notice acknowledgement, separate receipts and per-line reports; added synthetic regression tests | Assigned Dev 3 the Store track; retains specification decisions, PR review and merge authority |
| 2026-10-04 | Store rules/fixtures | Codex (OpenAI) | Reconciled the exact Figma 3× boundary in BR-42 and ADR-0008; added original demo case measurements, separate temperature orders, driver evidence links, wrong-item rows and scoped multilingual notice reads | Specified Figma as authoritative and retained lead review of demo estimates and translated copy |
| 2026-10-04 | Store receipt preview | Codex (OpenAI) | Added a shared server-side report preview and a regression for shortages already excluded by driver counts; exposed receipt timestamps for the Figma recent-delivery copy | Retained lead PR review and merge authority |
