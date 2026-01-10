"""Main entry point for Fireship content analyzer."""

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .loader import load_all_transcripts
from .extractor import ContentExtractor, VideoAnalysis, ContentGuidelines
from .formatter import (
    print_video_analysis,
    print_guidelines,
    save_guidelines_markdown,
    save_analysis_json,
)

console = Console()


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Analyze Fireship YouTube transcripts to extract content patterns"
    )
    parser.add_argument(
        "--transcripts",
        type=Path,
        default=Path("../youtube-transcriber/data/transcripts"),
        help="Path to transcripts directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of videos to analyze",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=None,
        help="Path to cache file for video analyses",
    )
    parser.add_argument(
        "--skip-individual",
        action="store_true",
        help="Skip individual video analysis (use cache only)",
    )

    args = parser.parse_args()

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Load transcripts
    console.print(f"\n[bold]Loading transcripts from {args.transcripts}[/bold]")
    transcripts = load_all_transcripts(args.transcripts)
    console.print(f"Found {len(transcripts)} transcripts")

    # Limit if specified
    if args.limit and args.limit < len(transcripts):
        transcripts = transcripts[:args.limit]
        console.print(f"Analyzing first {args.limit} videos")

    # Show transcript stats
    total_duration = sum(t.duration_seconds for t in transcripts)
    avg_wpm = sum(t.words_per_minute for t in transcripts) / len(transcripts)
    console.print(f"Total duration: {int(total_duration // 60)} minutes")
    console.print(f"Average WPM: {avg_wpm:.0f}")

    # Initialize extractor
    extractor = ContentExtractor()
    analyses: list[VideoAnalysis] = []

    # Check for cache
    cache_path = args.cache or args.output / "analyses_cache.json"
    if cache_path.exists() and args.skip_individual:
        console.print(f"\n[yellow]Loading cached analyses from {cache_path}[/yellow]")
        with open(cache_path) as f:
            cached = json.load(f)
            analyses = [VideoAnalysis(**a) for a in cached]
    else:
        # Analyze individual videos
        console.print("\n[bold]Analyzing individual videos...[/bold]")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing...", total=len(transcripts))

            for transcript in transcripts:
                progress.update(task, description=f"Analyzing {transcript.video_id}...")
                try:
                    analysis = extractor.analyze_video(transcript)
                    analyses.append(analysis)
                    print_video_analysis(analysis)
                except Exception as e:
                    console.print(f"[red]Error analyzing {transcript.video_id}: {e}[/red]")
                progress.advance(task)

        # Cache analyses
        with open(cache_path, "w") as f:
            json.dump([a.model_dump() for a in analyses], f, indent=2)
        console.print(f"[green]Cached {len(analyses)} analyses to {cache_path}[/green]")

    if not analyses:
        console.print("[red]No analyses to aggregate![/red]")
        return

    # Generate aggregated guidelines
    console.print("\n[bold]Generating content guidelines...[/bold]")
    with console.status("Synthesizing patterns..."):
        guidelines = extractor.generate_guidelines(analyses)

    # Print guidelines
    print_guidelines(guidelines)

    # Save outputs
    save_guidelines_markdown(guidelines, args.output / "FIRESHIP_GUIDELINES.md")
    save_analysis_json(analyses, guidelines, args.output / "full_analysis.json")

    console.print("\n[bold green]Analysis complete![/bold green]")


if __name__ == "__main__":
    main()
