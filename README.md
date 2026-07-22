# PlantPulse

**Compound-risk intelligence for industrial safety.**

PlantPulse fuses sensor telemetry, equipment health, permit-to-work status,
maintenance schedules, worker location, and weather into a single
explainable risk score. It targets a specific failure mode: incidents where
every individual channel reads within normal range, but the *combination*
is dangerous — a condition a conventional single-sensor threshold alarm
cannot detect by construction.

Submitted to **ET AI Hackathon 2.0, Problem Statement #1 — Industrial
Safety Intelligence**.

| | |
|---|---|
| **Documentation** | [Architecture](ARCHITECTURE.md) · [Submission](SUBMISSION.md) · [Defense Q&A](DEFENSE.md) · [Video script](VIDEO_SCRIPT.md) · [Deck](deck/deck.pdf) |
| **Status** | All planned sessions (S1–S7) complete |
| **Stack** | Python (engine) · Next.js/TypeScript (control room) |

---

## Overview

Post-incident investigations at industrial sites frequently conclude that
"every system worked as designed" — each individual reading was within
tolerance, yet the incident still occurred. This happens because no system
in a typical control room evaluates signals jointly; permit systems,
maintenance schedulers, and sensor alarms each operate on their own slice
of plant state.

PlantPulse addresses this by combining six domain-specific detectors with
an unsupervised multivariate anomaly model, producing one calibrated 0–100
risk score with a ranked, explainable breakdown of contributing factors and
a knowledge-graph-generated causal narrative.

## Key capabilities

- **Compound-risk detection** — six specialist agents (sensor, equipment
  health, permit, maintenance, worker location, weather) plus an
  IsolationForest model trained exclusively on quiet-period data, fused
  into one calibrated score anchored at a fixed alert threshold.
- **Explainability by construction** — every alert is backed by a ranked
  contributor breakdown and a plant knowledge graph traversal that
  generates a plain-language causal explanation from real graph and event
  data, not a static template.
- **Operations copilot** — cause → recommended SOP → estimated risk
  reduction, with SOP steps cited to OISD-STD-105 and the Factories Act,
  1948, and risk-reduction estimates computed by re-scoring a genuine
  mitigated counterfactual scenario.
- **Incident reporting** — one-click PDF incident reports generated from
  the same computed data shown in the UI.
- **Live what-if analysis** — a FastAPI service exposes real-time
  counterfactual scoring (e.g., "what if ventilation were restored");
  the UI degrades gracefully to a precomputed equivalent if the service is
  unavailable, so no part of the core product depends on a live backend.
- **Deterministic, auditable pipeline** — every stage (simulation,
  calibration, scoring, evaluation) runs from a fixed random seed with no
  network dependency, producing byte-identical output on every run.

## Validated incident archetypes

Three synthetic incident types are used for evaluation. Each is
constructed so that every affected sensor channel remains under its own
single-channel alarm threshold for the full duration of the incident — a
constraint enforced programmatically at generation time
(`_validate_single_channel_normalcy` in `engine/simulator.py`), not merely
asserted.

| Archetype | Window | Compounding factors |
|---|---|---|
| Gas leak, masked by ventilation failure | 02:00–04:00 | Rising gas concentration + near-calm wind + unpermitted worker in zone |
| Early bearing failure | 09:00–13:00 | Rising vibration and temperature + maintenance overdue 6 days |
| Overpressure with degraded relief path | 16:00–18:00 | Rising pressure and temperature + relief valve mid-test + active hot-work permit |

## Evaluation results

Evaluated against two conventional baselines across 20 independently
seeded evaluation days (60 archetype instances total), with false-alarm
rate measured on 20 additional held-out quiet days. Full source data:
[`engine/metrics/results.json`](engine/metrics/results.json).

| Method | Detection rate | Median lead time | False alarms / day |
|---|---|---|---|
| **PlantPulse** | **100%** | **99.8 min** | **7.05** |
| Baseline A — single-channel threshold | 0% | N/A (never fires) | 0.00 |
| Baseline B — rolling z-score | 100% | 92.4 min | 8.30 |

PlantPulse outperforms both baselines on aggregate lead time and improves
on Baseline B's false-alarm rate. It leads on lead time for two of the
three archetypes individually; on the fastest-onset archetype
(overpressure) it trails Baseline B by approximately one minute (38.5 vs.
39.6 min). This result is reported as measured rather than adjusted,
consistent with the project's evaluation methodology — see
[DEFENSE.md](DEFENSE.md) for the full rationale.

## Architecture

```
Python engine (offline, seeded)
  simulator → 6 agents + IsolationForest → fused risk score
        │
        ├── export.py ──► static JSON + PDF reports ──► Next.js control room
        │
        └── FastAPI (optional, upside-only) ──► live what-if scoring
```

