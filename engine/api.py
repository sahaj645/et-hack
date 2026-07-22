"""FastAPI backend for the live what-if slider (and cache-served copilot
answers). This is upside only: the cinematic demo and the rest of the UI
read precomputed JSON and never depend on this service being up. Run with:

    uvicorn engine.api:app --reload --port 8000

from the repo root. See README.md for the full command including how
engine/ is put on the Python path.
"""

from __future__ import annotations

import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

_ENGINE_DIR = Path(__file__).resolve().parent
for _p in (_ENGINE_DIR, _ENGINE_DIR / "engine", _ENGINE_DIR / "agents", _ENGINE_DIR / "copilot"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import risk_agent
from model import build_and_fit_hero_model
from simulator import SEED, generate_scenario
from whatif import score_whatif

_state: dict = {}


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    df, plant, events = generate_scenario(seed=SEED)
    hero_model = build_and_fit_hero_model()
    original_result = risk_agent.compute_risk_timeline(df, hero_model=hero_model)

    cache_path = _ENGINE_DIR / "copilot" / "cache.json"
    copilot_cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else []

    _state.update(
        df=df,
        plant=plant,
        events=events,
        hero_model=hero_model,
        original_result=original_result,
        copilot_cache=copilot_cache,
    )
    yield
    _state.clear()


app = FastAPI(title="PlantPulse API", version="0.1.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _score_from_result(result: dict, index: int) -> dict:
    contributors = risk_agent.contributor_breakdown(result["agent_scores"], index)
    return {
        "index": index,
        "risk": round(float(result["risk"].iloc[index]), 2),
        "confidence": round(float(result["confidence"].iloc[index]), 3),
        "contributors": {c["agent"]: c["contribution_pct"] for c in contributors},
    }


@app.get("/health")
def health():
    return {"status": "ok", "seed": SEED}


@app.get("/risk")
def get_risk(index: int = Query(..., ge=0)):
    df = _state["df"]
    if index >= len(df):
        raise HTTPException(400, f"index must be < {len(df)}")
    return _score_from_result(_state["original_result"], index)


class WhatIfRequest(BaseModel):
    index: int = Field(..., ge=0)
    ventilation_pct: float = Field(100.0, ge=70.0, le=100.0)
    delay_maintenance: bool = False


@app.post("/whatif")
def post_whatif(req: WhatIfRequest):
    """Rebuilds a real counterfactual window and re-scores it through the
    same fusion model (engine/engine/whatif.py) — a genuine recompute, not
    a lookup table pretending to be one. `WhatIf.tsx` falls back to a
    precomputed grid built with this exact same function only when this
    endpoint is unreachable.
    """
    df = _state["df"]
    if req.index >= len(df):
        raise HTTPException(400, f"index must be < {len(df)}")

    adjusted = score_whatif(df, _state["hero_model"], req.index, req.ventilation_pct, req.delay_maintenance)

    return {
        "inputs": {"index": req.index, "ventilation_pct": req.ventilation_pct, "delay_maintenance": req.delay_maintenance},
        "baseline": _score_from_result(_state["original_result"], req.index),
        "adjusted": adjusted,
    }


@app.get("/copilot")
def get_copilot(event_id: str = Query(...)):
    for entry in _state["copilot_cache"]:
        if entry["event_id"] == event_id:
            return entry
    raise HTTPException(404, f"No cached answer for event_id={event_id}")
