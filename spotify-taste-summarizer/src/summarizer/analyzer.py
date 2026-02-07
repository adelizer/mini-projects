from collections import Counter

from openai import OpenAI

from summarizer.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from summarizer.spotify import TIME_RANGES


def aggregate_genres(data: dict) -> Counter:
    genre_counter: Counter = Counter()
    for time_range in TIME_RANGES:
        for artist in data["top_artists"].get(time_range, []):
            for genre in artist["genres"]:
                genre_counter[genre] += 1
    return genre_counter


def compute_avg_popularity(data: dict) -> float:
    popularities = []
    for time_range in TIME_RANGES:
        for artist in data["top_artists"].get(time_range, []):
            popularities.append(artist["popularity"])
    return round(sum(popularities) / len(popularities), 1) if popularities else 0


def format_artists(artists: list[dict]) -> str:
    lines = []
    for i, a in enumerate(artists, 1):
        genres = ", ".join(a["genres"][:3]) if a["genres"] else "no genres listed"
        lines.append(f"{i}. **{a['name']}** (popularity: {a['popularity']}) — {genres}")
    return "\n".join(lines)


def format_tracks(tracks: list[dict]) -> str:
    lines = []
    for i, t in enumerate(tracks, 1):
        lines.append(f"{i}. \"{t['name']}\" by {t['artist']} (popularity: {t['popularity']})")
    return "\n".join(lines)


def build_prompt(data: dict) -> str:
    genre_counts = aggregate_genres(data)
    top_genres = genre_counts.most_common(15)
    genre_breakdown = "\n".join(f"- {genre}: {count} mentions" for genre, count in top_genres)

    return USER_PROMPT_TEMPLATE.format(
        short_term_artists=format_artists(data["top_artists"].get("short_term", [])),
        medium_term_artists=format_artists(data["top_artists"].get("medium_term", [])),
        long_term_artists=format_artists(data["top_artists"].get("long_term", [])),
        short_term_tracks=format_tracks(data["top_tracks"].get("short_term", [])),
        medium_term_tracks=format_tracks(data["top_tracks"].get("medium_term", [])),
        long_term_tracks=format_tracks(data["top_tracks"].get("long_term", [])),
        genre_breakdown=genre_breakdown,
        avg_popularity=compute_avg_popularity(data),
        unique_genres=len(genre_counts),
        top_genre=top_genres[0][0] if top_genres else "unknown",
    )


def generate_summary(data: dict) -> str:
    client = OpenAI()
    prompt = build_prompt(data)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
        max_tokens=1500,
    )
    return response.choices[0].message.content
