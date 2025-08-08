"""
Project management API endpoints.

Handles CRUD operations for projects, idea-project connections, 
and project analysis functionality.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import ValidationError

from ..database import (
    get_db_cursor, get_idea_by_id, validate_database_schema
)
from ..models import (
    ProjectCreate, ProjectResponse, ProjectStatus,
    IdeaProjectConnection, ChatSessionCreate, ChatSessionResponse,
    ChatMessageCreate, ChatMessageResponse, ProjectAnalysis
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("/", response_model=ProjectResponse)
async def create_project(project: ProjectCreate, background_tasks: BackgroundTasks):
    """
    Create a new project and optionally connect it to ideas.
    
    Args:
        project: Project creation data
        background_tasks: FastAPI background tasks for analysis
        
    Returns:
        ProjectResponse: Created project data
        
    Raises:
        HTTPException: If project creation fails or folder path invalid
    """
    print(f"DEBUG: Received project data: {project}")
    print(f"DEBUG: Project name: {project.name}")
    print(f"DEBUG: Project folder_path: {project.folder_path}")
    print(f"DEBUG: Project status: {project.status}")
    # Validate and potentially create folder path
    try:
        folder_path = Path(project.folder_path)
        
        # Check if path exists
        if folder_path.exists():
            if not folder_path.is_dir():
                raise HTTPException(status_code=400, detail=f"Path exists but is not a directory: {project.folder_path}")
        else:
            # Check if parent directory exists
            parent_path = folder_path.parent
            if not parent_path.exists():
                raise HTTPException(status_code=400, detail=f"Parent directory does not exist: {parent_path}. Please create it first.")
            
            # Create the project directory
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise HTTPException(status_code=400, detail=f"Cannot create directory: {e}")
                
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=400, detail=f"Invalid folder path: {str(e)}")
    
    try:
        with get_db_cursor() as cursor:
            # Insert project
            cursor.execute(
                """
                INSERT INTO projects (name, description, folder_path, status, repository_url)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    project.name,
                    project.description,
                    str(folder_path.absolute()),
                    project.status.value,
                    project.repository_url
                )
            )
            project_id = cursor.lastrowid
            
            # Connect to ideas if provided
            idea_count = 0
            for idea_id in project.idea_ids:
                # Verify idea exists
                idea = get_idea_by_id(idea_id)
                if idea:
                    cursor.execute(
                        """
                        INSERT INTO idea_projects (idea_id, project_id)
                        VALUES (?, ?)
                        """,
                        (idea_id, project_id)
                    )
                    idea_count += 1
            
            # Get created project
            cursor.execute(
                "SELECT * FROM projects WHERE id = ?",
                (project_id,)
            )
            project_data = dict(cursor.fetchone())
            project_data['idea_count'] = idea_count
            project_data['last_analysis'] = None
            
            # Schedule initial project analysis
            background_tasks.add_task(analyze_project_async, project_id)
            
            return ProjectResponse(**project_data)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(status: Optional[ProjectStatus] = None, limit: int = 50):
    """
    List all projects with optional status filtering.
    
    Args:
        status: Optional status filter
        limit: Maximum number of projects to return
        
    Returns:
        List[ProjectResponse]: List of projects
    """
    try:
        with get_db_cursor() as cursor:
            query = "SELECT * FROM projects"
            params = []
            
            if status:
                query += " WHERE status = ?"
                params.append(status.value)
                
            query += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            projects = []
            
            for row in cursor.fetchall():
                project_data = dict(row)
                
                # Get idea count
                cursor.execute(
                    "SELECT COUNT(*) FROM idea_projects WHERE project_id = ?",
                    (project_data['id'],)
                )
                project_data['idea_count'] = cursor.fetchone()[0]
                
                # Get last analysis date
                cursor.execute(
                    "SELECT MAX(analysis_date) FROM project_analyses WHERE project_id = ?",
                    (project_data['id'],)
                )
                last_analysis = cursor.fetchone()[0]
                project_data['last_analysis'] = last_analysis
                
                projects.append(ProjectResponse(**project_data))
                
            return projects
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: int):
    """
    Get detailed project information by ID.
    
    Args:
        project_id: Project identifier
        
    Returns:
        ProjectResponse: Project details
        
    Raises:
        HTTPException: If project not found
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            project_row = cursor.fetchone()
            
            if not project_row:
                raise HTTPException(status_code=404, detail="Project not found")
                
            project_data = dict(project_row)
            
            # Get idea count
            cursor.execute(
                "SELECT COUNT(*) FROM idea_projects WHERE project_id = ?",
                (project_id,)
            )
            project_data['idea_count'] = cursor.fetchone()[0]
            
            # Get last analysis date
            cursor.execute(
                "SELECT MAX(analysis_date) FROM project_analyses WHERE project_id = ?",
                (project_id,)
            )
            last_analysis = cursor.fetchone()[0]
            project_data['last_analysis'] = last_analysis
            
            return ProjectResponse(**project_data)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get project: {str(e)}")


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: int, project_update: ProjectCreate):
    """
    Update project information.
    
    Args:
        project_id: Project identifier
        project_update: Updated project data
        
    Returns:
        ProjectResponse: Updated project
        
    Raises:
        HTTPException: If project not found or update fails
    """
    try:
        with get_db_cursor() as cursor:
            # Check if project exists
            cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Project not found")
                
            # Validate folder path
            folder_path = Path(project_update.folder_path)
            if not folder_path.exists() or not folder_path.is_dir():
                raise HTTPException(status_code=400, detail="Invalid folder path")
            
            # Update project
            cursor.execute(
                """
                UPDATE projects 
                SET name = ?, description = ?, folder_path = ?, status = ?, 
                    repository_url = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    project_update.name,
                    project_update.description,
                    str(folder_path.absolute()),
                    project_update.status.value,
                    project_update.repository_url,
                    project_id
                )
            )
            
            # Update idea connections
            cursor.execute("DELETE FROM idea_projects WHERE project_id = ?", (project_id,))
            for idea_id in project_update.idea_ids:
                if get_idea_by_id(idea_id):  # Verify idea exists
                    cursor.execute(
                        "INSERT INTO idea_projects (idea_id, project_id) VALUES (?, ?)",
                        (idea_id, project_id)
                    )
            
            return await get_project(project_id)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update project: {str(e)}")


