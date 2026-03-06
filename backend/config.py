"""Configuration settings for FRC AutoScouter."""
import os
from dotenv import load_dotenv

load_dotenv()

# Anthropic / Claude
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-opus-4-6"

# The Blue Alliance API
TBA_API_KEY = os.getenv("TBA_API_KEY", "")
TBA_BASE_URL = "https://www.thebluealliance.com/api/v3"

# Stream settings
FRAME_INTERVAL_SECONDS = 5        # How often to capture a frame for analysis
MAX_FRAMES_PER_MATCH = 60         # Safety cap
STREAM_QUALITY = "720p60,720p,best"

# Scoring categories with weights
SCORING_CATEGORIES = {
    "auto_scoring": {
        "label": "Auto Period",
        "weight": 1.5,
        "description": "FUEL scored in Hub + L1 Tower climb during the 20-second autonomous period"
    },
    "fuel_scoring": {
        "label": "FUEL Scoring",
        "weight": 1.2,
        "description": "Yellow foam balls scored into the Hub during teleop (1 pt each)"
    },
    "tower_climb": {
        "label": "Tower Climb",
        "weight": 1.4,
        "description": "Endgame Tower climb level achieved: L1 (lowest), L2 (bumpers above rung 1), L3 (highest)"
    },
    "collection_efficiency": {
        "label": "Collection",
        "weight": 1.0,
        "description": "Efficiency collecting FUEL from the Depot or receiving from the Outpost human player"
    },
    "defense": {
        "label": "Defense",
        "weight": 0.8,
        "description": "Defensive plays, opponent disruption, and field positioning"
    },
    "trench_usage": {
        "label": "Trench Usage",
        "weight": 0.7,
        "description": "Effective use of the Trench (~22\" tunnel) to bypass the Bump and maintain cycle speed"
    },
    "consistency": {
        "label": "Consistency",
        "weight": 1.0,
        "description": "Reliability across the match, avoiding penalties and robot faults"
    },
    "speed": {
        "label": "Speed & Cycling",
        "weight": 0.9,
        "description": "FUEL cycle time: Depot/Outpost → Hub round-trip speed"
    },
}

# Database
DATABASE_URL = "sqlite+aiosqlite:///./autoscouter.db"

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# FRC 2026 Game: REBUILT™
CURRENT_GAME = "REBUILT"
CURRENT_YEAR = 2026

# Tower climb point values (auto / teleop)
TOWER_LEVELS = {
    "L1": {"description": "Fully supported by Tower; not touching carpet", "auto_pts": 5,  "teleop_pts": 5},
    "L2": {"description": "Bumpers completely above the Low Rung",          "auto_pts": 0,  "teleop_pts": 15},
    "L3": {"description": "Bumpers completely above the Mid Rung",          "auto_pts": 0,  "teleop_pts": 30},
}

# Hub Shift schedule (teleop, excluding endgame)
# Immediately after Auto: 10-second Transition where both Hubs are inactive.
# Then four 25-second Shifts alternate which alliance's Hub is active.
# Endgame (final 30s): both Hubs active simultaneously.
# The alliance that scores more FUEL in Auto gets to choose their shift order.
HUB_SHIFTS = {
    "transition": {"duration_sec": 10,  "active_hub": "none",  "description": "Post-auto transition; both Hubs inactive"},
    "shift1":     {"duration_sec": 25,  "active_hub": "tbd",   "description": "First scoring shift (alliance chosen by Auto FUEL winner)"},
    "shift2":     {"duration_sec": 25,  "active_hub": "tbd",   "description": "Second scoring shift (opposing alliance)"},
    "shift3":     {"duration_sec": 25,  "active_hub": "tbd",   "description": "Third scoring shift"},
    "shift4":     {"duration_sec": 25,  "active_hub": "tbd",   "description": "Fourth scoring shift"},
    "endgame":    {"duration_sec": 30,  "active_hub": "both",  "description": "Both Hubs active; Tower climbing begins"},
}
