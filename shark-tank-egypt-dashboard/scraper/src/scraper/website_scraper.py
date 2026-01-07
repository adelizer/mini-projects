"""Scraper for sharktank-egypt.com to get official episode list."""

import json
import re
from pathlib import Path
from typing import Optional

import httpx

from .models import Video


class WebsiteScraper:
    """Scrapes episode data from the official Shark Tank Egypt website."""

    BASE_URL = "https://sharktank-egypt.com"
    SEASONS = [
        {"slug": "season-1", "name": "Season 1", "number": 1},
        {"slug": "season-2", "name": "Season 2", "number": 2},
        {"slug": "season-3", "name": "Season 3", "number": 3},
        {"slug": "special-episodes-", "name": "Special Episodes", "number": 0},
    ]

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.client = httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
            follow_redirects=True,
            timeout=30.0,
        )

    def get_season_episodes(self, season_slug: str, season_number: int) -> list[Video]:
        """Fetch episodes for a specific season."""
        url = f"{self.BASE_URL}/en/seasons/{season_slug}"
        print(f"Fetching {url}...")

        try:
            response = self.client.get(url)
            response.raise_for_status()
            html = response.text

            # Extract YouTube video IDs from the page
            # Pattern matches youtube.com/watch?v=VIDEO_ID
            pattern = r'youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})'
            video_ids = re.findall(pattern, html)

            # Remove duplicates while preserving order
            seen = set()
            unique_ids = []
            for vid_id in video_ids:
                if vid_id not in seen:
                    seen.add(vid_id)
                    unique_ids.append(vid_id)

            videos = []
            for i, video_id in enumerate(unique_ids, 1):
                video = Video(
                    id=video_id,
                    title=f"Season {season_number} Episode {i}" if season_number > 0 else f"Special Episode {i}",
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    season_number=season_number if season_number > 0 else None,
                    episode_number=i,
                )
                videos.append(video)

            print(f"  Found {len(videos)} episodes")
            return videos

        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return []

    def get_all_episodes(self) -> list[Video]:
        """Fetch all episodes from all seasons."""
        all_videos = []

        for season in self.SEASONS:
            videos = self.get_season_episodes(season["slug"], season["number"])

            # Update titles with season info
            for video in videos:
                if season["number"] > 0:
                    video.title = f"Season {season['number']} - Episode {video.episode_number}"
                else:
                    video.title = f"Special Episode {video.episode_number}"

            all_videos.extend(videos)

        print(f"\nTotal episodes found: {len(all_videos)}")
        return all_videos

    def get_video_metadata(self, videos: list[Video]) -> list[Video]:
        """Enrich videos with metadata from YouTube using yt-dlp."""
        import subprocess

        enriched = []
        for i, video in enumerate(videos):
            print(f"[{i+1}/{len(videos)}] Getting metadata for {video.id}...")

            cmd = [
                "yt-dlp",
                "--dump-json",
                "--no-download",
                video.url,
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    video.duration = data.get("duration")
                    video.thumbnail_url = data.get("thumbnail")
                    video.published_at = data.get("upload_date")
                    # Keep our custom title with season info
            except Exception as e:
                print(f"  Error getting metadata: {e}")

            enriched.append(video)

        return enriched

    def save_episodes(self, videos: list[Video], filename: str = "episodes.json") -> Path:
        """Save episodes to JSON file."""
        output_path = self.data_dir / filename
        data = [v.model_dump() for v in videos]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Saved {len(videos)} episodes to {output_path}")
        return output_path

    def load_episodes(self, filename: str = "episodes.json") -> list[Video]:
        """Load episodes from JSON file."""
        input_path = self.data_dir / filename

        if not input_path.exists():
            return []

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [Video(**v) for v in data]

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
