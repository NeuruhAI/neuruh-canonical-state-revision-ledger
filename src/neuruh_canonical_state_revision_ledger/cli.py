import argparse, json
from pathlib import Path
from .core import CanonicalRevisionLedger

def main(argv=None):
    p = argparse.ArgumentParser(prog="neuruh-canonical-state-revision-ledger")
    s = p.add_subparsers(dest="cmd", required=True)
    for n in ("validate", "digest", "tip", "inspect"):
        x = s.add_parser(n)
        x.add_argument("file")
    a = p.parse_args(argv)
    o = CanonicalRevisionLedger.from_jsonl(Path(a.file).read_text())
    if a.cmd == "validate":
        print(json.dumps({
            "ok": True,
            "entries": len(o.entries),
            "lifecycle_anchor_digest": o.lifecycle_anchor_digest,
            "anchor_stage": o.anchor_stage,
            "effective_state_digest": o.effective_state_digest,
            "lifecycle_ledger_mutated": False,
            "canonical_state_revision_authority": False,
            "mutation_authority": False,
        }, sort_keys=True))
    elif a.cmd == "digest":
        print(o.digest())
    elif a.cmd == "tip":
        print(o.tip)
    else:
        print(json.dumps([e.to_dict() for e in o.entries], indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
