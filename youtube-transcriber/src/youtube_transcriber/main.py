"""Main entry point for YouTube Transcriber CLI."""

import argparse
import sys
from pathlib import Path

from .youtube import YouTubeFetcher
from .transcriber import Transcriber
from .models import Video


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Transcriber - Download and transcribe YouTube videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Transcribe a single video
  yt-transcribe --video "https://www.youtube.com/watch?v=VIDEO_ID"
  yt-transcribe --video VIDEO_ID

  # Transcribe multiple videos
  yt-transcribe --videos VIDEO_ID1 VIDEO_ID2 VIDEO_ID3

  # Transcribe all videos from a channel
  yt-transcribe --channel "https://www.youtube.com/@ChannelName"

  # Transcribe all videos from a playlist
  yt-transcribe --playlist "https://www.youtube.com/playlist?list=PLAYLIST_ID"

  # Use Whisper for videos without YouTube transcripts
  yt-transcribe --video VIDEO_ID --use-whisper --whisper-language ar

  # Search and transcribe videos
  yt-transcribe --search "Python tutorial" --max-results 5
""",
    )

    # Input source options (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--video",
        type=str,
        help="Single YouTube video URL or ID",
    )
    source_group.add_argument(
        "--videos",
        nargs="+",
        type=str,
        help="Multiple YouTube video URLs or IDs",
    )
    source_group.add_argument(
        "--channel",
        type=str,
        help="YouTube channel URL to transcribe all videos from",
    )
    source_group.add_argument(
        "--playlist",
        type=str,
        help="YouTube playlist URL to transcribe all videos from",
    )
    source_group.add_argument(
        "--search",
        type=str,
        help="Search query to find and transcribe videos",
    )

    # Output options
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Directory to store transcripts and data (default: ./data)",
    )

    # Transcription options
    parser.add_argument(
        "--languages",
        nargs="+",
        default=["en", "ar"],
        help="Language codes to try for YouTube transcripts (default: en ar)",
    )
    parser.add_argument(
        "--use-whisper",
        action="store_true",
        help="Use OpenAI Whisper API when YouTube transcript not available (requires OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--whisper-language",
        type=str,
        default="en",
        help="Language code for Whisper transcription (default: en)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Number of parallel workers for Whisper transcription (default: 3)",
    )

    # Search options
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum number of search results (default: 10)",
    )

    # Processing options
    parser.add_argument(
        "--start-from",
        type=int,
        default=0,
        help="Start processing from this video index (for resuming)",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only list videos without transcribing",
    )
    parser.add_argument(
        "--cleanup-audio",
        action="store_true",
        help="Delete audio files after successful Whisper transcription",
    )

    args = parser.parse_args()

    # Create output directory
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {output_dir}")

    # Initialize components
    fetcher = YouTubeFetcher(output_dir)
    transcriber = Transcriber(output_dir)

    # Get videos based on input source
    videos = []

    if args.video:
        print(f"\n=== Fetching video ===")
        video = fetcher.get_video(args.video)
        if video:
            videos = [video]
            print(f"Found: {video.title}")
        else:
            print(f"Error: Could not fetch video: {args.video}")
            sys.exit(1)

    elif args.videos:
        print(f"\n=== Fetching {len(args.videos)} videos ===")
        videos = fetcher.get_videos(args.videos)
        print(f"Found {len(videos)} videos")

    elif args.channel:
        print(f"\n=== Fetching videos from channel ===")
        print(f"Channel: {args.channel}")
        videos = fetcher.get_channel_videos(args.channel)
        print(f"Found {len(videos)} videos")
        if videos:
            fetcher.save_videos(videos, "channel_videos.json")

    elif args.playlist:
        print(f"\n=== Fetching videos from playlist ===")
        print(f"Playlist: {args.playlist}")
        videos = fetcher.get_playlist_videos(args.playlist)
        print(f"Found {len(videos)} videos")
        if videos:
            fetcher.save_videos(videos, "playlist_videos.json")

    elif args.search:
        print(f"\n=== Searching for videos ===")
        print(f"Query: {args.search}")
        videos = fetcher.search_videos(args.search, max_results=args.max_results)
        print(f"Found {len(videos)} videos")
        if videos:
            fetcher.save_videos(videos, "search_videos.json")

    if not videos:
        print("No videos found!")
        sys.exit(1)

    # List videos if requested
    if args.list_only:
        print(f"\n=== Video List ===")
        for i, video in enumerate(videos):
            duration_str = ""
            if video.duration:
                minutes = video.duration // 60
                seconds = video.duration % 60
                duration_str = f" ({minutes}:{seconds:02d})"
            print(f"{i + 1}. {video.title}{duration_str}")
            print(f"   URL: {video.url}")
        return

    # Transcribe videos
    print(f"\n=== Transcribing {len(videos)} videos ===")
    results = transcriber.transcribe_all(
        videos,
        languages=args.languages,
        use_whisper=args.use_whisper,
        whisper_language=args.whisper_language,
        max_workers=args.workers,
        start_from=args.start_from,
    )

    # Clean up audio files if requested
    if args.cleanup_audio:
        deleted = transcriber.cleanup_audio()
        print(f"Cleaned up {deleted} audio files")

    # Print results
    print(f"\n=== Results ===")
    for result in results:
        status = "✓" if result.success else "✗"
        source = f" ({result.transcript.source})" if result.transcript else ""
        error = f" - {result.error}" if result.error else ""
        print(f"{status} {result.video.title[:60]}{source}{error}")

    # Exit with error code if any failures
    failures = sum(1 for r in results if not r.success)
    if failures > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
