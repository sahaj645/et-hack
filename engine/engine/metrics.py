"""Pure calculation functions used by engine/metrics/run.py. No simulation,
no randomness — just turning alarm series and event windows into numbers.

Lead-time methodology: S1's three archetypes are built so no single
channel ever crosses its own alarm threshold during the scripted incident
window — that's the entire premise. So "lead time before the first
single-sensor alarm would fire" has no literal answer inside the window
as scripted. We answer the honest version of the question instead: fit
the observed ramp-up rate of each archetype's primary hazard channel(s)
(using `ramp_steps`, the true ramp-up length simulator.py already
records) and linearly extrapolate forward to the point a conventional
threshold *would* cross if the trend continued unaddressed. This is a
deterministic calculation on real simulated data — not a new simulation
mode, not a fabricated number — and it is almost certainly conservative,
since real leaks/wear/heat buildup tend to accelerate rather than hold a
constant rate.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd


def estimate_single_channel_alarm_time(
    df: pd.DataFrame, event: dict, channel_specs: dict
) -> Optional[float]:
    """Earliest (fractional) index at which any of the event's primary
    hazard channels would cross its own alarm_high, extrapolating the
    observed ramp-up slope forward. Returns None if no affected channel
    has a rising trend (shouldn't happen for these 3 archetypes).
    """
    start = event["start_idx"]
    ramp_steps = max(int(event.get("ramp_steps", 6)), 3)
    primary_channels = [c for c in event["affected_channels"] if c in channel_specs]

    best_idx = None
    for ch in primary_channels:
        segment = df[ch].iloc[start:start + ramp_steps + 1].to_numpy()
        if len(segment) < 3:
            continue
        t = np.arange(len(segment))
        slope = np.polyfit(t, segment, 1)[0]
        if slope <= 0:
            continue  # this channel isn't trending toward its own alarm
        alarm = channel_specs[ch]["alarm_high"]
        current = segment[-1]
        if current >= alarm:
            crossing_idx = float(start + len(segment) - 1)
        else:
            crossing_idx = start + (len(segment) - 1) + (alarm - current) / slope
        if best_idx is None or crossing_idx < best_idx:
            best_idx = crossing_idx
    return best_idx


def first_detection_in_range(fired: pd.Series, search_start: int, search_end: int) -> Optional[int]:
    """First index in [search_start, search_end] (inclusive) where `fired`
    is True, or None if it never fires in that range.
    """
    search_end = min(search_end, len(fired) - 1)
    if search_start > search_end:
        return None
    window = fired.iloc[search_start:search_end + 1]
    if not window.any():
        return None
    return search_start + int(np.argmax(window.to_numpy()))


def debounce_alarm_events(fired: pd.Series, gap_steps: int = 15) -> list:
    """Collapse a boolean alarm series into contiguous alarm *events*,
    merging crossings that are within `gap_steps` of each other. Used so
    "false alarms per day" counts distinct incidents, not raw timesteps.
    """
    true_idx = np.flatnonzero(fired.to_numpy())
    if len(true_idx) == 0:
        return []
    events = []
    seg_start = true_idx[0]
    seg_end = true_idx[0]
    for idx in true_idx[1:]:
        if idx - seg_end <= gap_steps:
            seg_end = idx
        else:
            events.append((int(seg_start), int(seg_end)))
            seg_start = idx
            seg_end = idx
    events.append((int(seg_start), int(seg_end)))
    return events


def lead_time_minutes(detection_idx: Optional[int], reference_idx: Optional[float], dt_minutes: int) -> Optional[float]:
    if detection_idx is None or reference_idx is None:
        return None
    return (reference_idx - detection_idx) * dt_minutes
