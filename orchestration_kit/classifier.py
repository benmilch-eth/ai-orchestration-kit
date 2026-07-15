"""Turn a raw handoff into a structured triage: each action item tagged
DONE / SAFE / SURFACE / BLOCKED. Ships an LLM classifier (DeepSeek-first,
Anthropic fallback, stdlib HTTP) but any callable(handoff_text)->triage_md works."""
from __future__ import annotations
import json, os, urllib.request

TRIAGE_PROMPT = """You are a background agent triaging a handoff a human wrote from another session.
Categorize EACH action item into exactly one bucket and output markdown with these headers:

## DONE — already handled (recognizable from artifacts/state)
## SAFE — can be auto-executed within a strict allowlist (idempotent, non-destructive)
## SURFACE — needs the human's judgment or hands
## BLOCKED — has a hard prerequisite the human must resolve first

For each SAFE item, write ONE line as: `- OP | target | payload`
where OP is one of MARK_COMPLETE, APPEND_NOTE, MIRROR_WRITE. Be conservative:
when unsure, choose SURFACE, never SAFE. Output only the four sections.

=== HANDOFF ===
{handoff}
=== END ==="""


def _post(url, headers, body, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={**headers, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def llm_classifier(handoff_text, *, deepseek_key=None, anthropic_key=None,
                   deepseek_model="deepseek-chat", anthropic_model="claude-sonnet-4-5",
                   max_tokens=4096):
    prompt = TRIAGE_PROMPT.format(handoff=handoff_text[:20000])
    dk = deepseek_key or os.getenv("DEEPSEEK_API_KEY")
    ak = anthropic_key or os.getenv("ANTHROPIC_API_KEY")
    if dk:
        try:
            d = _post("https://api.deepseek.com/chat/completions", {"Authorization": "Bearer " + dk},
                      {"model": deepseek_model, "messages": [{"role": "user", "content": prompt}],
                       "max_tokens": max_tokens, "temperature": 0.2})
            return d["choices"][0]["message"]["content"]
        except Exception:
            pass
    if ak:
        d = _post("https://api.anthropic.com/v1/messages",
                  {"x-api-key": ak, "anthropic-version": "2023-06-01"},
                  {"model": anthropic_model, "max_tokens": max_tokens,
                   "messages": [{"role": "user", "content": prompt}]})
        return d["content"][0]["text"]
    raise RuntimeError("Set DEEPSEEK_API_KEY and/or ANTHROPIC_API_KEY, or pass your own classifier.")
