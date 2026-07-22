"""Structured prompt -> cause -> recommendation -> SOP steps -> estimated
risk reduction template. This is the actual answer-generation path used
in the demo (see engine/copilot/llm.py for why no live model is called).

Every field is assembled from real upstream computation:
  - cause bullets        <- knowledge_graph.compute_hazardous_path's clauses
  - recommendation       <- the SOP procedure's own first two steps
  - SOP steps / source   <- sop_agent.recommend -> data/sop_library.json
  - risk reduction       <- sop_agent.recommend's simulated mitigation
Nothing here is free-text generation; it is retrieval and formatting over
those four real sources.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parents[1]
for _p in (_ENGINE_DIR, _ENGINE_DIR / "engine", _ENGINE_DIR / "agents"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def render_answer(event: dict, zone_name: str, clauses: list, sop_rec: dict, peak_confidence: float) -> dict:
    procedure = sop_rec["procedure"]
    recommendation = procedure["steps"][:2]

    return {
        "event_id": event["id"],
        "question": f"Why is {zone_name} ({event['zone_id']}) unsafe right now?",
        "answer": {
            "cause": clauses,
            "recommendation": recommendation,
            "sop_procedure_id": procedure["id"],
            "sop_procedure_title": procedure["title"],
            "sop_steps": procedure["steps"],
            "sop_source": procedure["source"],
            "estimated_risk_reduction_pct": sop_rec["estimated_risk_reduction_pct"],
            "peak_risk": sop_rec["original_peak_risk"],
            "confidence": round(peak_confidence, 2),
        },
    }


def build_demo_cache(scenario_df, plant, events, hero_model) -> list:
    """The 3 canonical demo Q&As — one per archetype — pre-generated so
    the copilot works fully offline. Reuses the exact same computation as
    the Knowledge tab and risk timeline; nothing is computed twice with
    different logic.
    """
    import risk_agent
    import sop_agent
    from knowledge_graph import build_plant_graph, compute_hazardous_path

    graph = build_plant_graph(plant)
    risk_result = risk_agent.compute_risk_timeline(scenario_df, hero_model=hero_model)

    answers = []
    for event in events:
        zone = plant.zones[event["zone_id"]]
        path = compute_hazardous_path(graph, event, scenario_df, plant)
        sop_rec = sop_agent.recommend(scenario_df, event, hero_model=hero_model)
        peak_idx = sop_rec["peak_idx"]
        confidence = float(risk_result["confidence"].iloc[peak_idx])

        answers.append(render_answer(event, zone.name, path["clauses"], sop_rec, confidence))

    return answers
