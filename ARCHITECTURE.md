# Architecture

026 lifecycle tip (anchor)
→ 033 authority → 025 consumption → external canonical-store revision → 034 receipt
→ 035 lineage entry (this artifact)
→ 036 effective-state resolution (separate release)

One lineage = one lifecycle anchor. Entry N's `from_canonical_state_digest` must equal entry N-1's `to_canonical_state_digest`; entry 0 must begin from the anchored canonical state. Each entry binds the exact 034 receipt digest and 033 authorization digest, both single-use within the lineage.

035 records that canonical truth was legitimately revised. It never claims the lifecycle ledger changed and never carries authority.
