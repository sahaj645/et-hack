# PlantPulse

PlantPulse is a compound-risk scoring system for industrial plants. It's not
a sensor alarm — it's what sits on top of the sensors and everything else in
the control room (equipment health, permits, maintenance schedules, worker
location, weather) and asks a question none of those systems ask on their
own: what if every one of these readings is individually fine, but the
combination isn't?

That's the actual failure mode behind a lot of real industrial incident
reports. Read the post-mortems and they all say some version of "every
system worked as designed." The gas detector was under threshold. The
permit was valid. The maintenance log wasn't overdue by much. Nobody was
watching the combination, because nothing in the plant is built to.

Built solo over one week for ET AI Hackathon 2.0, Problem Statement #1
(Industrial Safety Intelligence). Everything in this repo — the simulator,
the six agents, the anomaly model, the control room, the copilot, the
reports — was built and evaluated from scratch across seven sessions, with
Claude Code as a pair-programmer and no runtime LLM calls in the shipped
product.

## What it actually does

Three synthetic incidents are baked into the simulator, and each one is
deliberately designed so that no single sensor channel involved ever
crosses its own alarm threshold — there's a function,
`_validate_single_channel_normalcy` in `engine/simulator.py`, that refuses
to generate the scenario if it does. That constraint is the whole point:
if a conventional threshold alarm could catch it, it wouldn't prove
anything.

1. **Gas leak, masked by a ventilation failure.** Gas concentration drifts
   up slowly between 02:00 and 04:00 while wind speed collapses toward
   calm, and an unpermitted worker walks into the Tank Farm zone in the
   middle of it.
2. **Bearing failure that's already underway.** Vibration and discharge
   temperature both creep upward from 09:00 to 13:00, never enough to
   alarm, on a compressor whose maintenance task is six days overdue and
   whose health score keeps dropping even after the readings settle.
3. **Overpressure with a degraded relief path.** Tank pressure and shell
   temperature climb with the afternoon heat (16:00–18:00), staying under
   alarm the whole time, while the relief valve is mid function-test and
   there's an active hot-work permit in the same restricted zone.

Six small agents each watch one slice of plant state — sensors, equipment
health, permits, maintenance, worker location, weather — and an
IsolationForest trained only on 30 quiet calibration days watches all of
it jointly, since it's the actual combination that matters and I didn't
want a model trained to memorize three specific fixtures. Both get
converted from raw scores into a 0–100 number using a sigmoid anchored at
the calibrated alert threshold, not a percentile rank — percentile rank
turned out to be a real bug early on (see below), since it's uniformly
distributed on in-distribution data and made the fused score look
"moderately elevated" on completely ordinary days about half the time.
On top of that blend there's one hard-coded rule: if at least two agents
independently report something meaningfully elevated and it holds for ten
minutes straight, that counts as an alert on its own, because "several
weak signals agreeing" is the actual thesis of this project and I'd
rather encode it explicitly than hope the model finds it.

## Does it actually work better

Yes, and here's the number, not the adjective. Evaluated against a plain
single-channel threshold alarm and a rolling z-score baseline (a real
adaptive baseline — both mean and standard deviation move with a trailing
window, not a strawman), across 20 independently seeded evaluation days
(60 archetype instances total) plus 20 held-out quiet days to measure
false alarms:

| Method | Detected | Median lead time | False alarms / day |
|---|---|---|---|
| PlantPulse | 100% | 99.8 min | 7.05 |
| Threshold baseline | 0% | never fires, by construction | 0.00 |
| Rolling z-score baseline | 100% | 92.4 min | 8.30 |

PlantPulse beats the z-score baseline on lead time for two of the three
archetypes. On the third — overpressure, the fastest-onset one on purpose
— it loses by about a minute (38.5 vs. 39.6 min). I could close that gap,
and did try, but every version that won all three cost false-alarm rate,
and a system that cries wolf more than a basic baseline is a worse pitch
than one that's honest about a one-minute loss on the hardest case. So
that's what's reported. The full reasoning, plus nine other questions I
expect to get asked, is in [DEFENSE.md](DEFENSE.md).

Every number above comes straight out of
[`engine/metrics/results.json`](engine/metrics/results.json) — nothing in
the app or the docs states a metric that isn't traceable back to that
file.

## A couple of bugs worth mentioning

Two things broke in ways that were instructive enough to leave in the
project's memory rather than just quietly fix:

- The equipment-health signal (`compressor_health`) had zero variance
  across calibration days in its natural wear term, so the agent watching
  it treated any decline at all as "exactly the 1st percentile" — it fired
  constantly. Fixed by adding AR(1)-correlated noise to the wear term
  instead of loosening the agent's threshold.
