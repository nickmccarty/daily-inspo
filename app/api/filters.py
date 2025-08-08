"""
Filters API router.

Handles filter-related endpoints including available tags,
filter combinations, and filter validation.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import logging

from ..models import TagSummary
from ..database import get_available_tags, count_ideas_with_filters

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/tags/", response_model=List[TagSummary])
async def get_available_tags_endpoint():
    """
    Retrieve all available tags grouped by category.
    
    Returns:
        List[TagSummary]: Available tags organized by category
    """
    try:
        tags_by_category = get_available_tags()
        
        tag_summaries = []
        for category, values in tags_by_category.items():
            tag_summaries.append(TagSummary(
                category=category,
                values=values,
                count=len(values)
            ))
            
        return tag_summaries
        
    except Exception as e:
        logger.error(f"Failed to get available tags: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve available tags")


@router.get("/tags/{category}", response_model=List[str])
async def get_tags_by_category(category: str):
    """
    Retrieve all available values for a specific tag category.
    
    Args:
        category: Tag category (industry, technology, etc.)
        
    Returns:
        List[str]: Available tag values for the category
        
    Raises:
        HTTPException: 404 if category not found
    """
    try:
        tags_by_category = get_available_tags()
        
        if category not in tags_by_category:
            raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
            
        return tags_by_category[category]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tags for category {category}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve tags for category")


@router.get("/industries/", response_model=List[str])
async def get_available_industries():
    """
    Retrieve list of all industries represented in ideas.
    
    Returns:
        List[str]: Available industry tags
    """
    try:
        tags_by_category = get_available_tags()
        return tags_by_category.get('industry', [])
        
    except Exception as e:
        logger.error(f"Failed to get industries: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve industries")


@router.get("/technologies/", response_model=List[str])
async def get_available_technologies():
    """
    Retrieve list of all technologies represented in ideas.
    
    Returns:
        List[str]: Available technology tags
    """
    try:
        tags_by_category = get_available_tags()
        return tags_by_category.get('technology', [])
        
    except Exception as e:
        logger.error(f"Failed to get technologies: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve technologies")


@router.get("/complexity-levels/", response_model=List[str])
async def get_complexity_levels():
    """
    Retrieve available complexity level options.
    
    Returns:
        List[str]: Available complexity levels
    """
    try:
        tags_by_category = get_available_tags()
        complexity_levels = tags_by_category.get('complexity', [])
        
        # If no complexity levels in database, return defaults
        if not complexity_levels:
            return ['mvp', 'medium', 'complex']
            
        return complexity_levels
        
    except Exception as e:
        logger.error(f"Failed to get complexity levels: {str(e)}")
        # Return defaults on error
        return ['mvp', 'medium', 'complex']


@router.get("/target-markets/", response_model=List[str])
async def get_target_markets():
    """
    Retrieve available target market options.
    
    Returns:
        List[str]: Available target market categories
    """
    try:
        tags_by_category = get_available_tags()
        target_markets = tags_by_category.get('target_market', [])
        
        # If no target markets in database, return defaults
        if not target_markets:
            return ['b2b', 'b2c', 'enterprise', 'consumer']
            
        return target_markets
        
    except Exception as e:
        logger.error(f"Failed to get target markets: {str(e)}")
        # Return defaults on error
        return ['b2b', 'b2c', 'enterprise', 'consumer']


@router.post("/validate/")
async def validate_filter_combination(filters: Dict[str, Any]):
    """
    Validate that a filter combination will return results.
    
    Args:
        filters: Dictionary of filter parameters to validate
        
    Returns:
        Dict: Validation result with expected result count
    """
    try:
        # Remove pagination parameters for count
        clean_filters = filters.copy()
        clean_filters.pop('limit', None)
        clean_filters.pop('offset', None)
        
        # Get count of matching ideas
        count = count_ideas_with_filters(clean_filters)
        
        return {
            'valid': count > 0,
            'expected_count': count,
            'message': f"Found {count} matching ideas" if count > 0 else "No ideas match the selected filters"
        }
        
    except Exception as e:
        logger.error(f"Failed to validate filters: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to validate filter combination")