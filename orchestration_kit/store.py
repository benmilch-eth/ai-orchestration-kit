"""Substrate = a shared store used as a message bus between an ephemeral session
(mobile/chat) and an always-on agent. LocalStore is the reference implementation;
swap in a Drive/S3/GCS backend by matching this small interface."""
from __future__ import annotations
import json, time
from pathlib import Path


class LocalStore:
    """A folder as the substrate. Handoffs are files; processed state is tracked in state.json."""
    def __init__(self, root, state_name="state.json"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.root / state_name

    def _state(self):
        if self.state_path.exists():
            try: return json.loads(self.state_path.read_text())
            except Exception: pass
        return {"processed": []}

    def _save(self, s):
        self.state_path.write_text(json.dumps(s, indent=2))

    def new_items(self, pattern="*.md", max_age_hours=None):
        """Files matching pattern, not yet marked processed, newest first."""
        s = self._state()
        done = set(s.get("processed", []))
        out = []
        for p in sorted(self.root.glob(pattern), key=lambda x: x.stat().st_mtime, reverse=True):
            if p.name == self.state_path.name or p.name in done:
                continue
            if max_age_hours and (time.time() - p.stat().st_mtime) > max_age_hours * 3600:
                continue
            out.append(p)
        return out

    def read(self, path):
        return Path(path).read_text(encoding="utf-8")

    def write(self, name, content):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return p

    def mark_processed(self, name):
        s = self._state()
        if name not in s["processed"]:
            s["processed"].append(name)
            self._save(s)
