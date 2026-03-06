"""AI-powered FRC match frame analysis using Claude Vision."""
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, SCORING_CATEGORIES, CURRENT_GAME

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = f"""You are an expert FRC (FIRST Robotics Competition) match analyst specialized in the {CURRENT_GAME} game (2025).

In Reefscape 2025:
- CORAL pieces are placed on the REEF structure at L1/L2/L3/L4 levels
- ALGAE pieces float on the reef and can be removed to the processor or barge
- AUTO period: 15 seconds, robots act autonomously
- TELEOP period: 2 min 15 sec, drivers control robots
- ENDGAME: final 30 seconds, robots can CAGE CLIMB on chains (Level 1, 2, or 3) or PARK
- Red alliance is on the left side, blue alliance on the right (from audience perspective)
- Robot team numbers appear on bumpers (4-digit numbers)

Your job is to analyze match footage frames and extract structured scouting data.
Be precise, conservative in your estimates, and flag low-confidence observations."""

ANALYSIS_PROMPT = """Analyze this FRC Reefscape match frame and return a JSON object with the following structure.

If you can identify robot team numbers from bumpers, include them. Robots may be partially obscured.

Return ONLY valid JSON (no markdown, no explanation), structured exactly as:
{
  "match_phase": "auto|teleop|endgame|unknown",
  "robots_detected": [
    {
      "team_number": <integer or null if unreadable>,
      "alliance": "red|blue|unknown",
      "position_description": "<brief description>",
      "actions_observed": ["<action1>", "<action2>"],
      "scores": {
        "auto_scoring": <0-10>,
        "teleop_scoring": <0-10>,
        "defense": <0-10>,
        "endgame": <0-10>,
        "consistency": <0-10>,
        "speed": <0-10>,
        "coral_handling": <0-10>,
        "algae_handling": <0-10>
      },
      "events": {
        "game_pieces_scored": <integer>,
        "penalties_incurred": <integer>,
        "climb_attempted": <boolean>,
        "climb_successful": <boolean>
      },
      "confidence": <0.0-1.0>
    }
  ],
  "field_observations": "<brief overall description of what's happening in the frame>",
  "score_display": {
    "red": <integer or null>,
    "blue": <integer or null>
  },
  "time_remaining": <integer seconds or null>
}

Score guidelines (0-10):
- 0: Not observed / not applicable
- 1-3: Poor / minimal contribution
- 4-6: Average contribution
- 7-9: Good contribution
- 10: Exceptional

Only score categories relevant to the current match_phase.
Set auto_scoring=0 if not in auto phase, etc."""


@dataclass
class RobotAnalysisResult:
    team_number: Optional[int]
    alliance: str
    position_description: str
    actions_observed: list[str]
    auto_scoring: float = 0
    teleop_scoring: float = 0
    defense: float = 0
    endgame: float = 0
    consistency: float = 0
    speed: float = 0
    coral_handling: float = 0
    algae_handling: float = 0
    game_pieces_scored: int = 0
    penalties_incurred: int = 0
    climb_attempted: bool = False
    climb_successful: bool = False
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
            teleop_scoring=float(scores.get("teleop_scoring", 0)),
            defense=float(scores.get("defense", 0)),
            endgame=float(scores.get("endgame", 0)),
            consistency=float(scores.get("consistency", 0)),
            speed=float(scores.get("speed", 0)),
            coral_handling=float(scores.get("coral_handling", 0)),
            algae_handling=float(scores.get("algae_handling", 0)),
            game_pieces_scored=int(events.get("game_pieces_scored", 0)),
            penalties_incurred=int(events.get("penalties_incurred", 0)),
            climb_attempted=bool(events.get("climb_attempted", False)),
            climb_successful=bool(events.get("climb_successful", False)),
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
