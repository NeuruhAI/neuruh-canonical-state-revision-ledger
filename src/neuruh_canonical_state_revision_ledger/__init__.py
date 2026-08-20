from importlib.metadata import PackageNotFoundError, version as _metadata_version

from .core import (
    REQUIRED_RECEIPT_STATUS,
    REVISION_MODE,
    SCHEMA_VERSION,
    STAGES,
    CanonicalRevisionEntry,
    CanonicalRevisionLedger,
    CanonicalRevisionLedgerError,
    append_revision,
    canonical_json,
    sha256_ref,
    verify_ledger,
)

__all__ = [
    "REQUIRED_RECEIPT_STATUS",
    "REVISION_MODE",
    "SCHEMA_VERSION",
    "STAGES",
    "CanonicalRevisionEntry",
    "CanonicalRevisionLedger",
    "CanonicalRevisionLedgerError",
    "append_revision",
    "canonical_json",
    "sha256_ref",
    "verify_ledger",
]

try:
    __version__ = _metadata_version("neuruh-canonical-state-revision-ledger")
except PackageNotFoundError:  # running from a source tree that was never installed
    __version__ = "unknown"
