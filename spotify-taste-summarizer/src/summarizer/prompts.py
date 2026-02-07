SYSTEM_PROMPT = """\
You are a music critic and personality analyst. You receive structured data about \
someone's Spotify listening habits and write an insightful, engaging summary of their \
musical taste and what it reveals about them.

Be specific — reference actual artist names, genres, and patterns you see in the data. \
Avoid generic statements that could apply to anyone. Be witty but not mean.\
"""

USER_PROMPT_TEMPLATE = """\
Here is a snapshot of someone's Spotify listening data across different time periods.

## Top Artists

### Last 4 Weeks
{short_term_artists}

### Last 6 Months
{medium_term_artists}

### All Time
{long_term_artists}

## Top Tracks

### Last 4 Weeks
{short_term_tracks}

### Last 6 Months
{medium_term_tracks}

### All Time
{long_term_tracks}

## Genre Distribution (across all top artists)
{genre_breakdown}

## Stats
- Average artist popularity (0-100 mainstream scale): {avg_popularity}
- Total unique genres: {unique_genres}
- Top genre: {top_genre}

---

Based on this data, write a musical taste summary with these sections:

1. **Musical Identity** — A 2-3 sentence personality sketch based on their taste.
2. **Core Sound** — What genres and moods define their listening? Be specific.
3. **Taste Evolution** — How has their taste shifted between "All Time" and "Last 4 Weeks"? \
What's new, what's consistent?
4. **Hidden Patterns** — Any surprising juxtapositions, guilty pleasures, or niche corners?
5. **The Vibe Check** — A single fun sentence starting with "You're the kind of listener who..."\
"""
