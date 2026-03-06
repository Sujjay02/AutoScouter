"""Database models and setup."""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean, Text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True)
    match_key = Column(String, unique=True, index=True)
    event_key = Column(String, nullable=True)
    twitch_channel = Column(String)
    stream_url = Column(String, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    match_phase = Column(String, default="pre_match")  # pre_match, auto, teleop, endgame, post_match
    red_alliance = Column(JSON, default=list)   # [team_number, ...]
    blue_alliance = Column(JSON, default=list)
    raw_score_red = Column(Integer, nullable=True)
    raw_score_blue = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)


class RobotObservation(Base):
    __tablename__ = "robot_observations"

    id = Column(Integer, primary_key=True, index=True)
    match_key = Column(String, index=True)
    team_number = Column(Integer, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    frame_number = Column(Integer, default=0)
    match_phase = Column(String)  # auto, teleop, endgame

    # Raw scores from AI analysis (0-10 scale per observation)
    auto_scoring = Column(Float, default=0)
    teleop_scoring = Column(Float, default=0)
    defense = Column(Float, default=0)
    endgame = Column(Float, default=0)
    consistency = Column(Float, default=0)
    speed = Column(Float, default=0)
    coral_handling = Column(Float, default=0)
    algae_handling = Column(Float, default=0)

    # Specific events detected
    game_pieces_scored = Column(Integer, default=0)
    penalties_incurred = Column(Integer, default=0)
    climb_attempted = Column(Boolean, default=False)
    climb_successful = Column(Boolean, default=False)

    ai_analysis_text = Column(Text, nullable=True)
    confidence = Column(Float, default=0.5)


class TeamStats(Base):
    __tablename__ = "team_stats"

    id = Column(Integer, primary_key=True, index=True)
    team_number = Column(Integer, unique=True, index=True)
    team_name = Column(String, nullable=True)
    matches_scouted = Column(Integer, default=0)
    overall_rank = Column(Integer, nullable=True)

    # Averaged scores (0-100 scale)
    avg_auto_scoring = Column(Float, default=0)
    avg_teleop_scoring = Column(Float, default=0)
    avg_defense = Column(Float, default=0)
    avg_endgame = Column(Float, default=0)
    avg_consistency = Column(Float, default=0)
    avg_speed = Column(Float, default=0)
    avg_coral_handling = Column(Float, default=0)
    avg_algae_handling = Column(Float, default=0)
    overall_score = Column(Float, default=0)

    total_game_pieces = Column(Integer, default=0)
    total_penalties = Column(Integer, default=0)
    climb_attempts = Column(Integer, default=0)
    climb_successes = Column(Integer, default=0)

    last_updated = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
