import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from summarizer.analyzer import aggregate_genres, compute_avg_popularity, generate_summary
from summarizer.spotify import TIME_RANGES, fetch_all_data, get_spotify_client

console = Console()


def print_stats(data: dict) -> None:
    console.print(Panel("[bold]Your Spotify Data[/bold]", style="green"))

    for time_range, label in TIME_RANGES.items():
        artists = data["top_artists"].get(time_range, [])
        tracks = data["top_tracks"].get(time_range, [])

        console.print(f"\n[bold cyan]{label}[/bold cyan]")
        if artists:
            console.print(f"  Top artists: {', '.join(a['name'] for a in artists[:5])}")
        if tracks:
            console.print(f"  Top tracks: {', '.join(t['name'] for t in tracks[:5])}")

    genre_counts = aggregate_genres(data)
    top_genres = genre_counts.most_common(10)
    console.print(f"\n[bold cyan]Top Genres:[/bold cyan]")
    for genre, count in top_genres:
        console.print(f"  {genre} ({count})")

    console.print(f"\n[bold cyan]Avg Popularity:[/bold cyan] {compute_avg_popularity(data)}/100")


def save_markdown(summary: str, data: dict) -> Path:
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    filename = output_dir / f"taste-summary-{datetime.now().strftime('%Y-%m-%d')}.md"

    lines = [
        "# My Spotify Taste Summary",
        f"*Generated on {datetime.now().strftime('%B %d, %Y')}*\n",
        summary,
        "\n---\n",
        "## Raw Data\n",
    ]

    for time_range, label in TIME_RANGES.items():
        artists = data["top_artists"].get(time_range, [])
        tracks = data["top_tracks"].get(time_range, [])
        lines.append(f"### {label}\n")
        if artists:
            lines.append("**Top Artists:**")
            for i, a in enumerate(artists[:10], 1):
                genres = ", ".join(a["genres"][:3]) if a["genres"] else ""
                lines.append(f"{i}. {a['name']} — {genres}")
        if tracks:
            lines.append("\n**Top Tracks:**")
            for i, t in enumerate(tracks[:10], 1):
                lines.append(f'{i}. "{t["name"]}" by {t["artist"]}')
        lines.append("")

    filename.write_text("\n".join(lines))
    return filename


def main():
    load_dotenv()
    console.print(Panel("[bold magenta]Spotify Taste Summarizer[/bold magenta]"))

    with console.status("[bold green]Connecting to Spotify..."):
        sp = get_spotify_client()

    with console.status("[bold green]Fetching your listening data..."):
        data = fetch_all_data(sp)

    print_stats(data)

    with console.status("[bold green]Generating AI summary..."):
        summary = generate_summary(data)

    console.print()
    console.print(Panel("[bold]AI-Generated Taste Summary[/bold]", style="magenta"))
    console.print(Markdown(summary))

    filepath = save_markdown(summary, data)
    console.print(f"\n[dim]Saved to {filepath}[/dim]")


if __name__ == "__main__":
    main()
