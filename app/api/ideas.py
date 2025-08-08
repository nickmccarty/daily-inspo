"""
Ideas API router.

Handles all idea-related API endpoints including retrieval,
filtering, and detailed view data.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
import logging
import subprocess
import sys
import os
from pathlib import Path

from ..models import IdeaResponse, IdeaCardResponse, FilteredIdeasResponse, SystemStatus
from ..database import (
    get_ideas_with_filters, get_idea_by_id, get_random_idea, get_system_stats,
    count_ideas_with_filters
)
from datetime import datetime, timedelta

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[IdeaCardResponse])
async def get_ideas(
    limit: int = Query(50, ge=1, le=100, description="Number of ideas to return"),
    offset: int = Query(0, ge=0, description="Number of ideas to skip")
):
    """
    Retrieve paginated list of ideas for card display.
    
    Args:
        limit: Maximum number of ideas to return
        offset: Number of ideas to skip for pagination
        
    Returns:
        List[IdeaCardResponse]: List of idea cards
    """
    try:
        filters = {'limit': limit, 'offset': offset}
        ideas = get_ideas_with_filters(filters)
        
        # Convert to IdeaCardResponse format
        card_responses = []
        for idea in ideas:
            # Truncate summary for card display
            summary = idea['summary'][:150] + '...' if len(idea['summary']) > 150 else idea['summary']
            
            card_responses.append(IdeaCardResponse(
                id=idea['id'],
                title=idea['title'],
                summary=summary,
                tags=idea.get('tags', []),
                generated_date=datetime.fromisoformat(idea['generated_date'].replace('Z', '+00:00')) if isinstance(idea['generated_date'], str) else idea['generated_date']
            ))
            
        return card_responses
        
    except Exception as e:
        logger.error(f"Failed to retrieve ideas: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve ideas")


@router.get("/{idea_id}", response_model=IdeaResponse)
async def get_idea_detail(idea_id: int):
    """
    Retrieve complete details for a specific idea.
    
    Args:
        idea_id: Unique identifier for the idea
        
    Returns:
        IdeaResponse: Complete idea details
        
    Raises:
        HTTPException: 404 if idea not found
    """
    try:
        idea = get_idea_by_id(idea_id)
        
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")
            
        # Convert market_data competitors from JSON string to list if needed
        market_data = idea.get('market_data')
        if market_data and isinstance(market_data.get('competitors'), str):
            import json
            try:
                market_data['competitors'] = json.loads(market_data['competitors'])
            except json.JSONDecodeError:
                market_data['competitors'] = []
                
        return IdeaResponse(
            id=idea['id'],
            title=idea['title'],
            summary=idea['summary'],
            description=idea['description'],
            supporting_logic=idea['supporting_logic'],
            generated_date=datetime.fromisoformat(idea['generated_date'].replace('Z', '+00:00')) if isinstance(idea['generated_date'], str) else idea['generated_date'],
            tags=idea.get('tags', []),
            market_data=market_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve idea {idea_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve idea details")


@router.get("/search/", response_model=FilteredIdeasResponse)
async def search_ideas(
    q: Optional[str] = Query(None, description="Search query"),
    industry: Optional[List[str]] = Query(None, description="Industry filters"),
    target_market: Optional[List[str]] = Query(None, description="Target market filters"),
    complexity: Optional[List[str]] = Query(None, description="Complexity filters"),
    technology: Optional[List[str]] = Query(None, description="Technology filters"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset")
):
    """
    Search and filter ideas based on multiple criteria.
    
    Args:
        q: Text search query
        industry: List of industry filters
        target_market: List of target market filters  
        complexity: List of complexity filters
        technology: List of technology filters
        limit: Maximum number of results
        offset: Results offset for pagination
        
    Returns:
        FilteredIdeasResponse: Filtered ideas with metadata
    """
    try:
        # Build filters dictionary
        filters = {
            'limit': limit,
            'offset': offset
        }
        
        if q:
            filters['search'] = q
        if industry:
            filters['industry'] = industry
        if target_market:
            filters['target_market'] = target_market
        if complexity:
            filters['complexity'] = complexity
        if technology:
            filters['technology'] = technology
            
        # Get filtered ideas
        ideas = get_ideas_with_filters(filters)
        
        # Get total count for pagination
        total_count = count_ideas_with_filters(filters)
        
        # Convert to card responses
        card_responses = []
        for idea in ideas:
            summary = idea['summary'][:150] + '...' if len(idea['summary']) > 150 else idea['summary']
            
            card_responses.append(IdeaCardResponse(
                id=idea['id'],
                title=idea['title'],
                summary=summary,
                tags=idea.get('tags', []),
                generated_date=datetime.fromisoformat(idea['generated_date'].replace('Z', '+00:00')) if isinstance(idea['generated_date'], str) else idea['generated_date']
            ))
            
        return FilteredIdeasResponse(
            ideas=card_responses,
            total_count=total_count,
            has_more=(offset + limit) < total_count
        )
        
    except Exception as e:
        logger.error(f"Failed to search ideas: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to search ideas")


@router.get("/random/", response_model=IdeaCardResponse)
async def get_random_idea_endpoint():
    """
    Retrieve a random idea for inspiration.
    
    Returns:
        IdeaCardResponse: Random idea card
        
    Raises:
        HTTPException: 404 if no ideas available
    """
    try:
        idea = get_random_idea()
        
        if not idea:
            raise HTTPException(status_code=404, detail="No ideas available")
            
        summary = idea['summary'][:150] + '...' if len(idea['summary']) > 150 else idea['summary']
        
        return IdeaCardResponse(
            id=idea['id'],
            title=idea['title'],
            summary=summary,
            tags=idea.get('tags', []),
            generated_date=datetime.fromisoformat(idea['generated_date'].replace('Z', '+00:00')) if isinstance(idea['generated_date'], str) else idea['generated_date']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get random idea: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get random idea")


@router.get("/recent/", response_model=List[IdeaCardResponse])
async def get_recent_ideas(days: int = Query(7, ge=1, le=30, description="Days to look back")):
    """
    Retrieve ideas generated in the last N days.
    
    Args:
        days: Number of days to look back
        
    Returns:
        List[IdeaCardResponse]: Recently generated ideas
    """
    try:
        # Calculate date filter
        date_from = datetime.now() - timedelta(days=days)
        
        filters = {
            'date_from': date_from,
            'limit': 100  # Get more recent ideas
        }
        
        ideas = get_ideas_with_filters(filters)
        
        # Convert to card responses
        card_responses = []
        for idea in ideas:
            summary = idea['summary'][:150] + '...' if len(idea['summary']) > 150 else idea['summary']
            
            card_responses.append(IdeaCardResponse(
                id=idea['id'],
                title=idea['title'],
                summary=summary,
                tags=idea.get('tags', []),
                generated_date=datetime.fromisoformat(idea['generated_date'].replace('Z', '+00:00')) if isinstance(idea['generated_date'], str) else idea['generated_date']
            ))
            
        return card_responses
        
    except Exception as e:
        logger.error(f"Failed to get recent ideas: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve recent ideas")


@router.get("/stats/", response_model=SystemStatus)
async def get_system_status():
    """
    Retrieve system status and statistics.
    
    Returns:
        SystemStatus: Current system status and stats
    """
    try:
        stats = get_system_stats()
        
        # Convert last_generation timestamp if it exists
        last_generation = None
        next_scheduled = None  # For now, we don't have scheduled info
        
        if stats.get('last_generation'):
            last_gen = stats['last_generation']
            if 'timestamp' in last_gen:
                last_generation = datetime.fromisoformat(last_gen['timestamp'].replace('Z', '+00:00')) if isinstance(last_gen['timestamp'], str) else last_gen['timestamp']
        
        return SystemStatus(
            total_ideas=stats['total_ideas'],
            last_generation=last_generation,
            next_scheduled=next_scheduled,
            system_healthy=stats['recent_generation_success_rate'] > 0.7  # 70% success rate threshold
        )
        
    except Exception as e:
        logger.error(f"Failed to get system status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system status")


@router.post("/generate/", response_model=IdeaResponse)
async def generate_new_idea():
    """
    Generate a new idea using the idea generation script.
    
    Returns:
        IdeaResponse: The newly generated idea
        
    Raises:
        HTTPException: 500 if generation fails
    """
    try:
        # Get the project root directory
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / "scripts" / "generate_idea.py"
        
        if not script_path.exists():
            raise HTTPException(status_code=500, detail="Generation script not found")
        
        # Get the current highest idea ID before generation
        current_ideas = get_ideas_with_filters({'limit': 1, 'offset': 0})
        max_id_before = current_ideas[0]['id'] if current_ideas else 0
        
        # Run the generation script
        logger.info("Starting idea generation...")
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            logger.error(f"Generation script failed: {result.stderr}")
            raise HTTPException(status_code=500, detail=f"Failed to generate idea: {result.stderr}")
        
        logger.info("Idea generated successfully")
        
        # Try to extract the idea ID from script output
        generated_idea_id = None
        for line in result.stdout.splitlines():
            if line.startswith("GENERATED_IDEA_ID:"):
                try:
                    generated_idea_id = int(line.split(":", 1)[1])
                    logger.info(f"Captured generated idea ID: {generated_idea_id}")
                    break
                except (ValueError, IndexError):
                    logger.warning(f"Failed to parse idea ID from line: {line}")
        
        if generated_idea_id:
            # Get the specific idea that was generated
            idea_details = get_idea_by_id(generated_idea_id)
        else:
            # Fallback: find the newest idea by ID comparison
            logger.warning("Could not capture idea ID, using fallback method")
            new_ideas = get_ideas_with_filters({'limit': 10, 'offset': 0})  # Get recent ideas
            newest_idea = None
            
            for idea in new_ideas:
                if idea['id'] > max_id_before:
                    newest_idea = idea
                    break
            
            if not newest_idea:
                # Ultimate fallback: get the most recent idea
                newest_idea = new_ideas[0] if new_ideas else None
                
            if not newest_idea:
                raise HTTPException(status_code=500, detail="No ideas found after generation")
                
            idea_details = get_idea_by_id(newest_idea['id'])
        
        if not idea_details:
            raise HTTPException(status_code=500, detail="Failed to retrieve generated idea details")
        
        return IdeaResponse(
            id=idea_details['id'],
            title=idea_details['title'],
            summary=idea_details['summary'],
            description=idea_details['description'],
            supporting_logic=idea_details['supporting_logic'],
            tags=idea_details.get('tags', []),
            generated_date=datetime.fromisoformat(idea_details['generated_date'].replace('Z', '+00:00')) if isinstance(idea_details['generated_date'], str) else idea_details['generated_date']
        )
        
    except subprocess.TimeoutExpired:
        logger.error("Idea generation timed out")
        raise HTTPException(status_code=500, detail="Idea generation timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate idea: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate new idea")