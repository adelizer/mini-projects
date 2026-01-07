"""Main entry point for the Shark Tank Egypt scraper."""

import argparse
from pathlib import Path

from .youtube_scraper import YouTubeScraper
from .website_scraper import WebsiteScraper
from .transcriber import Transcriber
from .extractor import StartupExtractor
from .models import Video


def main():
    parser = argparse.ArgumentParser(description="Shark Tank Egypt Data Scraper")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).parent.parent.parent.parent / "data",
        help="Directory to store data",
    )

    # Source options (mutually exclusive)
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--use-website",
        action="store_true",
        help="Scrape from official website sharktank-egypt.com (recommended)",
    )
    source_group.add_argument(
        "--use-channel",
        action="store_true",
        help="Scrape from YouTube channel (includes shorts/clips)",
    )
    source_group.add_argument(
        "--playlist-url",
        type=str,
        help="YouTube playlist URL to scrape",
    )

    # Pipeline control
    parser.add_argument(
        "--skip-transcription",
        action="store_true",
        help="Skip transcription step",
    )
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="Skip LLM extraction step",
    )
    parser.add_argument(
        "--start-from",
        type=int,
        help="Start transcription from this video index (for resuming)",
    )
    parser.add_argument(
        "--transcribe-only",
        action="store_true",
        help="Only run transcription (skip scraping if videos exist, skip extraction)",
    )
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Only run extraction using cached transcripts",
    )
    parser.add_argument(
        "--fetch-metadata",
        action="store_true",
        help="Fetch video metadata (duration, etc.) from YouTube",
    )

    # Whisper transcription options
    parser.add_argument(
        "--use-whisper",
        action="store_true",
        help="Use OpenAI Whisper API for transcription (requires OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=3,
        help="Number of parallel workers for Whisper transcription (default: 3)",
    )
    parser.add_argument(
        "--cleanup-audio",
        action="store_true",
        help="Delete audio files after successful transcription",
    )
    parser.add_argument(
        "--single-video",
        type=str,
        help="Transcribe a single video by ID (for testing)",
    )

    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    print(f"Data directory: {data_dir}")

    # Step 1: Get videos
    videos = []

    # Try loading existing episodes first
    website_scraper = WebsiteScraper(data_dir)
    videos = website_scraper.load_episodes()

    if not videos:
        # Try loading from old videos.json
        yt_scraper = YouTubeScraper(data_dir)
        videos = yt_scraper.load_videos()

    if not videos:
        print("\n=== Step 1: Fetching episodes ===")

        if args.use_website or (not args.use_channel and not args.playlist_url):
            # Default to website scraping
            print("Fetching from official website (sharktank-egypt.com)...")
            with WebsiteScraper(data_dir) as scraper:
                videos = scraper.get_all_episodes()

                if videos and args.fetch_metadata:
                    print("\nFetching video metadata from YouTube...")
                    videos = scraper.get_video_metadata(videos)

                if videos:
                    scraper.save_episodes(videos)

        elif args.use_channel:
            print("Fetching from YouTube channel...")
            yt_scraper = YouTubeScraper(data_dir)
            videos = yt_scraper.get_channel_videos()
            if videos:
                yt_scraper.save_videos(videos)

        elif args.playlist_url:
            print(f"Fetching from playlist: {args.playlist_url}")
            yt_scraper = YouTubeScraper(data_dir)
            videos = yt_scraper.get_playlist_videos(args.playlist_url)
            if videos:
                yt_scraper.save_videos(videos)

        if not videos:
            print("No videos found!")
            return

    print(f"Found {len(videos)} episodes")

    # Calculate total duration if available
    total_duration = sum(v.duration or 0 for v in videos)
    if total_duration > 0:
        hours = total_duration / 3600
        print(f"Total duration: {hours:.1f} hours")

    transcriber = Transcriber(data_dir)

    # Handle --single-video mode for testing
    if args.single_video:
        print(f"\n=== Testing single video transcription: {args.single_video} ===")
        test_video = Video(
            id=args.single_video,
            title="Test Video",
            url=f"https://www.youtube.com/watch?v={args.single_video}",
        )
        transcript = transcriber.transcribe_video(test_video, use_whisper=args.use_whisper)
        if transcript:
            print(f"✓ Success! Transcript length: {len(transcript.text)} chars")
            print(f"First 500 chars:\n{transcript.text[:500]}")
        else:
            print("✗ Failed to transcribe video")
        return

    # Handle --extract-only mode
    if args.extract_only:
        print("\n=== Running extraction only (using cached transcripts) ===")
        transcripts = transcriber.load_all_cached()
        if not transcripts:
            print("No cached transcripts found! Run transcription first.")
            return
    elif args.skip_transcription:
        print("Skipping transcription...")
        return
    else:
        # Step 2: Transcribe videos
        print("\n=== Step 2: Transcribing videos ===")
        if args.use_whisper:
            print("Using OpenAI Whisper API for transcription...")
            transcripts = transcriber.transcribe_all(
                videos,
                start_from=args.start_from,
                use_whisper=True,
                max_workers=args.workers,
            )
            if args.cleanup_audio:
                print("\nCleaning up audio files...")
                transcriber.cleanup_audio()
        else:
            transcripts = transcriber.transcribe_all(videos, start_from=args.start_from)

    if args.skip_extraction or args.transcribe_only:
        print("Skipping extraction...")
        return

    # Step 3: Extract startup data
    print("\n=== Step 3: Extracting startup data ===")
    extractor = StartupExtractor(data_dir)

    videos_dict = {v.id: v for v in videos}
    startups = extractor.extract_all(transcripts, videos_dict)

    if startups:
        extractor.save_startups(startups)
        print(f"\nTotal startups extracted: {len(startups)}")

        # Print summary
        deals = [s for s in startups if s.deal_made]
        print(f"Deals made: {len(deals)}/{len(startups)}")
    else:
        print("No startups extracted!")


if __name__ == "__main__":
    main()
