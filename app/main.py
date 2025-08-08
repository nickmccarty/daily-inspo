"""
FastAPI main application module.

Provides REST API endpoints for the Daily Inspo idea management system.
Handles idea retrieval, filtering, and detailed view requests.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import List, Optional
import logging
from pathlib import Path

from .database import validate_database_schema
from .models import IdeaResponse, FilterParams
from .api.ideas import router as ideas_router
from .api.filters import router as filters_router
from .api.projects import router as projects_router
from .api.chat import router as chat_router

app = FastAPI(
    title="Daily Inspo API",
    description="Automated app idea generation and management system",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Include API routers
app.include_router(ideas_router, prefix="/api/ideas", tags=["ideas"])
app.include_router(filters_router, prefix="/api/filters", tags=["filters"])
app.include_router(projects_router, tags=["projects"])
app.include_router(chat_router, tags=["chat"])


@app.get("/", response_class=HTMLResponse)
async def serve_homepage(request: Request):
    """
    Serve the main application homepage.
    
    Returns:
        HTMLResponse: Main application interface
    """
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Homepage not found")


@app.get("/idea/{idea_id}", response_class=HTMLResponse)
async def serve_idea_detail(request: Request, idea_id: int):
    """
    Serve detailed view for specific idea.
    
    Args:
        idea_id: Unique identifier for the idea
        
    Returns:
        HTMLResponse: Detailed idea view page
    """
    # For now, redirect to homepage with modal trigger
    # In a full implementation, this could render a server-side page
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        # Add JavaScript to auto-open the idea modal
        html_content = html_content.replace(
            "</body>",
            f"<script>window.addEventListener('load', () => {{ window.dailyInspoApp?.showIdeaModal({idea_id}); }});</script></body>"
        )
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Page not found")


@app.on_event("startup")
async def startup_event():
    """
    Initialize application on startup.
    Ensure database exists and is properly configured.
    """
    logger = logging.getLogger(__name__)
    
    # Validate database schema
    if not validate_database_schema():
        logger.warning("Database schema validation failed - some features may not work")
    else:
        logger.info("Database schema validation successful")
        
    logger.info("Daily Inspo application started successfully")


@app.on_event("shutdown") 
async def shutdown_event():
    """
    Clean up resources on application shutdown.
    """
    logger = logging.getLogger(__name__)
    logger.info("Daily Inspo application shutting down")
    # No specific cleanup needed for SQLite connections


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)