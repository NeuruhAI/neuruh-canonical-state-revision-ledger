# Neuruh Canonical State Revision Ledger

Public Commons Release 035.

An append-only, hash-chained memory of canonical-state revisions. Each revision lineage is anchored to exactly one Release 026 lifecycle entry (the lifecycle tip current when revision authority was granted) and consumes exactly one successful Release 034 canonical-state revision receipt per entry.

## 035 is memory, not power

035 hard-codes:
- `lifecycle_ledger_mutated=false`
- `lifecycle_transition_authority=false`
- `canonical_state_revision_authority=false`
- `canonical_state_authority=false`
- `execution_authority=false`
- `deployment_authority=false`
- `reconciliation_authority=false`
- `mutation_authority=false`

Recording a revision grants nothing. The lineage remembers which exact canonical-state revisions legitimately happened, in which order, under which anchor.

## Semantics

- **One lifecycle anchor per lineage.** `lifecycle_anchor_digest`, `anchor_stage`, and `anchor_state_digest` are constant across all entries of a lineage.
- **Chain.** Entries are hash-chained (`previous_entry_hash`), contiguous from sequence 0, tamper-evident (`entry_hash` over the canonical body).
- **Threading.** Entry 0 begins from the anchored canonical state; every later entry begins from the previous entry's `to_canonical_state_digest`.
- **Consumption.** A Release 034 receipt digest may appear in a lineage at most once; the bound Release 033 authorization digest likewise. A failed receipt cannot advance the lineage.
- **State-only by construction.** Entries carry a single `anchor_stage`. A lifecycle-stage change is unrepresentable as a revision entry; the append API rejects any receipt whose pre/target/post stage differs from the anchor stage.
- **Stale anchors are explicit.** Appending a receipt anchored to a different lifecycle entry than the lineage anchor fails closed.

## What 035 does not do

It does not mutate the Release 026 lifecycle ledger, does not grant or retire authority, does not execute, deploy, or reconcile anything, and does not decide effective canonical truth — that projection is Release 036.
