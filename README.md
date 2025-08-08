# Daily Inspo - Automated App Idea Generator with Project Management

An automated system that generates outstanding app ideas daily using Claude Code CLI, stores them in a SQLite database, and provides a comprehensive web interface to browse, filter, explore ideas, and manage connected development projects with integrated Claude Code chat assistance.

## Overview

Daily Inspo provides a complete development workflow from idea generation to project execution:

### Idea Generation
1. Automated cron job runs weekdays at 10 AM
2. Executes Claude Code CLI with specially-crafted prompts
3. Generates comprehensive app ideas with factual supporting data
4. Stores ideas in SQLite with tags and metadata

### Project Management  
1. Connect ideas to real development projects on your file system
2. Track project status, repository links, and progress
3. Analyze project alignment with original ideas
4. Chat with Claude Code about specific projects and development guidance

## Key Features

### Idea Management
- **Automated Generation**: Cron job runs weekdays at 10 AM (skips weekends)
- **Comprehensive Tagging**: Industry, target market, complexity, technology focus
- **Factual Data**: Market size, competitor analysis, technical feasibility
- **Responsive Interface**: Mobile-friendly web UI built with vanilla JavaScript
- **Advanced Filtering**: Search and filter by tags, date, or content
- **Detailed Views**: Click cards to see full supporting logic and rationale

### Project Management
- **Project Creation**: Link ideas to actual development folders
- **Status Tracking**: Monitor project progress (planning, development, testing, completed)
- **Idea Connections**: Associate multiple ideas with projects for comprehensive context
- **Project Analysis**: Compare current project state with connected ideas
- **Repository Integration**: Link projects to Git repositories

### Claude Code Chat Integration
- **Project-Specific Chat**: Dedicated Claude Code assistant for each project
- **Context-Aware Conversations**: Chat knows about your project and connected ideas
- **Development Guidance**: Get specific advice about implementation, architecture, and progress
- **Real-Time Assistance**: Interactive chat interface with persistent conversation history

## Tech Stack

- **Backend**: FastAPI (Python) with WebSocket support
- **Database**: SQLite with extended schema for projects and chat
- **Frontend**: Vanilla JavaScript + HTML/CSS with real-time chat interface
- **Automation**: Python cron script
- **CLI Integration**: Claude Code CLI
- **Project Analysis**: Automated directory scanning and code analysis
- **Chat System**: WebSocket-based real-time messaging

## Quick Start

```bash
# Install dependencies (including WebSocket support)
pip install -r requirements.txt

# Initialize database with new project management schema
python scripts/init_db.py

# Run development server
uvicorn app.main:app --reload --port 8000

# Set up cron job for daily idea generation
python scripts/setup_cron.py
```

## Usage

### Idea Management
1. **Browse Ideas**: Visit the homepage to see generated ideas
2. **Filter & Search**: Use the filtering controls to find specific types of ideas
3. **View Details**: Click idea cards to see full descriptions and supporting data

### Project Management
1. **Create Project**: Click "Create Project" to link ideas to development folders
2. **Connect Ideas**: Select relevant ideas when creating a project
3. **Track Progress**: Update project status as you develop
4. **Analyze Alignment**: Use the "Analyze" button to compare project state with ideas

### Claude Code Chat
1. **Open Chat**: Click the 💬 Chat button on any project card
2. **Get Context**: Claude knows about your project and connected ideas
3. **Ask Questions**: Get development guidance, architecture advice, and progress insights
4. **Persistent History**: Conversations are saved for future reference

## Project Structure

```
daily-inspo/
├── app/
│   ├── main.py           # FastAPI application with WebSocket support
│   ├── models.py         # Extended database models (ideas + projects + chat)
│   ├── database.py       # Database connection with new schema
│   └── api/
│       ├── ideas.py      # Ideas API endpoints
│       ├── filters.py    # Filtering endpoints
│       ├── projects.py   # Project management endpoints
│       └── chat.py       # Chat system with WebSocket support
├── scripts/
│   ├── generate_idea.py  # Daily idea generation script
│   ├── init_db.py       # Database initialization (extended schema)
│   └── setup_cron.py    # Cron job setup
├── static/
│   ├── css/
│   │   └── styles.css   # Includes project management and chat UI styles
│   ├── js/
│   │   └── app.js       # Enhanced with project management and chat features
│   └── index.html       # Updated with project management and chat modals
├── templates/
├── docs/                # Updated documentation
├── idea_generation/
│   └── CLAUDE.md        # Claude prompt methodology
└── daily_ideas.db      # Extended SQLite database
```

## Development

This is a functional prototype focused on core features. The system is designed to be lightweight, reliable, and easily extensible.