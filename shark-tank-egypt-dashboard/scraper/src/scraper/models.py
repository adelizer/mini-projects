"""Data models for Shark Tank Egypt scraper."""

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
    season_number: Optional[int] = None
    episode_number: Optional[int] = None


class Transcript(BaseModel):
    """Video transcript."""

    video_id: str
    text: str
    language: str = "ar"
    segments: Optional[list[dict]] = None  # timestamp segments if available


class Startup(BaseModel):
    """Extracted startup information."""

    id: str
    name: str
    name_ar: Optional[str] = None  # Arabic name
    season_number: Optional[int] = None
    episode_number: int
    description: str
    industry: Optional[str] = None

    # Pitch details
    ask_amount: Optional[float] = None  # in EGP
    ask_equity: Optional[float] = None  # percentage
    valuation: Optional[float] = None  # calculated or stated

    # Deal outcome
    deal_made: bool
    deal_amount: Optional[float] = None
    deal_equity: Optional[float] = None
    sharks: list[str] = []  # names of sharks who made the deal

    # Additional info
    website: Optional[str] = None
    social_media: Optional[dict[str, str]] = None
    founders: list[str] = []
    screenshot_url: Optional[str] = None

    # Source reference
    video_id: str
    video_url: str
    timestamp_start: Optional[str] = None  # when they appear in the video


class Episode(BaseModel):
    """Episode information."""

    number: int
    title: str
    video: Video
    transcript: Optional[Transcript] = None
    startups: list[Startup] = []
