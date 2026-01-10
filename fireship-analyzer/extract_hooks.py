"""Extract hooks (first 20 seconds) from YouTube playlist videos."""

import json
import sys
from pathlib import Path

# Add youtube-transcriber to path
sys.path.insert(0, str(Path(__file__).parent.parent / "youtube-transcriber" / "src"))

from youtube_transcriber.youtube import YouTubeFetcher
from youtube_transcriber.transcriber import Transcriber


def extract_hook_from_transcript(transcript, max_seconds: float = 20.0) -> str:
    """Extract the first N seconds of text from a transcript.

    Args:
        transcript: Transcript object with segments
        max_seconds: Maximum duration to extract (default: 20 seconds)

    Returns:
        Text from the first N seconds of the video
    """
    if not transcript.segments:
        # If no segments, take first ~50 words as approximation
        words = transcript.text.split()
        # Assuming ~150 WPM, 20 seconds = ~50 words
        return " ".join(words[:50])

    hook_text_parts = []
    for segment in transcript.segments:
        # Segment has 'start', 'duration', 'text'
        start = segment.get("start", 0)
        if start < max_seconds:
            hook_text_parts.append(segment.get("text", ""))
        else:
            break

    return " ".join(hook_text_parts)


def main():
    playlist_url = "https://www.youtube.com/playlist?list=PL0vfts4VzfNieTtC_yYSK7M1S5Hz_ffPz"

    # Setup output directory
    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("Fireship Hooks Extractor")
    print("=" * 60)

    # Fetch playlist videos
    print(f"\nFetching videos from playlist...")
    fetcher = YouTubeFetcher(output_dir=output_dir)
    videos = fetcher.get_playlist_videos(playlist_url)

    if not videos:
        print("No videos found in playlist!")
        return

    print(f"Found {len(videos)} videos in playlist")

    # Setup transcriber
    transcriber = Transcriber(output_dir=output_dir)

    # Extract hooks for each video
    results = []

    for i, video in enumerate(videos, 1):
        print(f"\n[{i}/{len(videos)}] {video.title[:60]}...")

        # Get transcript
        result = transcriber.transcribe_video(video, languages=["en"])

        if not result.success or not result.transcript:
            print(f"  - No transcript available")
            results.append({
                "video_id": video.id,
                "video_url": video.url,
                "title": video.title,
                "hook": None,
                "error": result.error or "No transcript available"
            })
            continue

        # Extract hook (first 20 seconds)
        hook = extract_hook_from_transcript(result.transcript, max_seconds=20.0)
        print(f"  - Hook extracted: {hook[:80]}...")

        results.append({
            "video_id": video.id,
            "video_url": video.url,
            "title": video.title,
            "hook": hook,
            "error": None
        })

    # Save results to JSON
    output_file = output_dir / "fireship_hooks.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n" + "=" * 60)
    print(f"Results saved to {output_file}")

    # Also create a readable markdown file
    md_file = output_dir / "fireship_hooks.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write("# Fireship Video Hooks (First 20 Seconds)\n\n")
        f.write(f"Playlist: {playlist_url}\n\n")
        f.write(f"Total videos: {len(results)}\n\n")
        f.write("---\n\n")

        for r in results:
            f.write(f"## {r['title']}\n\n")
            f.write(f"**Video:** {r['video_url']}\n\n")
            if r['hook']:
                f.write(f"**Hook:**\n> {r['hook']}\n\n")
            else:
                f.write(f"**Error:** {r['error']}\n\n")
            f.write("---\n\n")

    print(f"Markdown saved to {md_file}")

    # Summary
    successful = sum(1 for r in results if r['hook'])
    print(f"\nSummary: {successful}/{len(results)} hooks extracted")


if __name__ == "__main__":
    main()
