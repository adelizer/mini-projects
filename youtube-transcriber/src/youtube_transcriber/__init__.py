"""YouTube Transcriber - A general-purpose YouTube video transcription tool."""

from .models import Video, Transcript
from .youtube import YouTubeFetcher
from .transcriber import Transcriber

__version__ = "0.1.0"
__all__ = ["Video", "Transcript", "YouTubeFetcher", "Transcriber"]
