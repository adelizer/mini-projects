"""Transcription service for YouTube videos."""

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from .models import Transcript, Video

load_dotenv()


class Transcriber:
    """Handles video transcription using YouTube's built-in transcripts or Whisper."""

    # Whisper API has a 25MB limit per file
    MAX_FILE_SIZE_MB = 25

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.transcripts_dir = data_dir / "transcripts"
        self.audio_dir = data_dir / "audio"
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)

        # Create API instances
        self.yt_api = YouTubeTranscriptApi()
        self.openai_client: Optional[OpenAI] = None

    def _get_openai_client(self) -> OpenAI:
        """Lazy initialization of OpenAI client."""
        if self.openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")
            self.openai_client = OpenAI(api_key=api_key)
        return self.openai_client

    def get_youtube_transcript(
        self, video_id: str, languages: list[str] = ["ar", "en"]
    ) -> Optional[Transcript]:
        """Fetch transcript from YouTube's auto-generated or manual captions."""
        try:
            transcript_list = self.yt_api.list(video_id)

            transcript = None
            language = None

            for lang in languages:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    language = lang
                    break
                except NoTranscriptFound:
                    continue

            if not transcript:
                try:
                    transcript = transcript_list.find_generated_transcript(languages)
                    language = languages[0]
                except NoTranscriptFound:
                    return None

            segments = transcript.fetch()
            full_text = " ".join([seg.text for seg in segments])

            return Transcript(
                video_id=video_id,
                text=full_text,
                language=language or "unknown",
                segments=[
                    {
                        "start": seg.start,
                        "duration": seg.duration,
                        "text": seg.text,
                    }
                    for seg in segments
                ],
            )

        except (TranscriptsDisabled, VideoUnavailable) as e:
            print(f"Could not fetch transcript for {video_id}: {e}")
            return None
        except Exception as e:
            print(f"Error fetching transcript for {video_id}: {e}")
            return None

    def download_audio(self, video: Video) -> Optional[Path]:
        """Download audio from YouTube video using yt-dlp."""
        output_path = self.audio_dir / f"{video.id}.mp3"

        # Skip if already downloaded
        if output_path.exists():
            print(f"  Audio already downloaded: {video.id}")
            return output_path

        cmd = [
            "yt-dlp",
            "-x",  # Extract audio
            "--audio-format", "mp3",
            "--audio-quality", "5",  # Medium quality (0=best, 9=worst)
            "-o", str(output_path),
            "--no-playlist",
            "--quiet",
            "--no-warnings",
            video.url,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                print(f"  Error downloading audio: {result.stderr[:200]}")
                return None

            if output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"  Downloaded audio: {size_mb:.1f} MB")
                return output_path
            else:
                print(f"  Audio file not created for {video.id}")
                return None

        except subprocess.TimeoutExpired:
            print(f"  Timeout downloading audio for {video.id}")
            return None
        except Exception as e:
            print(f"  Error downloading audio: {e}")
            return None

    def transcribe_with_whisper(self, video: Video) -> Optional[Transcript]:
        """Transcribe using OpenAI's Whisper API."""
        # Download audio first
        audio_path = self.download_audio(video)
        if not audio_path:
            return None

        # Check file size
        size_mb = audio_path.stat().st_size / (1024 * 1024)
        if size_mb > self.MAX_FILE_SIZE_MB:
            print(f"  Audio file too large ({size_mb:.1f} MB > {self.MAX_FILE_SIZE_MB} MB)")
            # TODO: Split audio into chunks
            return None

        try:
            client = self._get_openai_client()

            print(f"  Sending to Whisper API ({size_mb:.1f} MB)...")
            with open(audio_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ar",  # Arabic
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )

            # Parse response
            segments = []
            if hasattr(response, "segments") and response.segments:
                for seg in response.segments:
                    segments.append({
                        "start": getattr(seg, "start", 0),
                        "duration": getattr(seg, "end", 0) - getattr(seg, "start", 0),
                        "text": getattr(seg, "text", ""),
                    })

            transcript = Transcript(
                video_id=video.id,
                text=response.text,
                language="ar",
                segments=segments if segments else None,
            )

            # Save immediately
            self.save_transcript(transcript)

            # Optionally delete audio to save space
            # audio_path.unlink()

            return transcript

        except Exception as e:
            print(f"  Whisper API error: {e}")
            return None

    def transcribe_video(
        self, video: Video, use_whisper: bool = False
    ) -> Optional[Transcript]:
        """Get transcript for a video."""
        # Check if we already have a transcript saved
        cached = self.load_transcript(video.id)
        if cached:
            return cached

        # Try YouTube's built-in transcripts first (free)
        if not use_whisper:
            transcript = self.get_youtube_transcript(video.id)
            if transcript:
                self.save_transcript(transcript)
                return transcript

        # Use Whisper API
        return self.transcribe_with_whisper(video)

    def transcribe_batch_whisper(
        self,
        videos: list[Video],
        max_workers: int = 3,
        start_from: Optional[int] = None,
    ) -> dict[str, Transcript]:
        """Transcribe multiple videos in parallel using Whisper."""
        transcripts = {}
        failed_videos = []

        # Load existing transcripts
        for video in videos:
            cached = self.load_transcript(video.id)
            if cached:
                transcripts[video.id] = cached

        # Filter out already transcribed
        start_idx = start_from if start_from is not None else 0
        videos_to_process = [
            (i + start_idx, v)
            for i, v in enumerate(videos[start_idx:])
            if v.id not in transcripts
        ]

        if not videos_to_process:
            print("All videos already transcribed!")
            return transcripts

        print(f"Processing {len(videos_to_process)} videos with {max_workers} workers")
        print(f"Already have {len(transcripts)} cached transcripts")

        # Download all audio files first (can be parallelized)
        print("\n=== Downloading audio files ===")
        audio_files = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_video = {
                executor.submit(self.download_audio, video): (idx, video)
                for idx, video in videos_to_process
            }

            for future in as_completed(future_to_video):
                idx, video = future_to_video[future]
                try:
                    audio_path = future.result()
                    if audio_path:
                        audio_files[video.id] = (idx, video, audio_path)
                    else:
                        failed_videos.append((idx, video.id, "Failed to download audio"))
                except Exception as e:
                    failed_videos.append((idx, video.id, str(e)))

        print(f"\nDownloaded {len(audio_files)} audio files")

        # Transcribe with Whisper (sequential to avoid rate limits, but can parallel)
        print("\n=== Transcribing with Whisper ===")

        def transcribe_single(item):
            idx, video, audio_path = item
            size_mb = audio_path.stat().st_size / (1024 * 1024)

            if size_mb > self.MAX_FILE_SIZE_MB:
                return (idx, video.id, None, f"File too large: {size_mb:.1f} MB")

            try:
                client = self._get_openai_client()

                with open(audio_path, "rb") as audio_file:
                    response = client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language="ar",
                        response_format="verbose_json",
                        timestamp_granularities=["segment"],
                    )

                segments = []
                if hasattr(response, "segments") and response.segments:
                    for seg in response.segments:
                        segments.append({
                            "start": getattr(seg, "start", 0),
                            "duration": getattr(seg, "end", 0) - getattr(seg, "start", 0),
                            "text": getattr(seg, "text", ""),
                        })

                transcript = Transcript(
                    video_id=video.id,
                    text=response.text,
                    language="ar",
                    segments=segments if segments else None,
                )

                self.save_transcript(transcript)
                return (idx, video.id, transcript, None)

            except Exception as e:
                return (idx, video.id, None, str(e))

        # Process in parallel with limited workers
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(transcribe_single, item): item
                for item in audio_files.values()
            }

            for future in as_completed(futures):
                idx, video_id, transcript, error = future.result()
                if transcript:
                    transcripts[video_id] = transcript
                    print(f"  [{idx}/{len(videos)}] ✓ {video_id}")
                else:
                    failed_videos.append((idx, video_id, error))
                    print(f"  [{idx}/{len(videos)}] ✗ {video_id}: {error}")

                # Save progress periodically
                self._save_progress(transcripts, failed_videos)

        # Final summary
        print("\nTranscription complete:")
        print(f"  - Success: {len(transcripts)}/{len(videos)}")
        print(f"  - Failed: {len(failed_videos)}")

        if failed_videos:
            print("\nFailed videos:")
            for idx, vid_id, error in failed_videos[:10]:
                print(f"  [{idx}] {vid_id}: {error}")

        return transcripts

    def save_transcript(self, transcript: Transcript) -> Path:
        """Save transcript to JSON file."""
        output_path = self.transcripts_dir / f"{transcript.video_id}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(transcript.model_dump(), f, ensure_ascii=False, indent=2)

        return output_path

    def load_transcript(self, video_id: str) -> Optional[Transcript]:
        """Load transcript from JSON file."""
        input_path = self.transcripts_dir / f"{video_id}.json"

        if not input_path.exists():
            return None

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return Transcript(**data)

    def transcribe_all(
        self,
        videos: list[Video],
        start_from: Optional[int] = None,
        use_whisper: bool = False,
        max_workers: int = 3,
    ) -> dict[str, Transcript]:
        """Transcribe all videos."""
        if use_whisper:
            return self.transcribe_batch_whisper(videos, max_workers, start_from)

        # Original YouTube transcript logic
        transcripts = {}
        failed_videos = []

        for video in videos:
            cached = self.load_transcript(video.id)
            if cached:
                transcripts[video.id] = cached

        start_idx = start_from if start_from is not None else 0
        videos_to_process = videos[start_idx:]

        print(f"Processing {len(videos_to_process)} videos (starting from index {start_idx})")
        print(f"Already have {len(transcripts)} cached transcripts")

        for i, video in enumerate(videos_to_process):
            current_idx = start_idx + i

            if video.id in transcripts:
                print(f"[{current_idx}/{len(videos)}] Skipping {video.id} (cached)")
                continue

            print(f"[{current_idx}/{len(videos)}] Processing: {video.title[:50]}...")

            try:
                transcript = self.transcribe_video(video, use_whisper=False)
                if transcript:
                    transcripts[video.id] = transcript
                    print(f"  ✓ Saved transcript for {video.id}")
                else:
                    failed_videos.append((current_idx, video.id, "No transcript available"))
                    print(f"  ✗ No transcript for {video.id}")
            except Exception as e:
                failed_videos.append((current_idx, video.id, str(e)))
                print(f"  ✗ Error for {video.id}: {e}")
                self._save_progress(transcripts, failed_videos)

        self._save_progress(transcripts, failed_videos)

        print("\nTranscription complete:")
        print(f"  - Success: {len(transcripts)}/{len(videos)}")
        print(f"  - Failed: {len(failed_videos)}")

        if failed_videos:
            print("\nFailed videos (can retry with --start-from):")
            for idx, vid_id, error in failed_videos[:10]:
                print(f"  [{idx}] {vid_id}: {error}")
            if len(failed_videos) > 10:
                print(f"  ... and {len(failed_videos) - 10} more")

        return transcripts

    def _save_progress(
        self, transcripts: dict[str, Transcript], failed: list[tuple]
    ) -> None:
        """Save progress report to help with resuming."""
        progress_path = self.data_dir / "transcription_progress.json"

        progress = {
            "completed_count": len(transcripts),
            "completed_ids": list(transcripts.keys()),
            "failed": [
                {"index": idx, "video_id": vid_id, "error": error}
                for idx, vid_id, error in failed
            ],
        }

        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    def load_all_cached(self) -> dict[str, Transcript]:
        """Load all cached transcripts from disk."""
        transcripts = {}

        if not self.transcripts_dir.exists():
            return transcripts

        for path in self.transcripts_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                transcript = Transcript(**data)
                transcripts[transcript.video_id] = transcript
            except Exception as e:
                print(f"Error loading {path}: {e}")

        print(f"Loaded {len(transcripts)} cached transcripts")
        return transcripts

    def cleanup_audio(self, keep_failed: bool = True) -> None:
        """Delete downloaded audio files to save space."""
        if not self.audio_dir.exists():
            return

        transcribed_ids = set(self.load_all_cached().keys())
        deleted = 0

        for audio_file in self.audio_dir.glob("*.mp3"):
            video_id = audio_file.stem
            if video_id in transcribed_ids or not keep_failed:
                audio_file.unlink()
                deleted += 1

        print(f"Deleted {deleted} audio files")
