# Shark Tank Egypt Dashboard

A dashboard showcasing all startups from Shark Tank Egypt episodes.

## Overview

This project:
1. Scrapes all Shark Tank Egypt episode videos from YouTube
2. Transcribes each episode
3. Extracts startup information using AI
4. Displays everything in an interactive dashboard

## Project Structure

```
shark-tank-egypt-dashboard/
├── scraper/          # Python data collection tools
│   ├── pyproject.toml
│   ├── src/
│   │   ├── youtube_scraper.py    # Get video URLs
│   │   ├── transcriber.py        # Get/generate transcripts
│   │   └── extractor.py          # Extract startup data with LLM
│   └── main.py
├── dashboard/        # Next.js frontend
│   └── ...
└── data/            # Collected data
    ├── videos.json
    ├── transcripts/
    └── startups.json
```

## Setup

### Scraper (Python)

```bash
cd scraper
uv sync
uv run python main.py
```

### Dashboard (Next.js)

```bash
cd dashboard
npm install
npm run dev
```

## Data Schema

### Startup

```json
{
  "id": "string",
  "name": "string",
  "episode": "number",
  "description": "string",
  "askAmount": "number",
  "askEquity": "number",
  "dealMade": "boolean",
  "dealAmount": "number | null",
  "dealEquity": "number | null",
  "sharks": ["string"],
  "website": "string | null",
  "screenshotUrl": "string | null",
  "videoUrl": "string",
  "timestamp": "string"
}
```
