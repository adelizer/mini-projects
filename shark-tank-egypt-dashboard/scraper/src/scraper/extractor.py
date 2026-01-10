"""Extract startup information from transcripts using LLM."""

import hashlib
import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

from .models import Startup, Transcript, Video

load_dotenv()


EXTRACTION_PROMPT = """You are analyzing a transcript from Shark Tank Egypt (شارك تانك مصر).
Your task is to extract information about each startup that pitched in this episode.

For each startup mentioned, extract:
1. name: The startup/company name (both English and Arabic if available)
2. description: What the company does (1-2 sentences)
3. industry: The industry/sector (e.g., Food, Tech, Healthcare, Fashion, etc.)
4. ask_amount: How much money they asked for (in EGP)
5. ask_equity: What percentage equity they offered
6. deal_made: Whether a deal was made (true/false)
7. deal_amount: Final deal amount if different from ask (in EGP)
8. deal_equity: Final equity percentage if different from ask
9. sharks: Names of sharks who made the deal (empty list if no deal)
10. founders: Names of founders/presenters
11. website: Website URL if mentioned
12. timestamp_start: Approximate start time in the video if mentioned

Return a JSON array of startup objects. If no startups are found, return an empty array.

Here is the transcript:
{transcript}

Return ONLY valid JSON, no other text."""


class StartupExtractor:
    """Extracts startup information from transcripts using OpenAI."""

    def __init__(self, data_dir: Path, model: str = "gpt-4o-mini"):
        self.data_dir = data_dir
        self.model = model
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.cache_dir = data_dir / "extraction_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def extract_startups(self, transcript: Transcript, video: Video) -> list[Startup]:
        """Extract startup information from a transcript."""
        # Check cache first
        cached = self._load_from_cache(transcript.video_id)
        if cached:
            print(f"Using cached extraction for {transcript.video_id}")
            return cached

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a data extraction assistant. Extract structured information from Shark Tank Egypt transcripts.",
                    },
                    {
                        "role": "user",
                        "content": EXTRACTION_PROMPT.format(transcript=transcript.text),
                    },
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if not content:
                return []

            data = json.loads(content)

            # Handle both array and object with "startups" key
            if isinstance(data, dict):
                startups_data = data.get("startups", [])
            else:
                startups_data = data

            startups = []
            for i, s in enumerate(startups_data):
                startup = self._parse_startup(s, video, i)
                if startup:
                    startups.append(startup)

            # Cache the results
            self._save_to_cache(transcript.video_id, startups)

            return startups

        except Exception as e:
            print(f"Error extracting from {transcript.video_id}: {e}")
            return []

    def _parse_startup(self, data: dict, video: Video, index: int) -> Optional[Startup]:
        """Parse raw extraction data into Startup model."""
        name = data.get("name")
        name_ar = data.get("name_ar")

        # Handle case where LLM returns name as dict with english/arabic keys
        if isinstance(name, dict):
            name_ar = name.get("arabic") or name.get("ar")
            name = name.get("english") or name.get("en") or str(name)

        if not name:
            return None

        # Generate a unique ID
        startup_id = self._generate_id(video.id, name, index)

        return Startup(
            id=startup_id,
            name=name,
            name_ar=name_ar or data.get("name_ar"),
            season_number=video.season_number,
            episode_number=video.episode_number or 0,
            description=data.get("description", ""),
            industry=data.get("industry"),
            ask_amount=self._parse_number(data.get("ask_amount")),
            ask_equity=self._parse_number(data.get("ask_equity")),
            valuation=self._calculate_valuation(
                self._parse_number(data.get("ask_amount")),
                self._parse_number(data.get("ask_equity")),
            ),
            deal_made=bool(data.get("deal_made", False)),
            deal_amount=self._parse_number(data.get("deal_amount")),
            deal_equity=self._parse_number(data.get("deal_equity")),
            sharks=data.get("sharks", []),
            website=data.get("website"),
            founders=data.get("founders", []),
            timestamp_start=data.get("timestamp_start"),
            video_id=video.id,
            video_url=video.url,
        )

    def _generate_id(self, video_id: str, name: str, index: int) -> str:
        """Generate a unique ID for a startup."""
        raw = f"{video_id}_{name}_{index}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _parse_number(self, value) -> Optional[float]:
        """Parse a number from various formats."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remove common formatting
            cleaned = value.replace(",", "").replace("EGP", "").replace("%", "").strip()
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    def _calculate_valuation(
        self, amount: Optional[float], equity: Optional[float]
    ) -> Optional[float]:
        """Calculate implied valuation from ask amount and equity."""
        if amount and equity and equity > 0:
            return (amount / equity) * 100
        return None

    def _get_cache_path(self, video_id: str) -> Path:
        """Get cache file path for a video."""
        return self.cache_dir / f"{video_id}.json"

    def _load_from_cache(self, video_id: str) -> Optional[list[Startup]]:
        """Load extracted startups from cache."""
        cache_path = self._get_cache_path(video_id)
        if not cache_path.exists():
            return None

        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return [Startup(**s) for s in data]

    def _save_to_cache(self, video_id: str, startups: list[Startup]) -> None:
        """Save extracted startups to cache."""
        cache_path = self._get_cache_path(video_id)

        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(
                [s.model_dump() for s in startups], f, ensure_ascii=False, indent=2
            )

    def extract_all(
        self, transcripts: dict[str, Transcript], videos: dict[str, Video]
    ) -> list[Startup]:
        """Extract startups from all transcripts."""
        all_startups = []

        for video_id, transcript in transcripts.items():
            video = videos.get(video_id)
            if not video:
                continue

            startups = self.extract_startups(transcript, video)
            all_startups.extend(startups)
            print(f"Extracted {len(startups)} startups from {video.title}")

        return all_startups

    def save_startups(
        self, startups: list[Startup], filename: str = "startups.json"
    ) -> Path:
        """Save all startups to a JSON file."""
        output_path = self.data_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                [s.model_dump() for s in startups], f, ensure_ascii=False, indent=2
            )

        print(f"Saved {len(startups)} startups to {output_path}")
        return output_path
