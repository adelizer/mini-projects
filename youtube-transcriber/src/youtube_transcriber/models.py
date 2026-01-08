"""Data models for YouTube Transcriber."""

from pydantic import BaseModel
from typing import Optional


class Video(BaseModel):
    """YouTube video metadata."""

    id: str
    title: str
    url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[int] = None  # seconds
    published_at: Optional[str] = None
    channel_id: Optional[str] = None
    channel_title: Optional[str] = None


class Transcript(BaseModel):
    """Video transcript."""

    video_id: str
    text: str
    language: str = "en"
    segments: Optional[list[dict]] = None  # timestamp segments if available
    source: str = "youtube"  # "youtube" or "whisper"


class TranscriptResult(BaseModel):
    """Result of a transcription attempt."""

    video: Video
    transcript: Optional[Transcript] = None
    success: bool
    error: Optional[str] = None
    needs_whisper: bool = False  # True if YouTube transcript not available
