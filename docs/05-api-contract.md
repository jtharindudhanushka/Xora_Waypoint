# 05 · API contract

- **Base URL:** `/api/v1`. JSON throughout, with times in ISO 8601 and an offset (`+05:30`).
- **The source of truth is the generated OpenAPI** at `/api/v1/openapi.json` (Swagger UI at `/api/docs`). This doc is the plan; the Pydantic schemas are the contract. The frontend client is generated with `npm run gen:api` (openapi-typescript), so hand-written fetch types are not allowed.
- **Auth:** `Authorization: Bearer <jwt>`. A role guard is listed per route.
- **Errors (RFC 7807):**
  ```json
  {"type":"about:blank","title":"Rule violated","status":422,"code":"WEIGHT_CAP","rule_id":"BR-06","detail":"VEH036 trip 1: 1,096 kg exceeds 1,040 kg"}
  ```
- **Pagination:** `?limit=&cursor=` where a list can grow. Not needed for most lists at our scale.

## Auth & clock
| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | `/auth/login` | public | `{email, password}` → `{access_token, user}` |
| GET | `/auth/me` | any | the current user + scope |
| GET | `/clock` | any | `{now, is_demo}` |
| PUT | `/clock` | dispatcher | `{demo_now}`: set or advance demo time (BR-56) |

## Catalog (read-only)
| GET | `/outlets/{code}` · `/vehicles` · `/districts` · `/calendar/{date}` | any (scoped) |
|---|---|---|

## Orders (store)
| Method | Path | Role | Purpose / rules |
|---|---|---|---|
| GET | `/outlets/{code}/usual-items` | store | usual items for S2 |
| POST | `/orders/check` | store | `{lines}` → sanity warnings (BR-42), no write |
| POST | `/orders` | store | place an order; cutoff → `delivery_date` (BR-40); chilled and dry separate (BR-41) |
| GET | `/orders?outlet=&date=` | store, dispatcher | list |
| GET | `/outlets/{code}/next-deliveries` | store | per-order lines with ETA window + status (BR-43) |
| POST | `/outlets/{code}/driver-note` | store | same-day note (BR-39) |

## Fleet
| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/fleet?date=` | dispatcher | vehicles + status + fuel used (Fleet tab) |
| PATCH | `/fleet/{vehicle}/{date}` | dispatcher | `{switched_on, off_reason}` (BR-10) |

## Planning (dispatcher)
| Method | Path | Purpose / rules |
|---|---|---|
| POST | `/plans/{date}/generate` | run the engine on the switched-on fleet; keeps locked trips (BR-20); returns a draft version |
| GET | `/plans/{date}` | latest version: KPIs, bottleneck, lanes, trips, stops (two clocks), deferrals |
| POST | `/plan-versions/{id}/validate-move` | `{order_ref, to_vehicle, to_trip}` → ok or rule violation (BR-19), no write |
| POST | `/plan-versions/{id}/edits` | batch edits; rejected if any rule breaks |
| POST | `/trips/{id}/lock` · DELETE `/trips/{id}/lock` | lock or unlock (BR-20) |
| POST | `/deferrals/{id}/serve-instead` | returns the counterfactual displaced set; applies on confirm |
| POST | `/plan-versions/{id}/deferrals/confirm` | `{items:[{deferral_id, reason?}]}`; repeat skips need a reason (BR-21) |
| GET | `/plan-versions/{id}/publish-check` | the gate checklist (BR-22) |
| POST | `/plan-versions/{id}/publish` | immutable publish → notifications + SSE (BR-23) |

## Loading (loader)
| Method | Path | Purpose |
|---|---|---|
| GET | `/docks/{dock}/trips?date=` | trips in departure order + version (BR-25) |
| GET | `/trips/{id}/load-list` | lines in **reverse stop order** + item counts (BR-24) |
| POST | `/trips/{id}/loaded` | mark loaded |
| (sync) | event `shortfall_reported` | → hold + exception (BR-26, BR-27) |
| POST | `/plan-versions/{id}/ack` | acknowledge; releases a hold if the version resolves it (BR-31) |

## Repair (dispatcher)
| Method | Path | Purpose |
|---|---|---|
| GET | `/shortfalls/{id}/options` | up to 3 options with loss, delay, effects, store-rule check (BR-28, BR-29) |
| POST | `/shortfalls/{id}/apply` | `{option_id}` → publishes v(n+1) (BR-30) |

Repair quotes include the D6 report, standing store rule, windows and A/B/C view models.
Option ids bind the published version and candidate snapshot; an outdated choice returns
`409 STALE_REPAIR_OPTION`. Applying creates new trips/stops and publishes `plan.published`
without changing v1. `StopOrderOut.top_up_of_order_ref` identifies linked portions.
Active holds move to the new trip ids and stay active until loader acknowledgement (BR-31).
Option C creates a next-operating-day order and records its link in the repair audit event.

## Driver
| Method | Path | Purpose |
|---|---|---|
| GET | `/vehicles/{code}/today` | trip(s) for the vehicle, current version, stops, two clocks, store notes, pre-filled shortfall (BR-32 to BR-34, BR-39) |
| (sync) | events `trip_acknowledged`, `arrived`, `outcome_recorded` | see the sync protocol |

## Sync (driver, loader); details in [07](07-offline-sync.md)
| Method | Path | Purpose |
|---|---|---|
| POST | `/sync` | `{device_id, events:[…]}` → `{results:[{event_id, status: accepted, duplicate or conflict, conflict_id?}], server_time}` |
| GET | `/sync/bootstrap` | everything the device needs to work offline today (plan, stops, outlets, notes) |

## Receipts & issues
| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/orders/{ref}/receipt-draft` | store | lines pre-filled with driver counts (BR-46) |
| POST | `/orders/{ref}/receipt` | store | confirm; any difference → issue |
| POST | `/orders/{ref}/issues` | store | per-line problems (BR-47) |
| GET | `/issues?status=open` | dispatcher | D10/D13 queue |
| GET | `/issues/{id}` | dispatcher | side-by-side evidence |
| POST | `/issues/{id}/resolve` | dispatcher | `{resolution, note}` (BR-51, BR-52) |

