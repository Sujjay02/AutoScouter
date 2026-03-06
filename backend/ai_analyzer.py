"""AI-powered FRC match frame analysis — supports Claude and Gemini."""
import base64
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from config import (
    AI_PROVIDER,
    ANTHROPIC_API_KEY, CLAUDE_MODEL,
    GEMINI_API_KEY, GEMINI_MODEL,
)

logger = logging.getLogger(__name__)

# ── Lazy-initialise whichever client is needed ────────────────────────────────

def _make_claude_client():
    import anthropic
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def _make_gemini_client():
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel(
        model_name=GEMINI_MODEL,
        generation_config={"response_mime_type": "application/json"},
    )

_claude_client = None
_gemini_client = None

def _claude():
    global _claude_client
    if _claude_client is None:
        _claude_client = _make_claude_client()
    return _claude_client

def _gemini():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = _make_gemini_client()
    return _gemini_client


# ── Prompts (shared between providers) ───────────────────────────────────────

SYSTEM_PROMPT = """You are an expert FRC (FIRST Robotics Competition) match analyst specialized in FRC 2026 REBUILT™.

━━━ FIELD ZONES ━━━
- Red Alliance Zone / Blue Alliance Zone (opposite ends of field)
- Neutral Zone (center)
- Hub: Central goal structure; FUEL scored here (1 pt each when Hub is ACTIVE)
- Tower: Climbing structure in each Alliance Zone — 3 rungs (Low, Mid, High)
- Outpost: Human player station on alliance wall — feeds FUEL to robots
- Depot: Corner area containing starting FUEL supply
- Trench: Low-clearance tunnel (~22" tall) — robots can pass through to bypass the Bump
- Bump: Raised barrier dividing zones; robots go over it or use the Trench

━━━ GAME PIECE — FUEL ━━━
- Bright yellow foam spheres (~5.91" diameter, ~0.47 lbs)
- Robots preload up to 8 FUEL; no in-match holding cap
- Scored by shooting/placing into an ACTIVE Hub = 1 point each
- CRITICAL: FUEL scored in an INACTIVE Hub scores 0 points
- Human players at the Outpost may also throw FUEL into the Hub

━━━ MATCH TIMELINE ━━━
1. AUTO (20 sec): Both Hubs active. Robots act autonomously.
   - FUEL into Hub = 1 pt each
   - L1 Tower climb before Auto ends = 5 pts (up to 2 robots per alliance earn this bonus)
   - Alliance that scores more FUEL in Auto wins the Shift Order Advantage

2. TRANSITION (10 sec): Both Hubs go INACTIVE. No scoring. Field assesses Auto results.

3. TELEOP SHIFTS (4 × 25 sec = 100 sec total): Alternating Hub activation.
   - Only ONE alliance's Hub is active per Shift; the other is inactive (0 pts for FUEL)
   - Shift order: determined by Auto FUEL advantage (winner typically takes Shifts 2 & 4)
   - Shift 1 & 3: one alliance active | Shift 2 & 4: the other alliance active
   - Look for on-screen indicators showing which Hub is currently active

4. ENDGAME (final 30 sec): Both Hubs active simultaneously. Tower climbing begins.
   - L1 climb: Robot fully supported by Tower, not touching carpet — 5 pts
   - L2 climb: Bumpers completely above the Low Rung — 15 pts
   - L3 climb: Bumpers completely above the Mid Rung — 30 pts
   - No parking points; only climb level matters

━━━ RANKING POINTS ━━━
- Energized RP: Alliance reaches a FUEL scoring threshold
- Traversal RP: Alliance collective climb points reach a threshold (typically needs L3 or multiple climbs)

━━━ ROBOT IDENTIFICATION ━━━
- Team numbers (4 digits) on colored bumpers (red bumpers = red alliance, blue = blue)

Analyze frames precisely. Be conservative. Flag low-confidence readings."""

