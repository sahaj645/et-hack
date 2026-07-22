# PlantPulse — ET AI Hackathon 2.0, Problem Statement #1 (Industrial Safety Intelligence)

## Innovation

PlantPulse's claim is narrow and falsifiable: individual sensor channels can
each read "normal" while their combination is lethal, and a conventional
single-sensor alarm structurally cannot see that — it only ever has one
signal to look at. We didn't just assert this; we built three physically
realistic compound-incident archetypes (a slow gas leak masked by a
ventilation failure, an early bearing failure on an overdue-maintenance
compressor, an overpressure risk while the relief path is degraded) where
every affected channel is *validated at generation time* to stay under its
own alarm threshold for the entire incident window — if an archetype ever
breaches that constraint, the code raises and the run fails, not the
metric. On top of that we fused six independently-explainable domain
agents (sensor, equipment, permit, maintenance, worker, weather) with a
genuinely multivariate IsolationForest, anchored the resulting score at a
calibrated alert threshold instead of a raw percentile rank (percentile
rank is uniformly distributed on in-distribution data — a subtlety that
cost us a real debugging session before we caught it), and added an
explicit cross-signal early-trigger rule: several independent signals
mildly agreeing counts as real evidence, which is the literal thesis, made
computable rather than left to hope.

## Technical Implementation

The system is a deterministic three-layer pipeline: a seeded Python engine
(simulator → six agents → IsolationForest hero model → knowledge graph →
SOP/copilot/PDF-report generation) exports JSON artifacts that a Next.js
control room renders, with a small FastAPI service powering only the
live what-if slider — never a dependency for the core demo. Every seed is
fixed; re-running `engine/export.py` or `engine/metrics/run.py` produces
byte-identical output, verified directly (SHA-256 comparison across
repeated runs). The hero model is trained exclusively on 30 seeded quiet
days — never on the 3 archetypes — specifically so the reported metrics
measure genuine anomaly detection rather than memorized fixtures. Measured
on 20 held-out seeded evaluation days (60 archetype instances): **100%
detection at a median 99.8-minute lead time over an extrapolated
conventional alarm, with 7.05 false alarms/day versus a rolling z-score
baseline's 8.30** — and the hero model wins on lead time on two of the
three archetypes individually, not just in aggregate. On the third
(overpressure, the fastest-onset archetype), it trails the z-score
baseline by roughly a minute; we report that rather than tune it away,
because tuning it away is exactly the failure mode this project is built
to avoid in the plant, not just in the metrics table.

## Feasibility / Scalability

Every number a judge can click through traces to `engine/metrics/results.json`
or `data/cost_basis.md` — nothing in the UI, deck, or this document is
hand-typed. The architecture is deliberately boring where it needs to be:
JSON contracts between Python and the frontend, a model retrained from
30 days of an existing SCADA/DCS historian's normal-operation data (no new
sensor hardware required), and six agents that map one-to-one onto data a
real control room already has (permits, maintenance schedules, worker
location, weather, and the sensors themselves). Scaling to a real facility
means recalibrating the six agents' normal-operation statistics against
that facility's own historian, retraining the IsolationForest on that
plant's quiet-day telemetry, and encoding that plant's actual asset/zone
topology into the knowledge graph — all mechanical, none of it requiring a
new archetype-design cycle, because the model is unsupervised and
therefore not limited to the 3 patterns we validated against.

## Problem Relevance

Compound, cross-domain industrial incidents — a permit issued without
visibility into equipment state, a worker in a restricted zone without
visibility into atmospheric conditions, a maintenance delay without
visibility into a live process excursion — are exactly the class of
incident that post-mortems repeatedly describe as "every individual
system worked as designed." PlantPulse is aimed at that specific gap: not
a better single-sensor alarm, but the fusion layer that reads permits,
maintenance state, worker location, and weather *alongside* the sensors,
because that is where compound risk actually lives and where a
conventional DCS/SCADA setup has no visibility at all.

## Documentation / Presentation

The full pipeline — simulator, six agents, hero model, two baselines,
evaluation harness, knowledge graph, SOP library, copilot, PDF report
generator, cinematic demo, live what-if API, and impact board — is
committed with a session-by-session build history, an `ARCHITECTURE.md`
with the data-flow and knowledge-graph diagrams, a `DEFENSE.md` prepared
for the hardest questions a judge is likely to ask, and a `data/cost_basis.md`
that discloses every assumption behind every ₹ or hour figure on the
impact board. Simulation methodology is disclosed openly throughout: this
is simulated plant data, not a real deployment, and every place that
matters says so explicitly rather than leaving it to be inferred.
