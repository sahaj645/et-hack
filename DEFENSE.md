# PlantPulse — Defense Doc

Pre-written answers to the questions most likely to actually hurt if I
don't have a ready answer. Written in first person so I can say these
out loud without translating them first.

---

### 1. "Walk me through your code."

"There are three layers, and I'll walk through them in the order data
actually flows. First, `engine/simulator.py` — a seeded random-number
generator produces one 24-hour day of five correlated sensor channels,
and I inject three compound incidents into it. Each one is checked by a
function called `_validate_single_channel_normalcy` that literally
refuses to run if any single channel crosses its own alarm threshold —
that's the whole thesis enforced in code, not just claimed in a slide.

Second, `engine/agents/` and `engine/engine/model.py` — six small,
readable Python files each look at one domain (sensors, equipment
health, permits, maintenance, worker location, weather) and produce a
score, plus an IsolationForest model that looks at all fifteen
engineered features jointly. `risk_agent.py` fuses those into one 0-to-100
number, anchored at a calibrated threshold, with a ranked list of which
agent contributed how much.

Third, `engine/export.py` writes all of that to JSON files, and the
Next.js app in `web/` just renders those files — it never computes
anything itself except the live what-if slider, which calls a small
FastAPI service that does the exact same computation the Python side
already does. If you want to see it run: `python engine/export.py`
regenerates everything from scratch, deterministically, in under a
minute."

### 2. "Is the data real?"

"No, and I say that upfront everywhere it matters — the README, the
architecture doc, the impact board. It's simulated plant telemetry with
a fixed random seed, built to be physically realistic (correlated noise,
diurnal cycles, ISO-10816-style vibration bands, typical toxic-gas
detector ranges), not scraped or claimed to be from a real facility.
Every business figure on the impact board is explicitly labeled
'Simulation output' for the same reason. What is real is the
*evaluation* — the metrics in `results.json` come from actually running
the model against this simulated data 20 different seeded ways, not from
picking one flattering run."

### 3. "How is risk computed?"

"Two independent signals, blended 60/40. One is the IsolationForest's
anomaly score, converted from a raw path-length into a 0-to-100 number
using a sigmoid anchored at a calibrated alert threshold — 50 means
you're exactly at the line, not some arbitrary midpoint. The other is
the sum of the six agents' normalized scores, calibrated the same way.
On top of that there's one explicit rule: if at least two of the six
agents independently report something meaningfully elevated, sustained
for ten minutes, that counts as an alert even if the blended number
hasn't crossed the line yet — because several weak signals agreeing is
real evidence, and that's the literal point of this product, made into
a concrete rule instead of hoping the model discovers it."

### 4. "Why won't it false-alarm constantly?"

"It does false-alarm sometimes — 7.05 times per simulated day, measured
on 20 held-out quiet days where nothing is actually wrong. I report that
number because hiding it would be worse. What I can say is it's lower
than the rolling z-score baseline's 8.30, and I got there by fixing real
bugs, not by loosening the threshold — for example, I found that the
compressor's natural wear signal had zero variance across quiet days,
which made the agent watching it think '1% percentile of normal' was
the *same* as 'completely typical,' and it fired constantly. I fixed the
underlying signal, not the alarm count."

### 5. "How does this scale to a real plant?"

"The six agents are designed to map onto data a real control room
already has — permits, maintenance schedules, worker location systems,
weather feeds, and the sensors themselves. Scaling means recalibrating:
running 30 days of that plant's own historian through
`engine/engine/calibration.py` to learn what normal actually looks like
there, retraining the IsolationForest on that, and encoding that plant's
real zones and assets into the knowledge graph. None of that requires
designing new incident archetypes, because the hero model is
unsupervised — it was never trained to recognize these three specific
patterns, only to recognize deviation from that plant's own normal."

### 6. "Why IsolationForest and not a supervised model or deep learning?"

"Because I have exactly three hand-designed archetypes. A supervised
model trained on three examples doesn't learn 'compound risk' — it
learns to recognize my three fixtures, and the metrics would measure
memorization, not detection. Real plants match this problem too: you can
always get months of normal operation, you almost never have a labeled
set of real overpressure events. An unsupervised model trained purely on
normal operation is the honest thing to ship, and it's still genuinely
multivariate — it isolates a point by partitioning the *joint* feature
space, so something unremarkable on every individual feature can still
get flagged because the combination is rare."

### 7. "Your overpressure archetype loses to the baseline on lead time — doesn't that undermine your pitch?"

"It's a real, honest result and I'd rather you hear it from me than
notice it yourselves. On that specific archetype — the fastest-onset one
of the three, by design — PlantPulse trails the rolling z-score baseline
by about a minute, 38.5 versus 39.6. On the other two it wins clearly,
and overall it wins on the aggregate median. I spent real effort trying
to close that last gap and it kept coming at the cost of the false-alarm
rate, which I decided was the wrong trade — a system that cries wolf
more than a simple baseline is a worse pitch than one that's honest about
a one-minute gap on the hardest case. That's the same principle the
whole project is built on: I'd rather report a weak number than tune it
away."

### 8. "How do you know your baselines are fair, not strawmen?"

"Baseline A is a literal single-channel threshold alarm — that's what a
lot of legacy DCS/SCADA setups actually do, and it's *supposed* to never
fire on these archetypes, because that's the whole premise; I verify
that with an automated check, not by eyeballing it. Baseline B is a
rolling z-score — both the mean and the standard deviation adapt over a
trailing window, which is a real, textbook statistical-process-control
technique, and a genuinely stronger baseline than a fixed threshold. I
specifically did NOT make it weak: early in development it was
catching incidents almost as fast as my model, and instead of handicapping
it, I found the actual cause — my simulated sensor noise was
unrealistically clean — and fixed the simulation's realism, which is a
harder and more honest fix than just weakening the baseline would have
been."

### 9. "What happens if the FastAPI backend goes down during your live demo?"

"Nothing, on purpose. The cinematic demo and the rest of the app read
precomputed JSON and never call the API at all. Only the what-if slider
talks to it, and if that call fails or times out, `WhatIf.tsx` falls back
to a precomputed grid built by the exact same scoring function the live
endpoint uses — I tested this by killing the API mid-session and the
slider correctly switched to an 'OFFLINE — precomputed fallback' state
and returned the identical number the live call would have."

### 10. "Are your business impact numbers real?"

"They're real arithmetic on a disclosed assumption, which is different
from a real-world claim, and I labeled it that way everywhere it
appears. The measured part — 100% detection, 20 unsafe zone entries
flagged across 20 evaluation seeds — comes straight out of
`results.json`. The assumed part — that each of the three validated
patterns might recur once a quarter, that an avoided incident is worth
roughly four hours of downtime and about three lakh rupees — is an
illustrative, round, conservative estimate, and I say so directly in
`data/cost_basis.md`, including the line that actual costs vary by 10x
or more by facility. I deliberately don't show a 'lives saved' number at
all, because that's the one figure where dressing up a simulation as a
safety claim would actually be dishonest, not just optimistic."