ANALYSIS_PROMPT = """Analyze this FRC 2026 REBUILT™ match frame and return a JSON object.

If you can identify robot team numbers from bumpers, include them. Robots may be partially obscured.

Return ONLY valid JSON (no markdown, no explanation):
{
  "match_phase": "auto|transition|shift1|shift2|shift3|shift4|endgame|unknown",
  "active_hub": "red|blue|both|none|unknown",
  "robots_detected": [
    {
      "team_number": <integer or null>,
      "alliance": "red|blue|unknown",
      "position_description": "<Hub area, Depot, Trench, Neutral Zone, Tower, etc.>",
      "actions_observed": ["<action1>", "<action2>"],
      "hub_active_for_robot": <boolean — is this robot's alliance Hub currently active?>,
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
        "fuel_scored": <integer — FUEL balls observed entering an ACTIVE Hub>,
        "fuel_wasted": <integer — FUEL scored into INACTIVE Hub (worth 0 pts)>,
        "penalties_incurred": <integer>,
        "tower_climb_level": <0, 1, 2, or 3>,
        "climb_attempted": <boolean>,
        "climb_successful": <boolean>,
        "used_trench": <boolean>,
        "auto_climb_bonus": <boolean — L1 completed before Auto ends>
      },
      "confidence": <0.0-1.0>
    }
  ],
  "field_observations": "<phase, active Hub, key actions, notable positioning>",
  "score_display": {
    "red": <integer or null>,
    "blue": <integer or null>
  },
  "time_remaining": <integer seconds or null>
}

Score guidelines (0-10):
- 0: Not observed / not applicable this phase
- 1-3: Poor / minimal
- 4-6: Average
- 7-9: Strong
- 10: Exceptional

Phase-specific scoring rules:
- AUTO: score auto_scoring, collection_efficiency, consistency; fuel_scoring=0, tower_climb=0
- TRANSITION: consistency only; all scoring categories=0 (no Hub active)
- SHIFT1-4: score fuel_scoring (ONLY if Hub is active for that robot), collection_efficiency,
  defense, trench_usage, speed, consistency; auto_scoring=0, tower_climb=0
  IMPORTANT: if a robot is scoring into an INACTIVE Hub, set fuel_scoring low (poor strategy)
- ENDGAME: score tower_climb (primary), fuel_scoring if Hubs still active, consistency"""


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class RobotAnalysisResult:
    team_number: Optional[int]
    alliance: str
    position_description: str
    actions_observed: list[str]
    hub_active_for_robot: bool = False
    auto_scoring: float = 0
    fuel_scoring: float = 0
    tower_climb: float = 0
    collection_efficiency: float = 0
    defense: float = 0
    trench_usage: float = 0
    consistency: float = 0
    speed: float = 0
    fuel_scored: int = 0
    fuel_wasted: int = 0
    penalties_incurred: int = 0
    tower_climb_level: int = 0
    climb_attempted: bool = False
    climb_successful: bool = False
    used_trench: bool = False
    auto_climb_bonus: bool = False
    confidence: float = 0.5


@dataclass
class FrameAnalysisResult:
    match_phase: str = "unknown"
    active_hub: str = "unknown"
    robots: list[RobotAnalysisResult] = field(default_factory=list)
    field_observations: str = ""
    score_red: Optional[int] = None
    score_blue: Optional[int] = None
    time_remaining: Optional[int] = None
    raw_response: str = ""
    error: Optional[str] = None
    provider: str = ""


# ── Provider implementations ──────────────────────────────────────────────────

def _call_claude(frame_b64: str, prompt: str) -> str:
    import anthropic
    message = _claude().messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": frame_b64},
                },
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return message.content[0].text


def _call_gemini(frame_b64: str, prompt: str) -> str:
    import google.generativeai as genai
    from PIL import Image
    import io

    img_bytes = base64.b64decode(frame_b64)
    img = Image.open(io.BytesIO(img_bytes))

    # Gemini takes system + user content in a single turn
    full_prompt = SYSTEM_PROMPT + "\n\n" + prompt
    response = _gemini().generate_content([full_prompt, img])
    return response.text


# ── Public interface ──────────────────────────────────────────────────────────

def analyze_frame(frame_b64: str, match_context: dict | None = None) -> FrameAnalysisResult:
    """Analyze a frame using whichever provider is configured (AI_PROVIDER env var)."""
    context_note = ""
    if match_context:
        red = match_context.get("red_alliance", [])
        blue = match_context.get("blue_alliance", [])
        if red or blue:
            context_note = (
                f"\n\nKnown alliance composition: RED={red}, BLUE={blue}. "
                "Use this to help identify partially visible bumper numbers."
            )

    prompt = ANALYSIS_PROMPT + context_note
    raw = ""
    provider = AI_PROVIDER

    try:
        if provider == "gemini":
            if not GEMINI_API_KEY:
                return FrameAnalysisResult(error="GEMINI_API_KEY not set in .env", provider=provider)
            raw = _call_gemini(frame_b64, prompt)
        else:
            if not ANTHROPIC_API_KEY:
                return FrameAnalysisResult(error="ANTHROPIC_API_KEY not set in .env", provider=provider)
            raw = _call_claude(frame_b64, prompt)

        # Gemini with response_mime_type=application/json may still wrap in markdown
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```", 2)[1]
            if clean.startswith("json"):
                clean = clean[4:]
            clean = clean.rsplit("```", 1)[0].strip()

        data = json.loads(clean)
        result = _parse_analysis_response(data, raw)
        result.provider = provider
        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error ({provider}): {e}\nResponse: {raw[:500]}")
        return FrameAnalysisResult(error=f"JSON parse error: {e}", raw_response=raw[:500], provider=provider)
    except Exception as e:
        logger.error(f"Analysis error ({provider}): {e}")
        return FrameAnalysisResult(error=str(e), provider=provider)


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
            hub_active_for_robot=bool(r.get("hub_active_for_robot", False)),
            auto_scoring=float(scores.get("auto_scoring", 0)),
            fuel_scoring=float(scores.get("fuel_scoring", 0)),
            tower_climb=float(scores.get("tower_climb", 0)),
            collection_efficiency=float(scores.get("collection_efficiency", 0)),
            defense=float(scores.get("defense", 0)),
            trench_usage=float(scores.get("trench_usage", 0)),
            consistency=float(scores.get("consistency", 0)),
            speed=float(scores.get("speed", 0)),
            fuel_scored=int(events.get("fuel_scored", 0)),
            fuel_wasted=int(events.get("fuel_wasted", 0)),
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
        active_hub=data.get("active_hub", "unknown"),
        robots=robots,
        field_observations=data.get("field_observations", ""),
        score_red=score_display.get("red"),
        score_blue=score_display.get("blue"),
        time_remaining=data.get("time_remaining"),
        raw_response=raw,
    )
