"""Fuses the six specialist agents and the hero multivariate model into a
single 0-100 compound risk score, a ranked contributor breakdown, and a
non-random confidence value. This is the number the whole product orbits.

Two independent signals are blended 60/40:
  - the IsolationForest's percentile score (engine/engine/model.py) —
    genuinely multivariate, catches joint patterns no single agent
    encodes by hand.
  - the six agents' combined, explainable score — the part with a plain-
    English "why." Contributor percentages come entirely from this side.

Agents with a naturally bounded 0-1 raw scale (permit, maintenance) are
used as-is; worker_agent is scaled by a documented domain constant (max
plausible zone headcount). sensor/equipment/weather are continuous and
always present even on a quiet day, so they're normalized against 30
days of measured normal variation instead — "normal" for a permit flag
is trivially always zero, so a statistical percentile of an all-zero
distribution is undefined and would be dishonest to fake.

Confidence = 0.5 * model_margin + 0.5 * cross-agent agreement. Not
random: model_margin is how far the fused score sits above the alert
threshold (as a fraction of the gap to the worst calibration reading),
and agreement is the fraction of the six agents independently reporting
a meaningfully elevated score at the same instant.
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parents[1]
for _p in (_ENGINE_DIR, _ENGINE_DIR / "engine", _ENGINE_DIR / "agents"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np
import pandas as pd

import equipment_agent
import maintenance_agent
import permit_agent
import sensor_agent
import weather_agent
import worker_agent

AGENT_MODULES = {
    "sensor": sensor_agent,
    "equipment": equipment_agent,
    "permit": permit_agent,
    "maintenance": maintenance_agent,
    "worker": worker_agent,
    "weather": weather_agent,
}

STATISTICAL_AGENTS = {"sensor", "equipment", "weather"}
WORKER_MAX_HEADCOUNT = 3.0  # documented domain constant: max scripted day-shift headcount in Z1

MODEL_WEIGHT = 0.6
AGENT_WEIGHT = 0.4
AGENT_AGREEMENT_THRESHOLD = 0.4


def _normalize_agent(name: str, raw: pd.Series, agent_calibration: dict) -> pd.Series:
    if name in STATISTICAL_AGENTS:
        p99 = max(agent_calibration[f"{name}_agent"]["p99"], 1e-6)
        return raw / p99
    if name == "worker":
        return (raw / WORKER_MAX_HEADCOUNT).clip(upper=1.5)
    return raw  # permit, maintenance are already 0-1 by construction


def _agent_totals(df: pd.DataFrame, normal_stats: dict, agent_calibration: dict) -> dict:
    raws = {name: mod.raw_score(df, normal_stats) for name, mod in AGENT_MODULES.items()}
    normed = {name: _normalize_agent(name, raws[name], agent_calibration) for name in AGENT_MODULES}
    return raws, normed


AGENT_SCORE_STEEPNESS = 2.5  # same sigmoid steepness as HeroModel.calibrated_score, for a consistent scale


@lru_cache(maxsize=1)
def _agent_total_calibration_stats() -> tuple:
    """(median, 99th-percentile threshold) of the summed agent score across
    the 30 quiet calibration days — the sigmoid anchor for the agent side
    of the fused risk, mirroring HeroModel.calibrated_score.
    """
    from calibration import get_agent_calibration, get_calibration_frames, get_normal_stats

    normal_stats = get_normal_stats()
    agent_cal = get_agent_calibration()
    totals = []
    for f in get_calibration_frames():
        _raws, normed = _agent_totals(f, normal_stats, agent_cal)
        totals.append(pd.concat(normed.values(), axis=1).sum(axis=1).to_numpy())
    combined = np.concatenate(totals)
    return float(np.median(combined)), float(np.quantile(combined, 0.99))


def _calibrated_score(values: np.ndarray, median: float, threshold: float, steepness: float = AGENT_SCORE_STEEPNESS) -> np.ndarray:
    """Sigmoid anchored at `threshold` (-> 50) with `median` (-> ~a few
    points) setting the natural scale — see HeroModel.calibrated_score for
    the full rationale. Percentile RANK is uniform on in-distribution data
    by construction, so it makes a bad "how anomalous is this" score; this
    is anchored at the actual decision boundary instead.
    """
    spread = max(threshold - median, 1e-9)
    z = (values - threshold) / spread
    return 100.0 / (1.0 + np.exp(-steepness * z))


def compute_risk_timeline(df: pd.DataFrame, hero_model=None) -> dict:
    """Per-timestep fused risk (0-100), confidence (0-1), and each agent's
    normalized score (for the contributor breakdown), aligned to df's index.
    """
    from calibration import get_agent_calibration, get_normal_stats
    from features import build_feature_matrix
    from model import build_and_fit_hero_model

    normal_stats = get_normal_stats()
    agent_cal = get_agent_calibration()

    raws, normed = _agent_totals(df, normal_stats, agent_cal)
    agent_total = pd.concat(normed.values(), axis=1).sum(axis=1)
    agent_median, agent_threshold = _agent_total_calibration_stats()
    agent_score = _calibrated_score(agent_total.to_numpy(), agent_median, agent_threshold)

    if hero_model is None:
        hero_model = build_and_fit_hero_model()
    X = build_feature_matrix(df, normal_stats)
    model_raw = hero_model.anomaly_score(X)
    model_score = hero_model.calibrated_score(model_raw)

    risk = np.clip(MODEL_WEIGHT * model_score + AGENT_WEIGHT * agent_score, 0, 100)

    model_margin = np.clip((model_score - 50.0) / 50.0, 0.0, 1.0)
    agreement = (
        pd.concat([(normed[name] > AGENT_AGREEMENT_THRESHOLD).astype(float) for name in AGENT_MODULES], axis=1)
        .sum(axis=1)
        .to_numpy()
        / len(AGENT_MODULES)
    )
    confidence = np.clip(0.5 * model_margin + 0.5 * agreement, 0, 1)

    return {
        "risk": pd.Series(risk, index=df.index),
        "confidence": pd.Series(confidence, index=df.index),
        "model_score": pd.Series(model_score, index=df.index),
        "agent_score": pd.Series(agent_score, index=df.index),
        "agent_scores": normed,
        "agent_raw": raws,
    }


@lru_cache(maxsize=1)
def get_hero_operating_threshold() -> float:
    """99th percentile of the fused risk score across the 30 calibration
    days — the alert threshold used everywhere risk_agent's alarm_series
    is needed (metrics comparison, UI).
    """
    from calibration import get_calibration_frames
    from model import build_and_fit_hero_model

    hero_model = build_and_fit_hero_model()
    combined = np.concatenate(
        [compute_risk_timeline(f, hero_model=hero_model)["risk"].to_numpy() for f in get_calibration_frames()]
    )
    return float(np.quantile(combined, 0.99))


EARLY_TRIGGER_MIN_AGENTS = 2  # of 6, each above AGENT_AGREEMENT_THRESHOLD, simultaneously
EARLY_TRIGGER_SUSTAIN_STEPS = 5  # ~10 min: agreement must hold, not just blip once


def alarm_series(df: pd.DataFrame, hero_model=None) -> pd.Series:
    """Fires on EITHER of two conditions:
      1. the fused risk score crosses its calibrated 99th-percentile
         threshold (the general-purpose multivariate detector), or
      2. at least EARLY_TRIGGER_MIN_AGENTS of the six agents independently
         report a meaningfully elevated score (> AGENT_AGREEMENT_THRESHOLD)
         at the same instant, SUSTAINED for EARLY_TRIGGER_SUSTAIN_STEPS in a
         row, even if none of them individually looks statistically extreme.

    Condition 2 is the literal product thesis, made explicit rather than
    left for the blended score to discover implicitly: several independent
    signals mildly agreeing is treated as real evidence, not noise, which
    is exactly the case a single-channel system — however statistically
    sophisticated — structurally cannot represent, since it only ever has
    one signal to look at. The sustain requirement exists because, once
    every agent has a real (non-degenerate) calibration reference, brief
    coincidental co-elevation of two continuous, independently-noisy
    signals happens often enough by chance alone to be a poor trigger on
    its own — same logic a real alarm system uses "N consecutive readings"
    debounce for, not just a raw instantaneous crossing.
    """
    result = compute_risk_timeline(df, hero_model=hero_model)
    threshold = get_hero_operating_threshold()
    primary = result["risk"] >= threshold

    agreement_count = pd.concat(
        [(s > AGENT_AGREEMENT_THRESHOLD).astype(int) for s in result["agent_scores"].values()], axis=1
    ).sum(axis=1)
    cross_signal_instant = agreement_count >= EARLY_TRIGGER_MIN_AGENTS
    cross_signal = (
        cross_signal_instant.rolling(EARLY_TRIGGER_SUSTAIN_STEPS, min_periods=EARLY_TRIGGER_SUSTAIN_STEPS)
        .min()
        .fillna(0)
        .astype(bool)
    )

    return primary | cross_signal


def contributor_breakdown(agent_scores: dict, idx: int) -> list:
    values = {name: float(s.iloc[idx]) for name, s in agent_scores.items()}
    total = sum(max(v, 0.0) for v in values.values())
    ranked = sorted(values.items(), key=lambda kv: kv[1], reverse=True)
    breakdown = []
    for name, v in ranked:
        pct = (max(v, 0.0) / total * 100.0) if total > 1e-9 else 0.0
        breakdown.append({"agent": name, "normalized_score": round(v, 3), "contribution_pct": round(pct, 1)})
    return breakdown


def explain_confidence(model_margin: float, agreement: float) -> str:
    return (
        f"{agreement * 100:.0f}% of the six agents independently flag something unusual "
        f"at this instant, and the fused score sits {model_margin * 100:.0f}% of the way "
        f"from the alert threshold toward the worst reading seen in 30 days of normal operation."
    )


if __name__ == "__main__":
    from model import build_and_fit_hero_model
    from simulator import generate_scenario

    scenario_df, _plant, events = generate_scenario()
    hero_model = build_and_fit_hero_model()
    result = compute_risk_timeline(scenario_df, hero_model=hero_model)
    threshold = get_hero_operating_threshold()

    print(f"Hero operating threshold (risk 0-100 scale): {threshold:.2f}\n")

    sample = next(e for e in events if e["id"] == "evt-overpressure-01")
    peak_idx = int(result["risk"].iloc[sample["start_idx"]:sample["end_idx"] + 1].idxmax())

    print(f"Sample incident: {sample['title']}")
    print(f"Window: idx {sample['start_idx']}-{sample['end_idx']} ({sample['start_time']} -> {sample['end_time']})\n")

    print("Risk timeline (every 3rd step through the window):")
    for i in range(sample["start_idx"], sample["end_idx"] + 1, 3):
        marker = "  <-- peak" if i == peak_idx else ""
        print(f"  idx {i:>3}  risk={result['risk'].iloc[i]:5.1f}  confidence={result['confidence'].iloc[i]:.2f}{marker}")

    print(f"\nAt peak (idx {peak_idx}):")
    for c in contributor_breakdown(result["agent_scores"], peak_idx):
        print(f"  {c['agent']:>12}: {c['contribution_pct']:5.1f}%  (normalized={c['normalized_score']})")

    print(f"\nConfidence: {result['confidence'].iloc[peak_idx]:.2f}")
    print(" ", explain_confidence(
        np.clip((result["model_score"].iloc[peak_idx] - 50.0) / 50.0, 0, 1),
        sum(1 for s in result["agent_scores"].values() if s.iloc[peak_idx] > AGENT_AGREEMENT_THRESHOLD) / 6,
    ))
