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
        "description": "Points and game pieces scored during autonomous"
    },
    "teleop_scoring": {
        "label": "Teleop Scoring",
        "weight": 1.0,
        "description": "Game pieces scored during teleoperated period"
    },
    "defense": {
        "label": "Defense",
        "weight": 0.8,
        "description": "Defensive plays and opponent disruption"
    },
    "endgame": {
        "label": "Endgame / Climb",
        "weight": 1.2,
        "description": "Cage climbs, park points, endgame actions"
    },
    "consistency": {
        "label": "Consistency",
        "weight": 1.0,
        "description": "Reliability and avoiding penalties"
    },
    "speed": {
        "label": "Speed & Agility",
        "weight": 0.7,
        "description": "Cycle time and field traversal speed"
    },
    "coral_handling": {
        "label": "Coral Handling",
        "weight": 1.1,
        "description": "Reef coral placement accuracy (Reefscape 2025)"
    },
    "algae_handling": {
        "label": "Algae Handling",
        "weight": 0.9,
        "description": "Algae removal/processing (Reefscape 2025)"
    },
}

# Database
DATABASE_URL = "sqlite+aiosqlite:///./autoscouter.db"

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# FRC 2025 Game: Reefscape
CURRENT_GAME = "Reefscape"
CURRENT_YEAR = 2025
