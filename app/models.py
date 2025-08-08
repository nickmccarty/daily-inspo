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


class ProjectStatus(str, Enum):
    """Project development status."""
    PLANNING = "planning"
    DEVELOPMENT = "development"
    TESTING = "testing"
    COMPLETED = "completed"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ProjectBase(BaseModel):
    """Base project model with core fields."""
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Project description")
    folder_path: str = Field(..., description="Absolute path to project folder")
    status: ProjectStatus = Field(ProjectStatus.PLANNING, description="Current project status")
    repository_url: Optional[str] = Field(None, description="Git repository URL")


class ProjectCreate(ProjectBase):
    """Model for creating new projects."""
    idea_ids: List[int] = Field(default_factory=list, description="Connected idea IDs")


class ProjectResponse(ProjectBase):
    """Model for project API responses."""
    id: int = Field(..., description="Unique project identifier")
    created_at: datetime = Field(..., description="Project creation date")
    updated_at: datetime = Field(..., description="Last update date")
    idea_count: int = Field(0, description="Number of connected ideas")
    last_analysis: Optional[datetime] = Field(None, description="Last project analysis date")
    
    class Config:
        from_attributes = True


class ProjectSnapshot(BaseModel):
    """Model for capturing project state at a point in time."""
    project_id: int = Field(..., description="Associated project ID")
    snapshot_date: datetime = Field(..., description="When snapshot was taken")
    file_count: int = Field(..., description="Number of files in project")
    line_count: int = Field(..., description="Total lines of code")
    key_files: List[str] = Field(default_factory=list, description="Important project files")
    technologies_detected: List[str] = Field(default_factory=list, description="Technologies found")
    progress_notes: Optional[str] = Field(None, description="Progress observations")


class ChatMessage(BaseModel):
    """Individual chat message."""
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")


class ChatSessionBase(BaseModel):
    """Base chat session model."""
    project_id: int = Field(..., description="Associated project ID")
    title: str = Field(..., description="Chat session title")


class ChatSessionCreate(ChatSessionBase):
    """Model for creating chat sessions."""
    initial_message: Optional[str] = Field(None, description="Initial user message")


class ChatSessionResponse(ChatSessionBase):
    """Model for chat session responses."""
    id: int = Field(..., description="Unique session identifier")
    created_at: datetime = Field(..., description="Session creation date")
    updated_at: datetime = Field(..., description="Last update date")
    message_count: int = Field(0, description="Number of messages in session")
    last_message: Optional[str] = Field(None, description="Preview of last message")
    
    class Config:
        from_attributes = True


class ChatMessageCreate(BaseModel):
    """Model for creating chat messages."""
    session_id: int = Field(..., description="Chat session ID")
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")


class ChatMessageResponse(ChatMessage):
    """Model for chat message responses."""
    id: int = Field(..., description="Unique message identifier")
    session_id: int = Field(..., description="Associated session ID")
    
    class Config:
        from_attributes = True


class IdeaProjectConnection(BaseModel):
    """Model for idea-project connections."""
    idea_id: int = Field(..., description="Connected idea ID")
    project_id: int = Field(..., description="Connected project ID")
    connection_date: datetime = Field(..., description="When connection was made")
    relevance_notes: Optional[str] = Field(None, description="How idea relates to project")


class ProjectAnalysis(BaseModel):
    """Model for project-idea comparison analysis."""
    project_id: int = Field(..., description="Analyzed project ID")
    analysis_date: datetime = Field(..., description="When analysis was performed")
    idea_alignment_score: float = Field(..., description="How well project matches connected ideas (0-1)")
    implemented_features: List[str] = Field(default_factory=list, description="Features implemented")
    missing_features: List[str] = Field(default_factory=list, description="Features from ideas not yet implemented")
    divergent_features: List[str] = Field(default_factory=list, description="Features not in original ideas")
    technical_debt_score: float = Field(..., description="Technical debt assessment (0-1)")
    completion_estimate: float = Field(..., description="Estimated completion percentage (0-1)")
    recommendations: List[str] = Field(default_factory=list, description="Development recommendations")