The engine computes everything; the frontend renders it. The only
component with a live backend dependency is the what-if slider, and it
falls back to a precomputed grid built by the identical scoring function
if the API is unreachable. See [ARCHITECTURE.md](ARCHITECTURE.md) for the
full data-flow and knowledge-graph schema diagrams.

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 18+ and pnpm (or npm)

### Engine

```bash
cd engine
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

python metrics/run.py         # evaluation: hero model vs. baselines
python export.py              # generates all web/public/data/*.json + PDF reports
python preview.py             # optional: sanity-check plots -> engine/_preview/
```

All engine entry points are deterministic (fixed seed = 42, no network
access) and produce byte-identical output across runs. Run
`metrics/run.py` before `export.py` on a first run — `export.py` copies
`results.json` into the web app's data directory and uses it to build the
impact board and PDF reports, without independently computing any metric.

### Web application

```bash
cd web
pnpm install
pnpm dev
```

The Live, Demo, and Knowledge tabs run entirely from the JSON files
`export.py` generates and make no network calls.

### Live what-if API (optional)

```bash
# from repository root
uvicorn engine.api:app --reload --port 8000
```

Serves only the ventilation/maintenance what-if sliders on the Demo tab.
If unavailable, the UI transparently falls back to
`web/public/data/whatif_fallback.json`.

## Project structure

```
et-hack/
├── engine/
│   ├── data_model.py  simulator.py  export.py  preview.py  api.py
│   ├── agents/          sensor_agent.py, equipment_agent.py, permit_agent.py,
│   │                     maintenance_agent.py, worker_agent.py, weather_agent.py,
│   │                     risk_agent.py, sop_agent.py, report_agent.py
│   ├── engine/           calibration.py, features.py, model.py, baselines.py,
│   │                     metrics.py, knowledge_graph.py, impact.py, whatif.py
│   ├── copilot/          llm.py, templates.py, cache.json
│   ├── metrics/          run.py, results.json
│   └── requirements.txt
├── web/
│   ├── app/  components/  lib/
│   └── public/data/*.json     public/reports/*.pdf
├── data/                 sop_library.json, cost_basis.md
├── docs/                  dataflow.mmd, kg-schema.mmd
├── deck/                  deck.md, deck.pdf
├── README.md
├── ARCHITECTURE.md
├── SUBMISSION.md
├── VIDEO_SCRIPT.md
└── DEFENSE.md
```

## Technology stack

| Layer | Technologies |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, Framer Motion, Recharts, react-force-graph-2d |
| Engine | Python 3.11+, NumPy, pandas, scikit-learn, NetworkX, FastAPI, ReportLab |
| Copilot | Templated response generation over computed engine output — no runtime LLM calls (see [`engine/copilot/llm.py`](engine/copilot/llm.py)) |

## Data, methodology, and disclosures

- **Data provenance.** All plant telemetry is synthetically generated by
  `engine/simulator.py` from a fixed random seed. It is designed to be
  physically plausible (correlated sensor noise, diurnal cycles,
  ISO-10816-consistent vibration bands, representative gas-detector
  ranges) but does not derive from, and does not claim to represent, any
  real facility.
- **Evaluation methodology.** All performance figures are computed by
  running the model against 20 independently seeded evaluation days;
  results are not selected from a single favorable run. Source data is
  version-controlled at `engine/metrics/results.json`.
- **Business-impact figures.** Figures shown on the Demo tab (incidents
  prevented, downtime avoided, cost avoided) are computed from a measured
  count multiplied by a disclosed assumption, and are labeled "Simulation
  output" in the UI. Full basis: [`data/cost_basis.md`](data/cost_basis.md).
  No safety-outcome claim (e.g., lives saved) is made anywhere in the
  project.
- **Regulatory references.** SOP content in
  [`data/sop_library.json`](data/sop_library.json) cites OISD-STD-105
  (India's Oil Industry Safety Directorate work-permit standard) and the
  Factories Act, 1948, by name and section; regulatory text is not
  reproduced verbatim.
- **AI-assisted development.** Built with Claude Code (Anthropic) as a
  development tool across all sessions. No LLM is invoked at runtime by
  the shipped product.
- **Third-party software.** All dependencies are unmodified packages from
  public registries (npm, PyPI), used under their respective open-source
  licenses.
- **Diagrams and deck.** Diagrams are authored in Mermaid (MIT license;
  source in `docs/*.mmd`, rendered natively by GitHub/VS Code). The pitch
  deck is built with Marp CLI (MIT license) from `deck/deck.md`.

## Documentation

| Document | Description |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, data flow, and knowledge-graph schema |
| [SUBMISSION.md](SUBMISSION.md) | Hackathon submission write-up |
| [DEFENSE.md](DEFENSE.md) | Prepared responses to anticipated evaluation questions |
| [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md) | Shot-by-shot demo video script |
| [deck/deck.md](deck/deck.md) / [deck/deck.pdf](deck/deck.pdf) | Pitch deck |
