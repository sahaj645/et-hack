# PlantPulse

Not a sensor alarm — a Plant Intelligence system that fuses everything a
control room already knows (sensors, equipment health, permit-to-work,
maintenance schedule, worker location, weather) into one explainable
compound-risk score. The point: individual channels can each read "normal"
while their combination is lethal, and no single-sensor threshold alarm
catches that. PlantPulse does.

Built for ET AI Hackathon 2.0, Problem Statement #1 (Industrial Safety
Intelligence). See [ARCHITECTURE.md](ARCHITECTURE.md) for the system design.

## Status: Session 2 — fusion engine + baselines + metrics

- [x] `engine/data_model.py` — Assets, Workers, Zones, Permits, Maintenance, Weather
- [x] `engine/simulator.py` — seeded correlated time-series + 3 compound archetypes
- [x] `engine/export.py` — writes `web/public/data/scenario.json` + `metrics.json`
- [x] `engine/preview.py` — sanity-check plots in `engine/_preview/`
- [x] `engine/agents/{sensor,equipment,permit,maintenance,worker,weather}_agent.py`
      — six independently-explainable specialist agents
- [x] `engine/agents/risk_agent.py` — fuses agents + hero model into a 0-100
      risk score, ranked contributor breakdown, and non-random confidence
- [x] `engine/engine/{calibration,features,model,baselines,metrics}.py`
      — 30-day normal-operation calibration, IsolationForest hero model,
      two conventional baselines, pure metric-calculation functions
- [x] `engine/metrics/run.py` — hero vs both baselines across 20 seeded
      days, writes `engine/metrics/results.json`

Not built yet: Next.js control room UI (S3), knowledge graph (S4), copilot
+ SOPs (S5), what-if slider (S6), write-up (S7). The `web/` app currently
boots to a placeholder page only.

## Run it — engine

```bash
cd engine
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

python export.py    # writes web/public/data/scenario.json
python preview.py   # writes sanity-check plots to engine/_preview/
```

`export.py` and `preview.py` are fully deterministic (fixed seed = 42, no
network) — re-running either produces byte-identical output.

## Run it — web (scaffold only, S3 builds the actual control room)

```bash
cd web
pnpm install   # or npm install
pnpm dev       # or npm run dev
```

## The three compound incidents

Each is tuned so every individual sensor channel it touches stays under its
own single-channel alarm threshold for the entire window — verified
automatically at generation time (`_validate_single_channel_normalcy` in
`engine/simulator.py`). The danger only appears when you read the channels
together with what else is happening in the plant.

1. **Slow gas leak masked by ventilation failure** (02:00–04:00) — gas
   concentration ramps to 45% of alarm while wind collapses to near-calm and
   an unpermitted worker enters the Tank Farm.
2. **Early bearing failure on an overdue-maintenance compressor**
   (09:00–13:00) — vibration and discharge temperature both trend up but
   stay under alarm; the tell is a maintenance task overdue by six days and
   a health score that keeps falling after the readings settle back down.
3. **Overpressure risk while the relief path is degraded** (16:00–18:00) —
   tank pressure and shell temperature climb with the afternoon heat but
   stay under alarm, while the relief valve is mid function-test (~50%
   effective capacity) and an active hot-work permit is issued in the same
   restricted zone.

## Repo layout

```
plantpulse/
├── engine/
│   ├── data_model.py  simulator.py  export.py  preview.py
│   ├── agents/ engine/ copilot/ metrics/    (S2+)
│   ├── _preview/                            sanity-check PNGs
│   └── requirements.txt
├── web/
│   ├── app/ components/ lib/
│   └── public/data/scenario.json
├── data/                                    (S5: sop_library.json, cost_basis.md)
├── README.md
└── ARCHITECTURE.md
```

## Stack

Frontend: Next.js 14 (App Router) + TypeScript + Tailwind + Framer Motion,
Recharts, custom SVG twin/heatmap, react-force-graph for the knowledge graph.
Engine: Python 3.11+, numpy, pandas, scikit-learn, networkx, FastAPI,
reportlab. Copilot: LLM answers cached to JSON + templated offline fallback.
