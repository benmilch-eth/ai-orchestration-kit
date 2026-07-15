"""Watcher: scan the substrate for new handoffs, classify each into a triage doc,
write it back to the substrate, mark processed. SURFACE-ONLY — never executes."""
from __future__ import annotations
from datetime import datetime, timezone


def run_watch(store, classifier, triage_subdir="triage", max_age_hours=8, notify=None):
    processed = []
    for item in store.new_items(max_age_hours=max_age_hours):
        raw = store.read(item)
        triage = classifier(raw)
        name = f"{triage_subdir}/{datetime.now(timezone.utc):%Y-%m-%d}-{item.stem}.md"
        store.write(name, f"# Triage — {item.name}\n\n{triage}\n")
        store.mark_processed(item.name)
        processed.append({"handoff": item.name, "triage": name})
        if notify:
            notify(f"triaged {item.name} -> {name}")
    return processed
