# YouTube Transcriber

A general-purpose YouTube video transcription tool that supports channels, playlists, and individual videos.

## Features

- Fetch videos from YouTube channels, playlists, or individual URLs
- Automatically retrieve YouTube's built-in transcripts (free)
- Fall back to OpenAI Whisper API for videos without transcripts (paid)
- Support for multiple languages
- Parallel processing for batch transcription
- Caching to avoid re-processing

## Installation

```bash
# Navigate to the project directory
cd youtube-transcriber

# Install with UV
uv sync

# Or with pip
pip install -e .

# For Whisper support (optional)
pip install -e ".[whisper]"
```

## Prerequisites

- **yt-dlp**: Must be installed and available in PATH
  ```bash
  # macOS
  brew install yt-dlp

  # Or with pip
  pip install yt-dlp
  ```

- **OpenAI API Key** (optional, for Whisper): Set in environment or `.env` file
  ```bash
  export OPENAI_API_KEY=your_key_here
  ```

## Usage

### Transcribe a Single Video

```bash
# Using video URL
yt-transcribe --video "https://www.youtube.com/watch?v=VIDEO_ID"

# Using video ID
yt-transcribe --video VIDEO_ID
```

### Transcribe Multiple Videos

```bash
yt-transcribe --videos VIDEO_ID1 VIDEO_ID2 VIDEO_ID3
```

### Transcribe from Channel

```bash
yt-transcribe --channel "https://www.youtube.com/@ChannelName"
```

### Transcribe from Playlist

```bash
yt-transcribe --playlist "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

### Search and Transcribe

```bash
yt-transcribe --search "Python tutorial" --max-results 5
```

### List Videos Without Transcribing

```bash
yt-transcribe --channel "https://www.youtube.com/@ChannelName" --list-only
```

## Whisper Fallback

When a video doesn't have a YouTube transcript available, you'll see a message suggesting to use Whisper:

```
✗ No YouTube transcript available
...
X videos need Whisper transcription.
Run with --use-whisper flag to transcribe these videos.
Note: This requires an OPENAI_API_KEY and will incur costs.
```

To use Whisper:

```bash
# Set your API key
export OPENAI_API_KEY=your_key_here

# Run with Whisper enabled
yt-transcribe --video VIDEO_ID --use-whisper

# Specify language for Whisper (default: en)
yt-transcribe --video VIDEO_ID --use-whisper --whisper-language ar

# Clean up audio files after transcription
yt-transcribe --video VIDEO_ID --use-whisper --cleanup-audio
```

## Options

| Option | Description |
|--------|-------------|
| `--video` | Single YouTube video URL or ID |
| `--videos` | Multiple YouTube video URLs or IDs |
| `--channel` | YouTube channel URL |
| `--playlist` | YouTube playlist URL |
| `--search` | Search query to find videos |
| `--output-dir` | Output directory (default: ./data) |
| `--languages` | Language codes to try (default: en ar) |
| `--use-whisper` | Use Whisper when YouTube transcript unavailable |
| `--whisper-language` | Language for Whisper (default: en) |
| `--workers` | Parallel workers for Whisper (default: 3) |
| `--max-results` | Max search results (default: 10) |
| `--start-from` | Resume from video index |
| `--list-only` | List videos without transcribing |
| `--cleanup-audio` | Delete audio after Whisper transcription |

## Output Structure

```
data/
├── videos.json              # Video metadata
├── transcripts/             # Transcript JSON files
│   ├── VIDEO_ID1.json
│   ├── VIDEO_ID2.json
│   └── ...
└── audio/                   # Downloaded audio (if using Whisper)
    ├── VIDEO_ID1.mp3
    └── ...
```

## Transcript Format

Each transcript is saved as a JSON file:

```json
{
  "video_id": "VIDEO_ID",
  "text": "Full transcript text...",
  "language": "en",
  "source": "youtube",
  "segments": [
    {
      "start": 0.0,
      "duration": 2.5,
      "text": "Hello and welcome..."
    }
  ]
}
```

## Python API

```python
from youtube_transcriber import YouTubeFetcher, Transcriber

# Initialize
fetcher = YouTubeFetcher()
transcriber = Transcriber()

# Get videos from a channel
videos = fetcher.get_channel_videos("https://www.youtube.com/@ChannelName")

# Transcribe all videos
results = transcriber.transcribe_all(videos, languages=["en", "ar"])

# Check results
for result in results:
    if result.success:
        print(f"✓ {result.video.title}: {len(result.transcript.text)} chars")
    elif result.needs_whisper:
        print(f"→ {result.video.title}: Needs Whisper")
    else:
        print(f"✗ {result.video.title}: {result.error}")
```

## Development

```bash
# Install dependencies
uv sync

# Run from source
uv run python -m youtube_transcriber.main --video VIDEO_ID

# Or use the CLI
uv run yt-transcribe --video VIDEO_ID
```
