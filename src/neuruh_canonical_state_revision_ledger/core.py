from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json, re
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "neuruh.canonical-state-revision-ledger.v0.1"
STAGES = ("sandbox", "canary", "pilot", "production")
REVISION_MODE = "adopt_observed"
REQUIRED_RECEIPT_STATUS = "succeeded"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

class CanonicalRevisionLedgerError(ValueError):
    """Fail-closed refusal for malformed, replayed, forked, stale-anchored, or tampered canonical revision lineage."""

def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)

def sha256_ref(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return "sha256:" + sha256(value).hexdigest()

def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CanonicalRevisionLedgerError(f"{name} must be a non-empty string")
    return value

def _sha(value: Any, name: str) -> str:
    value = _nonempty(value, name)
    if not value.startswith("sha256:") or not HEX64.fullmatch(value[7:]):
        raise CanonicalRevisionLedgerError(f"{name} must be sha256:<64 lowercase hex>")
    return value

def _hash64(value: Any, name: str) -> str:
    value = _nonempty(value, name)
    if not HEX64.fullmatch(value):
        raise CanonicalRevisionLedgerError(f"{name} must be 64 lowercase hex")
    return value

def _time(value: Any, name: str) -> datetime:
    value = _nonempty(value, name)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CanonicalRevisionLedgerError(f"{name} must be RFC3339/ISO-8601") from exc
    if dt.tzinfo is None:
        raise CanonicalRevisionLedgerError(f"{name} must include a timezone")
    return dt.astimezone(timezone.utc)

def _keys(raw: Mapping[str, Any], required: set[str], context: str) -> None:
    missing = sorted(required - set(raw))
    unknown = sorted(set(raw) - required)
    if missing:
        raise CanonicalRevisionLedgerError(f"{context} missing required field(s): {', '.join(missing)}")
    if unknown:
        raise CanonicalRevisionLedgerError(f"{context} contains unknown field(s): {', '.join(unknown)}")

@dataclass(frozen=True)
class CanonicalRevisionEntry:
    ledger_id: str
    revision_id: str
    sequence: int
    target_id: str

    lifecycle_anchor_digest: str
    anchor_stage: str
    anchor_state_digest: str

    revision_authorization_digest: str
    revision_receipt_digest: str
    revision_mode: str
    receipt_status: str

    from_canonical_state_digest: str
    to_canonical_state_digest: str
    recorded_at: str

    previous_entry_hash: str | None = None

    lifecycle_ledger_mutated: bool = False
    lifecycle_transition_authority: bool = False
    canonical_state_revision_authority: bool = False
    canonical_state_authority: bool = False
    execution_authority: bool = False
    deployment_authority: bool = False
    reconciliation_authority: bool = False
    mutation_authority: bool = False
    entry_hash: str | None = None

    def body_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "ledger_id": self.ledger_id,
            "revision_id": self.revision_id,
            "sequence": self.sequence,
            "target_id": self.target_id,
            "lifecycle_anchor_digest": self.lifecycle_anchor_digest,
            "anchor_stage": self.anchor_stage,
            "anchor_state_digest": self.anchor_state_digest,
            "revision_authorization_digest": self.revision_authorization_digest,
            "revision_receipt_digest": self.revision_receipt_digest,
            "revision_mode": self.revision_mode,
            "receipt_status": self.receipt_status,
            "from_canonical_state_digest": self.from_canonical_state_digest,
            "to_canonical_state_digest": self.to_canonical_state_digest,
            "recorded_at": self.recorded_at,
            "previous_entry_hash": self.previous_entry_hash,
            "lifecycle_ledger_mutated": False,
            "lifecycle_transition_authority": False,
            "canonical_state_revision_authority": False,
            "canonical_state_authority": False,
            "execution_authority": False,
            "deployment_authority": False,
            "reconciliation_authority": False,
            "mutation_authority": False,
        }

    def calculated_hash(self) -> str:
        return sha256(canonical_json(self.body_dict()).encode("utf-8")).hexdigest()

    @property
    def digest_ref(self) -> str:
        self.validate()
        return "sha256:" + self.entry_hash

    def validate(self, *, check_hash: bool = True) -> None:
        for value, name in [
            (self.ledger_id, "ledger_id"),
            (self.revision_id, "revision_id"),
            (self.target_id, "target_id"),
        ]:
            _nonempty(value, name)

        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 0:
            raise CanonicalRevisionLedgerError("sequence must be a non-negative integer")

        for value, name in [
            (self.lifecycle_anchor_digest, "lifecycle_anchor_digest"),
            (self.anchor_state_digest, "anchor_state_digest"),
            (self.revision_authorization_digest, "revision_authorization_digest"),
            (self.revision_receipt_digest, "revision_receipt_digest"),
            (self.from_canonical_state_digest, "from_canonical_state_digest"),
            (self.to_canonical_state_digest, "to_canonical_state_digest"),
        ]:
            _sha(value, name)

        if self.anchor_stage not in STAGES:
            raise CanonicalRevisionLedgerError("anchor_stage must be a known lifecycle stage")
        if self.revision_mode != REVISION_MODE:
            raise CanonicalRevisionLedgerError("v0.1 supports adopt_observed only")
        if self.receipt_status != REQUIRED_RECEIPT_STATUS:
            raise CanonicalRevisionLedgerError(
                "failed or non-successful revision receipt cannot advance canonical revision lineage"
            )
        if self.from_canonical_state_digest == self.to_canonical_state_digest:
            raise CanonicalRevisionLedgerError("canonical revision must change the canonical state digest")
        _time(self.recorded_at, "recorded_at")

        if self.sequence == 0:
            if self.previous_entry_hash is not None:
                raise CanonicalRevisionLedgerError("sequence zero cannot have previous_entry_hash")
        else:
            if self.previous_entry_hash is None:
                raise CanonicalRevisionLedgerError("nonzero sequence requires previous_entry_hash")
            _hash64(self.previous_entry_hash, "previous_entry_hash")

        if self.lifecycle_ledger_mutated is not False:
            raise CanonicalRevisionLedgerError("revision lineage never mutates the Release 026 lifecycle ledger")
        for value, name in [
            (self.lifecycle_transition_authority, "lifecycle_transition_authority"),
            (self.canonical_state_revision_authority, "canonical_state_revision_authority"),
            (self.canonical_state_authority, "canonical_state_authority"),
            (self.execution_authority, "execution_authority"),
            (self.deployment_authority, "deployment_authority"),
            (self.reconciliation_authority, "reconciliation_authority"),
            (self.mutation_authority, "mutation_authority"),
        ]:
            if value is not False:
                raise CanonicalRevisionLedgerError(f"revision lineage is memory, not power: {name} must be false")

        if check_hash:
            if self.entry_hash is None:
                raise CanonicalRevisionLedgerError("entry_hash is required")
            _hash64(self.entry_hash, "entry_hash")
            if self.entry_hash != self.calculated_hash():
                raise CanonicalRevisionLedgerError("entry_hash mismatch")

    def seal(self) -> "CanonicalRevisionEntry":
        self.validate(check_hash=False)
        obj = CanonicalRevisionEntry(**{
            **self.__dict__,
            "lifecycle_ledger_mutated": False,
            "lifecycle_transition_authority": False,
            "canonical_state_revision_authority": False,
            "canonical_state_authority": False,
            "execution_authority": False,
            "deployment_authority": False,
            "reconciliation_authority": False,
            "mutation_authority": False,
            "entry_hash": None,
        })
        obj = CanonicalRevisionEntry(**{**obj.__dict__, "entry_hash": obj.calculated_hash()})
        obj.validate()
        return obj

    def to_dict(self) -> dict[str, Any]:
        obj = self.seal()
        out = obj.body_dict()
        out["entry_hash"] = obj.entry_hash
        return out

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "CanonicalRevisionEntry":
        required = {
            "schema_version", "ledger_id", "revision_id", "sequence", "target_id",
            "lifecycle_anchor_digest", "anchor_stage", "anchor_state_digest",
            "revision_authorization_digest", "revision_receipt_digest", "revision_mode", "receipt_status",
            "from_canonical_state_digest", "to_canonical_state_digest", "recorded_at",
            "previous_entry_hash", "lifecycle_ledger_mutated", "lifecycle_transition_authority",
            "canonical_state_revision_authority", "canonical_state_authority", "execution_authority",
            "deployment_authority", "reconciliation_authority", "mutation_authority", "entry_hash",
        }
        _keys(raw, required, "canonical revision entry")
        if raw["schema_version"] != SCHEMA_VERSION:
            raise CanonicalRevisionLedgerError("unsupported schema_version")
        obj = cls(**{k: raw[k] for k in required if k != "schema_version"})
        obj.validate()
        return obj

