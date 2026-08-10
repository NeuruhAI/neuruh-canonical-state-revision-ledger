import unittest
from neuruh_canonical_state_revision_ledger import *

H = sha256_ref
ANCHOR = H("lifecycle-entry-A")
S0 = H("canonical-state-0")
S1 = H("canonical-state-1")
S2 = H("canonical-state-2")

def kw(**over):
    d = dict(
        revision_id="rev-1",
        target_id="t1",
        lifecycle_anchor_digest=ANCHOR,
        anchor_stage="pilot",
        anchor_state_digest=S0,
        revision_authorization_digest=H("auth-1"),
        revision_receipt_digest=H("receipt-1"),
        receipt_status="succeeded",
        receipt_revision_mode="adopt_observed",
        receipt_previous_lifecycle_entry_digest=ANCHOR,
        receipt_pre_canonical_stage="pilot",
        receipt_pre_canonical_state_digest=S0,
        receipt_target_canonical_stage="pilot",
        receipt_target_canonical_state_digest=S1,
        receipt_post_canonical_stage="pilot",
        receipt_post_canonical_state_digest=S1,
        recorded_at="2026-08-10T12:00:00Z",
    )
    d.update(over)
    return d

def one() -> CanonicalRevisionLedger:
    return append_revision(CanonicalRevisionLedger(), **kw())

def two() -> CanonicalRevisionLedger:
    return append_revision(one(), **kw(
        revision_id="rev-2",
        revision_authorization_digest=H("auth-2"),
        revision_receipt_digest=H("receipt-2"),
        receipt_pre_canonical_state_digest=S1,
        receipt_target_canonical_state_digest=S2,
        receipt_post_canonical_state_digest=S2,
        recorded_at="2026-08-10T12:05:00Z",
    ))

