# Daily Inspo - Automated App Idea Generator

An automated system that generates outstanding app ideas daily using Claude Code CLI, stores them in a SQLite database, and provides a responsive web interface to browse, filter, and explore ideas with supporting rationale.

## Overview

Daily Inspo runs a scheduled cron job every weekday at 10 AM that:
1. Executes the Claude Code CLI with a specially-crafted prompt
2. Generates comprehensive app ideas with factual supporting data
3. Stores ideas in SQLite with tags and metadata
4. Provides a FastAPI web interface to explore the idea collection

## Features

- **Automated Generation**: Cron job runs weekdays at 10 AM (skips weekends)
- **Comprehensive Tagging**: Industry, target market, complexity, technology focus
- **Factual Data**: Market size, competitor analysis, technical feasibility
- **Responsive Interface**: Mobile-friendly web UI built with vanilla JavaScript
- **Advanced Filtering**: Search and filter by tags, date, or content
- **Detailed Views**: Click cards to see full supporting logic and rationale

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: SQLite
- **Frontend**: Vanilla JavaScript + HTML/CSS
- **Automation**: Python cron script
- **CLI Integration**: Claude Code CLI

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Run development server
uvicorn app.main:app --reload --port 8002

# Set up cron job
python scripts/setup_cron.py
```

## Project Structure

```
daily-inspo/
├── app/
│   ├── main.py           # FastAPI application
│   ├── models.py         # Database models
│   ├── database.py       # Database connection
│   └── api/
│       ├── ideas.py      # Ideas API endpoints
│       └── filters.py    # Filtering endpoints
├── scripts/
│   ├── generate_idea.py  # Daily idea generation script
│   ├── init_db.py       # Database initialization
│   └── setup_cron.py    # Cron job setup
├── static/
│   ├── css/
│   ├── js/
│   └── index.html
├── templates/
├── idea_generation/
│   └── CLAUDE.md        # Claude prompt methodology
└── daily_ideas.db      # SQLite database
```

## Development

This is a functional prototype focused on core features. The system is designed to be lightweight, reliable, and easily extensible.