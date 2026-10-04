# ADR-0009 · Repeatable bounded planning search

**Status:** Accepted for the hackathon demo.

**Context:** Wall-clock parallel search returned different allocations for the same
input, so the loading and shortfall walkthrough could refer to the wrong trip.

**Decision:** Canonicalize order, vehicle and lock ordering before planning. Use
OR-Tools' deterministic interleaved search with seed 0, eight workers and batches
of 16. Cap deterministic work for both neighbourhood and full searches, alongside
the existing shared ten-second wall-clock safety cap. A wall-clock interruption
before the deterministic budget completes returns the validated greedy baseline.
Validation, sequencing, explanations and honest solver statuses remain shared.

**Consequences:** Completed searches are repeatable for identical inputs and the
same pinned solver version. A slow deployment can still return GREEDY; the UI and
demo must inspect the published plan instead of assuming an order's trip number.
This bounded search favours repeatability over the best incumbent obtainable from
unrestricted parallel timing. No dataset-specific assignments are hard-coded.
