"""FRC AutoScouter API Server."""
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

import database as db
from database import init_db, get_db, Match, RobotObservation, TeamStats
from scouter_engine import start_scouting, stop_scouting, get_result_queue, get_active_matches
from tba_client import get_match, parse_alliance_teams, get_team_info
from config import SCORING_CATEGORIES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FRC AutoScouter",
    description="AI-powered FRC match analysis from Twitch livestreams",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws) if ws in self.active else None

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

manager = ConnectionManager()


@app.on_event("startup")
async def startup():
    await init_db()
    # Start WebSocket broadcaster
    asyncio.create_task(_broadcast_loop())
    logger.info("FRC AutoScouter started")


async def _broadcast_loop():
    """Relay results from the scouting engine to all WebSocket clients."""
    queue = get_result_queue()
    while True:
        try:
            item = await asyncio.wait_for(queue.get(), timeout=1.0)
            await manager.broadcast({"type": "frame_result", "data": item})
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.error(f"Broadcast error: {e}")


# ─── Request/Response Models ────────────────────────────────────────────────

class StartScoutingRequest(BaseModel):
    match_key: str
    twitch_channel: str
    event_key: Optional[str] = None
    tba_match_key: Optional[str] = None
    red_alliance: list[int] = []
    blue_alliance: list[int] = []
    use_mock: bool = False


class TeamNoteRequest(BaseModel):
    notes: str


# ─── Match Endpoints ────────────────────────────────────────────────────────

