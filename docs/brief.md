# Hackathon brief (restated from the Challenge Booklet)

**Due Sun 2026-10-04 23:59 Sri Lanka time (UTC+05:30).** Code pushed after the deadline is not considered.
Form: https://forms.gle/WurHAKjbq2XEZQhbA

## Requirements
- **A responsive web application** that lets a judge complete the delivery workflow across **all four roles**, from planning through loading and delivery to receipt at the outlet. **The driver and loader experiences are judged on phone-sized screens.** Native apps are optional.
- **Respect the operating constraints:** capacity (weight **and** volume), temperature, outlet access, delivery windows and fuel quotas.
- **Planning and allocation:** assign orders to vehicles and trips; handle a day when demand exceeds capacity. Automatic, assisted or manual with validation, but it must produce an allocation that respects the constraints and **identifies deferred orders**.
- **Judge walkthrough:** a numbered walkthrough in the README across all four roles, from planning to completed delivery. Seed with the **shared datasets** plus at least one realistic delivery day, so it works on a fresh install.

## Deliverables
- **Deployed system:** a public URL plus credentials for **4 seeded accounts**, one per role. Keep it live through review, the semifinal and the Grand Finale.
- **GitHub monorepo `TeamName_SolutionName`** (ours: `Xora_Waypoint`) containing:
  - a README covering setup and configuration, seeded accounts, the judge walkthrough, and **significant departures from the Designathon submission**;
  - **`docker-compose.yml` and `.env.example` at the root**, where **`docker compose up` starts the complete stack, including the database and seed data**;
  - **`docs/`** with an **architecture diagram** and a **data model**;
  - an **AI tool disclosure** in `docs/`.
- **Demo video:** 5–8 min, unlisted YouTube. All four roles complete the walkthrough, then a brief explanation of the code and architecture.

## Judging
| Criterion | Weight |
|---|---|
| Engineering quality and architecture | **25%** |
| Functional completeness across all four roles | 20% |
| Planning and allocation engine | 20% |
| Degradation, offline operation and recovery | 10% |
| Fidelity to the Day 5 design | 10% |
| Demo video | 10% |
| Creativity | 5% |

## Operating constraints (from the booklet)
- **Vehicles:**
  - every vehicle has a weight **and** a volume limit per trip;
  - only reefers carry chilled goods (reefers may also carry ambient);
  - each vehicle has a **weekly fuel quota**, consumed by route distance;
  - **up to 2 routes per day**;
  - operations run **Monday to Saturday**;
  - drivers are not a separate constraint.
- **Outlets:**
  - every outlet has a delivery window;
  - Fresh arrives before 8 AM;
  - mall outlets accept deliveries only inside the mall window;
  - `van_only` outlets can't be served by trucks;
  - dock types are rear dock, street and mall bay.
- **Orders** for the next day close at **16:00**. Late orders wait for the following run.
- **When demand exceeds capacity**, the dispatcher decides which orders move and **records the reason**.
- **Connectivity** drops in the hill country, the Kandy corridor and rural districts. Work away from the depot must stay usable offline and reconcile when the connection returns.

## Data usage terms
The datasets may be used **only** for this competition. They must **not be shared, distributed or published, nor any derivatives**. Violations mean disqualification. That's why `datasets/` is gitignored and supplied locally (see [09-seed-and-demo.md](09-seed-and-demo.md)).
