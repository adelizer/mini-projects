"""YouTube scraper for Shark Tank Egypt videos."""

import json
import re
import subprocess
from pathlib import Path
from typing import Optional

from .models import Video


class YouTubeScraper:
    """Scrapes Shark Tank Egypt videos from YouTube."""

    # Official Shark Tank Egypt channel
    CHANNEL_URL = "https://www.youtube.com/@SharkTankEgypt"
    # Playlist URL can be provided when calling get_playlist_videos()
    PLAYLIST_URL: Optional[str] = None

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_playlist_videos(self, playlist_url: str) -> list[Video]:
        """Get all videos from a YouTube playlist using yt-dlp."""
        url = playlist_url

        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--dump-json",
            url,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error fetching playlist: {result.stderr}")
            return []

        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            data = json.loads(line)
            video = self._parse_video_data(data)
            if video:
                videos.append(video)

        return videos

    def get_channel_videos(self, channel_url: Optional[str] = None) -> list[Video]:
        """Get all videos from a YouTube channel."""
        url = channel_url or self.CHANNEL_URL

        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--dump-json",
            f"{url}/videos",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error fetching channel: {result.stderr}")
            return []

        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            data = json.loads(line)
            video = self._parse_video_data(data)
            if video:
                videos.append(video)

        return videos

    def search_videos(self, query: str = "Shark Tank Egypt", max_results: int = 50) -> list[Video]:
        """Search YouTube for Shark Tank Egypt videos."""
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--dump-json",
            f"ytsearch{max_results}:{query}",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error searching: {result.stderr}")
            return []

        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            data = json.loads(line)
            video = self._parse_video_data(data)
            if video:
                videos.append(video)

        return videos

    def _parse_video_data(self, data: dict) -> Optional[Video]:
        """Parse yt-dlp JSON output into Video model."""
        video_id = data.get("id")
        if not video_id:
            return None

        title = data.get("title", "")
        episode_num = self._extract_episode_number(title)

        return Video(
            id=video_id,
            title=title,
            url=f"https://www.youtube.com/watch?v={video_id}",
            thumbnail_url=data.get("thumbnail"),
            duration=data.get("duration"),
            published_at=data.get("upload_date"),
            episode_number=episode_num,
        )

    def _extract_episode_number(self, title: str) -> Optional[int]:
        """Extract episode number from video title."""
        # Common patterns: "Episode 1", "الحلقة 1", "E01", "Ep. 1", etc.
        patterns = [
            r"Episode\s*(\d+)",
            r"الحلقة\s*(\d+)",
            r"E(\d+)",
            r"Ep\.?\s*(\d+)",
            r"حلقة\s*(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    def save_videos(self, videos: list[Video], filename: str = "videos.json") -> Path:
        """Save videos to JSON file."""
        output_path = self.data_dir / filename
        data = [v.model_dump() for v in videos]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Saved {len(videos)} videos to {output_path}")
        return output_path

    def load_videos(self, filename: str = "videos.json") -> list[Video]:
        """Load videos from JSON file."""
        input_path = self.data_dir / filename

        if not input_path.exists():
            return []

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [Video(**v) for v in data]
