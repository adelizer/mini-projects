"""Transcription service for YouTube videos."""

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)

from .models import Transcript, TranscriptResult, Video

load_dotenv()


class Transcriber:
    """Handles video transcription using YouTube's built-in transcripts or Whisper."""

    # Whisper API has a 25MB limit per file
    MAX_FILE_SIZE_MB = 25

    def __init__(self, output_dir: Optional[Path] = None):
        """Initialize the transcriber.

        Args:
            output_dir: Directory to store transcripts and audio files.
                       If not provided, a default 'data' directory will be created.
        """
        self.output_dir = output_dir or Path("data")
        self.transcripts_dir = self.output_dir / "transcripts"
        self.audio_dir = self.output_dir / "audio"
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)

        # Create API instance
        self.yt_api = YouTubeTranscriptApi()
        self._openai_client = None

    def _get_openai_client(self):
        """Lazy initialization of OpenAI client."""
        if self._openai_client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "OpenAI package not installed. Install with: pip install openai"
                )

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY environment variable not set. "
                    "Set it in your environment or create a .env file."
                )
            self._openai_client = OpenAI(api_key=api_key)
        return self._openai_client

    def get_youtube_transcript(
        self, video_id: str, languages: list[str] = None
    ) -> Optional[Transcript]:
        """Fetch transcript from YouTube's auto-generated or manual captions.

        Args:
            video_id: YouTube video ID
            languages: List of language codes to try (default: ["en", "ar"])

        Returns:
            Transcript object if found, None otherwise
        """
        if languages is None:
            languages = ["en", "ar"]

        try:
            transcript_list = self.yt_api.list(video_id)

            transcript = None
            language = None

            # Try to find a transcript in the preferred languages
            for lang in languages:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    language = lang
                    break
                except NoTranscriptFound:
                    continue

            # Fall back to generated transcript
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
                source="youtube",
            )

        except (TranscriptsDisabled, VideoUnavailable) as e:
            return None
        except Exception as e:
            print(f"Error fetching transcript for {video_id}: {e}")
            return None

    def download_audio(self, video: Video) -> Optional[Path]:
        """Download audio from YouTube video using yt-dlp.

        Args:
            video: Video object to download audio for

        Returns:
            Path to downloaded audio file, or None if download failed
        """
        output_path = self.audio_dir / f"{video.id}.mp3"

        # Skip if already downloaded
        if output_path.exists():
            return output_path

        cmd = [
            "yt-dlp",
            "-x",  # Extract audio
            "--audio-format",
            "mp3",
            "--audio-quality",
            "5",  # Medium quality (0=best, 9=worst)
            "-o",
            str(output_path),
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
                return output_path
            else:
                return None

        except subprocess.TimeoutExpired:
            print(f"  Timeout downloading audio for {video.id}")
            return None
        except Exception as e:
            print(f"  Error downloading audio: {e}")
            return None

    def transcribe_with_whisper(
        self, video: Video, language: str = "en"
    ) -> Optional[Transcript]:
        """Transcribe using OpenAI's Whisper API.

        Args:
            video: Video object to transcribe
            language: Language code for transcription (default: "en")

        Returns:
            Transcript object if successful, None otherwise
        """
        # Download audio first
        audio_path = self.download_audio(video)
        if not audio_path:
            return None

        # Check file size
        size_mb = audio_path.stat().st_size / (1024 * 1024)
        if size_mb > self.MAX_FILE_SIZE_MB:
            print(
                f"  Audio file too large ({size_mb:.1f} MB > {self.MAX_FILE_SIZE_MB} MB)"
            )
            return None

        try:
            client = self._get_openai_client()

            print(f"  Sending to Whisper API ({size_mb:.1f} MB)...")
            with open(audio_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                )

            # Parse response
            segments = []
            if hasattr(response, "segments") and response.segments:
                for seg in response.segments:
                    segments.append(
                        {
                            "start": getattr(seg, "start", 0),
                            "duration": getattr(seg, "end", 0)
                            - getattr(seg, "start", 0),
                            "text": getattr(seg, "text", ""),
                        }
                    )

            transcript = Transcript(
                video_id=video.id,
                text=response.text,
                language=language,
                segments=segments if segments else None,
                source="whisper",
            )

            # Save immediately
            self.save_transcript(transcript)

            return transcript

        except Exception as e:
            print(f"  Whisper API error: {e}")
            return None

    def transcribe_video(
        self,
        video: Video,
        languages: list[str] = None,
        use_whisper: bool = False,
        whisper_language: str = "en",
    ) -> TranscriptResult:
        """Transcribe a single video.

        This method first tries to get the transcript from YouTube. If no transcript
        is available and use_whisper is False, it returns a result indicating that
        Whisper transcription is needed.

        Args:
            video: Video object to transcribe
            languages: List of language codes to try for YouTube transcripts
            use_whisper: If True, use Whisper when YouTube transcript not available
            whisper_language: Language code for Whisper transcription

        Returns:
            TranscriptResult with transcript or error information
        """
        # Check if we already have a transcript saved
        cached = self.load_transcript(video.id)
        if cached:
            return TranscriptResult(
                video=video,
                transcript=cached,
                success=True,
            )

        # Try YouTube's built-in transcripts first (free)
        transcript = self.get_youtube_transcript(video.id, languages)
        if transcript:
            self.save_transcript(transcript)
            return TranscriptResult(
                video=video,
                transcript=transcript,
                success=True,
            )

        # No YouTube transcript available
        if not use_whisper:
            return TranscriptResult(
                video=video,
                transcript=None,
                success=False,
                error="No YouTube transcript available",
                needs_whisper=True,
            )

        # Use Whisper API
        transcript = self.transcribe_with_whisper(video, language=whisper_language)
        if transcript:
            return TranscriptResult(
                video=video,
                transcript=transcript,
                success=True,
            )

        return TranscriptResult(
            video=video,
            transcript=None,
            success=False,
            error="Failed to transcribe with Whisper",
        )

    def transcribe_all(
        self,
        videos: list[Video],
        languages: list[str] = None,
        use_whisper: bool = False,
        whisper_language: str = "en",
        max_workers: int = 3,
        start_from: int = 0,
    ) -> list[TranscriptResult]:
        """Transcribe multiple videos.

        Args:
            videos: List of Video objects to transcribe
            languages: List of language codes to try for YouTube transcripts
            use_whisper: If True, use Whisper when YouTube transcript not available
            whisper_language: Language code for Whisper transcription
            max_workers: Number of parallel workers for Whisper transcription
            start_from: Index to start processing from (for resuming)

        Returns:
            List of TranscriptResult objects
        """
        results = []
        needs_whisper = []

        # Process videos starting from the specified index
        videos_to_process = videos[start_from:]

        print(f"Processing {len(videos_to_process)} videos (starting from index {start_from})")

        # First pass: Try YouTube transcripts
        for i, video in enumerate(videos_to_process):
            current_idx = start_from + i
            print(f"[{current_idx + 1}/{len(videos)}] {video.title[:50]}...")

            result = self.transcribe_video(
                video,
                languages=languages,
                use_whisper=False,  # First try YouTube only
            )

            if result.success:
                print(f"  ✓ Got YouTube transcript")
                results.append(result)
            elif result.needs_whisper:
                needs_whisper.append((current_idx, video))
                if use_whisper:
                    print(f"  → No YouTube transcript, will use Whisper")
                else:
                    print(f"  ✗ No YouTube transcript available")
                    results.append(result)

        # Second pass: Use Whisper for videos without YouTube transcripts
        if use_whisper and needs_whisper:
            print(f"\n=== Transcribing {len(needs_whisper)} videos with Whisper ===")

            # Download all audio files first
            print("Downloading audio files...")
            audio_files = {}
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_video = {
                    executor.submit(self.download_audio, video): (idx, video)
                    for idx, video in needs_whisper
                }

                for future in as_completed(future_to_video):
                    idx, video = future_to_video[future]
                    try:
                        audio_path = future.result()
                        if audio_path:
                            audio_files[video.id] = (idx, video, audio_path)
                        else:
                            results.append(
                                TranscriptResult(
                                    video=video,
                                    success=False,
                                    error="Failed to download audio",
                                )
                            )
                    except Exception as e:
                        results.append(
                            TranscriptResult(
                                video=video,
                                success=False,
                                error=str(e),
                            )
                        )

            # Transcribe with Whisper
            print(f"Transcribing {len(audio_files)} audio files with Whisper...")

            def transcribe_single(item):
                idx, video, audio_path = item
                return (
                    idx,
                    video,
                    self.transcribe_with_whisper(video, language=whisper_language),
                )

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(transcribe_single, item): item
                    for item in audio_files.values()
                }

                for future in as_completed(futures):
                    idx, video, transcript = future.result()
                    if transcript:
                        print(f"  [{idx + 1}/{len(videos)}] ✓ {video.id}")
                        results.append(
                            TranscriptResult(
                                video=video,
                                transcript=transcript,
                                success=True,
                            )
                        )
                    else:
                        print(f"  [{idx + 1}/{len(videos)}] ✗ {video.id}")
                        results.append(
                            TranscriptResult(
                                video=video,
                                success=False,
                                error="Whisper transcription failed",
                            )
                        )

        # Summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        whisper_needed = sum(1 for r in results if r.needs_whisper and not r.success)

        print(f"\n=== Transcription Summary ===")
        print(f"  Total: {len(results)}")
        print(f"  Successful: {successful}")
        print(f"  Failed: {failed}")

        if whisper_needed > 0 and not use_whisper:
            print(f"\n{whisper_needed} videos need Whisper transcription.")
            print("Run with --use-whisper flag to transcribe these videos.")
            print("Note: This requires an OPENAI_API_KEY and will incur costs.")

        return results

    def save_transcript(self, transcript: Transcript) -> Path:
        """Save transcript to JSON file.

        Args:
            transcript: Transcript object to save

        Returns:
            Path to saved file
        """
        output_path = self.transcripts_dir / f"{transcript.video_id}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(transcript.model_dump(), f, ensure_ascii=False, indent=2)

        return output_path

    def load_transcript(self, video_id: str) -> Optional[Transcript]:
        """Load transcript from JSON file.

        Args:
            video_id: YouTube video ID

        Returns:
            Transcript object if found, None otherwise
        """
        input_path = self.transcripts_dir / f"{video_id}.json"

        if not input_path.exists():
            return None

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return Transcript(**data)

    def load_all_transcripts(self) -> dict[str, Transcript]:
        """Load all cached transcripts from disk.

        Returns:
            Dictionary mapping video IDs to Transcript objects
        """
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

        return transcripts

    def cleanup_audio(self, keep_failed: bool = True) -> int:
        """Delete downloaded audio files to save space.

        Args:
            keep_failed: If True, keep audio files for videos that failed transcription

        Returns:
            Number of files deleted
        """
        if not self.audio_dir.exists():
            return 0

        transcribed_ids = set(self.load_all_transcripts().keys())
        deleted = 0

        for audio_file in self.audio_dir.glob("*.mp3"):
            video_id = audio_file.stem
            if video_id in transcribed_ids or not keep_failed:
                audio_file.unlink()
                deleted += 1

        return deleted
