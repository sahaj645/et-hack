---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section { font-size: 26px; }
  h1 { color: #0f172a; }
  table { font-size: 20px; }
  .stat { font-size: 64px; font-weight: bold; color: #0891b2; }
---

# PlantPulse
### Compound-risk intelligence for industrial safety

**A gas leak masked by ventilation failure. A bearing failure on an
overdue-maintenance compressor. An overpressure risk while the relief
path is degraded.**

Every one built so **no single sensor ever crosses its own alarm
threshold** — and PlantPulse still catches all three.

<span class="stat">100%</span> detected · <span class="stat">99.8 min</span> median lead time

*ET AI Hackathon 2.0 — Problem Statement #1, Industrial Safety Intelligence*

---

## The insight

Post-mortems on real industrial incidents keep saying the same thing:
**"every individual system worked as designed."**

- The permit system didn't know the compressor was oscillating.
- The gas detector didn't know a worker had just entered the zone.
- The maintenance scheduler didn't know a relief valve was already offline.

Individually normal. Combined, lethal. A conventional single-sensor alarm
**cannot see this** — it only ever has one signal to look at.

---

## Three real compound archetypes

Each validated at generation time: every affected channel stays under its
own single-channel alarm threshold for the whole incident window, or the
code refuses to run.

| Archetype | Compounding factors |
|---|---|
| Slow gas leak, masked ventilation | Gas trending up + wind near-calm + unpermitted worker entry |
| Early bearing failure | Vibration + temp trending up + maintenance overdue 6 days |
| Overpressure, degraded relief | Pressure + temp trending up + relief valve mid-test + active hot-work permit |

---

## How it works

```
Python engine (offline, seeded) --exports--> JSON --> Next.js control room
  6 agents + IsolationForest                            plays precomputed demo
  fused into one score                                   live what-if slider
        |                                                       |
        +----------------------- FastAPI (upside only) ---------+
```

- **6 explainable agents** (sensor, equipment, permit, maintenance, worker, weather)
- **1 genuinely multivariate model** (IsolationForest, trained only on 30 quiet days — never on the incidents)
- **Fused score anchored at a calibrated alert threshold** — not a raw percentile, which is uniform on normal data by construction

---

## The control room

Live risk gauge, plant twin, geospatial heatmap, and ranked contributor
bars — all driven by the same exported JSON, deterministically.

*(Live/Demo/Knowledge tabs — see recorded demo)*

Zone turns **RESTRICTED** the moment compound risk crosses threshold.
Workers render as dots; an unpermitted entry renders in red.

---

## Explainable by construction

A real knowledge graph (`Worker → Zone → Permit`, `Asset → Channel`,
`Asset → Maintenance Task`) built fresh from plant state every run — not
a static diagram.

> "Worker 05 enters Tank Farm (Z1) — Z1's standing entry permit P-01 is
> held by Worker 01, not Worker 05; TANK-01 shows Gas Concentration
> rising; wind has dropped to near-calm, stalling dispersion."

Generated from real graph traversal + real event data. Every incident.

---

## The metric that matters

20 seeded evaluation days, 60 archetype instances, 20 held-out quiet days
for false-alarm rate. Source: `engine/metrics/results.json`.

| Method | Detected | Median Lead Time | False Alarms/Day |
|---|---|---|---|
| **PlantPulse (hero)** | **100%** | **99.8 min** | **7.05** |
| Threshold baseline | 0% | never fires | 0.00 |
| Rolling z-score baseline | 100% | 92.4 min | 8.30 |

Wins on lead time on **2 of 3 archetypes individually** — the third
(fastest-onset overpressure) trails by ~1 minute, reported honestly.

---

## From alert to action

Ask "Why is Tank Farm unsafe right now?" →

**Cause** (from the knowledge graph) → **Recommendation** (top SOP steps)
→ **SOP-GAS-01**, cited to OISD-STD-105 & Factories Act 1948 §36 →
**Estimated risk reduction: computed** by rescoring a real mitigated
counterfactual through the same model, not invented → **One-click PDF
incident report**.

Runs fully offline from a pre-generated cache.

---

## Business impact — labeled honestly

*(All figures: simulation output — measured count × disclosed assumption. Full basis in `data/cost_basis.md`.)*

| Figure | Value | Basis |
|---|---|---|
| Near-misses prevented/yr | 12 | 3 archetypes × 4/yr assumed × 100% detected |
| Downtime avoided/yr | 48h | 4h assumed per incident |
| Cost avoided/yr | ₹36,00,000 | ₹3,00,000 assumed per incident |
| Unsafe entries flagged | 20/20 | Measured, not assumed |

No "lives saved" figure — a life-safety claim tied to a simulation would
be dishonest regardless of labeling.

---

# The ask

PlantPulse is a fusion layer, not a new sensor: it recalibrates against a
plant's own historian and its own asset/zone topology — no new hardware.

**We're asking for the chance to pilot this against one real facility's
historian data.**

Repo: github.com/sahaj645/et-hack
