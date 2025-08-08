"""
Chat API endpoints for Claude Code chatbot integration.

Handles chat sessions, messages, and Claude Code CLI interactions 
for project-specific conversations.
"""

import json
import asyncio
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from ..database import get_db_cursor, get_idea_by_id
from ..models import (
    ChatSessionCreate, ChatSessionResponse,
    ChatMessageCreate, ChatMessageResponse
)

router = APIRouter(prefix="/api/chat", tags=["chat"])

# WebSocket connection manager for real-time chat
class ChatConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: int):
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, session_id: int):
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
    
    async def send_message(self, message: dict, session_id: int):
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except:
                    # Remove dead connections
                    await self.disconnect(connection, session_id)

manager = ChatConnectionManager()


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(session: ChatSessionCreate):
    """
    Create a new chat session for a project.
    
    Args:
        session: Chat session creation data
        
    Returns:
        ChatSessionResponse: Created session
    """
    try:
        with get_db_cursor() as cursor:
            # Verify project exists
            cursor.execute("SELECT id FROM projects WHERE id = ?", (session.project_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Project not found")
            
            # Create session
            cursor.execute(
                """
                INSERT INTO chat_sessions (project_id, title)
                VALUES (?, ?)
                """,
                (session.project_id, session.title)
            )
            session_id = cursor.lastrowid
            
            # Add initial message if provided
            if session.initial_message:
                cursor.execute(
                    """
                    INSERT INTO chat_messages (session_id, role, content)
                    VALUES (?, ?, ?)
                    """,
                    (session_id, 'user', session.initial_message)
                )
                
                # Generate Claude response
                await generate_claude_response(session_id, session.initial_message)
            
            # Get created session
            cursor.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,))
            session_data = dict(cursor.fetchone())
            
            # Get message count and last message
            cursor.execute(
                "SELECT COUNT(*) FROM chat_messages WHERE session_id = ?",
                (session_id,)
            )
            session_data['message_count'] = cursor.fetchone()[0]
            
            cursor.execute(
                """
                SELECT content FROM chat_messages 
                WHERE session_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
                """,
                (session_id,)
            )
            last_msg = cursor.fetchone()
            session_data['last_message'] = last_msg[0] if last_msg else None
            
            return ChatSessionResponse(**session_data)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")


