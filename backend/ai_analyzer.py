"""AI-powered FRC match frame analysis using Claude Vision."""
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, SCORING_CATEGORIES, CURRENT_GAME

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are an expert FRC (FIRST Robotics Competition) match analyst specialized in the FRC 2026 game.

FRC 2026 Game Rules:
FIELD ZONES:
- Red Alliance Zone and Blue Alliance Zone (each side of the field)
- Neutral Zone (center)
- Hub: Central goal structure where FUEL is scored (both Hubs active in Auto)
- Tower: Climbing structure in each Alliance Zone (3 rungs)
- Outpost: Human player station on alliance wall — feeds FUEL to robots
- Depot: Corner holding area with starting FUEL
- Trench: Low-clearance tunnel (~22" tall) robots can use to bypass the Bump
- Bump: Raised barrier robots must traverse if not using the Trench

GAME PIECE — FUEL:
- Bright yellow spherical foam balls (~5.91" diameter, ~0.47 lbs)
- Robots preload up to 8 FUEL; no in-match holding limit
- Scored by shooting/placing into the Hub = 1 point each
- Human players at the Outpost can also throw FUEL into the Hub

MATCH PERIODS:
- AUTO (20 seconds): Robots act autonomously. Score FUEL into Hub. Up to 2 robots per alliance
  can earn bonus points by completing an L1 Tower climb before Auto ends.
- TELEOP (~2 min 10 sec): Driver-controlled FUEL scoring into Hub.
- ENDGAME (final 30 seconds): Tower climbing. NO parking points — only climb levels score.
  * L1: Robot off ground, touching the lowest rung
  * L2: Robot bumpers above the first rung
  * L3: Robot bumpers above the second rung (highest reward)

ROBOT IDENTIFICATION:
- Team numbers (4 digits) appear on colored bumpers (red or blue)
- Red alliance bumpers are red; blue alliance bumpers are blue

Your job is to analyze match footage frames and extract structured scouting data.
Be precise, conservative in your estimates, and flag low-confidence observations."""

ANALYSIS_PROMPT = """Analyze this FRC 2026 match frame and return a JSON object with the following structure.

If you can identify robot team numbers from bumpers, include them. Robots may be partially obscured.

Return ONLY valid JSON (no markdown, no explanation), structured exactly as:
{
  "match_phase": "auto|teleop|endgame|unknown",
  "robots_detected": [
    {
      "team_number": <integer or null if unreadable>,
      "alliance": "red|blue|unknown",
      "position_description": "<where on field: Hub area, Depot, Trench, Neutral Zone, Tower, etc.>",
      "actions_observed": ["<action1>", "<action2>"],
      "scores": {
        "auto_scoring": <0-10>,
        "fuel_scoring": <0-10>,
        "tower_climb": <0-10>,
        "collection_efficiency": <0-10>,
        "defense": <0-10>,
        "trench_usage": <0-10>,
        "consistency": <0-10>,
        "speed": <0-10>
      },
      "events": {
        "fuel_scored": <integer, FUEL balls observed going into Hub>,
        "penalties_incurred": <integer>,
        "tower_climb_level": <0, 1, 2, or 3 — 0 if no climb attempted>,
        "climb_attempted": <boolean>,
        "climb_successful": <boolean>,
        "used_trench": <boolean>,
        "auto_climb_bonus": <boolean — L1 climb completed before Auto ends>
      },
      "confidence": <0.0-1.0>
    }
  ],
  "field_observations": "<brief overall description: phase, key actions, field positioning>",
  "score_display": {
    "red": <integer or null — read from on-screen scoreboard if visible>,
    "blue": <integer or null>
  },
  "time_remaining": <integer seconds or null — read from timer if visible>
}

Score guidelines (0-10 per category):
- 0: Not observed / not applicable in this phase
- 1-3: Poor / minimal contribution
- 4-6: Average contribution
- 7-9: Strong contribution
- 10: Exceptional / best-in-class

Phase-specific scoring:
- AUTO phase: score auto_scoring and collection_efficiency; set fuel_scoring=0, tower_climb=0 unless endgame
- TELEOP phase: score fuel_scoring, collection_efficiency, defense, trench_usage, speed; auto_scoring=0
- ENDGAME phase: score tower_climb primarily; note the climb level (L1/L2/L3) in events
- Always score consistency across all phases"""


@dataclass
class RobotAnalysisResult:
    team_number: Optional[int]
    alliance: str
    position_description: str
    actions_observed: list[str]
    auto_scoring: float = 0
    fuel_scoring: float = 0
    tower_climb: float = 0
    collection_efficiency: float = 0
    defense: float = 0
    trench_usage: float = 0
    consistency: float = 0
    speed: float = 0
    fuel_scored: int = 0
    penalties_incurred: int = 0
    tower_climb_level: int = 0   # 0 = none, 1 = L1, 2 = L2, 3 = L3
    climb_attempted: bool = False
    climb_successful: bool = False
    used_trench: bool = False
    auto_climb_bonus: bool = False
    confidence: float = 0.5


@dataclass
class FrameAnalysisResult:
    match_phase: str = "unknown"
    robots: list[RobotAnalysisResult] = field(default_factory=list)
    field_observations: str = ""
    score_red: Optional[int] = None
    score_blue: Optional[int] = None
    time_remaining: Optional[int] = None
    raw_response: str = ""
    error: Optional[str] = None


def analyze_frame(frame_b64: str, match_context: dict | None = None) -> FrameAnalysisResult:
    """
    Send a frame to Claude for analysis.
    Returns a FrameAnalysisResult with all detected robot data.
    """
    context_note = ""
    if match_context:
        red = match_context.get("red_alliance", [])
        blue = match_context.get("blue_alliance", [])
        if red or blue:
            context_note = (
                f"\n\nKnown alliance composition: "
                f"RED={red}, BLUE={blue}. "
                "Use this to help identify partially visible bumper numbers."
            )

    try:
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": frame_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": ANALYSIS_PROMPT + context_note,
                        },
                    ],
                }
            ],
        )

        raw = message.content[0].text
        data = json.loads(raw)
        return _parse_analysis_response(data, raw)

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error in AI response: {e}\nResponse: {raw[:500]}")
        return FrameAnalysisResult(error=f"JSON parse error: {e}", raw_response=raw[:500])
    except anthropic.APIError as e:
        logger.error(f"Anthropic API error: {e}")
        return FrameAnalysisResult(error=str(e))
    except Exception as e:
        logger.error(f"Unexpected analysis error: {e}")
        return FrameAnalysisResult(error=str(e))


def _parse_analysis_response(data: dict, raw: str) -> FrameAnalysisResult:
    robots = []
    for r in data.get("robots_detected", []):
        scores = r.get("scores", {})
        events = r.get("events", {})
        robots.append(RobotAnalysisResult(
            team_number=r.get("team_number"),
            alliance=r.get("alliance", "unknown"),
            position_description=r.get("position_description", ""),
            actions_observed=r.get("actions_observed", []),
            auto_scoring=float(scores.get("auto_scoring", 0)),
            fuel_scoring=float(scores.get("fuel_scoring", 0)),
            tower_climb=float(scores.get("tower_climb", 0)),
            collection_efficiency=float(scores.get("collection_efficiency", 0)),
            defense=float(scores.get("defense", 0)),
            trench_usage=float(scores.get("trench_usage", 0)),
            consistency=float(scores.get("consistency", 0)),
            speed=float(scores.get("speed", 0)),
            fuel_scored=int(events.get("fuel_scored", 0)),
            penalties_incurred=int(events.get("penalties_incurred", 0)),
            tower_climb_level=int(events.get("tower_climb_level", 0)),
            climb_attempted=bool(events.get("climb_attempted", False)),
            climb_successful=bool(events.get("climb_successful", False)),
            used_trench=bool(events.get("used_trench", False)),
            auto_climb_bonus=bool(events.get("auto_climb_bonus", False)),
            confidence=float(r.get("confidence", 0.5)),
        ))

    score_display = data.get("score_display", {})
    return FrameAnalysisResult(
        match_phase=data.get("match_phase", "unknown"),
        robots=robots,
        field_observations=data.get("field_observations", ""),
        score_red=score_display.get("red"),
        score_blue=score_display.get("blue"),
        time_remaining=data.get("time_remaining"),
        raw_response=raw,
    )
