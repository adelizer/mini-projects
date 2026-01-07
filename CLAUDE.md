# Claude Code Instructions

## Project Overview

This repository contains mini projects and demos for a YouTube channel.

## General Guidelines

- Use UV as the package manager for Python projects
- Use Next.js with TypeScript for web dashboards
- Keep projects self-contained in their own directories

## Project-Specific Instructions

### Shark Tank Egypt Dashboard

Located in `./shark-tank-egypt-dashboard/`

**Directory Structure:**
- `scraper/` - Python scraping tools (UV project)
- `dashboard/` - Next.js frontend application
- `data/` - Collected data (JSON, transcripts, etc.)

**Development Commands:**

```bash
# Python scraper (from scraper/ directory)
uv sync                                    # Install dependencies
uv run python -m scraper.main              # Run full pipeline
uv run python -m scraper.main --use-channel  # Scrape from channel
uv run python -m scraper.main --skip-extraction  # Skip LLM step

# Next.js dashboard (from dashboard/ directory)
npm install                # Install dependencies
npm run dev                # Start dev server at localhost:3000
npm run build              # Production build
```

**Environment Variables:**
- Create `scraper/.env` with `OPENAI_API_KEY=your_key` for LLM extraction

**ngrok for development:**
```bash
ngrok http 3000 --url=exotic-koi-thoroughly.ngrok-free.app
```

## Data Pipeline

1. **Scrape** - Get all Shark Tank Egypt video URLs from YouTube channel
2. **Transcribe** - Fetch YouTube auto-generated transcripts (Arabic)
3. **Extract** - Use GPT-4o-mini to extract startup data from transcripts
4. **Store** - Save structured data as JSON in `data/` directory
5. **Display** - Render in Next.js dashboard with filters

## Data Files

- `data/videos.json` - YouTube video metadata
- `data/transcripts/` - Individual transcript files per video
- `data/startups.json` - Extracted startup information
- `data/extraction_cache/` - Cached LLM extractions
