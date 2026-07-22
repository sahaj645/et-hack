"""Impact Board figures: real measured counts from engine/metrics/results.json
combined with explicitly-labeled illustrative assumptions. See
data/cost_basis.md for the full disclosure — this module only implements
the arithmetic described there. Every constant below is named in that file;
changing an assumption means changing both.
"""

from __future__ import annotations

ARCHETYPES_VALIDATED = 3
RECURRENCE_PER_ARCHETYPE_PER_YEAR = 4  # once/quarter — illustrative, not a measured base rate
DOWNTIME_HOURS_PER_INCIDENT = 4.0  # illustrative order-of-magnitude estimate
COST_PER_INCIDENT_INR = 300_000  # illustrative order-of-magnitude estimate


def build_impact_summary(results: dict, unsafe_zone_entries_flagged: int, eval_seed_count: int) -> dict:
    detection = results["detection"]["overall"]["hero"]
    false_alarms = results["false_alarms_per_day"]

    incidents_per_year_assumed = ARCHETYPES_VALIDATED * RECURRENCE_PER_ARCHETYPE_PER_YEAR
    detection_rate = detection["detected_pct"] / 100.0
    near_misses_prevented_per_year = round(incidents_per_year_assumed * detection_rate)
    downtime_avoided_hours_per_year = round(incidents_per_year_assumed * DOWNTIME_HOURS_PER_INCIDENT, 1)
    cost_avoided_inr_per_year = round(incidents_per_year_assumed * COST_PER_INCIDENT_INR)

    return {
        "measured": {
            "archetypes_validated": ARCHETYPES_VALIDATED,
            "detection_rate_pct": detection["detected_pct"],
            "median_lead_time_min": detection["median_lead_min"],
            "false_alarms_per_day_hero": false_alarms["hero"]["mean_false_alarms_per_day"],
            "false_alarms_per_day_baseline_b": false_alarms["baseline_b"]["mean_false_alarms_per_day"],
            "unsafe_zone_entries_flagged": unsafe_zone_entries_flagged,
            "eval_seed_count": eval_seed_count,
        },
        "assumptions": {
            "recurrence_per_archetype_per_year": RECURRENCE_PER_ARCHETYPE_PER_YEAR,
            "downtime_hours_per_incident": DOWNTIME_HOURS_PER_INCIDENT,
            "cost_per_incident_inr": COST_PER_INCIDENT_INR,
            "basis": "See data/cost_basis.md for full disclosure of every assumption and its rationale.",
        },
        "derived": {
            "incidents_per_year_assumed": incidents_per_year_assumed,
            "near_misses_prevented_per_year": near_misses_prevented_per_year,
            "downtime_avoided_hours_per_year": downtime_avoided_hours_per_year,
            "cost_avoided_inr_per_year": cost_avoided_inr_per_year,
        },
        "label": "All figures below are simulation outputs (measured count x disclosed assumption), not verified real-world claims. See data/cost_basis.md.",
    }
