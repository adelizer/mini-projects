"""Demo script to simulate transcription progress for screen recording."""

import json
import random
import time
from pathlib import Path


def load_episodes(data_dir: Path) -> list[dict]:
    """Load episodes from episodes.json."""
    episodes_path = data_dir / "episodes.json"
    if episodes_path.exists():
        with open(episodes_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def load_transcript(transcripts_dir: Path, video_id: str) -> dict | None:
    """Load a transcript file."""
    transcript_path = transcripts_dir / f"{video_id}.json"
    if transcript_path.exists():
        with open(transcript_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def format_duration(seconds: int) -> str:
    """Format duration as mm:ss or hh:mm:ss."""
    if seconds >= 3600:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h}:{m:02d}:{s:02d}"
    else:
        m = seconds // 60
        s = seconds % 60
        return f"{m}:{s:02d}"


def simulate_transcription(data_dir: Path, delay_range: tuple[float, float] = (1.5, 3.0)):
    """Simulate the transcription process with realistic output."""
    transcripts_dir = data_dir / "transcripts"

    # Load episodes
    episodes = load_episodes(data_dir)
    if not episodes:
        print("No episodes found!")
        return

    # Filter to only episodes with transcripts
    episodes_with_transcripts = []
    for ep in episodes:
        transcript = load_transcript(transcripts_dir, ep["id"])
        if transcript:
            ep["_transcript"] = transcript
            episodes_with_transcripts.append(ep)

    total = len(episodes_with_transcripts)

    print(f"Data directory: {data_dir}")
    print(f"\n=== Step 1: Loading episodes ===")
    time.sleep(0.5)
    print(f"Found {total} episodes")

    # Calculate total duration
    total_duration = sum(ep.get("duration", 0) for ep in episodes_with_transcripts)
    hours = total_duration / 3600
    print(f"Total duration: {hours:.1f} hours")

    time.sleep(1.0)

    print(f"\n=== Step 2: Transcribing videos ===")
    print(f"Processing {total} videos")
    print(f"Already have 0 cached transcripts\n")

    time.sleep(0.5)

    for i, ep in enumerate(episodes_with_transcripts):
        video_id = ep["id"]
        season = ep.get("season_number", "?")
        episode = ep.get("episode_number", "?")
        duration = ep.get("duration", 0)
        transcript = ep["_transcript"]

        # Build title
        title = f"S{season}E{episode}"

        print(f"[{i}/{total}] Processing: {title} ({format_duration(duration)})...")

        # Simulate processing time based on duration
        # Shorter videos = faster, with some randomness
        base_delay = random.uniform(*delay_range)
        duration_factor = min(duration / 300, 2.0)  # Cap at 2x for long videos
        actual_delay = base_delay * (0.5 + duration_factor * 0.5)

        time.sleep(actual_delay)

        # Show success with transcript length
        text_len = len(transcript.get("text", ""))
        print(f"  ✓ Saved transcript for {video_id} ({text_len:,} chars)")

    print(f"\nTranscription complete:")
    print(f"  - Success: {total}/{total}")
    print(f"  - Failed: 0")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Demo transcription progress")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).parent.parent.parent.parent / "data",
        help="Directory with data",
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=1.5,
        help="Minimum delay between videos (seconds)",
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=3.0,
        help="Maximum delay between videos (seconds)",
    )

    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    simulate_transcription(data_dir, (args.min_delay, args.max_delay))


if __name__ == "__main__":
    main()