@dataclass(frozen=True)
class CanonicalRevisionLedger:
    entries: tuple[CanonicalRevisionEntry, ...] = ()

    def validate(self, *, expected_tip: str | None = None) -> None:
        if not self.entries:
            if expected_tip is not None:
                raise CanonicalRevisionLedgerError("empty lineage cannot match expected tip")
            return

        if len({e.ledger_id for e in self.entries}) != 1:
            raise CanonicalRevisionLedgerError("ledger_id must remain constant")
        if len({e.target_id for e in self.entries}) != 1:
            raise CanonicalRevisionLedgerError("target_id must remain constant")
        if len({(e.lifecycle_anchor_digest, e.anchor_stage, e.anchor_state_digest) for e in self.entries}) != 1:
            raise CanonicalRevisionLedgerError("revision lineage is bound to exactly one lifecycle anchor")
        if [e.sequence for e in self.entries] != list(range(len(self.entries))):
            raise CanonicalRevisionLedgerError("sequence must be contiguous from zero")

        ids = [e.revision_id for e in self.entries]
        if len(ids) != len(set(ids)):
            raise CanonicalRevisionLedgerError("revision_id values must be unique")

        receipts = [e.revision_receipt_digest for e in self.entries]
        if len(receipts) != len(set(receipts)):
            raise CanonicalRevisionLedgerError("duplicate revision receipt consumption")

        authorizations = [e.revision_authorization_digest for e in self.entries]
        if len(authorizations) != len(set(authorizations)):
            raise CanonicalRevisionLedgerError("canonical revision authorization may support only one lineage revision")

        for i, entry in enumerate(self.entries):
            entry.validate()
            expected_previous = None if i == 0 else self.entries[i - 1].entry_hash
            if entry.previous_entry_hash != expected_previous:
                raise CanonicalRevisionLedgerError("broken previous_entry_hash chain")

            expected_from = entry.anchor_state_digest if i == 0 else self.entries[i - 1].to_canonical_state_digest
            if entry.from_canonical_state_digest != expected_from:
                raise CanonicalRevisionLedgerError(
                    "revision does not begin from the previous effective canonical state"
                )

            if i > 0:
                previous = self.entries[i - 1]
                if _time(entry.recorded_at, "recorded_at") < _time(previous.recorded_at, "previous recorded_at"):
                    raise CanonicalRevisionLedgerError("revision records must be non-decreasing in time")

        if expected_tip is not None:
            _hash64(expected_tip, "expected_tip")
            if self.entries[-1].entry_hash != expected_tip:
                raise CanonicalRevisionLedgerError("expected tip mismatch")

    @property
    def tip(self) -> str | None:
        return None if not self.entries else self.entries[-1].entry_hash

    @property
    def lifecycle_anchor_digest(self) -> str | None:
        return None if not self.entries else self.entries[0].lifecycle_anchor_digest

    @property
    def anchor_stage(self) -> str | None:
        return None if not self.entries else self.entries[0].anchor_stage

    @property
    def anchor_state_digest(self) -> str | None:
        return None if not self.entries else self.entries[0].anchor_state_digest

    @property
    def effective_state_digest(self) -> str | None:
        return None if not self.entries else self.entries[-1].to_canonical_state_digest

    def digest(self) -> str:
        self.validate()
        return sha256_ref(canonical_json([e.to_dict() for e in self.entries]))

    def to_jsonl(self) -> str:
        self.validate()
        return "".join(canonical_json(e.to_dict()) + "\n" for e in self.entries)

    @classmethod
    def from_jsonl(cls, text: str) -> "CanonicalRevisionLedger":
        rows = []
        for line_no, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CanonicalRevisionLedgerError(f"invalid JSON on line {line_no}") from exc
            rows.append(CanonicalRevisionEntry.from_mapping(raw))
        obj = cls(tuple(rows))
        obj.validate()
        return obj