- The fused risk score used percentile rank until partway through
  development, and percentile rank on in-distribution data is uniform by
  definition — so on a totally ordinary day, the score sat around 50 as
  often as not, which reads as "moderately worrying" even when nothing is
  happening. Replacing it with a sigmoid anchored at the calibrated alert
  threshold (50 = exactly at the line) fixed it, and the eval numbers
  barely moved, because the threshold recalibrates with the scale.

## Running it

**Engine** (Python 3.11+):

```bash
cd engine
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt

python metrics/run.py     # hero vs. baselines -> engine/metrics/results.json
python export.py          # writes everything in web/public/data/*.json + PDF reports
python preview.py         # quick sanity plots -> engine/_preview/
```

Fixed seed (42), no network calls, so re-running any of these three
produces byte-identical output. Run `metrics/run.py` before `export.py`
the first time — `export.py` copies `results.json` into the web app's
data folder and builds the impact board and PDF reports from it, but
never computes a metric itself.

**Web app:**

```bash
cd web
pnpm install   # or npm install
pnpm dev       # or npm run dev
```

Live, Demo, and Knowledge tabs run entirely off the JSON `export.py`
wrote — none of them touch a network endpoint.

**Live what-if API** (optional — only powers one slider):

```bash
uvicorn engine.api:app --reload --port 8000
```

This is the one part of the stack with a live backend, and it's
deliberately upside-only: it powers the ventilation/maintenance sliders
on the Demo tab and nothing else. If it's not running, the slider falls
back to a precomputed grid (`web/public/data/whatif_fallback.json`) built
by the exact same scoring function the live endpoint calls, so the rest
of the demo — including the cinematic playback — never depends on it
being up. I tested this by killing the API mid-demo.

## Layout

```
et-hack/
├── engine/
│   ├── data_model.py  simulator.py  export.py  preview.py  api.py
│   ├── agents/        sensor, equipment, permit, maintenance, worker,
│   │                   weather, risk, sop, report agents
│   ├── engine/         calibration, features, model, baselines, metrics,
│   │                    knowledge_graph, impact, whatif
│   ├── copilot/         llm.py, templates.py, cache.json
│   └── metrics/         run.py, results.json
├── web/
│   ├── app/  components/  lib/
│   └── public/data/*.json   public/reports/*.pdf
├── data/                sop_library.json, cost_basis.md
├── docs/                 dataflow.mmd, kg-schema.mmd
└── deck/                 deck.md, deck.pdf
```

Frontend is Next.js 14 (App Router) + TypeScript + Tailwind + Framer
Motion + Recharts, with a hand-built SVG plant twin/heatmap and
react-force-graph-2d for the knowledge graph. Engine is Python — numpy,
pandas, scikit-learn, networkx, FastAPI, reportlab. The copilot answers
are templated over real computed data and cached to JSON; there's no live
LLM call anywhere in the shipped product, and `engine/copilot/llm.py`
says exactly why.

## What's real and what isn't

All of the plant telemetry is simulated — `engine/simulator.py` generates
it from a fixed seed, built to be physically plausible (correlated noise,
diurnal cycles, ISO-10816-ish vibration bands, realistic gas-detector
ranges) but not derived from or claiming to be any real facility's data.
The evaluation numbers above are real in the sense that matters: they
come from actually running the model against 20 different seeded days,
not from cherry-picking one good run.

The business-impact figures on the Demo tab (near-misses prevented,
downtime avoided, cost avoided) are real arithmetic on a disclosed
assumption — full basis in [`data/cost_basis.md`](data/cost_basis.md) —
and every one of them is labeled "simulation output" in the UI itself,
not just in this file. There's deliberately no "lives saved" number
anywhere in the project; that's the one figure where dressing up a
simulation as a safety claim would actually be dishonest rather than
just optimistic.

The SOP steps cited by the copilot reference real regulatory documents —
OISD-STD-105 (India's Oil Industry Safety Directorate work-permit
standard) and the Factories Act, 1948 — by name and section, not
reproduced verbatim; see the `citation_note` in
[`data/sop_library.json`](data/sop_library.json).

Diagrams are Mermaid (renders natively on GitHub/VS Code, source in
`docs/*.mmd`), and the deck was built with Marp CLI from `deck/deck.md`.
All third-party packages — Next.js, React, scikit-learn, FastAPI, and the
rest — are installed unmodified from their public registries under their
own open-source licences.

## More detail

- [ARCHITECTURE.md](ARCHITECTURE.md) — system design, data flow, knowledge-graph schema
- [SUBMISSION.md](SUBMISSION.md) — the hackathon submission write-up
- [DEFENSE.md](DEFENSE.md) — the ten questions I expect judges to ask, answered in advance
- [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md) — shot-by-shot demo video script
- [deck/deck.md](deck/deck.md) / [deck/deck.pdf](deck/deck.pdf) — the pitch deck
