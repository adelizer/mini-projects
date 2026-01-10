"""Format analysis results for output."""

import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from .extractor import VideoAnalysis, ContentGuidelines


console = Console()


def print_video_analysis(analysis: VideoAnalysis) -> None:
    """Print a single video analysis to console."""
    console.print(Panel(
        f"[bold]{analysis.title_guess}[/bold]\n"
        f"Type: {analysis.video_type} | Duration: {analysis.duration} | WPM: {analysis.words_per_minute:.0f}",
        title=f"Video: {analysis.video_id}",
        border_style="blue"
    ))

    # Hook
    console.print("\n[bold yellow]Hook:[/bold yellow]")
    console.print(f"  \"{analysis.hook_text}\"")
    console.print(f"  Technique: {analysis.hook_technique} ({analysis.hook_duration_seconds}s)")

    # Structure
    console.print("\n[bold yellow]Structure:[/bold yellow]")
    console.print(f"  Intro: {analysis.intro_technique}")
    console.print(f"  Sections: {', '.join(analysis.main_sections)}")
    console.print(f"  Outro: {analysis.outro_technique}")

    # Engagement
    if analysis.humor_examples:
        console.print("\n[bold yellow]Humor:[/bold yellow]")
        for ex in analysis.humor_examples[:3]:
            console.print(f"  - {ex}")

    if analysis.analogies_used:
        console.print("\n[bold yellow]Analogies:[/bold yellow]")
        for ex in analysis.analogies_used[:3]:
            console.print(f"  - {ex}")

    # Technical
    console.print("\n[bold yellow]Technical Style:[/bold yellow]")
    console.print(f"  Code: {analysis.code_explanation_style}")
    console.print(f"  Simplification: {analysis.complexity_management}")

    console.print()


def print_guidelines(guidelines: ContentGuidelines) -> None:
    """Print aggregated guidelines to console."""
    console.print(Panel(
        "[bold]Content Creation Guidelines - Fireship Style[/bold]",
        border_style="green"
    ))

    # Hooks
    console.print("\n[bold cyan]HOOKS[/bold cyan]")
    console.print(f"Target Duration: ~{guidelines.avg_hook_duration:.0f} seconds")
    for pattern in guidelines.hook_patterns:
        console.print(f"  - {pattern}")

    # Structure
    console.print("\n[bold cyan]VIDEO STRUCTURE[/bold cyan]")
    console.print(f"Typical sections: {guidelines.typical_section_count}")
    console.print("\nIntro Techniques:")
    for tech in guidelines.common_intro_techniques:
        console.print(f"  - {tech}")
    console.print("\nOutro Techniques:")
    for tech in guidelines.common_outro_techniques:
        console.print(f"  - {tech}")

    # Pacing
    console.print("\n[bold cyan]PACING[/bold cyan]")
    console.print(f"Target WPM: ~{guidelines.avg_words_per_minute:.0f}")
    for guide in guidelines.pacing_guidelines:
        console.print(f"  - {guide}")

    # Engagement
    console.print("\n[bold cyan]ENGAGEMENT TECHNIQUES[/bold cyan]")
    console.print("\nHumor:")
    for tech in guidelines.humor_techniques:
        console.print(f"  - {tech}")
    console.print("\nAnalogies:")
    for pattern in guidelines.analogy_patterns:
        console.print(f"  - {pattern}")

    # Voice
    console.print("\n[bold cyan]VOICE & TONE[/bold cyan]")
    for char in guidelines.tone_characteristics:
        console.print(f"  - {char}")
    console.print("\nVocabulary:")
    for note in guidelines.vocabulary_notes:
        console.print(f"  - {note}")

    # Technical
    console.print("\n[bold cyan]TECHNICAL CONTENT[/bold cyan]")
    console.print("\nCode Explanation:")
    for pattern in guidelines.code_explanation_patterns:
        console.print(f"  - {pattern}")
    console.print("\nSimplification:")
    for tech in guidelines.simplification_techniques:
        console.print(f"  - {tech}")

    # Key Takeaways
    console.print("\n[bold green]KEY TAKEAWAYS[/bold green]")
    for i, takeaway in enumerate(guidelines.key_takeaways, 1):
        console.print(f"  {i}. {takeaway}")


def save_guidelines_markdown(guidelines: ContentGuidelines, path: Path) -> None:
    """Save guidelines as a markdown file."""
    md = f"""# Fireship Content Creation Guidelines

## Hooks
**Target Duration:** ~{guidelines.avg_hook_duration:.0f} seconds

### Hook Patterns
{chr(10).join(f'- {p}' for p in guidelines.hook_patterns)}

## Video Structure
**Typical Sections:** {guidelines.typical_section_count}

### Intro Techniques
{chr(10).join(f'- {t}' for t in guidelines.common_intro_techniques)}

### Outro Techniques
{chr(10).join(f'- {t}' for t in guidelines.common_outro_techniques)}

## Pacing
**Target WPM:** ~{guidelines.avg_words_per_minute:.0f}

### Guidelines
{chr(10).join(f'- {g}' for g in guidelines.pacing_guidelines)}

## Engagement Techniques

### Humor
{chr(10).join(f'- {t}' for t in guidelines.humor_techniques)}

### Analogies
{chr(10).join(f'- {p}' for p in guidelines.analogy_patterns)}

## Voice & Tone
{chr(10).join(f'- {c}' for c in guidelines.tone_characteristics)}

### Vocabulary Notes
{chr(10).join(f'- {n}' for n in guidelines.vocabulary_notes)}

## Technical Content

### Code Explanation
{chr(10).join(f'- {p}' for p in guidelines.code_explanation_patterns)}

### Simplification Techniques
{chr(10).join(f'- {t}' for t in guidelines.simplification_techniques)}

## Key Takeaways
{chr(10).join(f'{i}. {t}' for i, t in enumerate(guidelines.key_takeaways, 1))}
"""
    path.write_text(md)
    console.print(f"\n[green]Guidelines saved to {path}[/green]")


def save_analysis_json(analyses: list[VideoAnalysis], guidelines: ContentGuidelines, path: Path) -> None:
    """Save all analysis data as JSON."""
    data = {
        "video_analyses": [a.model_dump() for a in analyses],
        "guidelines": guidelines.model_dump()
    }
    path.write_text(json.dumps(data, indent=2))
    console.print(f"[green]Full analysis saved to {path}[/green]")