## Live ops, exceptions & notifications
| Method | Path | Role | Purpose |
|---|---|---|---|
| GET | `/ops/{date}` | dispatcher | KPIs + trips as stop chains (D5) |
| GET | `/exceptions?status=open` | dispatcher | ranked by impact (BR-48) |
| POST | `/exceptions/{id}/apply-fix` | dispatcher | e.g. swap stops |
| GET | `/notifications` · POST `/notifications/{id}/ack` | store | deferral notices (BR-44) |

## Server-Sent Events: `GET /stream`
Filtered per user scope. Each event is `event: <type>` + `data: <json>`.

| Event | Audience |
|---|---|
| `plan.published` | loaders and drivers on affected trips; store (ETA) |
| `hold.created` · `hold.released` | dispatcher · loader |
| `sync.applied` · `conflict.created` | dispatcher |
| `exception.created` · `exception.updated` | dispatcher |
| `notification.created` | store |
| `clock.changed` | all |

## Store implementation (Dev 3, task 3.1)

`GET /stores/me/orders` returns the authenticated outlet, clock-derived ordering
cutoff/date, today/upcoming/recent orders, item lines, driver note and one tracking
entry per order/trip in the latest published version. `GET /orders/{ref}` has the
same order view. Internal draft/placed states use `submission_status`; tracking
uses only BR-54 statuses. Published stops and event rows are read-only.

`POST /orders/check` and `POST /orders` share BR-40/42 guards. Submission accepts
`{request_id, draft_ref?, lines:[{product_id,qty}], confirm_unusual?}`. A questioned
quantity requires explicit confirmation; no write occurs on rejection. Zero/omitted
items remove lines from a saved draft. New app orders split by temperature.
ADR-0008 records the Figma ≥3× boundary and original demo case measurements.
Replay of an identical request id returns the existing orders; another payload
under that id returns 409.

`GET /notifications/{id}?language=en|si|ta` supports the account language and an
explicit reading language. Only deferral reason-code templates are translated;
other existing notices retain their authored text. Both `/read` (task request) and
`/ack` (original contract) acknowledge once and append a separate audit event.

`POST /orders/{ref}/receipt` accepts `{}` for the driver's item counts, or
`{lines:[{order_line_id,store_qty}]}`. Repeating an acceptance is idempotent; changing
an accepted receipt returns 409. Count differences create a `count_conflict` issue,
with both records retained. A receipt with explicit counts can precede offline sync.

`POST /orders/{ref}/issues` accepts `{request_id,lines:[{order_line_id?,product_id?,
problem,qty,photo_url?}]}`. Normal lines identify the order line. An additional
catalogue item identifies `product_id` and `wrong_item`. Good counts are confirmed
and a `store_report` plus item rows/exception are created for D10. Driver evidence
is linked by `driver_event_id`. Optional photo references are accepted; binary
photo upload is outside this contract. Invalid lines create nothing. Request replay
is idempotent; all audit events are append-only.
