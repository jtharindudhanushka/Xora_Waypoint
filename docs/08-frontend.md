# 08 · Frontend (`apps/web`)

React 18 + TypeScript (strict) + Vite, built as a PWA (vite-plugin-pwa / Workbox). **One app, four role areas.** After login, users are routed by role (X1). **Fidelity to Figma is scored (10%)**, so match the frames in the [Figma file](https://www.figma.com/design/G2O2aShpb6GCFNgBiftFFj/Xora-Rootcode). Each screen's Figma page and frame is listed below.

## Libraries
| Need | Choice |
|---|---|
| Routing | React Router 6 (data routers) |
| Server state | TanStack Query (with persist for offline reads) |
| API client | `openapi-typescript` + `openapi-fetch` (generated from `/api/v1/openapi.json`) |
| Offline store | Dexie (IndexedDB): outbox + cached plan |
| Styling | Tailwind CSS with the Figma tokens as CSS variables (below); no ad-hoc hex values |
| Drag and drop (D1 Edit) | dnd-kit |
| Forms | React Hook Form + Zod |
| i18n (S8 notice) | simple message catalogue `si` / `ta` / `en` |
| Tests | Vitest + Testing Library (units), Playwright (e2e) |

## Routes → screens
| Route | Screen | Figma page | Primary device |
|---|---|---|---|
| `/login` | X1 Sign in | Hi-fi · Store (X1) | all |
| `/dispatch/plan/:date` | D1 Plan workspace (tabs: Timeline · Deferred · Fleet · Orders; Edit mode; Publish dialog) | Hi-fi · Dispatcher | desktop ≥1280 |
| `/dispatch/ops/:date` | D5 Live operations | Hi-fi · Dispatcher | desktop |
| `/dispatch/shortfalls/:id` | D6 Resolve shortfall | Hi-fi · Dispatcher | desktop |
| `/dispatch/issues/:id` | D10 Review store report · D13 Reconcile (by issue kind) | Hi-fi · Dispatcher | desktop |
| `/dock` | L1 Today's loading trips (tablet: L1+L2 split view) | Hi-fi · Loader | phone 390 · tablet 1194×834 |
| `/dock/trips/:id` | L2 Load trip · L3 Report (sheet) · L4 On hold (state) · L5 Review v2 (state) | Hi-fi · Loader | phone · tablet |
| `/driver` | R1 Today's trip | Hi-fi · Driver | phone 390 |
| `/driver/stops/:id` | R2 Stop detail · R3 Record outcome | Hi-fi · Driver | phone |
| `/driver/uploads` | R4 Saved / R5 Uploaded / R7 Needs review | Hi-fi · Driver | phone |
| `/store` | S1 Home + tracking | Hi-fi · Store | phone · desktop |
| `/store/orders/new` | S2 New order | Hi-fi · Store | phone |
| `/store/orders/:ref/receipt` | S5 Confirm receipt → S6 Report a problem | Hi-fi · Store | phone |
| `/store/notices/:id` | S8 Delivery deferred | Hi-fi · Store | phone |

The global header (desktop) has the depot, the **demo clock** (dispatcher can advance it) and the user. Phone screens have a bottom nav per role (Driver: Trip · Uploads · Dispatch · Me; Store: Home · Orders · Issues · Account).

## Design tokens (from Figma; the source is the `Xora /` variable collections)
```css
:root {
  /* colour — semantic (Light) */
  --bg-canvas:#F7F7F6; --bg-surface:#FFFFFF; --bg-surface-sunken:#EFEFED; --bg-inverse:#1A1A1A;
  --bg-brand:#F26A21; --bg-brand-hover:#FF7F3F; --bg-brand-subtle:#FFF4ED; --bg-disabled:#E2E2DF;
  --text-primary:#1A1A1A; --text-secondary:#5A5A57; --text-tertiary:#7A7A76; --text-inverse:#FFFFFF;
  --text-on-brand:#1A1A1A; --text-brand:#B3410C; --text-disabled:#A3A39F; --text-on-danger:#FFFFFF;
  --border-default:#E2E2DF; --border-strong:#C9C9C5; --border-focus:#F26A21;
  --success-bg:#DDF3E6; --success-fg:#12673D; --warning-bg:#FDF0C4; --warning-fg:#7A5600;
  --danger-bg:#FCE2E4; --danger-fg:#A31D30; --danger-solid:#A31D30;
  --info-bg:#E0E9FD; --info-fg:#1D47AE; --neutral-bg:#EFEFED; --neutral-fg:#3D3D3B;
  /* spacing */ --space-2xs:2px; --space-xs:4px; --space-sm:8px; --space-md:12px; --space-lg:16px; --space-xl:20px; --space-2xl:24px; --space-3xl:32px; --space-4xl:40px; --space-5xl:48px;
  /* radius  */ --radius-sm:4px; --radius-md:6px; --radius-lg:8px; --radius-xl:12px; --radius-full:999px;
}
/* Dark mode (pre-dawn driver runs) mirrors the Figma "Dark" mode values. */
```
**Typography** (self-host the fonts for offline):

| Style | Font, size/line height |
|---|---|
| Display | IBM Plex Sans SemiBold 40/46 |
| H1 | IBM Plex Sans SemiBold 28/34 |
| H2 | IBM Plex Sans SemiBold 22/28 |
| H3 | IBM Plex Sans SemiBold 18/24 |
| Body L | IBM Plex Sans Regular 16/24 |
| Body | IBM Plex Sans Regular 14/20 |
| Body S | IBM Plex Sans Regular 12/16 |
| Label L / Label / Label S | IBM Plex Sans SemiBold 16/20 · 14/18 · 12/16 |
| Caption | IBM Plex Sans SemiBold 11/14 |
| Mono S / Mono / Mono L | IBM Plex Mono Medium 11/14 · 13/18 · 20/24 (IDs, times, quantities) |

**Visual direction (from the AI disclosure page):** an industrial, run-sheet look. Rows, not cards. **Orange only when something needs attention.**

## Rules for UI code
- **Never re-implement business rules.** Call `validate-move`, `publish-check`, `orders/check`. The UI only displays results.
- Status always shows **text + colour** (BR-54).
- Touch targets ≥ 48 px; primary field actions 56 px.
- Every screen handles **loading, empty, error and offline** states.
- Times come from the API (already the demo clock). Format as `HH:mm` in Asia/Colombo.
- Folder layout: `src/features/<role>/<screen>/` with components, hooks and a test. Shared UI lives in `src/ui/`, and the generated API in `src/api/`.
