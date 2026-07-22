# PlantPulse — Architecture

```
[ Python engine ] --exports--> web/public/data/*.json --> [ Next.js control room ]
  sim + model + KG + metrics                                plays precomputed demo
        |                                                    live what-if slider
        +----------------------- FastAPI <-------------------------+
```

- **Python is the brains.** `engine/` runs offline, seeded, deterministic. It
  owns the simulator, the fusion model, the knowledge graph, and all metrics.
  Nothing in it depends on the network or on the web app being up.
- **Next.js is the face.** `web/` renders whatever JSON `engine/export.py`
  (and later `engine/metrics/run.py`) wrote to `web/public/data/`. The main
  demo path plays back precomputed JSON — it cannot break on stage because
  it never depends on a live process.
- **FastAPI is upside, not a dependency.** `engine/api.py` (S6) powers only
  the live what-if slider. If it's down, the rest of the demo is unaffected.

## Determinism

Every simulation run uses a fixed seed (`engine/simulator.py::SEED`). Same
seed in -> byte-identical DataFrame out, every time. This is what lets the
demo be scripted and rehearsed instead of hoped for.

## Honesty guardrails

- No metric is ever hand-edited. `engine/metrics/run.py` (S2) is the only
  place performance numbers come from — if a number is weak, the scenario
  gets redesigned and re-run, not the number.
- Any business/₹ figure is labeled a simulation output and traces to
  `data/cost_basis.md` (S5): cited assumptions × simulated incident counts.
- The three compound-incident archetypes (`engine/simulator.py`) are
  constructed so every affected raw sensor channel stays under its own
  single-channel alarm threshold for the full incident window — enforced by
  `_validate_single_channel_normalcy`, which raises if an archetype
  accidentally becomes a normal single-sensor alarm.

## Module map

| Path | Owns | Session |
|---|---|---|
| `engine/data_model.py` | Assets, Workers, Zones, Permits, Maintenance, Weather | S1 |
| `engine/simulator.py` | Seeded time-series + 3 compound archetypes | S1 |
| `engine/export.py` | Writes `web/public/data/scenario.json` | S1 |
| `engine/preview.py` | Sanity-check plots in `engine/_preview/` | S1 |
| `engine/agents/` | Per-domain agents (sensor, equipment, permit, ...) | S2 |
| `engine/engine/` | `features.py`, `model.py`, `metrics.py`, `knowledge_graph.py` — the fusion engine | S2, S4 |
| `engine/metrics/run.py` | Real evaluation on simulated data -> `results.json` | S2 |
| `web/app/` | Live / Demo / Metrics / Knowledge tabs | S3+ |
| `web/components/` | Twin, Heatmap, Gauge, ContributorBars, KnowledgeGraph, Copilot, Timeline, WhatIf | S3-S6 |
| `engine/copilot/` | Cached LLM answers + templated offline fallback | S5 |
| `engine/api.py` | FastAPI service for the live what-if slider | S6 |
