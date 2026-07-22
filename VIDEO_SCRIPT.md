# PlantPulse — Video Script (~2:45)

Shot-by-shot. Every number spoken or shown is real, sourced from
`engine/metrics/results.json`, `web/public/data/impact_summary.json`, or
`web/public/data/demo_highlight.json` — nothing here is written to sound
good, it's written to match what the app actually shows.

## Production rules

- **No live typing, no spinners.** Every screen shown is either already
  loaded or a clean cut past the loading state.
- **Captions on for every spoken line** (accessibility + judges reviewing muted).
- **Two takes minimum** for the Demo Mode segment specifically — it's a
  timed 90-second in-app sequence; record it start-to-finish rather than
  cutting mid-sequence, and pick the cleaner of two full runs.
- **Screen-record at 1280x800 or larger**, Demo tab, freshly reloaded page
  each take (confirms determinism incidentally — both takes should show
  the same numbers).
- Cut the 90-second in-app Demo Mode down to ~55s of screen time using
  jump cuts between beats (not real-time playback) — note exactly where
  below.

---

## 0:00–0:12 — Cold open

**VISUAL:** Black screen, then a single stat fades in white-on-black:
"Every year, industrial incidents are traced back to conditions where
every individual sensor read normal."

**VO:** "The reports all say the same thing afterward: every system
worked as designed. The gas detector was fine. The permit was valid.
The maintenance log was up to date. And it still happened."

## 0:12–0:25 — "Two normal traces, one lethal combination"

**VISUAL:** Cut to the Live tab. Show the gas concentration trace and
wind-speed trace side by side, both clearly within their normal-looking
range — then cut to the compound risk gauge climbing past 80 in the same
moment.

**VO:** "Individually, these two readings are unremarkable. Together,
they're the compound risk PlantPulse exists to catch — and a
conventional single-sensor alarm structurally cannot see it, because it
only ever looks at one signal at a time."

## 0:25–0:35 — Cut to Demo Mode

**VISUAL:** Switch to the Demo tab. Show the "PLAY MOVIE" button once,
click it on camera.

**VO:** "Here's the same incident, start to finish."

## 0:35–1:30 — Demo Mode (compressed to ~55s of screen time)

Jump-cut through the real in-app beats — don't show all 90 seconds of
real time, cut between these exact moments:

1. **(app t=0s)** Calm state, gauge low, all zones green. *[hold 3s]*
2. **(app t=19s)** ALERT banner appears, gauge crosses threshold — no
   single sensor has alarmed. *[hold 4s]*
   **VO:** "PlantPulse alerts here — while every raw reading is still
   inside its own normal band."
3. **(app t=27s)** Worker W-05 enters Tank Farm without an active
   permit — worker dot turns red. *[hold 4s]*
4. **(app t=35s)** Risk climbs to 88, Tank Farm zone turns RESTRICTED,
   contributor bars populate (Sensor, Weather, Equipment, Worker).
   *[hold 5s]*
5. **(app t=44s)** Knowledge graph panel: hazardous path lights up, real
   sentence on screen. *[hold 5s, let the sentence be readable]*
6. **(app t=53s)** Copilot panel: cause bullets → SOP-GAS-01 → estimated
   risk reduction. *[hold 5s]*
7. **(app t=61s)** PDF report reveal. *[hold 2s]*
8. **(app t=76s)** Projection callout: "a conventional single-sensor
   alarm would not have fired until an estimated 04:34." *[hold 4s]*
9. **(app t=84s)** LEAD TIME counter counts up on screen: **2h 28m 42s**.
   *[hold full count-up, ~4s, then hold on final number 3s more]*

**VO (over beat 9):** "Two hours and twenty-eight minutes. That's how
much earlier PlantPulse would have caught this than a conventional
system — measured the same way our own evaluation measures it, not a
number picked to look good."

## 1:30–1:50 — The metric that matters

**VISUAL:** Cut to a clean results table (from the deck or README):
100% detected · 99.8 min median lead time · 7.05 false alarms/day vs.
8.30 for a rolling z-score baseline.

**VO:** "Across twenty independently seeded evaluation days — sixty
compound-incident instances — PlantPulse detected all of them, with a
median lead time of ninety-nine point eight minutes over an extrapolated
conventional alarm, and fewer false alarms per day than a standard
statistical baseline. It wins on lead time on two of the three incident
types individually — the third, the fastest-onset one, it trails by
about a minute, and we're telling you that on purpose."

## 1:50–2:00 — Architecture / knowledge graph flash (10s)

**VISUAL:** Quick flash of the architecture diagram (Python engine →
JSON → Next.js), then the knowledge-graph schema.

**VO:** "Six explainable agents, one genuinely multivariate model trained
only on normal operation, fused into a score anchored at a calibrated
alert threshold — and a knowledge graph that explains why, not just
that."

## 2:00–2:20 — Business impact (one-liner)

**VISUAL:** Impact board, all four "Simulation output" labels visible.

**VO:** "Every business figure here is labeled a simulation output and
traces to a disclosed assumption — twelve near-misses prevented a year,
forty-eight hours of downtime avoided, thirty-six lakh rupees avoided,
all clearly cited, none of it a real-world claim."

## 2:20–2:45 — Close

**VISUAL:** PlantPulse wordmark, repo link.

**VO:** "PlantPulse isn't a new sensor — it's the fusion layer plants
already have the data for. We're asking for the chance to pilot it
against one real facility's historian."

**ON SCREEN:** `github.com/sahaj645/et-hack`
