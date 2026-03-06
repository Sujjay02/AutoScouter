"""Core scouting engine: orchestrates stream capture, AI analysis, and DB writes."""
import asyncio
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ai_analyzer import analyze_frame, FrameAnalysisResult
from database import Match, RobotObservation, TeamStats, AsyncSessionLocal
from stream_capture import StreamCapture, MockStreamCapture
from config import FRAME_INTERVAL_SECONDS, MAX_FRAMES_PER_MATCH, SCORING_CATEGORIES

logger = logging.getLogger(__name__)


def _weighted_overall(row: dict) -> float:
    """Compute weighted overall score (0–100) from category averages."""
    total_weight = sum(c["weight"] for c in SCORING_CATEGORIES.values())
    score = sum(
        row.get(f"avg_{cat}", 0) * meta["weight"]
        for cat, meta in SCORING_CATEGORIES.items()
    )
    return round((score / total_weight), 2)


async def _upsert_team_stats(session: AsyncSession, team_number: int, obs: RobotObservation):
    """Update or create TeamStats for a team based on a new observation."""
    result = await session.execute(
        select(TeamStats).where(TeamStats.team_number == team_number)
    )
    stats = result.scalar_one_or_none()

    if not stats:
        stats = TeamStats(team_number=team_number, matches_scouted=0)
        session.add(stats)
        await session.flush()

    # Incremental running average
    n = stats.matches_scouted or 0

    def update_avg(current: float, new_val: float) -> float:
        if n == 0:
            return new_val
        return round((current * n + new_val) / (n + 1), 3)

    stats.avg_auto_scoring = update_avg(stats.avg_auto_scoring, obs.auto_scoring * 10)
    stats.avg_teleop_scoring = update_avg(stats.avg_teleop_scoring, obs.teleop_scoring * 10)
    stats.avg_defense = update_avg(stats.avg_defense, obs.defense * 10)
    stats.avg_endgame = update_avg(stats.avg_endgame, obs.endgame * 10)
    stats.avg_consistency = update_avg(stats.avg_consistency, obs.consistency * 10)
    stats.avg_speed = update_avg(stats.avg_speed, obs.speed * 10)
    stats.avg_coral_handling = update_avg(stats.avg_coral_handling, obs.coral_handling * 10)
    stats.avg_algae_handling = update_avg(stats.avg_algae_handling, obs.algae_handling * 10)

    stats.total_game_pieces += obs.game_pieces_scored
    stats.total_penalties += obs.penalties_incurred
    if obs.climb_attempted:
        stats.climb_attempts += 1
    if obs.climb_successful:
        stats.climb_successes += 1

    stats.matches_scouted = n + 1
    stats.last_updated = datetime.utcnow()

    stats.overall_score = _weighted_overall({
        "avg_auto_scoring": stats.avg_auto_scoring,
        "avg_teleop_scoring": stats.avg_teleop_scoring,
        "avg_defense": stats.avg_defense,
        "avg_endgame": stats.avg_endgame,
        "avg_consistency": stats.avg_consistency,
        "avg_speed": stats.avg_speed,
        "avg_coral_handling": stats.avg_coral_handling,
        "avg_algae_handling": stats.avg_algae_handling,
    })

    await session.commit()


async def _save_frame_results(
    match_key: str,
    frame_number: int,
    result: FrameAnalysisResult,
):
    """Persist all robot observations from a single frame to the database."""
    async with AsyncSessionLocal() as session:
        for robot in result.robots:
            if robot.team_number is None:
                continue  # Skip unidentified robots

            obs = RobotObservation(
                match_key=match_key,
                team_number=robot.team_number,
                frame_number=frame_number,
                match_phase=result.match_phase,
                auto_scoring=robot.auto_scoring,
                teleop_scoring=robot.teleop_scoring,
                defense=robot.defense,
                endgame=robot.endgame,
                consistency=robot.consistency,
                speed=robot.speed,
                coral_handling=robot.coral_handling,
                algae_handling=robot.algae_handling,
                game_pieces_scored=robot.game_pieces_scored,
                penalties_incurred=robot.penalties_incurred,
                climb_attempted=robot.climb_attempted,
                climb_successful=robot.climb_successful,
                ai_analysis_text=robot.position_description + " | " + ", ".join(robot.actions_observed),
                confidence=robot.confidence,
            )
            session.add(obs)

            await _upsert_team_stats(session, robot.team_number, obs)

        # Update match phase
        await session.execute(
            update(Match)
            .where(Match.match_key == match_key)
            .values(match_phase=result.match_phase)
        )
        await session.commit()


