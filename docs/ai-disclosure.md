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

## Dev 2 second assignment log (4 Oct 2026)

| Date | Area | Tool | What the AI did | What we did |
|---|---|---|---|---|
| 2026-10-04 | Bounded optimiser, task 2.6 | Codex (OpenAI) | Built CP-SAT compatible assignment/capacity/time/fuel/lock constraints, greedy hints and validated fallback; added synthetic/property tests; checked local S1 and dependency/image installation | Set solver budget, acceptance criteria and priority; lead reviews #17; prototype quality remains a documented gap |
| 2026-10-04 | Live operations, task 2.7 | Codex (OpenAI), Figma connector | Read D5 and its rationale; implemented depot-scoped views, impact ranking, pending sync, notices, safe stop swaps, immutable publication, tests and comparison | Assigned track boundaries; lead creates field events and reviews #18 |
| 2026-10-04 | Issues, task 2.8 | Codex (OpenAI), Figma connector | Implemented D10/D13 evidence and decisions, next-run redelivery, short claims, notifications/SSE and synthetic tests; compared both screens | Approved accurate loading-team notification wording; lead owns issue creation, loading pick-note display and review of #21 |
| 2026-10-04 | Fidelity and integration, task 2.9 | Codex (OpenAI), Figma connector | Reviewed eight frames; corrected planning geometry/type/tokens and refreshed comparisons; regenerated merged sync contracts and froze a flaky repair timer fixture | Authorized completion of in-progress work at freeze; lead reviews #25 and final deployed walkthrough |
| 2026-10-04 | Second handover | Codex (OpenAI) | Recorded merge order, statuses, measured S1 results, limitations, departures, integration risks and exact verification commands | Requested the report; retains merge, deployment and submission decisions |
| 2026-10-04 | Cross-track contract integration | Codex (OpenAI) | Merged latest main into remaining PR branches, retained all routers, regenerated contracts and fixed the dispatcher IssueOut type collision using its endpoint response; ran combined API and web checks | Explicitly requested merge commits, regenerated contracts and checked pushes; lead retains PR merge decisions |
| 2026-10-04 | Shortfall demo and deferral fixes | Codex (OpenAI) | Verified S1 shortfall/repair/ack flow for greedy and Trip 2 shapes, corrected deferral timezone dates and repicked driver projection, and added synthetic regressions | Kept the deployed solver configuration unchanged as requested; retained lead review, merge and deployment authority |
| 2026-10-04 | Merged architecture and video segment | Codex (OpenAI) | Checked registered routers, ORM keys, integrity triggers, outbox, scoped SSE and Compose deployment; corrected architecture/data diagrams and drafted the code segment script | Requested documentation to match merged code, retained lead review and narration |

## Lead implementation log (4 Oct 2026)

| Date | Area | Tool | What the AI did | What we did |
|---|---|---|---|---|
| 2026-10-04 | Azure deployment, task 1.1 | Claude Code (Anthropic) | Created the Azure for Students VM (B1ms + swap), firewall rules and Docker; ran the first real `docker compose up` (prod overlay + Caddy); fixed the `CORS_ORIGINS` env parsing crash and the web healthcheck; verified a fresh-clone `cp .env.example .env && docker compose up` with seed data | Chose the VM size and cost limits, signed in to Azure, copied the dataset to the VM with scp, approved every firewall change |
| 2026-10-04 | Sync API, task 1.2 | Claude Code (Anthropic) | Implemented `POST /sync` (idempotent by event id, commit per event, stale-plan and count conflicts that open `issues` rows), shortfall → hold, loader acknowledgement → hold release, `GET /sync/bootstrap` and `GET /vehicles/{code}/today`; wrote synthetic tests | Specified the protocol (docs/07) and the business rules; reviewed the PR and the API contract change (`rejected` status) |
| 2026-10-04 | Driver UI, task 1.3 | Claude Code (Anthropic), Figma connector | Read the R1–R7 frames and rationales; built the Dexie outbox, ordered sync loop, sync bar and the R1, R2, R3, R4/R5 and R7 screens with existing tokens and exported Figma icons | Set scope and cut order; reviewed the screens against Figma |
| 2026-10-04 | Integration, smoke and fixes | Claude Code (Anthropic) | Merged teammates' PRs on request; ran the walkthrough on a local seeded stack and on the live URL; fixed the walkthrough blockers it found (later trips unreachable, per-user outbox, receipt pre-fill field) | Signed in to every live account by hand (the agent never entered live credentials); decided what to cut and what counts as a blocker |
| 2026-10-04 | Submission docs | Claude Code (Anthropic) | Drafted the README (setup, accounts, walkthrough from the QA results, departures, known gaps) and this log | Reviewed and approved the final text |

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
| 2026-10-04 | Store UI, task 3.2 | Codex (OpenAI), Figma connector, Playwright | Implemented five Store screens using exported SVG assets, shared tokens and generated API types; compared 390 × 844 screenshots and exercised original synthetic flows, retries and offline states | Retained decisions on dispatch calling and photo uploads, native-language review and PR merge authority |
| 2026-10-04 | Live walkthrough smoke, task 3.3 | Codex (OpenAI), Playwright | Authored a separate live UI/API smoke suite, verified discovery of seven checks, and documented staged receipt coverage and Docker execution | Retained live Docker verification and CI-enablement decisions; no live walkthrough completion claimed |
| 2026-10-04 | Live walkthrough QA + demo footage | Claude Code (Anthropic), Playwright, ffmpeg | Ran the docs/09 walkthrough against the live deployment on human-captured sessions (no passwords handled by the tool); fixed test selectors/flows to match the app, added steps 6–14 with loader API stand-ins, filed bug lists, wrote walkthrough-results.md, recorded and stitched footage | Signed in all demo accounts by hand, approved the live target, triaged bugs to owners and records the voice-over |
| 2026-10-04 | Loader dock API and phone UI | Codex, Figma connector | Read L1–L5 frames and rationales; implemented depot-scoped load views and offline loader interactions; verified synthetic rules and local shortfall flow | Assigned loader scope, retained lead review and merge authority |
