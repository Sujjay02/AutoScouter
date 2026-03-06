"""The Blue Alliance API client for fetching FRC match and team data."""
import logging
from typing import Optional

import httpx
from config import TBA_API_KEY, TBA_BASE_URL

logger = logging.getLogger(__name__)

HEADERS = {"X-TBA-Auth-Key": TBA_API_KEY} if TBA_API_KEY else {}


async def get_team_info(team_number: int) -> Optional[dict]:
    """Fetch basic info for a team from TBA."""
    if not TBA_API_KEY:
        return None
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                f"{TBA_BASE_URL}/team/frc{team_number}",
                headers=HEADERS, timeout=10
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"TBA team fetch error: {e}")
            return None


async def get_event_teams(event_key: str) -> list[dict]:
    """Fetch all teams competing at an event."""
    if not TBA_API_KEY:
        return []
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                f"{TBA_BASE_URL}/event/{event_key}/teams",
                headers=HEADERS, timeout=10
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"TBA event teams fetch error: {e}")
            return []


async def get_event_matches(event_key: str) -> list[dict]:
    """Fetch all matches for an event."""
    if not TBA_API_KEY:
        return []
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                f"{TBA_BASE_URL}/event/{event_key}/matches",
                headers=HEADERS, timeout=10
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"TBA event matches fetch error: {e}")
            return []


async def get_match(match_key: str) -> Optional[dict]:
    """Fetch a specific match from TBA."""
    if not TBA_API_KEY:
        return None
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                f"{TBA_BASE_URL}/match/{match_key}",
                headers=HEADERS, timeout=10
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"TBA match fetch error: {e}")
            return None


def parse_alliance_teams(match_data: dict) -> tuple[list[int], list[int]]:
    """Extract team numbers from TBA match data."""
    alliances = match_data.get("alliances", {})
    red_keys = alliances.get("red", {}).get("team_keys", [])
    blue_keys = alliances.get("blue", {}).get("team_keys", [])

    def to_num(key: str) -> int:
        return int(key.replace("frc", ""))

    return [to_num(k) for k in red_keys], [to_num(k) for k in blue_keys]
