# 13 · Figma screen map (the UI spec)

**Rule: every screen must match its Figma frame exactly.** That covers layout, copy (word for word), spacing, typography, colour tokens, states and interactions. The submitted Figma file **is** the spec, and judges score fidelity to it (10%). If something can't be built as designed, log it under *Departures* in [02-business-rules.md](02-business-rules.md#departures-from-the-submitted-design) before building something different.

**File:** `G2O2aShpb6GCFNgBiftFFj` · base URL `https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=`. Append the node id with `:` replaced by `-` (e.g. `196:383` → `?node-id=196-383`).

## Dispatcher (desktop 1440, page "Hi-fi · Dispatcher" `141:205`)
| Screen | Frame | Node | Link | Route |
|---|---|---|---|---|
| D1 Plan workspace · Timeline + trip panel (D2) | `D1 · Plan workspace` | `196:383` | [open](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=196-383) | `/dispatch/plan` |
| D3 Deferred tab | `D1 · Deferred tab (D3)` | `197:440` | [open](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=197-440) | `/dispatch/plan?tab=deferred` |
| Fleet tab | `D1 · Fleet tab` | `198:274` | [open](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=198-274) | `/dispatch/plan?tab=fleet` |
| Edit trips (state) | `D1 · Edit trips` | `205:342` | [open](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=205-342) | `/dispatch/plan?edit=1` |
| D4 Publish dialog | `D1 · Publish dialog (D4)` | `197:682` | [open](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=197-682) | modal on D1 |
| D5 Live operations | `D5 · Live operations` | `157:322` | [open](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=157-322) | `/dispatch/ops` |
| D6 ⭐ Resolve shortfall | `D6 · Resolve shortfall before departure` | `156:283` | [open](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=156-283) | `/dispatch/shortfalls/:id` |
| D10 Review store report | `D10 · Review store report` | `250:409` | [open](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=250-409) | `/dispatch/issues/:id` |
| D13 ⭐ Reconcile offline record | `D13 · Reconcile offline record` | `201:307` | [open](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=201-307) | `/dispatch/issues/:id` |

## Loader (phone 390 + dock tablet 1194×834, page "Hi-fi · Loader" `141:206`)
| Screen | Phone node | Tablet node | Route |
|---|---|---|---|
| L1 Today's loading trips | [`150:2`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=150-2) | [`203:106`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=203-106) (L1+L2 split) | `/dock` |
| L2 Load trip | [`150:89`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=150-89) | (in `203:106`) | `/dock/trips/:id` |
| L3 ⭐ Report shortfall | [`151:60`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=151-60) | [`207:114`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=207-114) | sheet on L2 |
| L4 ⭐ Departure on hold | [`151:134`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=151-134) | [`209:125`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=209-125) | state of L2 |
| L5 Review revised load | [`200:91`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=200-91) | [`209:284`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=209-284) | state of L2 |

## Driver (phone 390, page "Hi-fi · Driver" `72:74`)
| Screen | Node | Route |
|---|---|---|
| R1 Today's trip | [`142:2`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=142-2) | `/driver` |
| R2 Stop detail | [`143:73`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=143-73) | `/driver/stops/:id` |
| R3 Record outcome | [`143:176`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=143-176) | `/driver/stops/:id/outcome` |
| R4 ⭐ Saved on this device | [`145:172`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=145-172) | `/driver/uploads` |
| R5 Record uploaded | [`145:259`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=145-259) | `/driver/uploads` |
| R7 ⭐ Needs review | [`145:348`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=145-348) | `/driver/uploads` |

## Store manager (phone 390, page "Hi-fi · Store" `141:207`)
| Screen | Node | Route |
|---|---|---|
| X1 Sign in (all roles) | [`158:476`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=158-476) | `/login` ✅ built |
| S1 Home + tracking | [`152:2`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=152-2) | `/store` |
| S2 New order (final, with item removal) | [`276:3245`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=276-3245) | `/store/orders/new` |
| S5 Confirm receipt | [`153:138`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=153-138) | `/store/orders/:ref/receipt` |
| S6 Report a problem | [`204:110`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=204-110) | `/store/orders/:ref/issue` |
| S8 ⭐ Delivery deferred | [`153:52`](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode?node-id=153-52) | `/store/notices/:id` |

## Other references
| What | Node |
|---|---|
| Design System page (tokens, type, components = style guide) | `68:173` |
| Prototype · all roles (flows: full story, dispatcher, loader tablet, driver, store) | `219:2` |
| Item Removal Variant prototype (final S2 flow) | `284:2` |
| Problem framing · Flow map · Core trade-off | `0:1` · `162:2` · `163:2` |

Each hi-fi frame has a **rationale text** under it in Figma. Read it before building: it explains *why* the screen works the way it does, and those reasons are the business rules (see [02](02-business-rules.md)).

## Fidelity checklist (per screen, before opening the PR)
- [ ] Copy is identical to the frame (titles, labels, button text, helper text).
- [ ] Layout and order of sections match, at the frame's size (390 phone · 1194 tablet · 1440 desktop).
- [ ] Only design tokens are used (`src/styles/tokens.css` / Tailwind theme); no raw hex.
- [ ] Type styles match (IBM Plex Sans/Mono, sizes from [08](08-frontend.md#design-tokens-from-figma-the-source-is-the-xora--variable-collections)).
- [ ] Status chips use `StatusBadge` and the shared vocabulary (BR-54).
- [ ] Every state shown in Figma exists (e.g. L4 is a state of L3), plus loading, empty and error.
- [ ] A side-by-side screenshot (Figma frame vs app at the same size) is attached to the PR.
- [ ] Data comes from the API (seeded S1), not hard-coded. Only clearly illustrative numbers in Figma may differ.
