# ADR-0008 · Store quantity boundary and app-order measurements

Status: implemented for the Hackathon demo · 4 October 2026.

Figma S2 (276:3245), its rationale (152:218) and walkthrough step 1 all question 60
cases against a usual 20. BR-42's original `>3×` wording contradicts that boundary.
Use **≥3×** server-side, including at submission; keeping an unusual amount requires
explicit confirmation. This preserves the specification's visible behavior.

The foundation Product table does not store case kg/m³. New app orders use original,
illustrative case measurements in `app/modules/orders/catalogue.py`. These are not
organiser data or derivatives. Chilled and ambient lines become separate orders.
Unknown products without configured measurements fail safely before any write.

A seeded draft retains its authoritative aggregate measurements when submitted with
its original case total (S1-001 corrected to 80). A different total scales its existing
per-case kg/m³ proportionally; it never gains or loses capacity by changing only cases.
This is an order-level demo estimate, not a claim of an item-specific warehouse
measurement. A production catalogue needs actual measurements and a migrated model.
No migration or dataset modification is needed for this demo decision.
