"""Stream capture and frame extraction module.

Supports:
  - Twitch streams via streamlink
  - YouTube live streams via yt-dlp
  - Any direct HLS/RTMP URL via OpenCV
  - Mock frames for testing
"""
import asyncio
import base64
import logging
import subprocess
import time
from typing import AsyncGenerator, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ─── URL Resolution ───────────────────────────────────────────────────────────

def get_twitch_stream_url(channel: str, quality: str = "720p60,720p,best") -> Optional[str]:
    """Resolve a Twitch channel name to a direct HLS URL using streamlink."""
    try:
        result = subprocess.run(
            ["streamlink", "--stream-url", f"https://www.twitch.tv/{channel}", quality],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            logger.info(f"Resolved Twitch stream URL for {channel}")
            return url
        logger.error(f"streamlink error for {channel}: {result.stderr.strip()}")
        return None
    except FileNotFoundError:
        logger.error("streamlink not found. Install with: pip install streamlink")
        return None
    except subprocess.TimeoutExpired:
        logger.error("streamlink timed out resolving Twitch stream URL")
        return None


def get_youtube_stream_url(video_id_or_url: str, quality: str = "best[height<=720]") -> Optional[str]:
    """
    Resolve a YouTube video ID or URL to a direct stream URL using yt-dlp.
    Works for both live streams and recorded videos.
    """
    url = (
        video_id_or_url
        if video_id_or_url.startswith("http")
        else f"https://www.youtube.com/watch?v={video_id_or_url}"
    )
    try:
        result = subprocess.run(
            ["yt-dlp", "--no-warnings", "-g", "-f", quality, url],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            direct_url = result.stdout.strip().splitlines()[0]
            logger.info(f"Resolved YouTube stream URL for {video_id_or_url}")
            return direct_url
        logger.error(f"yt-dlp error for {video_id_or_url}: {result.stderr.strip()}")
        return None
    except FileNotFoundError:
        logger.error("yt-dlp not found. Install with: pip install yt-dlp")
        return None
    except subprocess.TimeoutExpired:
        logger.error("yt-dlp timed out resolving YouTube stream URL")
        return None


# ─── Base StreamCapture ───────────────────────────────────────────────────────

class StreamCapture:
    """Captures frames from a live video stream for AI analysis."""

    def __init__(self, source: str, frame_interval: float = 5.0):
        self.source = source
        self.frame_interval = frame_interval
        self.cap: Optional[cv2.VideoCapture] = None
        self._stream_url: Optional[str] = None
        self._running = False
        self._frame_count = 0

    def _resolve_url(self) -> Optional[str]:
        """Subclasses override this to resolve the source to a direct URL."""
        return self.source  # assume already a direct URL

    def _open_capture(self) -> bool:
        """Resolve and open the video capture."""
        self._stream_url = self._resolve_url()
        if not self._stream_url:
            return False
        self.cap = cv2.VideoCapture(self._stream_url)
        if not self.cap.isOpened():
            logger.error(f"Failed to open stream: {self.source}")
            return False
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        logger.info(f"Opened stream: {self.source}")
        return True

    def stop(self):
        self._running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    async def frame_generator(self) -> AsyncGenerator[tuple[int, str], None]:
        """Async generator yielding (frame_number, base64_jpeg) at frame_interval."""
        self._running = True
        loop = asyncio.get_event_loop()

        opened = await loop.run_in_executor(None, self._open_capture)
        if not opened:
            logger.error("Could not open stream — yielding no frames.")
            return

        last_capture = 0.0
        while self._running:
            now = time.time()
            if now - last_capture < self.frame_interval:
                await asyncio.sleep(0.1)
                continue

            ret, frame = await loop.run_in_executor(None, self.cap.read)
            if not ret:
                logger.warning("Lost stream, attempting reconnect…")
                await asyncio.sleep(5)
                opened = await loop.run_in_executor(None, self._open_capture)
                if not opened:
                    break
                continue

            last_capture = now
            self._frame_count += 1
            b64 = await loop.run_in_executor(None, _encode_frame, frame)
            if b64:
                yield self._frame_count, b64

    # Legacy alias used by scouter_engine
    channel = property(lambda self: self.source)


class TwitchStreamCapture(StreamCapture):
    """Captures frames from a Twitch channel."""

    def _resolve_url(self) -> Optional[str]:
        return get_twitch_stream_url(self.source)


class YouTubeStreamCapture(StreamCapture):
    """Captures frames from a YouTube live stream or video."""

    def _resolve_url(self) -> Optional[str]:
        return get_youtube_stream_url(self.source)


# ─── Mock stream ─────────────────────────────────────────────────────────────

class MockStreamCapture(StreamCapture):
    """
    Mock stream for testing without a live feed.
    Serves synthetic FRC field frames.
    """

    async def frame_generator(self) -> AsyncGenerator[tuple[int, str], None]:
        self._running = True
        count = 0
        while self._running and count < 12:  # ~1 minute of mock data
            await asyncio.sleep(self.frame_interval)
            count += 1
            self._frame_count = count
            b64 = _make_mock_frame(count)
            if b64:
                yield count, b64


# ─── Factory ──────────────────────────────────────────────────────────────────

def create_stream_capture(
    channel_or_url: str,
    stream_type: str = "twitch",
    frame_interval: float = 5.0,
    use_mock: bool = False,
) -> StreamCapture:
    """
    Factory that returns the right StreamCapture subclass.

    Args:
        channel_or_url: Twitch channel name, YouTube video ID, or direct URL.
        stream_type: "twitch", "youtube", or "direct".
        frame_interval: Seconds between captured frames.
        use_mock: If True, always return a MockStreamCapture.
    """
    if use_mock:
        return MockStreamCapture(channel_or_url, frame_interval)
    if stream_type == "youtube":
        return YouTubeStreamCapture(channel_or_url, frame_interval)
    if stream_type == "twitch":
        return TwitchStreamCapture(channel_or_url, frame_interval)
    # Direct URL or unknown — use base class
    return StreamCapture(channel_or_url, frame_interval)


# ─── Utilities ────────────────────────────────────────────────────────────────

def _encode_frame(frame: np.ndarray) -> Optional[str]:
    """Encode an OpenCV frame to base64 JPEG (max 1280px wide)."""
    try:
        h, w = frame.shape[:2]
        if w > 1280:
            scale = 1280 / w
            frame = cv2.resize(frame, (1280, int(h * scale)))
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return base64.b64encode(buf.tobytes()).decode("utf-8")
    except Exception as e:
        logger.error(f"Frame encoding error: {e}")
        return None


def _make_mock_frame(n: int) -> Optional[str]:
    """Create a synthetic FRC field frame with frame number overlay."""
    try:
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        cv2.rectangle(img, (0, 0), (1280, 720), (30, 80, 30), -1)
        cv2.rectangle(img, (0, 0), (100, 720), (200, 50, 50), -1)
        cv2.rectangle(img, (1180, 0), (1280, 720), (50, 50, 200), -1)
        cv2.circle(img, (640, 360), 80, (255, 255, 255), 3)
        cv2.putText(img, f"FRC REBUILT 2026  Frame {n}", (380, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
        cv2.putText(img, "MOCK STREAM — No live feed connected", (310, 680),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return base64.b64encode(buf.tobytes()).decode("utf-8")
    except Exception as e:
        logger.error(f"Mock frame error: {e}")
        return None
