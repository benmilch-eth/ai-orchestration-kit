"""Append-only audit log + idempotency. Every executed action is recorded and never
re-run. The log is never edited in place — it is the safety ledger."""
from __future__ import annotations
import hashlib, json, time
from pathlib import Path


def action_hash(op, target, payload):
    return hashlib.sha1(f"{op}|{target}|{payload}".encode()).hexdigest()[:16]


class Audit:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def seen(self, source_id, ahash):
        if not self.path.exists():
            return False
        for line in self.path.read_text().splitlines():
            try:
                e = json.loads(line)
            except Exception:
                continue
            if e.get("source_id") == source_id and e.get("action_hash") == ahash:
                return True
        return False

    def append(self, entry):
        entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **entry}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