def append_revision(
    ledger: CanonicalRevisionLedger,
    *,
    revision_id: str,
    target_id: str,
    lifecycle_anchor_digest: str,
    anchor_stage: str,
    anchor_state_digest: str,
    revision_authorization_digest: str,
    revision_receipt_digest: str,
    receipt_status: str,
    receipt_revision_mode: str,
    receipt_previous_lifecycle_entry_digest: str,
    receipt_pre_canonical_stage: str,
    receipt_pre_canonical_state_digest: str,
    receipt_target_canonical_stage: str,
    receipt_target_canonical_state_digest: str,
    receipt_post_canonical_stage: str,
    receipt_post_canonical_state_digest: str,
    recorded_at: str,
) -> CanonicalRevisionLedger:
    ledger.validate()

    if receipt_status != REQUIRED_RECEIPT_STATUS:
        raise CanonicalRevisionLedgerError(
            "failed or non-successful revision receipt cannot advance canonical revision lineage"
        )
    if receipt_revision_mode != REVISION_MODE:
        raise CanonicalRevisionLedgerError("v0.1 supports adopt_observed only")

    _sha(lifecycle_anchor_digest, "lifecycle_anchor_digest")
    _sha(receipt_previous_lifecycle_entry_digest, "receipt_previous_lifecycle_entry_digest")
    if receipt_previous_lifecycle_entry_digest != lifecycle_anchor_digest:
        raise CanonicalRevisionLedgerError(
            "stale lifecycle anchor: receipt was anchored to a different lifecycle entry than this lineage"
        )

    if anchor_stage not in STAGES:
        raise CanonicalRevisionLedgerError("anchor_stage must be a known lifecycle stage")
    for value, name in [
        (receipt_pre_canonical_stage, "receipt_pre_canonical_stage"),
        (receipt_target_canonical_stage, "receipt_target_canonical_stage"),
        (receipt_post_canonical_stage, "receipt_post_canonical_stage"),
    ]:
        if value != anchor_stage:
            raise CanonicalRevisionLedgerError(
                f"lifecycle-stage change cannot be recorded as canonical revision: {name} must equal anchor_stage"
            )

    if receipt_post_canonical_state_digest != receipt_target_canonical_state_digest:
        raise CanonicalRevisionLedgerError("receipt post-canonical state contradicts the authorized target state")

    if ledger.entries:
        head = ledger.entries[0]
        if head.target_id != target_id:
            raise CanonicalRevisionLedgerError("target_id must match ledger target")
        if (head.lifecycle_anchor_digest, head.anchor_stage, head.anchor_state_digest) != (
            lifecycle_anchor_digest, anchor_stage, anchor_state_digest,
        ):
            raise CanonicalRevisionLedgerError("revision lineage is bound to exactly one lifecycle anchor")

    expected_from = anchor_state_digest if not ledger.entries else ledger.entries[-1].to_canonical_state_digest
    if receipt_pre_canonical_state_digest != expected_from:
        raise CanonicalRevisionLedgerError("revision does not begin from the previous effective canonical state")

    if any(e.revision_receipt_digest == revision_receipt_digest for e in ledger.entries):
        raise CanonicalRevisionLedgerError("duplicate revision receipt consumption")
    if any(e.revision_authorization_digest == revision_authorization_digest for e in ledger.entries):
        raise CanonicalRevisionLedgerError("canonical revision authorization may support only one lineage revision")

    entry = CanonicalRevisionEntry(
        ledger_id=ledger.entries[0].ledger_id if ledger.entries else "canonical-revision",
        revision_id=revision_id,
        sequence=len(ledger.entries),
        target_id=target_id,
        lifecycle_anchor_digest=lifecycle_anchor_digest,
        anchor_stage=anchor_stage,
        anchor_state_digest=anchor_state_digest,
        revision_authorization_digest=revision_authorization_digest,
        revision_receipt_digest=revision_receipt_digest,
        revision_mode=receipt_revision_mode,
        receipt_status=receipt_status,
        from_canonical_state_digest=receipt_pre_canonical_state_digest,
        to_canonical_state_digest=receipt_post_canonical_state_digest,
        recorded_at=recorded_at,
        previous_entry_hash=ledger.tip,
    ).seal()

    out = CanonicalRevisionLedger(ledger.entries + (entry,))
    out.validate()
    return out

def verify_ledger(
    entries: Sequence[CanonicalRevisionEntry],
    *,
    expected_tip: str | None = None,
) -> CanonicalRevisionLedger:
    obj = CanonicalRevisionLedger(tuple(entries))
    obj.validate(expected_tip=expected_tip)
    return obj
