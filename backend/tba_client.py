"""The Blue Alliance API client for fetching FRC match, team, event, and webcast data."""
import logging
from typing import Optional

import httpx
from config import TBA_API_KEY, TBA_BASE_URL

logger = logging.getLogger(__name__)

HEADERS = {"X-TBA-Auth-Key": TBA_API_KEY} if TBA_API_KEY else {}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _team_num(key: str) -> int:
    return int(key.replace("frc", ""))


async def _get(path: str) -> Optional[dict | list]:
    """Generic TBA GET with error handling."""
    if not TBA_API_KEY:
        return None
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{TBA_BASE_URL}{path}", headers=HEADERS, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"TBA request error [{path}]: {e}")
            return None


# ─── Teams ────────────────────────────────────────────────────────────────────

async def get_team_info(team_number: int) -> Optional[dict]:
    """Fetch basic info for a team from TBA."""
    return await _get(f"/team/frc{team_number}")


# ─── Events ───────────────────────────────────────────────────────────────────

async def get_events_for_year(year: int) -> list[dict]:
    """Fetch all events for a given season year."""
    data = await _get(f"/events/{year}")
    return data if isinstance(data, list) else []


async def get_event_info(event_key: str) -> Optional[dict]:
    """Fetch event details (name, location, dates, webcasts)."""
    return await _get(f"/event/{event_key}")


async def get_event_teams(event_key: str) -> list[dict]:
    """Fetch all teams competing at an event."""
    data = await _get(f"/event/{event_key}/teams")
    return data if isinstance(data, list) else []


async def get_event_matches(event_key: str) -> list[dict]:
    """Fetch all matches for an event, sorted by comp level and match number."""
    data = await _get(f"/event/{event_key}/matches")
    if not isinstance(data, list):
        return []
    level_order = {"qm": 0, "ef": 1, "qf": 2, "sf": 3, "f": 4}
    return sorted(
        data,
        key=lambda m: (
            level_order.get(m.get("comp_level", ""), 99),
            m.get("set_number", 0),
            m.get("match_number", 0),
        ),
    )


async def get_event_webcasts(event_key: str) -> list[dict]:
    """
    Fetch webcast entries for an event.
    Returns list of dicts with 'type' and 'channel' keys.
    Known types: 'twitch', 'youtube', 'ustream', 'livestream', etc.
    """
    info = await get_event_info(event_key)
    if not info:
        return []
    return info.get("webcasts", [])


# ─── Matches ──────────────────────────────────────────────────────────────────

async def get_match(match_key: str) -> Optional[dict]:
    """Fetch a specific match from TBA."""
    return await _get(f"/match/{match_key}")


def parse_alliance_teams(match_data: dict) -> tuple[list[int], list[int]]:
    """Extract red/blue team numbers from TBA match data."""
    alliances = match_data.get("alliances", {})
    red_keys = alliances.get("red", {}).get("team_keys", [])
    blue_keys = alliances.get("blue", {}).get("team_keys", [])
    return [_team_num(k) for k in red_keys], [_team_num(k) for k in blue_keys]


# ─── Webcast utilities ────────────────────────────────────────────────────────

WEBCAST_TYPE_LABELS = {
    "twitch": "Twitch",
    "youtube": "YouTube",
    "livestream": "Livestream",
    "ustream": "Ustream",
    "iframe": "Embedded",
    "html5": "HTML5",
    "dacast": "Dacast",
}


def webcast_to_stream_info(webcast: dict) -> dict:
    """
    Convert a TBA webcast object into a stream descriptor usable by the scouting engine.

    Returns:
        {
            "type": "twitch" | "youtube" | "other",
            "channel": "<channel or video id>",
            "url": "<full stream URL>",
            "label": "<human-readable label>",
        }
    """
    wtype = webcast.get("type", "").lower()
    channel = webcast.get("channel", "")
    file_field = webcast.get("file", "")

    if wtype == "twitch":
        return {
            "type": "twitch",
            "channel": channel,
            "url": f"https://www.twitch.tv/{channel}",
            "label": f"Twitch: {channel}",
        }
    if wtype == "youtube":
        vid = channel or file_field
        return {
            "type": "youtube",
            "channel": vid,
            "url": f"https://www.youtube.com/watch?v={vid}",
            "label": f"YouTube: {vid}",
        }
    # Fallback — return raw info
    return {
        "type": wtype or "other",
        "channel": channel,
        "url": channel if channel.startswith("http") else "",
        "label": f"{WEBCAST_TYPE_LABELS.get(wtype, wtype or 'Stream')}: {channel}",
    }


def format_match_label(match: dict) -> str:
    """Return a human-readable match label like 'Qual 12' or 'SF 1-1'."""
    level = match.get("comp_level", "")
    num = match.get("match_number", "?")
    set_num = match.get("set_number", 1)
    labels = {"qm": "Qual", "ef": "Elim", "qf": "QF", "sf": "SF", "f": "Finals"}
    prefix = labels.get(level, level.upper())
    if level == "qm":
        return f"{prefix} {num}"
    return f"{prefix} {set_num}-{num}"
