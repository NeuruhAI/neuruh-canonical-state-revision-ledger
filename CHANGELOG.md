# Changelog

## 0.1.0a0 — v0.1.0-alpha

Initial public release of Public Commons Release 035.

- Append-only, hash-chained canonical-state revision lineage anchored to exactly one Release 026 lifecycle entry.
- Single-consumption enforcement for Release 034 receipts and their bound Release 033 authorizations.
- State-only by construction: a lifecycle-stage change is unrepresentable as a revision entry.
- Stale anchors, broken chains, tampered entries, failed receipts, and duplicate consumption all fail closed.
- Every authority flag is hard-coded false.
- Published entry schema, CLI (`validate`, `digest`, `tip`, `inspect`), and synthetic examples.
- Apache-2.0 with the complete license text and a `NOTICE` carrying the copyright.
- Continuous integration on Python 3.11, 3.12, and 3.13.
