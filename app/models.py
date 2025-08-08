"""
Pydantic models for API request/response schemas.

Defines data structures for ideas, tags, filters, and API responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ComplexityLevel(str, Enum):
    """Idea complexity classification."""
    MVP = "mvp"
    MEDIUM = "medium"
    COMPLEX = "complex"


class TargetMarket(str, Enum):
    """Target market classification."""
    B2B = "b2b"
    B2C = "b2c"
    ENTERPRISE = "enterprise"
    CONSUMER = "consumer"


class Tag(BaseModel):
    """Individual tag for categorizing ideas."""
    category: str = Field(..., description="Tag category (industry, tech, etc.)")
    value: str = Field(..., description="Tag value")


class MarketData(BaseModel):
    """Market analysis and supporting data."""
    market_size: Optional[str] = Field(None, description="Estimated market size")
    competitors: List[str] = Field(default_factory=list, description="Key competitors")
    technical_feasibility: Optional[str] = Field(None, description="Technical feasibility assessment")
    development_timeline: Optional[str] = Field(None, description="Estimated development timeline")


class IdeaBase(BaseModel):
    """Base idea model with core fields."""
    title: str = Field(..., description="Idea title")
    summary: str = Field(..., description="Brief idea summary")
    description: str = Field(..., description="Detailed idea description")
    supporting_logic: str = Field(..., description="Supporting rationale and logic")


class IdeaCreate(IdeaBase):
    """Model for creating new ideas."""
    tags: List[Tag] = Field(default_factory=list, description="Categorization tags")
    market_data: Optional[MarketData] = Field(None, description="Market analysis data")


class IdeaResponse(IdeaBase):
    """Model for idea API responses."""
    id: int = Field(..., description="Unique idea identifier")
    generated_date: datetime = Field(..., description="When the idea was generated")
    tags: List[Tag] = Field(default_factory=list, description="Associated tags")
    market_data: Optional[MarketData] = Field(None, description="Market analysis data")
    
    class Config:
        from_attributes = True


class IdeaCardResponse(BaseModel):
    """Simplified model for idea card display."""
    id: int = Field(..., description="Unique idea identifier") 
    title: str = Field(..., description="Idea title")
    summary: str = Field(..., description="Brief summary (truncated)")
    tags: List[Tag] = Field(default_factory=list, description="Display tags")
    generated_date: datetime = Field(..., description="Generation date")


class FilterParams(BaseModel):
    """Model for filtering and search parameters."""
    search: Optional[str] = Field(None, description="Text search query")
    industry: Optional[List[str]] = Field(None, description="Industry filter")
    target_market: Optional[List[str]] = Field(None, description="Target market filter")
    complexity: Optional[List[ComplexityLevel]] = Field(None, description="Complexity filter")
    technology: Optional[List[str]] = Field(None, description="Technology filter")
    date_from: Optional[datetime] = Field(None, description="Filter ideas from this date")
    date_to: Optional[datetime] = Field(None, description="Filter ideas to this date")
    limit: Optional[int] = Field(50, description="Maximum results to return")
    offset: Optional[int] = Field(0, description="Results offset for pagination")


class FilteredIdeasResponse(BaseModel):
    """Response model for filtered idea queries."""
    ideas: List[IdeaCardResponse] = Field(..., description="Filtered ideas")
    total_count: int = Field(..., description="Total matching ideas")
    has_more: bool = Field(..., description="Whether more results exist")


class TagSummary(BaseModel):
    """Summary of available tags for filtering UI."""
    category: str = Field(..., description="Tag category")
    values: List[str] = Field(..., description="Available values in this category")
    count: int = Field(..., description="Number of ideas with this tag category")


class SystemStatus(BaseModel):
    """System status information."""
    total_ideas: int = Field(..., description="Total ideas in system")
    last_generation: Optional[datetime] = Field(None, description="Last successful generation")
    next_scheduled: Optional[datetime] = Field(None, description="Next scheduled generation")
    system_healthy: bool = Field(..., description="Overall system health")