@router.get("/sessions/{project_id}", response_model=List[ChatSessionResponse])
async def get_project_chat_sessions(project_id: int, limit: int = 20):
    """
    Get chat sessions for a project.
    
    Args:
        project_id: Project identifier
        limit: Maximum sessions to return
        
    Returns:
        List[ChatSessionResponse]: Project chat sessions
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM chat_sessions 
                WHERE project_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (project_id, limit)
            )
            
            sessions = []
            for row in cursor.fetchall():
                session_data = dict(row)
                
                # Get message count and last message
                cursor.execute(
                    "SELECT COUNT(*) FROM chat_messages WHERE session_id = ?",
                    (session_data['id'],)
                )
                session_data['message_count'] = cursor.fetchone()[0]
                
                cursor.execute(
                    """
                    SELECT content FROM chat_messages 
                    WHERE session_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                    """,
                    (session_data['id'],)
                )
                last_msg = cursor.fetchone()
                session_data['last_message'] = last_msg[0][:100] + "..." if last_msg and len(last_msg[0]) > 100 else (last_msg[0] if last_msg else None)
                
                sessions.append(ChatSessionResponse(**session_data))
                
            return sessions
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat sessions: {str(e)}")


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_chat_messages(session_id: int, limit: int = 100, offset: int = 0):
    """
    Get messages from a chat session.
    
    Args:
        session_id: Chat session identifier
        limit: Maximum messages to return
        offset: Offset for pagination
        
    Returns:
        List[ChatMessageResponse]: Chat messages
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM chat_messages 
                WHERE session_id = ?
                ORDER BY timestamp ASC
                LIMIT ? OFFSET ?
                """,
                (session_id, limit, offset)
            )
            
            messages = []
            for row in cursor.fetchall():
                message_data = dict(row)
                messages.append(ChatMessageResponse(**message_data))
                
            return messages
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat messages: {str(e)}")


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_chat_message(session_id: int, message: ChatMessageCreate):
    """
    Send a message in a chat session.
    
    Args:
        session_id: Chat session identifier
        message: Message to send
        
    Returns:
        ChatMessageResponse: Created message
    """
    try:
        with get_db_cursor() as cursor:
            # Verify session exists
            cursor.execute("SELECT project_id FROM chat_sessions WHERE id = ?", (session_id,))
            session = cursor.fetchone()
            if not session:
                raise HTTPException(status_code=404, detail="Chat session not found")
            
            # Store user message
            cursor.execute(
                """
                INSERT INTO chat_messages (session_id, role, content)
                VALUES (?, ?, ?)
                """,
                (session_id, message.role, message.content)
            )
            message_id = cursor.lastrowid
            
            # Update session timestamp
            cursor.execute(
                "UPDATE chat_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (session_id,)
            )
            
            # Get created message
            cursor.execute("SELECT * FROM chat_messages WHERE id = ?", (message_id,))
            message_data = dict(cursor.fetchone())
            
            # Broadcast message to WebSocket connections
            await manager.send_message({
                "type": "message",
                "data": message_data
            }, session_id)
            
            # Generate Claude response if user message
            if message.role == 'user':
                await generate_claude_response(session_id, message.content)
            
            return ChatMessageResponse(**message_data)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@router.websocket("/sessions/{session_id}/ws")
async def websocket_chat(websocket: WebSocket, session_id: int):
    """
    WebSocket endpoint for real-time chat.
    
    Args:
        websocket: WebSocket connection
        session_id: Chat session identifier
    """
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data['type'] == 'message':
                # Store and broadcast message
                message = ChatMessageCreate(
                    session_id=session_id,
                    role=data['role'],
                    content=data['content']
                )
                
                # Send message via REST endpoint logic
                await send_chat_message(session_id, message)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, session_id)


async def generate_claude_response(session_id: int, user_message: str):
    """
    Generate Claude Code CLI response for user message.
    
    Args:
        session_id: Chat session ID
        user_message: User's message content
    """
    try:
        with get_db_cursor() as cursor:
            # Get session and project context
            cursor.execute(
                """
                SELECT cs.*, p.name, p.folder_path, p.description
                FROM chat_sessions cs
                JOIN projects p ON cs.project_id = p.id
                WHERE cs.id = ?
                """,
                (session_id,)
            )
            session_data = dict(cursor.fetchone())
            
            # Get connected ideas for context
            cursor.execute(
                """
                SELECT i.title, i.summary, i.description
                FROM ideas i
                JOIN idea_projects ip ON i.id = ip.idea_id
                WHERE ip.project_id = ?
                """,
                (session_data['project_id'],)
            )
            connected_ideas = [dict(row) for row in cursor.fetchall()]
            
            # Build context for Claude
            context = build_claude_context(session_data, connected_ideas, user_message)
            
            # Call Claude Code CLI
            claude_response = await call_claude_cli(context, session_data['folder_path'])
            
            # Store Claude's response
            cursor.execute(
                """
                INSERT INTO chat_messages (session_id, role, content)
                VALUES (?, ?, ?)
                """,
                (session_id, 'assistant', claude_response)
            )
            claude_message_id = cursor.lastrowid
            
            # Get created message
            cursor.execute("SELECT * FROM chat_messages WHERE id = ?", (claude_message_id,))
            message_data = dict(cursor.fetchone())
            
            # Broadcast Claude's response
            await manager.send_message({
                "type": "message",
                "data": message_data
            }, session_id)
            
    except Exception as e:
        print(f"Failed to generate Claude response: {e}")
        
        # Send error message
        error_response = "I apologize, but I encountered an error processing your message. Please try again."
        
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_messages (session_id, role, content)
                VALUES (?, ?, ?)
                """,
                (session_id, 'assistant', error_response)
            )
            message_id = cursor.lastrowid
            
            cursor.execute("SELECT * FROM chat_messages WHERE id = ?", (message_id,))
            message_data = dict(cursor.fetchone())
            
            await manager.send_message({
                "type": "message",
                "data": message_data
            }, session_id)


