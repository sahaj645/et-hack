# PlantPulse

Not a sensor alarm — a Plant Intelligence system that fuses everything a
control room already knows (sensors, equipment health, permit-to-work,
maintenance schedule, worker location, weather) into one explainable
compound-risk score. The point: individual channels can each read "normal"
while their combination is lethal, and no single-sensor threshold alarm
catches that. PlantPulse does.

Built for ET AI Hackathon 2.0, Problem Statement #1 (Industrial Safety
Intelligence). See [ARCHITECTURE.md](ARCHITECTURE.md) for the system design.

## Status: Session 6 — cinematic demo + live what-if + impact board

- [x] S1 — engine foundation + seeded simulator, 3 compound archetypes
- [x] S2 — fusion engine (6 agents + IsolationForest hero model), two
      conventional baselines, `engine/metrics/run.py` evaluation harness
- [x] S3 — Next.js control room: plant twin, geospatial heatmap, live traces
- [x] S4 — ranked contributor breakdown + confidence, plant knowledge graph
- [x] S5 — operations copilot (cause → SOP → estimated risk reduction),
      cited OISD/Factories Act SOP library, PDF incident reports
- [x] S6 — cinematic Demo tab, FastAPI what-if backend, labeled impact board

Not built yet: submission write-up, deck, video script, defense doc (S7).

## Run it — engine

```bash
cd engine
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

python export.py             # writes every web/public/data/*.json + PDF reports
python preview.py            # sanity-check plots -> engine/_preview/
python metrics/run.py        # hero vs. baselines evaluation -> metrics/results.json
```

`export.py`, `preview.py`, and `metrics/run.py` are fully deterministic
(fixed seed = 42, no network) — re-running any of them produces
byte-identical output. Run `metrics/run.py` before `export.py` if
`engine/metrics/results.json` doesn't exist yet — `export.py` copies it
into `web/public/data/metrics.json` and uses it to build the impact board
and PDF reports; it never computes a metric itself.

## Run it — web

```bash
cd web
pnpm install   # or npm install
pnpm dev       # or npm run dev
```

Everything except the live what-if slider works fully offline from the
JSON `export.py` wrote — the Live, Demo, and Knowledge tabs never call a
network endpoint.

## Run it — live what-if API (optional, upside-only)

```bash
# from the repo root
uvicorn engine.api:app --reload --port 8000
```

Powers only the ventilation/maintenance sliders on the Demo tab
(`components/WhatIf.tsx`). If this isn't running, the slider falls back to
a precomputed grid (`web/public/data/whatif_fallback.json`, built by the
same scoring function the live endpoint uses) so the rest of the app —
including the cinematic demo — never depends on it.

## The three compound incidents

Each is tuned so every individual sensor channel it touches stays under its
own single-channel alarm threshold for the entire window — verified
automatically at generation time (`_validate_single_channel_normalcy` in
`engine/simulator.py`). The danger only appears when you read the channels
together with what else is happening in the plant.

1. **Slow gas leak masked by ventilation failure** (02:00–04:00) — gas
   concentration ramps up while wind collapses to near-calm and an
   unpermitted worker (W-05) enters the Tank Farm.
2. **Early bearing failure on an overdue-maintenance compressor**
   (09:00–13:00) — vibration and discharge temperature both trend up but
   stay under alarm; the tell is a maintenance task overdue by six days and
   a health score that keeps falling after the readings settle back down.
3. **Overpressure risk while the relief path is degraded** (16:00–18:00) —
   tank pressure and shell temperature climb with the afternoon heat but
   stay under alarm, while the relief valve is mid function-test and an
   active hot-work permit is issued in the same restricted zone.

## Measured results (`engine/metrics/results.json`)

Hero model vs. both baselines, 20 seeded evaluation days (60 archetype
instances) + 20 held-out quiet days for false-alarm rate:

| Method | Detected | Median Lead Time | False Alarms/Day |
|---|---|---|---|
| PlantPulse (hero) | 100% | 99.8 min | 7.05 |
| Baseline A (threshold) | 0% | n/a (never fires) | 0.00 |
| Baseline B (rolling z-score) | 100% | 92.4 min | 8.30 |

## Repo layout

```
et-hack/
├── engine/
│   ├── data_model.py  simulator.py  export.py  preview.py  api.py
│   ├── agents/       sensor/equipment/permit/maintenance/worker/weather
│   │                 _agent.py, risk_agent.py, sop_agent.py, report_agent.py
│   ├── engine/       calibration, features, model, baselines, metrics,
│   │                 knowledge_graph, impact, whatif
│   ├── copilot/      llm.py, templates.py, cache.json
│   ├── metrics/      run.py, results.json
│   └── requirements.txt
├── web/
│   ├── app/ components/ lib/
│   └── public/data/*.json   public/reports/*.pdf
├── data/             sop_library.json, cost_basis.md
├── README.md
└── ARCHITECTURE.md
```

## Stack

Frontend: Next.js 14 (App Router) + TypeScript + Tailwind + Framer Motion,
Recharts, custom SVG twin/heatmap, react-force-graph for the knowledge graph.
Engine: Python 3.11+, numpy, pandas, scikit-learn, networkx, FastAPI,
reportlab. Copilot: templated answers over real computed data, cached to
JSON — see `engine/copilot/llm.py` for why no live LLM call is made.

## Tools, data, and licences (declared)

- **Data**: 100% simulated. `engine/simulator.py` generates seeded synthetic
  plant telemetry — no real facility's data, logs, or historian is used
  anywhere in this project.
- **Third-party libraries** (all open source, standard licences — see each
  package's own repository): Next.js, React, TypeScript, Tailwind CSS,
  Framer Motion, Recharts, react-force-graph-2d (frontend); numpy, pandas,
  scikit-learn, networkx, FastAPI, uvicorn, pydantic, reportlab, matplotlib
  (engine). Installed via `npm`/`pip` from public registries, unmodified.
- **Regulatory references**: `data/sop_library.json` cites OISD-STD-105
  (Work Permit System, published by India's Oil Industry Safety
  Directorate) and the Factories Act, 1948 — cited by name/section for the
  topic they govern, not reproduced verbatim; see the file's own
  `citation_note` for the exact disclosure.
- **AI assistance**: built with Claude Code (Anthropic) as a pair-programming
  tool across all sessions. No LLM is called at runtime by the shipped
  product — see `engine/copilot/llm.py`.
- **Diagrams**: Mermaid (MIT licence), rendered natively in
  `ARCHITECTURE.md` on GitHub/VS Code; source files also in `docs/*.mmd`.
- **Deck**: built with Marp CLI (MIT licence) from `deck/deck.md`.
