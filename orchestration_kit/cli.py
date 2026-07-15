from __future__ import annotations
import argparse, json, sys
from .store import LocalStore
from .watcher import run_watch
from .executor import Executor
from .classifier import llm_classifier
try:
    from dotenv import load_dotenv; load_dotenv()
except Exception:
    pass


def cmd_watch(a):
    store = LocalStore(a.store)
    out = run_watch(store, llm_classifier, max_age_hours=a.max_age_hours,
                    notify=lambda m: print(f"[watch] {m}", file=sys.stderr))
    print(json.dumps(out, indent=2))


def cmd_execute(a):
    ex = Executor(a.allow, audit_path=a.audit, dry_run=not a.apply, max_actions=a.max_actions)
    triage = open(a.triage, encoding="utf-8").read()
    print(json.dumps(ex.run(a.triage, triage), indent=2))


def main(argv=None):
    p = argparse.ArgumentParser(prog="orchestrate", description="Substrate handoff bus: watch + safe execute.")
    sub = p.add_subparsers(dest="cmd", required=True)

    w = sub.add_parser("watch", help="Classify new handoffs in the store into triage docs (surface-only).")
    w.add_argument("--store", required=True, help="Substrate folder.")
    w.add_argument("--max-age-hours", type=int, default=8)
    w.set_defaults(func=cmd_watch)

    e = sub.add_parser("execute", help="Auto-run SAFE actions from a triage doc, inside the allowlist.")
    e.add_argument("--triage", required=True, help="Triage markdown file.")
    e.add_argument("--allow", nargs="+", required=True, help="Allowed target path prefixes.")
    e.add_argument("--audit", default="audit.jsonl")
    e.add_argument("--max-actions", type=int, default=5)
    e.add_argument("--apply", action="store_true", help="Actually execute (default is dry-run).")
    e.set_defaults(func=cmd_execute)
    return p.parse_args(argv).func(p.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
