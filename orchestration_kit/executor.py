"""Executor: auto-run ONLY the items a triage tagged SAFE, inside a hard safety boundary.

Guarantees (all enforced):
  - path allowlist (+ forbidden-substring deny) on every target
  - operation allowlist: MARK_COMPLETE / APPEND_NOTE / MIRROR_WRITE only
  - idempotency via an append-only audit log (never re-runs the same action)
  - dry-run by default; must opt in to apply
  - per-run action cap
Everything else surfaces to a human. Paranoid by design."""
from __future__ import annotations
from pathlib import Path
from .audit import Audit, action_hash

ALLOWED_OPS = {"MARK_COMPLETE", "APPEND_NOTE", "MIRROR_WRITE"}


class Executor:
    def __init__(self, allowed_paths, audit_path, dry_run=True, max_actions=5,
                 forbidden_substrings=("secret", ".env", "password", "token", "credential")):
        self.allowed = [str(p).replace("\\", "/").lower() for p in allowed_paths]
        self.forbidden = tuple(forbidden_substrings)
        self.audit = Audit(audit_path)
        self.dry_run = dry_run
        self.max_actions = max_actions

    def _target_ok(self, target):
        t = target.replace("\\", "/").lower()
        if any(fb in t for fb in self.forbidden):
            return False, "forbidden substring"
        if not any(t.startswith(a) for a in self.allowed):
            return False, "outside path allowlist"
        return True, "ok"

    @staticmethod
    def parse_safe(triage_md):
        """Lines under '## SAFE' of the form: - OP | target | payload"""
        actions, in_safe = [], False
        for ln in triage_md.splitlines():
            s = ln.strip()
            if s.startswith("## "):
                in_safe = s.upper().startswith("## SAFE")
                continue
            if in_safe and s.startswith("-"):
                parts = [p.strip() for p in s.lstrip("- ").split("|")]
                if len(parts) >= 2 and parts[0].upper() in ALLOWED_OPS:
                    actions.append({"op": parts[0].upper(), "target": parts[1],
                                    "payload": parts[2] if len(parts) > 2 else ""})
        return actions

    def run(self, source_id, triage_md):
        results, applied = [], 0
        for a in self.parse_safe(triage_md):
            ah = action_hash(a["op"], a["target"], a["payload"])
            if applied >= self.max_actions:
                results.append({**a, "skipped": "per-run cap"}); continue
            if self.audit.seen(source_id, ah):
                results.append({**a, "skipped": "already executed"}); continue
            ok, why = self._target_ok(a["target"])
            if not ok:
                results.append({**a, "skipped": why}); continue
            if self.dry_run:
                results.append({**a, "dry_run": True}); continue
            self._apply(a)
            self.audit.append({"source_id": source_id, "action_hash": ah, **a, "applied": True})
            results.append({**a, "applied": True}); applied += 1
        return results

    def _apply(self, a):
        op, target, payload = a["op"], a["target"], a["payload"]
        if op == "MARK_COMPLETE":
            p = Path(target)
            p.write_text(p.read_text(encoding="utf-8").replace(f"- [ ] {payload}", f"- [x] {payload}", 1),
                         encoding="utf-8")
        elif op == "APPEND_NOTE":
            with Path(target).open("a", encoding="utf-8") as f:
                f.write(f"\n{payload}\n")
        elif op == "MIRROR_WRITE":
            ok, why = self._target_ok(payload)          # payload = source path; must also be allowed
            if not ok:
                raise ValueError(f"mirror source rejected: {why}")
            Path(target).write_text(Path(payload).read_text(encoding="utf-8"), encoding="utf-8")