def build_claude_context(session_data: Dict, connected_ideas: List[Dict], user_message: str) -> str:
    """
    Build context string for Claude Code CLI.
    
    Args:
        session_data: Session and project information
        connected_ideas: Ideas connected to the project
        user_message: Current user message
        
    Returns:
        str: Formatted context for Claude
    """
    context_parts = [
        f"Project: {session_data['name']}",
        f"Description: {session_data['description']}",
        f"Location: {session_data['folder_path']}",
        "",
        "Connected Ideas:",
    ]
    
    for idea in connected_ideas:
        context_parts.extend([
            f"- {idea['title']}: {idea['summary']}",
            f"  Details: {idea['description'][:200]}{'...' if len(idea['description']) > 200 else ''}",
            ""
        ])
    
    context_parts.extend([
        "User Question:",
        user_message,
        "",
        "Please help with this question in the context of the project and its connected ideas.",
        "Focus on practical development guidance and how the current project state aligns with the original ideas."
    ])
    
    return "\n".join(context_parts)


async def call_claude_cli(context: str, project_path: str) -> str:
    """
    Call Claude Code CLI with the given context.
    
    Args:
        context: Context string for Claude
        project_path: Path to project directory
        
    Returns:
        str: Claude's response
    """
    try:
        # Change to project directory for context
        original_cwd = Path.cwd()
        project_dir = Path(project_path)
        
        if project_dir.exists() and project_dir.is_dir():
            process_cwd = project_dir
        else:
            process_cwd = original_cwd
        
        # Prepare Claude Code CLI command
        # Note: This is a simplified version - in practice you'd need to handle
        # authentication, proper command formatting, etc.
        cmd = [
            "claude-code",
            "--non-interactive",
            context
        ]
        
        # Execute Claude CLI
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=process_cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            return stdout.strip() if stdout else "I'm ready to help with your project!"
        else:
            return f"I encountered an issue accessing the project. Error: {stderr.strip()}"
            
    except FileNotFoundError:
        return "Claude Code CLI is not available. Please install it to enable project analysis features."
    except Exception as e:
        return f"I apologize, but I encountered a technical issue: {str(e)}"


@router.delete("/sessions/{session_id}")
async def delete_chat_session(session_id: int):
    """
    Delete a chat session and all its messages.
    
    Args:
        session_id: Chat session identifier
        
    Returns:
        dict: Success message
    """
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT title FROM chat_sessions WHERE id = ?", (session_id,))
            session = cursor.fetchone()
            
            if not session:
                raise HTTPException(status_code=404, detail="Chat session not found")
                
            session_title = session[0]
            
            # Delete session (CASCADE will handle messages)
            cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
            
            # Disconnect any active WebSocket connections
            if session_id in manager.active_connections:
                for connection in manager.active_connections[session_id][:]:
                    await connection.close()
                del manager.active_connections[session_id]
            
            return {"message": f"Chat session '{session_title}' deleted successfully"}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chat session: {str(e)}")


@router.get("/sessions/{session_id}/export")
async def export_chat_session(session_id: int):
    """
    Export chat session as formatted text.
    
    Args:
        session_id: Chat session identifier
        
    Returns:
        StreamingResponse: Chat export file
    """
    try:
        with get_db_cursor() as cursor:
            # Get session info
            cursor.execute(
                """
                SELECT cs.title, cs.created_at, p.name as project_name
                FROM chat_sessions cs
                JOIN projects p ON cs.project_id = p.id
                WHERE cs.id = ?
                """,
                (session_id,)
            )
            session_info = cursor.fetchone()
            
            if not session_info:
                raise HTTPException(status_code=404, detail="Chat session not found")
            
            # Get all messages
            cursor.execute(
                """
                SELECT role, content, timestamp
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
                """,
                (session_id,)
            )
            messages = cursor.fetchall()
            
            # Generate export content
            def generate_export():
                yield f"Chat Session: {session_info[0]}\n"
                yield f"Project: {session_info[2]}\n"
                yield f"Created: {session_info[1]}\n"
                yield f"Messages: {len(messages)}\n"
                yield "\n" + "="*50 + "\n\n"
                
                for role, content, timestamp in messages:
                    role_display = "You" if role == "user" else "Claude"
                    yield f"[{timestamp}] {role_display}:\n{content}\n\n"
            
            return StreamingResponse(
                generate_export(),
                media_type="text/plain",
                headers={"Content-Disposition": f"attachment; filename=chat_session_{session_id}.txt"}
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to export chat session: {str(e)}")