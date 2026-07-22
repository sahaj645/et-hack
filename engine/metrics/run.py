"""Evaluate the hero fusion model against both conventional baselines
across the 3 compound archetypes, over many seeded runs, and write the
one JSON file every later asset (deck, video, README, web UI) quotes
numbers from. No hand-typed metric anywhere downstream of this script.

Usage:
    python engine/metrics/run.py
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

from baselines import ThresholdBaseline, ZScoreBaseline  # noqa: E402
from calibration import CALIBRATION_SEEDS  # noqa: E402
from metrics import (  # noqa: E402
    debounce_alarm_events,
    estimate_single_channel_alarm_time,
    first_detection_in_range,
    lead_time_minutes,
)
from model import build_and_fit_hero_model  # noqa: E402
import risk_agent  # noqa: E402
from simulator import CHANNEL_SPECS, DT_MINUTES, SEED, _simulate_baseline, generate_scenario  # noqa: E402

REPO_ROOT = _ENGINE_DIR.parent
RESULTS_PATH = Path(__file__).resolve().parent / "results.json"

EVAL_SEEDS = list(range(2000, 2020))        # 20 seeded days, each with all 3 archetypes
QUIET_EVAL_SEEDS = list(range(3000, 3020))  # 20 held-out quiet days, false-alarm measurement
DEBOUNCE_GAP_STEPS = 15                     # 30 min: merge nearby crossings into one alarm event

METHODS = ["hero", "baseline_a", "baseline_b"]
METHOD_LABELS = {
    "hero": "PlantPulse (hero)",
    "baseline_a": "Baseline A (threshold)",
    "baseline_b": "Baseline B (rolling z-score)",
}


def _alarm_series_for(method: str, df: pd.DataFrame, hero_model, threshold_a, threshold_b) -> pd.Series:
    if method == "hero":
        return risk_agent.alarm_series(df, hero_model=hero_model)
    if method == "baseline_a":
        return threshold_a.alarm_series(df)
    return threshold_b.alarm_series(df)


def evaluate_incident_detection(hero_model, threshold_a, threshold_b) -> dict:
    """Across EVAL_SEEDS x 3 archetypes: does each method detect the
    archetype exactly as scripted (bounded window), and how much lead
    time does it buy versus an extrapolated conventional alarm?
    """
    per_archetype = {}
    all_rows = []

    for seed in EVAL_SEEDS:
        df, _plant, events = generate_scenario(seed=seed)
        series = {
            m: _alarm_series_for(m, df, hero_model, threshold_a, threshold_b) for m in METHODS
        }
        for event in events:
            archetype = event["archetype"]
            reference_idx = estimate_single_channel_alarm_time(df, event, CHANNEL_SPECS)

            row = {"seed": seed, "archetype": archetype, "reference_idx": reference_idx}
            for m in METHODS:
                detected_bounded = first_detection_in_range(series[m], event["start_idx"], event["end_idx"]) is not None
                search_end = int(np.ceil(reference_idx)) if reference_idx is not None else event["end_idx"]
                detection_idx = first_detection_in_range(series[m], event["start_idx"], search_end)
                lead = lead_time_minutes(detection_idx, reference_idx, DT_MINUTES)
                row[f"{m}_detected_bounded"] = detected_bounded
                row[f"{m}_detection_idx"] = detection_idx
                row[f"{m}_lead_min"] = lead
            all_rows.append(row)

    df_rows = pd.DataFrame(all_rows)
    for archetype, group in df_rows.groupby("archetype"):
        entry = {"n_instances": len(group)}
        for m in METHODS:
            detected_pct = float(group[f"{m}_detected_bounded"].mean() * 100)
            leads = group[f"{m}_lead_min"].dropna()
            entry[m] = {
                "detected_pct": round(detected_pct, 1),
                "median_lead_min": round(float(leads.median()), 1) if len(leads) else None,
                "lead_samples": int(len(leads)),
            }
        per_archetype[archetype] = entry

    overall = {"n_instances": len(df_rows)}
    for m in METHODS:
        detected_pct = float(df_rows[f"{m}_detected_bounded"].mean() * 100)
        leads = df_rows[f"{m}_lead_min"].dropna()
        overall[m] = {
            "detected_pct": round(detected_pct, 1),
            "median_lead_min": round(float(leads.median()), 1) if len(leads) else None,
            "lead_samples": int(len(leads)),
        }

    return {"per_archetype": per_archetype, "overall": overall, "raw_rows": df_rows}


def evaluate_false_alarms(hero_model, threshold_a, threshold_b) -> dict:
    """Across QUIET_EVAL_SEEDS (held out from calibration): how many
    distinct (debounced) alarm events does each method raise on a day
    with nothing wrong at all?
    """
    counts = {m: [] for m in METHODS}
    for seed in QUIET_EVAL_SEEDS:
        df = _simulate_baseline(np.random.default_rng(seed))
        for m in METHODS:
            series = _alarm_series_for(m, df, hero_model, threshold_a, threshold_b)
            events = debounce_alarm_events(series, gap_steps=DEBOUNCE_GAP_STEPS)
            counts[m].append(len(events))

    return {
        m: {
            "mean_false_alarms_per_day": round(float(np.mean(counts[m])), 2),
            "days_evaluated": len(QUIET_EVAL_SEEDS),
        }
        for m in METHODS
    }


def build_sample_incident(hero_model) -> dict:
    """The demo (seed=42) gas-leak archetype: chronologically first in the
    day, so its contributor breakdown isn't muddied by an earlier
    unresolved incident still elevating other agents' scores.
    """
    df, _plant, events = generate_scenario(seed=SEED)
    event = next(e for e in events if e["archetype"] == "gas_leak_ventilation_failure")
    result = risk_agent.compute_risk_timeline(df, hero_model=hero_model)
    threshold = risk_agent.get_hero_operating_threshold()

    peak_idx = int(result["risk"].iloc[event["start_idx"]:event["end_idx"] + 1].idxmax())
    timeline = [
        {
            "idx": i,
            "time": df["timestamp"].iloc[i],
            "risk": round(float(result["risk"].iloc[i]), 1),
            "confidence": round(float(result["confidence"].iloc[i]), 2),
        }
        for i in range(event["start_idx"], event["end_idx"] + 1, 3)
    ]
    contributors = risk_agent.contributor_breakdown(result["agent_scores"], peak_idx)
    model_margin = float(np.clip((result["model_score"].iloc[peak_idx] - 50.0) / 50.0, 0, 1))
    agreement = sum(
        1 for s in result["agent_scores"].values() if s.iloc[peak_idx] > risk_agent.AGENT_AGREEMENT_THRESHOLD
    ) / len(result["agent_scores"])

    return {
        "event_id": event["id"],
        "title": event["title"],
        "window": {"start_idx": event["start_idx"], "end_idx": event["end_idx"]},
        "operating_threshold": round(threshold, 2),
        "peak_idx": peak_idx,
        "timeline": timeline,
        "contributors_at_peak": contributors,
        "confidence_at_peak": round(float(result["confidence"].iloc[peak_idx]), 2),
        "confidence_explanation": risk_agent.explain_confidence(model_margin, agreement),
    }


def print_table(detection: dict, false_alarms: dict) -> None:
    print("\n=== PlantPulse vs Conventional Detection — Overall (20 seeds x 3 archetypes = 60 instances) ===")
    header = f"{'Method':<30}{'Detected %':>12}{'Median Lead (min)':>20}{'False Alarms/Day':>20}"
    print(header)
    print("-" * len(header))
    for m in METHODS:
        d = detection["overall"][m]
        fa = false_alarms[m]["mean_false_alarms_per_day"]
        lead = d["median_lead_min"]
        lead_str = f"{lead:>18.1f}" if lead is not None else f"{'n/a':>18}"
        print(f"{METHOD_LABELS[m]:<30}{d['detected_pct']:>11.1f}%{lead_str}{fa:>20.2f}")

    print("\n=== Per-archetype breakdown ===")
    for archetype, entry in detection["per_archetype"].items():
        print(f"\n{archetype}  (n={entry['n_instances']})")
        for m in METHODS:
            d = entry[m]
            lead = d["median_lead_min"]
            lead_str = f"{lead:.1f} min" if lead is not None else "n/a"
            print(f"  {METHOD_LABELS[m]:<30} detected={d['detected_pct']:>5.1f}%   median lead={lead_str}")


def main() -> None:
    print("Fitting hero model on 30 calibration (quiet) days...")
    hero_model = build_and_fit_hero_model()
    threshold_a = ThresholdBaseline()
    threshold_b = ZScoreBaseline()

    print(f"Evaluating detection across {len(EVAL_SEEDS)} seeded days ({len(EVAL_SEEDS) * 3} archetype instances)...")
    detection = evaluate_incident_detection(hero_model, threshold_a, threshold_b)

    print(f"Evaluating false-alarm rate across {len(QUIET_EVAL_SEEDS)} held-out quiet days...")
    false_alarms = evaluate_false_alarms(hero_model, threshold_a, threshold_b)

    print_table(detection, false_alarms)

    print("\nBuilding sample-incident printout (demo seed, gas-leak archetype)...")
    sample = build_sample_incident(hero_model)
    print(f"\n{sample['title']}")
    print(f"Operating threshold: {sample['operating_threshold']}")
    for pt in sample["timeline"]:
        print(f"  idx {pt['idx']:>3}  risk={pt['risk']:5.1f}  confidence={pt['confidence']:.2f}")
    print(f"\nAt peak (idx {sample['peak_idx']}):")
    for c in sample["contributors_at_peak"]:
        print(f"  {c['agent']:>12}: {c['contribution_pct']:5.1f}%")
    print(f"Confidence: {sample['confidence_at_peak']}  —  {sample['confidence_explanation']}")

    fn_rate_hero = 1 - detection["overall"]["hero"]["detected_pct"] / 100
    fn_rate_a = 1 - detection["overall"]["baseline_a"]["detected_pct"] / 100
    fn_reduction_pct = (
        round((fn_rate_a - fn_rate_hero) / fn_rate_a * 100, 1) if fn_rate_a > 0 else None
    )

    results = {
        "meta": {
            "eval_seeds": EVAL_SEEDS,
            "quiet_eval_seeds": QUIET_EVAL_SEEDS,
            "calibration_seeds": list(CALIBRATION_SEEDS),
            "debounce_gap_steps": DEBOUNCE_GAP_STEPS,
            "lead_time_methodology": (
                "Lead time is measured against an extrapolated single-channel alarm "
                "time: the observed ramp-up slope of each archetype's primary hazard "
                "channel(s) is linearly projected forward to the point a conventional "
                "threshold would cross if the trend continued unaddressed. Computed "
                "directly from simulated data, not a separate simulation mode."
            ),
        },
        "detection": {
            "overall": detection["overall"],
            "per_archetype": detection["per_archetype"],
        },
        "false_alarms_per_day": false_alarms,
        "false_negative_reduction_pct_vs_baseline_a": fn_reduction_pct,
        "sample_incident": sample,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_PATH.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {RESULTS_PATH.relative_to(REPO_ROOT)}")
    print(f"False-negative reduction vs Baseline A: {fn_reduction_pct}%")


if __name__ == "__main__":
    main()