@app.post("/api/matches/start")
async def start_match_scouting(req: StartScoutingRequest, session: AsyncSession = Depends(get_db)):
    """Start scouting a match from a Twitch stream."""
    # Auto-fetch alliance info from TBA if a TBA match key is provided
    red = req.red_alliance
    blue = req.blue_alliance
    if req.tba_match_key and (not red and not blue):
        match_data = await get_match(req.tba_match_key)
        if match_data:
            red, blue = parse_alliance_teams(match_data)

    # Check for existing active match
    existing = await session.execute(
        select(Match).where(Match.match_key == req.match_key, Match.is_active == True)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Match {req.match_key} is already being scouted.")

    match = Match(
        match_key=req.match_key,
        event_key=req.event_key,
        twitch_channel=req.twitch_channel,
        red_alliance=red,
        blue_alliance=blue,
        is_active=True,
    )
    session.add(match)
    await session.commit()

    match_context = {"red_alliance": red, "blue_alliance": blue}
    await start_scouting(req.match_key, req.twitch_channel, req.use_mock, match_context)

    return {
        "status": "started",
        "match_key": req.match_key,
        "channel": req.twitch_channel,
        "red_alliance": red,
        "blue_alliance": blue,
        "use_mock": req.use_mock,
    }


@app.post("/api/matches/{match_key}/stop")
async def stop_match_scouting(match_key: str):
    """Stop scouting a match."""
    await stop_scouting(match_key)
    return {"status": "stopped", "match_key": match_key}


@app.get("/api/matches")
async def list_matches(session: AsyncSession = Depends(get_db)):
    """List all scouted matches."""
    result = await session.execute(select(Match).order_by(desc(Match.started_at)))
    matches = result.scalars().all()
    active = get_active_matches()
    return [
        {
            "match_key": m.match_key,
            "event_key": m.event_key,
            "twitch_channel": m.twitch_channel,
            "started_at": m.started_at.isoformat() if m.started_at else None,
            "ended_at": m.ended_at.isoformat() if m.ended_at else None,
            "is_active": m.match_key in active,
            "match_phase": m.match_phase,
            "red_alliance": m.red_alliance,
            "blue_alliance": m.blue_alliance,
        }
        for m in matches
    ]


@app.get("/api/matches/{match_key}")
async def get_match_detail(match_key: str, session: AsyncSession = Depends(get_db)):
    """Get match details and all observations."""
    result = await session.execute(select(Match).where(Match.match_key == match_key))
    match = result.scalar_one_or_none()
    if not match:
        raise HTTPException(404, "Match not found")

    obs_result = await session.execute(
        select(RobotObservation)
        .where(RobotObservation.match_key == match_key)
        .order_by(RobotObservation.frame_number)
    )
    observations = obs_result.scalars().all()

    return {
        "match": {
            "match_key": match.match_key,
            "twitch_channel": match.twitch_channel,
            "match_phase": match.match_phase,
            "red_alliance": match.red_alliance,
            "blue_alliance": match.blue_alliance,
        },
        "observations": [
            {
                "team_number": o.team_number,
                "frame_number": o.frame_number,
                "match_phase": o.match_phase,
                "auto_scoring": o.auto_scoring,
                "teleop_scoring": o.teleop_scoring,
                "defense": o.defense,
                "endgame": o.endgame,
                "consistency": o.consistency,
                "speed": o.speed,
                "coral_handling": o.coral_handling,
                "algae_handling": o.algae_handling,
                "game_pieces_scored": o.game_pieces_scored,
                "climb_attempted": o.climb_attempted,
                "climb_successful": o.climb_successful,
                "ai_analysis_text": o.ai_analysis_text,
                "confidence": o.confidence,
            }
            for o in observations
        ],
    }


# ─── Rankings Endpoints ──────────────────────────────────────────────────────

@app.get("/api/rankings")
async def get_rankings(
    category: Optional[str] = None,
    session: AsyncSession = Depends(get_db)
):
    """
    Get robot rankings. Optionally sort by a specific category.
    Category must be one of the keys in SCORING_CATEGORIES.
    """
    valid_categories = list(SCORING_CATEGORIES.keys()) + ["overall_score"]
    sort_col = f"avg_{category}" if category and category != "overall_score" else "overall_score"
    if category and sort_col not in [f"avg_{c}" for c in SCORING_CATEGORIES] + ["overall_score"]:
        raise HTTPException(400, f"Invalid category. Valid: {valid_categories}")

    result = await session.execute(
        select(TeamStats).order_by(desc(getattr(TeamStats, sort_col, TeamStats.overall_score)))
    )
    teams = result.scalars().all()

    return {
        "sort_by": sort_col,
        "categories": SCORING_CATEGORIES,
        "rankings": [
            {
                "rank": i + 1,
                "team_number": t.team_number,
                "team_name": t.team_name,
                "matches_scouted": t.matches_scouted,
                "overall_score": round(t.overall_score, 1),
                "avg_auto_scoring": round(t.avg_auto_scoring, 1),
                "avg_teleop_scoring": round(t.avg_teleop_scoring, 1),
                "avg_defense": round(t.avg_defense, 1),
                "avg_endgame": round(t.avg_endgame, 1),
                "avg_consistency": round(t.avg_consistency, 1),
                "avg_speed": round(t.avg_speed, 1),
                "avg_coral_handling": round(t.avg_coral_handling, 1),
                "avg_algae_handling": round(t.avg_algae_handling, 1),
                "total_game_pieces": t.total_game_pieces,
                "total_penalties": t.total_penalties,
                "climb_attempts": t.climb_attempts,
                "climb_successes": t.climb_successes,
                "climb_rate": (
                    round(t.climb_successes / t.climb_attempts * 100, 1)
                    if t.climb_attempts > 0 else 0
                ),
                "last_updated": t.last_updated.isoformat() if t.last_updated else None,
            }
            for i, t in enumerate(teams)
        ],
    }


@app.get("/api/teams/{team_number}")
async def get_team(team_number: int, session: AsyncSession = Depends(get_db)):
    """Get detailed stats for a single team."""
    result = await session.execute(
        select(TeamStats).where(TeamStats.team_number == team_number)
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(404, "Team not found in scouting data")

    # Fetch from TBA if available
    tba_data = await get_team_info(team_number)

    obs_result = await session.execute(
        select(RobotObservation)
        .where(RobotObservation.team_number == team_number)
        .order_by(RobotObservation.timestamp)
    )
    observations = obs_result.scalars().all()

    return {
        "team_number": team.team_number,
        "team_name": team.team_name or (tba_data.get("nickname") if tba_data else None),
        "tba_name": tba_data.get("name") if tba_data else None,
        "school": tba_data.get("school_name") if tba_data else None,
        "location": (
            f"{tba_data.get('city', '')}, {tba_data.get('state_prov', '')}"
            if tba_data else None
        ),
        "matches_scouted": team.matches_scouted,
        "overall_score": round(team.overall_score, 1),
        "scores": {
            cat: {
                "label": meta["label"],
                "description": meta["description"],
                "weight": meta["weight"],
                "avg": round(getattr(team, f"avg_{cat}", 0), 1),
            }
            for cat, meta in SCORING_CATEGORIES.items()
        },
        "events": {
            "total_game_pieces": team.total_game_pieces,
            "total_penalties": team.total_penalties,
            "climb_attempts": team.climb_attempts,
            "climb_successes": team.climb_successes,
            "climb_success_rate": (
                round(team.climb_successes / team.climb_attempts * 100, 1)
                if team.climb_attempts > 0 else 0
            ),
        },
        "observations": [
            {
                "match_key": o.match_key,
                "frame": o.frame_number,
                "phase": o.match_phase,
                "analysis": o.ai_analysis_text,
                "confidence": o.confidence,
            }
            for o in observations[-20:]  # last 20 observations
        ],
    }


@app.patch("/api/teams/{team_number}/notes")
async def update_team_notes(
    team_number: int,
    body: TeamNoteRequest,
    session: AsyncSession = Depends(get_db)
):
    """Add manual scout notes to a team."""
    result = await session.execute(
        select(TeamStats).where(TeamStats.team_number == team_number)
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(404, "Team not found")
    team.notes = body.notes
    await session.commit()
    return {"status": "ok"}


@app.get("/api/config")
async def get_config():
    """Return scoring category config for the frontend."""
    return {"categories": SCORING_CATEGORIES, "game": "FRC Reefscape 2025"}


@app.get("/api/status")
async def get_status():
    """Health check and active match status."""
    return {
        "status": "running",
        "active_matches": get_active_matches(),
    }


# ─── WebSocket ───────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive
            await asyncio.sleep(30)
            await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# ─── Static frontend ─────────────────────────────────────────────────────────

import os
static_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    @app.get("/")
    async def root():
        return {"message": "FRC AutoScouter API running. Frontend not built yet."}
