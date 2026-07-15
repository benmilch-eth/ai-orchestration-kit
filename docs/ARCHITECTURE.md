# Architecture — substrate handoff bus

## Problem
Useful AI assistance often happens in an **ephemeral** context (a phone, a chat window) that can't
reach your real environment. The intent is captured; the execution never happens. Meanwhile an
always-on machine *can* act, but has no safe channel to receive that intent.

## Pattern: a shared substrate as the bus
Decouple the two with a store both sides can reach:

```
 ephemeral session            SUBSTRATE (folder / Drive / bucket)        always-on agent
 ─────────────────            ──────────────────────────────────        ───────────────
 writes a HANDOFF   ───────►  /handoffs/*.md                            WATCHER (poll)
                                                                          └─ classify via LLM
                              /triage/*.md            ◄───────────────      write triage, mark done
                                                                          EXECUTOR (poll)
                              (target files)          ◄───────────────      run SAFE items only
                              /audit.jsonl (append-only ledger)  ◄──────     record every action
```

- The **substrate** is the only shared dependency; neither side calls the other directly.
- **Idempotency** lives in the substrate (processed-state + audit ledger), so every role can crash and
  re-run safely.

## Two roles, one safety boundary
- **Watcher = perception.** It only ever *reads* handoffs and *writes* triage. Zero authority to act.
  This keeps the risky classification step (an LLM reading free-form text) fully sandboxed.
- **Executor = action, fenced.** It trusts nothing from the LLM except a narrow, structured contract:
  lines of `OP | target | payload` under a `## SAFE` header, where `OP` is one of three allowlisted
  operations and `target` must pass the path allowlist. Anything outside that contract is ignored.

## Why split them
A single "read and do" agent couples an unbounded input (natural language) to an unbounded output
(arbitrary actions). Splitting perception from action lets you make the **action** side provably
small — three operations, an allowlist, an audit log, a dry-run — while the perception side stays
flexible. The result degrades safely: worst case, it surfaces too much to the human, never too little.

## Extending
- Back the store with Drive/S3 to make the bus reachable from truly anywhere.
- Add operations to the executor allowlist one at a time, each with its own guard + audit shape.
- Add a `SURFACE` notifier (email/push) so the human sees what needs them without opening the triage.
