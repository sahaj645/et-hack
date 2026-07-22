# Cost Basis — Impact Board Assumptions

Every figure on the Impact Board is a **simulation output**: a real, measured
count from `engine/metrics/results.json` multiplied by an explicitly-labeled
assumption below. None of this is a verified real-world claim about any
specific facility — no unlabeled ₹ or safety figure appears anywhere in this
product. The computation lives in `engine/export.py::build_impact_summary`
so the numbers on screen are never hand-typed; changing an assumption here
requires changing the code and re-running `python engine/export.py`.

## What's measured (not assumed)

- **Compound archetypes validated**: 3 (gas leak, bearing failure, overpressure)
- **Detection rate**: 100% across 60 archetype instances / 20 seeded evaluation
  days (`results.json: detection.overall.hero.detected_pct`)
- **Median early-warning lead time**: from `results.json:
  detection.overall.hero.median_lead_min`
- **False-alarm rate**: from `results.json: false_alarms_per_day.hero`, shown
  against Baseline B for comparison

## What's assumed (illustrative, order-of-magnitude, not facility-specific)

These are round numbers chosen to be conservative and clearly labeled as
assumptions, not measured statistics for any real plant. Actual incident
recurrence rates and costs vary by facility, product, scale, and market
conditions — often by 10x or more.

| Assumption | Value | Basis |
|---|---|---|
| Recurrence rate per archetype | Once per quarter (4×/year) | Illustrative — treats each of the 3 validated compound patterns as a plausible quarterly event at a mid-sized process unit, not a measured base rate |
| Incidents/year across all 3 archetypes | 3 × 4 = 12 | Simulated count (3, from the validated archetypes) × the assumption above |
| Downtime avoided per caught incident | 4 hours | Illustrative order-of-magnitude estimate for an unplanned trip + restart avoided by early intervention, averaged across the 3 archetype types |
| Cost avoided per caught incident | ₹3,00,000 | Illustrative order-of-magnitude estimate for lost production + repair avoided on a mid-sized process unit; not derived from any specific facility's financials |

## Derived figures shown on the Impact Board

- **Near-misses prevented/year (simulated)** = incidents/year × detection rate
  = 12 × 100% = **12**
- **Downtime avoided/year (simulated)** = 12 × 4h = **48 hours**
- **Cost avoided/year (simulated)** = 12 × ₹3,00,000 = **₹36,00,000**
- **Unsafe zone entries flagged before exposure (simulated)** = count of
  worker-intrusion events across the 20 gas-leak evaluation instances = a
  real count, not an assumption (every gas-leak archetype instance in this
  simulation includes exactly one unpermitted zone entry, by design)

## Explicitly not claimed

- No "lives saved" or casualty-avoidance figure is shown. The Impact Board
  reports flagged unsafe *exposures* (a countable simulation event), not a
  body count, because a life-safety claim tied to a simulation would be
  dishonest regardless of how it were labeled.
- No number here is presented as validated against a real deployment. Every
  card on the Impact Board carries a "Simulation output" label for this
  reason.
