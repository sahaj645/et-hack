"""Maps a compound-risk state to the correct SOP procedure and computes
the estimated risk reduction that procedure would buy — by actually
constructing a counterfactual "SOP already applied" version of the
scenario and re-scoring it through the same risk_agent pipeline used
everywhere else, not by inventing a plausible-sounding percentage.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parents[1]
for _p in (_ENGINE_DIR, _ENGINE_DIR / "engine", _ENGINE_DIR / "agents"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np
import pandas as pd

SOP_LIBRARY_PATH = _ENGINE_DIR.parent / "data" / "sop_library.json"


def load_sop_library() -> dict:
    with SOP_LIBRARY_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def procedure_for_archetype(archetype: str) -> dict:
    library = load_sop_library()
    for proc in library["procedures"]:
        if proc["applies_to_archetype"] == archetype:
            return proc
    raise KeyError(f"No SOP procedure maps to archetype '{archetype}'")


def _pre_event_baseline(df: pd.DataFrame, column: str, start_idx: int, lookback: int = 30) -> float:
    lo = max(0, start_idx - lookback)
    if start_idx <= lo:
        return float(df[column].iloc[start_idx])
    return float(df[column].iloc[lo:start_idx].mean())


def build_mitigated_scenario(df: pd.DataFrame, event: dict) -> pd.DataFrame:
    """A copy of the scenario with the event's window rewritten as if the
    matching SOP's mitigating actions had already been taken. Only the
    specific columns each SOP actually controls are touched — this is
    meant to be the honest counterfactual, not a rosier version of every
    channel.
    """
    mitigated = df.copy()
    start, end = event["start_idx"], event["end_idx"]
    window = slice(start, end + 1)
    idx = mitigated.index[window]

    archetype = event["archetype"]
    if archetype == "gas_leak_ventilation_failure":
        # SOP-GAS-01: evacuate zone, restore ventilation
        mitigated.loc[idx, "workers_in_tank_farm"] = 0
        baseline_wind = _pre_event_baseline(df, "wind_speed_kmh", start)
        mitigated.loc[idx, "wind_speed_kmh"] = baseline_wind
    elif archetype == "overpressure_degraded_relief":
        # SOP-HOTWORK-01: suspend hot work, relief path restored
        mitigated.loc[idx, "hot_work_permit_active"] = False
        mitigated.loc[idx, "relief_capacity_pct"] = 100.0
    elif archetype == "bearing_failure_overdue_maintenance":
        # SOP-MECH-01: controlled shutdown — vibration/temp return toward
        # pre-event baseline, and health stops declining further
        baseline_vibration = _pre_event_baseline(df, "vibration_mms", start)
        baseline_temp = _pre_event_baseline(df, "temp_compressor_c", start)
        health_at_start = float(df["compressor_health"].iloc[start])
        mitigated.loc[idx, "vibration_mms"] = baseline_vibration
        mitigated.loc[idx, "temp_compressor_c"] = baseline_temp
        mitigated.loc[idx, "compressor_health"] = health_at_start
    else:
        raise KeyError(f"No mitigation model for archetype '{archetype}'")

    return mitigated


def estimate_risk_reduction(df: pd.DataFrame, event: dict, hero_model=None) -> dict:
    """Peak-risk delta between the real scenario and the SOP-mitigated
    counterfactual, both scored by risk_agent.compute_risk_timeline —
    this is the number the copilot quotes, and it comes straight out of
    the model.
    """
    import risk_agent

    mitigated_df = build_mitigated_scenario(df, event)

    original = risk_agent.compute_risk_timeline(df, hero_model=hero_model)
    mitigated = risk_agent.compute_risk_timeline(mitigated_df, hero_model=hero_model)

    window = slice(event["start_idx"], event["end_idx"] + 1)
    peak_idx = int(original["risk"].iloc[window].idxmax())
    original_peak = float(original["risk"].iloc[peak_idx])
    mitigated_peak = float(mitigated["risk"].iloc[peak_idx])
    reduction_pct = (original_peak - mitigated_peak) / max(original_peak, 1e-6) * 100.0

    return {
        "peak_idx": peak_idx,
        "original_peak_risk": round(original_peak, 1),
        "mitigated_peak_risk": round(mitigated_peak, 1),
        "estimated_risk_reduction_pct": round(np.clip(reduction_pct, 0, 100), 1),
    }


def recommend(df: pd.DataFrame, event: dict, hero_model=None) -> dict:
    """Full SOP recommendation for an event: which procedure, its steps
    and source, and the model-simulated risk reduction.
    """
    procedure = procedure_for_archetype(event["archetype"])
    reduction = estimate_risk_reduction(df, event, hero_model=hero_model)
    return {
        "event_id": event["id"],
        "procedure": procedure,
        **reduction,
    }


if __name__ == "__main__":
    from model import build_and_fit_hero_model
    from simulator import generate_scenario

    scenario_df, _plant, events = generate_scenario()
    hero_model = build_and_fit_hero_model()

    for event in events:
        rec = recommend(scenario_df, event, hero_model=hero_model)
        print(f"\n{event['title']}")
        print(f"  SOP: {rec['procedure']['id']} — {rec['procedure']['title']}")
        print(f"  Peak risk: {rec['original_peak_risk']} -> {rec['mitigated_peak_risk']} if SOP applied")
        print(f"  Estimated risk reduction: {rec['estimated_risk_reduction_pct']}%")