class T(unittest.TestCase):
    def bad(self, fn):
        with self.assertRaises(CanonicalRevisionLedgerError):
            fn()

    # -- positive lineage semantics
    def test_single_revision(self):
        l = one()
        self.assertEqual(l.effective_state_digest, S1)
        self.assertEqual(l.anchor_stage, "pilot")
        self.assertEqual(l.lifecycle_anchor_digest, ANCHOR)

    def test_two_revisions_thread(self):
        l = two()
        self.assertEqual(l.effective_state_digest, S2)
        self.assertEqual(l.entries[1].from_canonical_state_digest, S1)
        self.assertEqual(l.entries[1].previous_entry_hash, l.entries[0].entry_hash)

    def test_jsonl_roundtrip_deterministic(self):
        l = two()
        r = CanonicalRevisionLedger.from_jsonl(l.to_jsonl())
        self.assertEqual(r.digest(), l.digest())
        self.assertEqual(r.tip, l.tip)

    def test_replay_same_inputs_same_hash(self):
        self.assertEqual(one().tip, one().tip)
        self.assertEqual(one().digest(), one().digest())

    def test_verify_ledger_expected_tip(self):
        l = two()
        verify_ledger(l.entries, expected_tip=l.tip)
        self.bad(lambda: verify_ledger(l.entries, expected_tip="0" * 64))

    def test_revert_to_prior_state_allowed(self):
        l = append_revision(two(), **kw(
            revision_id="rev-3",
            revision_authorization_digest=H("auth-3"),
            revision_receipt_digest=H("receipt-3"),
            receipt_pre_canonical_state_digest=S2,
            receipt_target_canonical_state_digest=S0,
            receipt_post_canonical_state_digest=S0,
            recorded_at="2026-08-10T12:09:00Z",
        ))
        self.assertEqual(l.effective_state_digest, S0)

    # -- memory, not power
    def test_no_authority_flags(self):
        e = one().entries[0]
        self.assertFalse(e.lifecycle_ledger_mutated)
        self.assertFalse(e.lifecycle_transition_authority)
        self.assertFalse(e.canonical_state_revision_authority)
        self.assertFalse(e.canonical_state_authority)
        self.assertFalse(e.execution_authority)
        self.assertFalse(e.deployment_authority)
        self.assertFalse(e.reconciliation_authority)
        self.assertFalse(e.mutation_authority)

    def test_authority_claim_rejected(self):
        x = one().entries[0].to_dict()
        x["mutation_authority"] = True
        self.bad(lambda: CanonicalRevisionEntry.from_mapping(x))

    def test_lifecycle_mutation_claim_rejected(self):
        x = one().entries[0].to_dict()
        x["lifecycle_ledger_mutated"] = True
        self.bad(lambda: CanonicalRevisionEntry.from_mapping(x))

    def test_lifecycle_transition_authority_claim_rejected(self):
        x = one().entries[0].to_dict()
        x["lifecycle_transition_authority"] = True
        self.bad(lambda: CanonicalRevisionEntry.from_mapping(x))

    # -- required negative: duplicate receipt
    def test_duplicate_receipt_rejected(self):
        self.bad(lambda: append_revision(one(), **kw(
            revision_id="rev-2",
            revision_authorization_digest=H("auth-2"),
            receipt_pre_canonical_state_digest=S1,
            receipt_target_canonical_state_digest=S2,
            receipt_post_canonical_state_digest=S2,
            recorded_at="2026-08-10T12:05:00Z",
        )))

    def test_duplicate_authorization_rejected(self):
        self.bad(lambda: append_revision(one(), **kw(
            revision_id="rev-2",
            revision_receipt_digest=H("receipt-2"),
            receipt_pre_canonical_state_digest=S1,
            receipt_target_canonical_state_digest=S2,
            receipt_post_canonical_state_digest=S2,
            recorded_at="2026-08-10T12:05:00Z",
        )))

    # -- required negative: replayed append
    def test_replayed_append_rejected(self):
        self.bad(lambda: append_revision(one(), **kw()))

    # -- required negative: altered previous hash
    def test_altered_previous_hash_rejected(self):
        l = two()
        rows = [e.to_dict() for e in l.entries]
        rows[1]["previous_entry_hash"] = "0" * 64
        text = "\n".join(canonical_json(r) for r in rows)
        self.bad(lambda: CanonicalRevisionLedger.from_jsonl(text))

    # -- required negative: altered anchor
    def test_altered_anchor_rejected(self):
        l = one()
        x = l.entries[0].to_dict()
        x["lifecycle_anchor_digest"] = H("lifecycle-entry-FORGED")
        self.bad(lambda: CanonicalRevisionEntry.from_mapping(x))

    def test_second_entry_different_anchor_rejected(self):
        self.bad(lambda: append_revision(one(), **kw(
            revision_id="rev-2",
            revision_authorization_digest=H("auth-2"),
            revision_receipt_digest=H("receipt-2"),
            lifecycle_anchor_digest=H("lifecycle-entry-B"),
            receipt_previous_lifecycle_entry_digest=H("lifecycle-entry-B"),
            receipt_pre_canonical_state_digest=S1,
            receipt_target_canonical_state_digest=S2,
            receipt_post_canonical_state_digest=S2,
            recorded_at="2026-08-10T12:05:00Z",
        )))

    # -- required negative: wrong predecessor
    def test_wrong_predecessor_rejected(self):
        self.bad(lambda: append_revision(one(), **kw(
            revision_id="rev-2",
            revision_authorization_digest=H("auth-2"),
            revision_receipt_digest=H("receipt-2"),
            receipt_pre_canonical_state_digest=S0,
            receipt_target_canonical_state_digest=S2,
            receipt_post_canonical_state_digest=S2,
            recorded_at="2026-08-10T12:05:00Z",
        )))

    def test_first_entry_must_begin_at_anchor_state(self):
        self.bad(lambda: append_revision(CanonicalRevisionLedger(), **kw(
            receipt_pre_canonical_state_digest=H("not-the-anchor-state"),
        )))

    # -- required negative: failed receipt
    def test_failed_receipt_rejected(self):
        self.bad(lambda: append_revision(CanonicalRevisionLedger(), **kw(receipt_status="failed")))

    def test_unknown_receipt_status_rejected(self):
        self.bad(lambda: append_revision(CanonicalRevisionLedger(), **kw(receipt_status="pending")))

    # -- required negative: stage transition masquerading as revision
    def test_stage_transition_masquerade_rejected(self):
        self.bad(lambda: append_revision(CanonicalRevisionLedger(), **kw(
            receipt_target_canonical_stage="production",
            receipt_post_canonical_stage="production",
        )))

    def test_pre_stage_mismatch_rejected(self):
        self.bad(lambda: append_revision(CanonicalRevisionLedger(), **kw(
            receipt_pre_canonical_stage="canary",
        )))

    # -- required negative: stale lifecycle anchor
    def test_stale_lifecycle_anchor_rejected(self):
        self.bad(lambda: append_revision(CanonicalRevisionLedger(), **kw(
            receipt_previous_lifecycle_entry_digest=H("lifecycle-entry-OLD"),
        )))

    # -- required negative: missing authority evidence
    def test_missing_authority_evidence_rejected(self):
        self.bad(lambda: append_revision(CanonicalRevisionLedger(), **kw(
            revision_authorization_digest="",
        )))

    def test_malformed_authority_evidence_rejected(self):
        self.bad(lambda: append_revision(CanonicalRevisionLedger(), **kw(
            revision_authorization_digest="not-a-digest",
        )))

    # -- required negative: conflicting revision lineage
    def test_conflicting_lineage_rejected(self):
        l = two()
        fork = append_revision(one(), **kw(
            revision_id="rev-2b",
            revision_authorization_digest=H("auth-2b"),
            revision_receipt_digest=H("receipt-2b"),
            receipt_pre_canonical_state_digest=S1,
            receipt_target_canonical_state_digest=H("canonical-state-2b"),
            receipt_post_canonical_state_digest=H("canonical-state-2b"),
            recorded_at="2026-08-10T12:06:00Z",
        ))
        merged = l.entries + (fork.entries[1],)
        self.bad(lambda: verify_ledger(merged))

    # -- tampering
    def test_tampered_state_rejected(self):
        x = one().entries[0].to_dict()
        x["to_canonical_state_digest"] = H("forged-state")
        self.bad(lambda: CanonicalRevisionEntry.from_mapping(x))

    def test_unknown_field_rejected(self):
        x = one().entries[0].to_dict()
        x["deploy_now"] = True
        self.bad(lambda: CanonicalRevisionEntry.from_mapping(x))

    def test_missing_field_rejected(self):
        x = one().entries[0].to_dict()
        del x["revision_receipt_digest"]
        self.bad(lambda: CanonicalRevisionEntry.from_mapping(x))

    def test_wrong_schema_version_rejected(self):
        x = one().entries[0].to_dict()
        x["schema_version"] = "neuruh.canonical-state-revision-ledger.v9.9"
        self.bad(lambda: CanonicalRevisionEntry.from_mapping(x))

    # -- structural rules
    def test_no_op_revision_rejected(self):
        self.bad(lambda: append_revision(CanonicalRevisionLedger(), **kw(
            receipt_target_canonical_state_digest=S0,
            receipt_post_canonical_state_digest=S0,
        )))

    def test_post_target_contradiction_rejected(self):
        self.bad(lambda: append_revision(CanonicalRevisionLedger(), **kw(
            receipt_post_canonical_state_digest=H("something-else"),
        )))

    def test_time_regression_rejected(self):
        self.bad(lambda: append_revision(one(), **kw(
            revision_id="rev-2",
            revision_authorization_digest=H("auth-2"),
            revision_receipt_digest=H("receipt-2"),
            receipt_pre_canonical_state_digest=S1,
            receipt_target_canonical_state_digest=S2,
            receipt_post_canonical_state_digest=S2,
            recorded_at="2026-08-10T11:00:00Z",
        )))

    def test_target_mismatch_rejected(self):
        self.bad(lambda: append_revision(one(), **kw(
            revision_id="rev-2",
            target_id="other-target",
            revision_authorization_digest=H("auth-2"),
            revision_receipt_digest=H("receipt-2"),
            receipt_pre_canonical_state_digest=S1,
            receipt_target_canonical_state_digest=S2,
            receipt_post_canonical_state_digest=S2,
            recorded_at="2026-08-10T12:05:00Z",
        )))

    def test_bad_mode_rejected(self):
        self.bad(lambda: append_revision(CanonicalRevisionLedger(), **kw(
            receipt_revision_mode="restore_canonical",
        )))

if __name__ == "__main__":
    unittest.main()
