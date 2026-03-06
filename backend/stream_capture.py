"""Twitch stream capture and frame extraction module."""
import asyncio
import base64
import io
import logging
import subprocess
import tempfile
import time
from pathlib import Path
from typing import AsyncGenerator, Optional

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


def get_stream_url(channel: str, quality: str = "720p60,720p,best") -> Optional[str]:
    """Resolve a Twitch channel to a direct stream URL using streamlink."""
    try:
        result = subprocess.run(
            ["streamlink", "--stream-url", f"https://www.twitch.tv/{channel}", quality],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            logger.info(f"Resolved stream URL for {channel}")
            return url
        logger.error(f"streamlink error: {result.stderr}")
        return None
    except FileNotFoundError:
        logger.error("streamlink not found. Install with: pip install streamlink")
        return None
    except subprocess.TimeoutExpired:
        logger.error("streamlink timed out resolving stream URL")
        return None


class StreamCapture:
    """Captures frames from a Twitch livestream for analysis."""

    def __init__(self, channel: str, frame_interval: float = 5.0):
        self.channel = channel
        self.frame_interval = frame_interval
        self.cap: Optional[cv2.VideoCapture] = None
        self._stream_url: Optional[str] = None
        self._running = False
        self._frame_count = 0

    def _open_capture(self) -> bool:
        """Open the video capture from the stream URL."""
        self._stream_url = get_stream_url(self.channel)
        if not self._stream_url:
            return False
        self.cap = cv2.VideoCapture(self._stream_url)
        if not self.cap.isOpened():
            logger.error(f"Failed to open stream for {self.channel}")
            return False
        # Set buffer size small to stay near live
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        logger.info(f"Opened stream for {self.channel}")
        return True

    def stop(self):
        self._running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    async def frame_generator(self) -> AsyncGenerator[tuple[int, str], None]:
        """
        Async generator that yields (frame_number, base64_jpeg) tuples
        at the configured interval.
        """
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
            b64 = await loop.run_in_executor(None, self._encode_frame, frame)
            if b64:
                yield self._frame_count, b64

    @staticmethod
    def _encode_frame(frame: np.ndarray) -> Optional[str]:
        """Encode an OpenCV frame to base64 JPEG."""
        try:
            # Resize to reduce token cost — 1280×720 is plenty for vision
            h, w = frame.shape[:2]
            if w > 1280:
                scale = 1280 / w
                frame = cv2.resize(frame, (1280, int(h * scale)))
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return base64.b64encode(buf.tobytes()).decode("utf-8")
        except Exception as e:
            logger.error(f"Frame encoding error: {e}")
            return None


class MockStreamCapture(StreamCapture):
    """
    Mock stream capture for testing without a live Twitch stream.
    Serves synthetic FRC field frames via a test video file or solid color.
    """

    def __init__(self, source: str = "mock", frame_interval: float = 5.0):
        super().__init__(source, frame_interval)
        self.source = source

    async def frame_generator(self) -> AsyncGenerator[tuple[int, str], None]:
        self._running = True
        count = 0
        while self._running and count < 12:  # ~1 minute of mock data
            await asyncio.sleep(self.frame_interval)
            count += 1
            self._frame_count = count
            b64 = self._make_mock_frame(count)
            if b64:
                yield count, b64

    @staticmethod
    def _make_mock_frame(n: int) -> Optional[str]:
        """Create a synthetic blue/red field image with frame number overlay."""
        try:
            img = np.zeros((720, 1280, 3), dtype=np.uint8)
            # Field background
            cv2.rectangle(img, (0, 0), (1280, 720), (30, 80, 30), -1)
            # Alliance walls
            cv2.rectangle(img, (0, 0), (100, 720), (200, 50, 50), -1)    # red
            cv2.rectangle(img, (1180, 0), (1280, 720), (50, 50, 200), -1)  # blue
            # Center logo placeholder
            cv2.circle(img, (640, 360), 80, (255, 255, 255), 3)
            cv2.putText(img, f"FRC REEFSCAPE  Frame {n}", (400, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2)
            cv2.putText(img, "MOCK STREAM - No live Twitch feed connected", (280, 680),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return base64.b64encode(buf.tobytes()).decode("utf-8")
        except Exception as e:
            logger.error(f"Mock frame error: {e}")
            return None
