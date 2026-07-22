"""LLM call wrapper for the ops copilot.

This demo never calls a live model: every fact in a copilot answer (cause,
recommendation, SOP steps, estimated risk reduction) already comes from a
deterministic pipeline (risk_agent, knowledge_graph, sop_agent), and a live
LLM call would introduce exactly the two things the rest of this project
goes out of its way to avoid — non-determinism and a chance of inventing a
safety-relevant fact. If an API key is configured, `generate_with_llm`
could be used to lightly rephrase an already-assembled templated answer
for tone; it is never allowed to originate a number, procedure, or cause.
No key is configured for this deployment, so `templates.render_answer` is
the only path actually exercised.
"""

from __future__ import annotations

import os


def has_api_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def generate_with_llm(templated_answer: dict) -> dict:
    """Rephrasing-only hook. Not exercised in this offline demo (no API
    key configured) — templates.render_answer's structured output is used
    as-is. Left here so the architecture matches what a production
    deployment with a real key would look like, without ever making the
    offline demo depend on network access.
    """
    if not has_api_key():
        return templated_answer
    raise NotImplementedError(
        "Live LLM rephrasing is not wired up in this build — the templated "
        "answer is authoritative and should be used directly."
    )