@router.delete("/{project_id}")
async def delete_project(project_id: int):
    """
    Delete a project and all associated data.
    
    Args:
        project_id: Project identifier
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException: If project not found
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT name FROM projects WHERE id = ?", (project_id,))
            project = cursor.fetchone()
            
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
                
            project_name = project[0]
            
            # Delete project (CASCADE will handle related data)
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            
            return {"message": f"Project '{project_name}' deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")


@router.get("/{project_id}/ideas")
async def get_project_ideas(project_id: int):
    """
    Get all ideas connected to a project.
    
    Args:
        project_id: Project identifier
        
    Returns:
        dict: Project ideas and connection info
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT i.*, ip.connection_date, ip.relevance_notes
                FROM ideas i
                JOIN idea_projects ip ON i.id = ip.idea_id
                WHERE ip.project_id = ?
                ORDER BY ip.connection_date DESC
                """,
                (project_id,)
            )
            
            connected_ideas = []
            for row in cursor.fetchall():
                idea_data = dict(row)
                
                # Get idea tags
                cursor.execute(
                    """
                    SELECT t.category, t.value 
                    FROM tags t
                    JOIN idea_tags it ON t.id = it.tag_id
                    WHERE it.idea_id = ?
                    """,
                    (idea_data['id'],)
                )
                idea_data['tags'] = [{'category': r[0], 'value': r[1]} for r in cursor.fetchall()]
                
                connected_ideas.append(idea_data)
                
            return {
                "project_id": project_id,
                "connected_ideas": connected_ideas,
                "total_count": len(connected_ideas)
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get project ideas: {str(e)}")


@router.post("/{project_id}/connect-idea/{idea_id}")
async def connect_idea_to_project(
    project_id: int, 
    idea_id: int, 
    relevance_notes: Optional[str] = None
):
    """
    Connect an existing idea to a project.
    
    Args:
        project_id: Project identifier
        idea_id: Idea identifier
        relevance_notes: Optional notes about relevance
        
    Returns:
        dict: Success message
    """
    try:
        with get_db_cursor() as cursor:
            # Verify both exist
            cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Project not found")
                
            if not get_idea_by_id(idea_id):
                raise HTTPException(status_code=404, detail="Idea not found")
            
            # Check if already connected
            cursor.execute(
                "SELECT 1 FROM idea_projects WHERE idea_id = ? AND project_id = ?",
                (idea_id, project_id)
            )
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="Idea already connected to project")
            
            # Create connection
            cursor.execute(
                """
                INSERT INTO idea_projects (idea_id, project_id, relevance_notes)
                VALUES (?, ?, ?)
                """,
                (idea_id, project_id, relevance_notes)
            )
            
            return {"message": "Idea connected to project successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect idea: {str(e)}")


@router.post("/{project_id}/analyze", response_model=ProjectAnalysis)
async def analyze_project(project_id: int, background_tasks: BackgroundTasks):
    """
    Trigger project analysis to compare current state with connected ideas.
    
    Args:
        project_id: Project identifier
        background_tasks: FastAPI background tasks
        
    Returns:
        ProjectAnalysis: Analysis results
    """
    try:
        # Verify project exists
        with get_db_cursor() as cursor:
            cursor.execute("SELECT folder_path FROM projects WHERE id = ?", (project_id,))
            project = cursor.fetchone()
            
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
        
        # Run analysis in background
        background_tasks.add_task(analyze_project_async, project_id)
        
        return {"message": "Project analysis started", "project_id": project_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start analysis: {str(e)}")


async def analyze_project_async(project_id: int):
    """
    Perform detailed project analysis in background.
    
    Args:
        project_id: Project to analyze
    """
    try:
        with get_db_cursor() as cursor:
            # Get project and connected ideas
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            project = dict(cursor.fetchone())
            
            cursor.execute(
                """
                SELECT i.* FROM ideas i
                JOIN idea_projects ip ON i.id = ip.idea_id
                WHERE ip.project_id = ?
                """,
                (project_id,)
            )
            connected_ideas = [dict(row) for row in cursor.fetchall()]
            
            # Analyze project directory
            project_path = Path(project['folder_path'])
            analysis_results = await analyze_project_directory(project_path, connected_ideas)
            
            # Store analysis results
            cursor.execute(
                """
                INSERT INTO project_analyses 
                (project_id, idea_alignment_score, implemented_features, missing_features,
                 divergent_features, technical_debt_score, completion_estimate, recommendations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    analysis_results['idea_alignment_score'],
                    json.dumps(analysis_results['implemented_features']),
                    json.dumps(analysis_results['missing_features']),
                    json.dumps(analysis_results['divergent_features']),
                    analysis_results['technical_debt_score'],
                    analysis_results['completion_estimate'],
                    json.dumps(analysis_results['recommendations'])
                )
            )
            
    except Exception as e:
        print(f"Project analysis failed: {e}")


