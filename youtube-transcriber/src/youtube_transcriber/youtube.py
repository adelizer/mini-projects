"""YouTube video fetching utilities."""

import json
import re
import subprocess
from pathlib import Path
from typing import Optional

from .models import Video


class YouTubeFetcher:
    """Fetches video metadata from YouTube channels, playlists, and URLs."""

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize the fetcher.

        Args:
            output_dir: Optional directory to save video metadata.
                       If not provided, a default 'data' directory will be created.
        """
        self.output_dir = output_dir or Path("data")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_channel_videos(self, channel_url: str) -> list[Video]:
        """Get all videos from a YouTube channel.

        Args:
            channel_url: YouTube channel URL (e.g., https://www.youtube.com/@ChannelName)

        Returns:
            List of Video objects with metadata
        """
        # Ensure we're fetching from the videos tab
        url = channel_url.rstrip("/")
        if not url.endswith("/videos"):
            url = f"{url}/videos"

        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--dump-json",
            url,
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

    def get_playlist_videos(self, playlist_url: str) -> list[Video]:
        """Get all videos from a YouTube playlist.

        Args:
            playlist_url: YouTube playlist URL

        Returns:
            List of Video objects with metadata
        """
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--dump-json",
            playlist_url,
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

    def get_video(self, video_url: str) -> Optional[Video]:
        """Get metadata for a single video.

        Args:
            video_url: YouTube video URL or video ID

        Returns:
            Video object with metadata, or None if not found
        """
        # Handle video ID vs full URL
        if not video_url.startswith("http"):
            video_url = f"https://www.youtube.com/watch?v={video_url}"

        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-playlist",
            video_url,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Error fetching video: {result.stderr}")
            return None

        if not result.stdout.strip():
            return None

        data = json.loads(result.stdout.strip())
        return self._parse_video_data(data)

    def get_videos(self, video_urls: list[str]) -> list[Video]:
        """Get metadata for multiple videos.

        Args:
            video_urls: List of YouTube video URLs or video IDs

        Returns:
            List of Video objects with metadata
        """
        videos = []
        for url in video_urls:
            video = self.get_video(url)
            if video:
                videos.append(video)
            else:
                print(f"  Skipping invalid URL: {url}")
        return videos

    def search_videos(self, query: str, max_results: int = 10) -> list[Video]:
        """Search YouTube for videos matching a query.

        Args:
            query: Search query string
            max_results: Maximum number of results to return (default: 10)

        Returns:
            List of Video objects matching the search
        """
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

        return Video(
            id=video_id,
            title=data.get("title", ""),
            url=f"https://www.youtube.com/watch?v={video_id}",
            thumbnail_url=data.get("thumbnail"),
            duration=data.get("duration"),
            published_at=data.get("upload_date"),
            channel_id=data.get("channel_id"),
            channel_title=data.get("channel") or data.get("uploader"),
        )

    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats.

        Args:
            url: YouTube URL in any format

        Returns:
            Video ID string, or None if not found
        """
        patterns = [
            r"(?:v=|/)([a-zA-Z0-9_-]{11})(?:[&?]|$)",  # Standard and share URLs
            r"youtu\.be/([a-zA-Z0-9_-]{11})",  # Short URLs
            r"embed/([a-zA-Z0-9_-]{11})",  # Embed URLs
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # Check if it's already just a video ID
        if re.match(r"^[a-zA-Z0-9_-]{11}$", url):
            return url

        return None

    def save_videos(self, videos: list[Video], filename: str = "videos.json") -> Path:
        """Save videos to JSON file.

        Args:
            videos: List of Video objects
            filename: Output filename (default: videos.json)

        Returns:
            Path to saved file
        """
        output_path = self.output_dir / filename
        data = [v.model_dump() for v in videos]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Saved {len(videos)} videos to {output_path}")
        return output_path

    def load_videos(self, filename: str = "videos.json") -> list[Video]:
        """Load videos from JSON file.

        Args:
            filename: Input filename (default: videos.json)

        Returns:
            List of Video objects
        """
        input_path = self.output_dir / filename

        if not input_path.exists():
            return []

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [Video(**v) for v in data]
