"""Load and parse YouTube transcripts."""

import json
from pathlib import Path
from pydantic import BaseModel


class TranscriptSegment(BaseModel):
    """A single segment of the transcript with timing."""
    start: float
    duration: float
    text: str


class Transcript(BaseModel):
    """A YouTube video transcript."""
    video_id: str
    text: str
    language: str
    segments: list[TranscriptSegment]
    source: str

    @property
    def duration_seconds(self) -> float:
        """Total duration of the video in seconds."""
        if not self.segments:
            return 0
        last = self.segments[-1]
        return last.start + last.duration

    @property
    def duration_formatted(self) -> str:
        """Duration as MM:SS format."""
        total = int(self.duration_seconds)
        minutes = total // 60
        seconds = total % 60
        return f"{minutes}:{seconds:02d}"

    @property
    def word_count(self) -> int:
        """Total word count."""
        return len(self.text.split())

    @property
    def words_per_minute(self) -> float:
        """Average words per minute."""
        if self.duration_seconds == 0:
            return 0
        return self.word_count / (self.duration_seconds / 60)


def load_transcript(path: Path) -> Transcript:
    """Load a single transcript from a JSON file."""
    with open(path) as f:
        data = json.load(f)
    return Transcript(**data)


def load_all_transcripts(directory: Path) -> list[Transcript]:
    """Load all transcripts from a directory."""
    transcripts = []
    for path in sorted(directory.glob("*.json")):
        try:
            transcripts.append(load_transcript(path))
        except Exception as e:
            print(f"Error loading {path}: {e}")
    return transcripts