# Active scouting tasks: match_key -> asyncio.Task
_active_tasks: dict[str, asyncio.Task] = {}
# Event bus for broadcasting new results via WebSocket
_result_queue: asyncio.Queue = asyncio.Queue()


async def start_scouting(
    match_key: str,
    channel: str,
    use_mock: bool = False,
    match_context: dict | None = None,
):
    """Start an async scouting task for a match."""
    if match_key in _active_tasks and not _active_tasks[match_key].done():
        logger.warning(f"Match {match_key} already being scouted.")
        return

    task = asyncio.create_task(
        _scouting_loop(match_key, channel, use_mock, match_context)
    )
    _active_tasks[match_key] = task
    logger.info(f"Started scouting task for {match_key} on channel '{channel}'")


async def stop_scouting(match_key: str):
    """Cancel an active scouting task."""
    task = _active_tasks.get(match_key)
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    _active_tasks.pop(match_key, None)

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(Match)
            .where(Match.match_key == match_key)
            .values(is_active=False, ended_at=datetime.utcnow())
        )
        await session.commit()
    logger.info(f"Stopped scouting for {match_key}")


async def _scouting_loop(
    match_key: str,
    channel: str,
    use_mock: bool,
    match_context: dict | None,
):
    """Inner loop: capture frames, analyze with AI, persist results."""
    if use_mock:
        capture = MockStreamCapture(channel, frame_interval=FRAME_INTERVAL_SECONDS)
    else:
        capture = StreamCapture(channel, frame_interval=FRAME_INTERVAL_SECONDS)

    frame_count = 0
    try:
        async for frame_num, frame_b64 in capture.frame_generator():
            frame_count += 1
            if frame_count > MAX_FRAMES_PER_MATCH:
                logger.info(f"Reached max frames ({MAX_FRAMES_PER_MATCH}) for {match_key}")
                break

            logger.info(f"[{match_key}] Analyzing frame {frame_num}…")

            # Run AI analysis in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            result: FrameAnalysisResult = await loop.run_in_executor(
                None, analyze_frame, frame_b64, match_context
            )

            if result.error:
                logger.warning(f"Frame {frame_num} analysis error: {result.error}")
            else:
                await _save_frame_results(match_key, frame_num, result)
                await _result_queue.put({
                    "match_key": match_key,
                    "frame": frame_num,
                    "phase": result.match_phase,
                    "field_observations": result.field_observations,
                    "score_red": result.score_red,
                    "score_blue": result.score_blue,
                    "time_remaining": result.time_remaining,
                    "robots": [
                        {
                            "team_number": r.team_number,
                            "alliance": r.alliance,
                            "actions": r.actions_observed,
                            "confidence": r.confidence,
                        }
                        for r in result.robots
                    ],
                })
                logger.info(
                    f"[{match_key}] Frame {frame_num} done: "
                    f"phase={result.match_phase}, robots={len(result.robots)}"
                )

    except asyncio.CancelledError:
        logger.info(f"Scouting cancelled for {match_key}")
        raise
    finally:
        capture.stop()
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(Match)
                .where(Match.match_key == match_key)
                .values(is_active=False, ended_at=datetime.utcnow())
            )
            await session.commit()
        logger.info(f"Scouting loop finished for {match_key} ({frame_count} frames)")


def get_result_queue() -> asyncio.Queue:
    return _result_queue


def get_active_matches() -> list[str]:
    return [k for k, t in _active_tasks.items() if not t.done()]
