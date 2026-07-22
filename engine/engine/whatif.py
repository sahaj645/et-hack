"""Shared what-if counterfactual logic, used by both engine/api.py (the
live endpoint) and engine/export.py (the precomputed offline fallback
grid) — one implementation, so the fallback can never silently drift from
what the live API actually computes.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parents[1]
for _p in (_ENGINE_DIR, _ENGINE_DIR / "engine", _ENGINE_DIR / "agents"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

DEFAULT_WHATIF_INDEX = 65  # early in the gas-leak buildup — past the alert
# threshold with headroom left, so both sliders below produce a real,
# visible swing rather than being lost in an already-saturated peak.


def apply_whatif(df, index: int, ventilation_pct: float, delay_maintenance: bool):
    """Returns a modified copy of df with the requested counterfactual
    applied in a trailing window ending at `index` — the same "real
    counterfactual, re-scored by the real model" pattern as
    sop_agent.build_mitigated_scenario.
    """
    modified = df.copy()
    window_start = max(0, index - 30)
    idx_slice = modified.index[window_start : index + 1]

    ventilation_factor = ventilation_pct / 100.0
    modified.loc[idx_slice, "wind_speed_kmh"] = modified.loc[idx_slice, "wind_speed_kmh"] * ventilation_factor

    if delay_maintenance:
        current_health = float(df["compressor_health"].iloc[index])
        modified.loc[modified.index[index], "compressor_health"] = max(0.05, current_health - 0.15)

    return modified


def score_whatif(df, hero_model, index: int, ventilation_pct: float, delay_maintenance: bool) -> dict:
    import risk_agent

    modified = apply_whatif(df, index, ventilation_pct, delay_maintenance)
    result = risk_agent.compute_risk_timeline(modified, hero_model=hero_model)
    contributors = risk_agent.contributor_breakdown(result["agent_scores"], index)
    return {
        "index": index,
        "risk": round(float(result["risk"].iloc[index]), 2),
        "confidence": round(float(result["confidence"].iloc[index]), 3),
        "contributors": {c["agent"]: c["contribution_pct"] for c in contributors},
    }
