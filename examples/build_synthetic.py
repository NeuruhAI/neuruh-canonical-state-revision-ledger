"""Build the synthetic example lineage. Synthetic fixtures only."""
from pathlib import Path
from neuruh_canonical_state_revision_ledger import (
    CanonicalRevisionLedger, append_revision, sha256_ref,
)

H = sha256_ref
ANCHOR = H("synthetic-lifecycle-entry-A")

ledger = append_revision(
    CanonicalRevisionLedger(),
    revision_id="synthetic-rev-1",
    target_id="synthetic-target",
    lifecycle_anchor_digest=ANCHOR,
    anchor_stage="pilot",
    anchor_state_digest=H("synthetic-canonical-0"),
    revision_authorization_digest=H("synthetic-authorization-1"),
    revision_receipt_digest=H("synthetic-receipt-1"),
    receipt_status="succeeded",
    receipt_revision_mode="adopt_observed",
    receipt_previous_lifecycle_entry_digest=ANCHOR,
    receipt_pre_canonical_stage="pilot",
    receipt_pre_canonical_state_digest=H("synthetic-canonical-0"),
    receipt_target_canonical_stage="pilot",
    receipt_target_canonical_state_digest=H("synthetic-canonical-1"),
    receipt_post_canonical_stage="pilot",
    receipt_post_canonical_state_digest=H("synthetic-canonical-1"),
    recorded_at="2026-08-10T12:00:00Z",
)

Path(__file__).with_name("lineage.synthetic.jsonl").write_text(ledger.to_jsonl())
print(ledger.digest())
