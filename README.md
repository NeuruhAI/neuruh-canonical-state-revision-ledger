# Neuruh Canonical State Revision Ledger

[![ci](https://github.com/NeuruhAI/neuruh-canonical-state-revision-ledger/actions/workflows/ci.yml/badge.svg)](https://github.com/NeuruhAI/neuruh-canonical-state-revision-ledger/actions/workflows/ci.yml)

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

## Install

```bash
git clone https://github.com/NeuruhAI/neuruh-canonical-state-revision-ledger.git
cd neuruh-canonical-state-revision-ledger
python -m venv .venv
source .venv/bin/activate
pip install .
```

Or install a pinned release directly:

```bash
pip install "neuruh-canonical-state-revision-ledger @ git+https://github.com/NeuruhAI/neuruh-canonical-state-revision-ledger.git@v0.1.0-alpha"
```

## Sixty-second example

The repository ships a synthetic single-entry lineage. Inspect it with the installed CLI:

```bash
neuruh-canonical-state-revision-ledger validate examples/lineage.synthetic.jsonl
neuruh-canonical-state-revision-ledger digest   examples/lineage.synthetic.jsonl
neuruh-canonical-state-revision-ledger tip      examples/lineage.synthetic.jsonl
```

Expected output:

```text
{"anchor_stage": "pilot", "canonical_state_revision_authority": false, "effective_state_digest": "sha256:4a736ede8df2d2464e774214f5e925c36dab43052c589afc138c46dc52d475ca", "entries": 1, "lifecycle_anchor_digest": "sha256:c1942a9a25e5b7b3cdc8a5e7e905e23bf88de5076787007834733865b557b9b3", "lifecycle_ledger_mutated": false, "mutation_authority": false, "ok": true}
sha256:82ba56a7198a60a91662900ac7a02d9dbadb4a86648791070847aed5fbc5e8ce
4dedbf3d6de98f808ad1a9570ce8ced2c64d41a2193fbc269dc6f68eee8f0b6f
```

`inspect` prints the full entries. `examples/build_synthetic.py` regenerates the fixture from
scratch, so the whole append path can be read end to end.

Every command exits nonzero, with the rejection reason, when the chain is broken, an entry was
changed, a receipt is duplicated or failed, or a revision cites a different lifecycle anchor.

## API

| Name | Purpose |
| --- | --- |
| `append_revision(ledger, *, revision_id, target_id, lifecycle_anchor_digest, anchor_stage, anchor_state_digest, revision_authorization_digest, revision_receipt_digest, receipt_status, receipt_revision_mode, receipt_previous_lifecycle_entry_digest, receipt_pre_canonical_stage, receipt_pre_canonical_state_digest, receipt_target_canonical_stage, receipt_target_canonical_state_digest, receipt_post_canonical_stage, receipt_post_canonical_state_digest, recorded_at)` | Append one revision, enforcing every rule above. Returns a new ledger. |
| `verify_ledger(entries, *, expected_tip=None)` | Re-verify a whole lineage; optionally bind it to a separately stored tip. |
| `CanonicalRevisionLedger` | Immutable lineage of `CanonicalRevisionEntry`. |
| `CanonicalRevisionEntry` | One revision entry, including the hard-coded authority flags. |
| `CanonicalRevisionLedgerError` | Raised for every rejection. |
| `SCHEMA_VERSION`, `STAGES`, `REVISION_MODE`, `REQUIRED_RECEIPT_STATUS` | Declared vocabulary. |
| `canonical_json(value)`, `sha256_ref(value)` | Deterministic serialization and hashing helpers. |

The entry schema is published at
[`schema/canonical-state-revision-entry.v0.1.schema.json`](schema/canonical-state-revision-entry.v0.1.schema.json).

## Test

```bash
python -m unittest discover -s tests -v
```

## What 035 does not do

It does not mutate the Release 026 lifecycle ledger, does not grant or retire authority, does not execute, deploy, or reconcile anything, and does not decide effective canonical truth — that projection is Release 036.

## Safety boundary

Recording a revision grants nothing. Hash chaining is tamper evidence, not a signature and not
proof of who wrote an entry; binding a lineage to a separately stored tip is what makes tail
truncation detectable. This package holds no credentials, contacts no service, and ships only
synthetic fixtures — no production lifecycle data, revision history, or canonical state store.

See [`PUBLIC_PRIVATE_BOUNDARY.md`](PUBLIC_PRIVATE_BOUNDARY.md),
[`ARCHITECTURE.md`](ARCHITECTURE.md), [`SECURITY.md`](SECURITY.md), and the
[Neuruh Public Commons boundary](https://github.com/NeuruhAI/public-commons/blob/main/PUBLIC_PRIVATE_BOUNDARY.md).

## License

Apache License 2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