async def analyze_project_directory(project_path: Path, connected_ideas: List[Dict]) -> Dict:
    """
    Analyze project directory structure and code.
    
    Args:
        project_path: Path to project directory
        connected_ideas: Ideas connected to this project
        
    Returns:
        Dict: Analysis results
    """
    # Basic file system analysis
    file_count = 0
    line_count = 0
    code_files = []
    technologies = set()
    
    for file_path in project_path.rglob("*"):
        if file_path.is_file():
            file_count += 1
            
            # Count lines in text files
            try:
                if file_path.suffix in ['.py', '.js', '.ts', '.html', '.css', '.md']:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = len(f.readlines())
                        line_count += lines
                        code_files.append(str(file_path.relative_to(project_path)))
                        
                # Detect technologies
                if file_path.name == 'package.json':
                    technologies.add('Node.js')
                elif file_path.name == 'requirements.txt':
                    technologies.add('Python')
                elif file_path.suffix == '.py':
                    technologies.add('Python')
                elif file_path.suffix in ['.js', '.ts']:
                    technologies.add('JavaScript')
                    
            except:
                pass
    
    # Placeholder analysis - in real implementation, this would use
    # Claude Code CLI to perform deeper analysis
    return {
        'idea_alignment_score': 0.7,  # Placeholder
        'implemented_features': ['Basic structure', 'Core functionality'],
        'missing_features': ['User authentication', 'Advanced features'],
        'divergent_features': ['Extra utilities'],
        'technical_debt_score': 0.3,
        'completion_estimate': 0.6,
        'recommendations': [
            'Add comprehensive testing',
            'Improve error handling',
            'Add documentation'
        ]
    }


@router.get("/{project_id}/analysis")
async def get_project_analysis(project_id: int, limit: int = 5):
    """
    Get recent analysis results for a project.
    
    Args:
        project_id: Project identifier
        limit: Number of analyses to return
        
    Returns:
        dict: Analysis history
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM project_analyses 
                WHERE project_id = ?
                ORDER BY analysis_date DESC
                LIMIT ?
                """,
                (project_id, limit)
            )
            
            analyses = []
            for row in cursor.fetchall():
                analysis = dict(row)
                # Parse JSON fields
                analysis['implemented_features'] = json.loads(analysis['implemented_features'] or '[]')
                analysis['missing_features'] = json.loads(analysis['missing_features'] or '[]')
                analysis['divergent_features'] = json.loads(analysis['divergent_features'] or '[]')
                analysis['recommendations'] = json.loads(analysis['recommendations'] or '[]')
                analyses.append(analysis)
            
            return {
                "project_id": project_id,
                "analyses": analyses,
                "total_count": len(analyses)
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analysis: {str(e)}")