"""
Database connection and management utilities.

Handles SQLite database operations, connections, and schema management.
"""

import sqlite3
import json
import logging
from pathlib import Path
from contextlib import contextmanager
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Database configuration
DATABASE_PATH = Path("daily_ideas.db")

logger = logging.getLogger(__name__)


def get_db_connection() -> sqlite3.Connection:
    """
    Create and return a database connection.
    
    Returns:
        sqlite3.Connection: Database connection with row factory configured
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        conn.execute("PRAGMA journal_mode = WAL")  # Better performance for concurrent access
        return conn
    except sqlite3.Error as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


@contextmanager
def get_db_cursor():
    """
    Context manager for database operations.
    
    Yields:
        sqlite3.Cursor: Database cursor for executing queries
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        if conn:
            conn.close()


def initialize_database() -> bool:
    """
    Initialize database with required tables and indexes.
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        create_tables()
        create_indexes()
        logger.info("Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def create_tables() -> None:
    """
    Create all required database tables.
    
    Creates:
        - ideas: Main idea storage table
        - tags: Tag definitions table  
        - idea_tags: Many-to-many relationship table
        - market_data: Supporting market analysis data
        - generation_log: Idea generation history
    """
    table_schemas = [
        """
        CREATE TABLE IF NOT EXISTS ideas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            description TEXT NOT NULL,
            supporting_logic TEXT NOT NULL,
            generated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            value TEXT NOT NULL,
            UNIQUE(category, value)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS idea_tags (
            idea_id INTEGER,
            tag_id INTEGER,
            PRIMARY KEY (idea_id, tag_id),
            FOREIGN KEY (idea_id) REFERENCES ideas (id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_id INTEGER UNIQUE,
            market_size TEXT,
            competitors TEXT,
            technical_feasibility TEXT,
            development_timeline TEXT,
            FOREIGN KEY (idea_id) REFERENCES ideas (id) ON DELETE CASCADE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS generation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            success BOOLEAN NOT NULL,
            error_message TEXT,
            execution_time_seconds REAL,
            idea_id INTEGER,
            FOREIGN KEY (idea_id) REFERENCES ideas (id)
        )
        """
    ]
    
    with get_db_cursor() as cursor:
        for schema in table_schemas:
            cursor.execute(schema)
        logger.info("Database tables created successfully")


def create_indexes() -> None:
    """
    Create database indexes for optimal query performance.
    
    Indexes:
        - ideas.generated_date for date filtering
        - idea_tags.idea_id for tag lookups
        - idea_tags.tag_value for filter queries
    """
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_ideas_generated_date ON ideas(generated_date DESC)",
        "CREATE INDEX IF NOT EXISTS idx_ideas_title ON ideas(title)",
        "CREATE INDEX IF NOT EXISTS idx_idea_tags_idea_id ON idea_tags(idea_id)",
        "CREATE INDEX IF NOT EXISTS idx_idea_tags_tag_id ON idea_tags(tag_id)",
        "CREATE INDEX IF NOT EXISTS idx_tags_category ON tags(category)",
        "CREATE INDEX IF NOT EXISTS idx_tags_value ON tags(value)",
        "CREATE INDEX IF NOT EXISTS idx_generation_log_timestamp ON generation_log(timestamp DESC)",
        "CREATE INDEX IF NOT EXISTS idx_generation_log_success ON generation_log(success)"
    ]
    
    with get_db_cursor() as cursor:
        for index in indexes:
            cursor.execute(index)
        logger.info("Database indexes created successfully")


def validate_database_schema() -> bool:
    """
    Validate that database schema matches expected structure.
    
    Returns:
        bool: True if schema is valid, False if migration needed
    """
    expected_tables = {'ideas', 'tags', 'idea_tags', 'market_data', 'generation_log'}
    
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}
            
            missing_tables = expected_tables - existing_tables
            if missing_tables:
                logger.warning(f"Missing tables: {missing_tables}")
                return False
                
            logger.info("Database schema validation successful")
            return True
    except Exception as e:
        logger.error(f"Schema validation failed: {e}")
        return False


def insert_idea(idea_data: Dict[str, Any]) -> int:
    """
    Insert new idea into database.
    
    Args:
        idea_data: Dictionary containing idea information
        
    Returns:
        int: ID of inserted idea
        
    Raises:
        sqlite3.Error: If database operation fails
    """
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO ideas (title, summary, description, supporting_logic, generated_date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                idea_data['title'],
                idea_data['summary'],
                idea_data['description'],
                idea_data['supporting_logic'],
                idea_data.get('generated_date', datetime.now())
            )
        )
        idea_id = cursor.lastrowid
        
        # Insert tags if provided
        if 'tags' in idea_data and idea_data['tags']:
            insert_idea_tags(idea_id, idea_data['tags'])
            
        # Insert market data if provided
        if 'market_data' in idea_data and idea_data['market_data']:
            insert_market_data(idea_id, idea_data['market_data'])
            
        logger.info(f"Inserted new idea with ID {idea_id}: {idea_data['title']}")
        return idea_id


def insert_idea_tags(idea_id: int, tags: List[Dict[str, str]]) -> None:
    """
    Insert tags associated with an idea.
    
    Args:
        idea_id: ID of the idea
        tags: List of tag dictionaries with 'category' and 'value' keys
    """
    with get_db_cursor() as cursor:
        for tag in tags:
            # Insert or get existing tag
            cursor.execute(
                "INSERT OR IGNORE INTO tags (category, value) VALUES (?, ?)",
                (tag['category'], tag['value'])
            )
            
            # Get tag ID
            cursor.execute(
                "SELECT id FROM tags WHERE category = ? AND value = ?",
                (tag['category'], tag['value'])
            )
            tag_id = cursor.fetchone()[0]
            
            # Link idea to tag
            cursor.execute(
                "INSERT OR IGNORE INTO idea_tags (idea_id, tag_id) VALUES (?, ?)",
                (idea_id, tag_id)
            )


def insert_market_data(idea_id: int, market_data: Dict[str, Any]) -> None:
    """
    Insert market analysis data for an idea.
    
    Args:
        idea_id: ID of the idea
        market_data: Dictionary containing market analysis information
    """
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            INSERT OR REPLACE INTO market_data 
            (idea_id, market_size, competitors, technical_feasibility, development_timeline)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                idea_id,
                market_data.get('market_size'),
                json.dumps(market_data.get('competitors', [])),
                market_data.get('technical_feasibility'),
                market_data.get('development_timeline')
            )
        )


def get_idea_by_id(idea_id: int) -> Optional[Dict[str, Any]]:
    """
    Retrieve complete idea data by ID.
    
    Args:
        idea_id: Unique idea identifier
        
    Returns:
        Optional[Dict]: Complete idea data or None if not found
    """
    with get_db_cursor() as cursor:
        # Get main idea data
        cursor.execute(
            "SELECT * FROM ideas WHERE id = ?",
            (idea_id,)
        )
        idea_row = cursor.fetchone()
        
        if not idea_row:
            return None
            
        # Convert to dictionary
        idea = dict(idea_row)
        
        # Get associated tags
        cursor.execute(
            """
            SELECT t.category, t.value 
            FROM tags t
            JOIN idea_tags it ON t.id = it.tag_id
            WHERE it.idea_id = ?
            """,
            (idea_id,)
        )
        idea['tags'] = [{'category': row[0], 'value': row[1]} for row in cursor.fetchall()]
        
        # Get market data
        cursor.execute(
            "SELECT * FROM market_data WHERE idea_id = ?",
            (idea_id,)
        )
        market_row = cursor.fetchone()
        
        if market_row:
            market_data = dict(market_row)
            # Parse competitors JSON
            if market_data['competitors']:
                try:
                    market_data['competitors'] = json.loads(market_data['competitors'])
                except json.JSONDecodeError:
                    market_data['competitors'] = []
            idea['market_data'] = market_data
        else:
            idea['market_data'] = None
            
        return idea


def get_ideas_with_filters(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Retrieve ideas matching specified filters.
    
    Args:
        filters: Dictionary of filter parameters
        
    Returns:
        List[Dict]: List of matching ideas
    """
    with get_db_cursor() as cursor:
        # Base query
        query = "SELECT DISTINCT i.* FROM ideas i"
        joins = []
        where_conditions = []
        params = []
        
        # Add tag filtering
        if filters.get('industry') or filters.get('target_market') or filters.get('complexity') or filters.get('technology'):
            joins.append("JOIN idea_tags it ON i.id = it.idea_id")
            joins.append("JOIN tags t ON it.tag_id = t.id")
            
            tag_conditions = []
            if filters.get('industry'):
                industry_values = filters['industry'] if isinstance(filters['industry'], list) else [filters['industry']]
                tag_conditions.append(f"(t.category = 'industry' AND t.value IN ({','.join(['?'] * len(industry_values))}))") 
                params.extend(industry_values)
                
            if filters.get('target_market'):
                market_values = filters['target_market'] if isinstance(filters['target_market'], list) else [filters['target_market']]
                tag_conditions.append(f"(t.category = 'target_market' AND t.value IN ({','.join(['?'] * len(market_values))}))") 
                params.extend(market_values)
                
            if filters.get('complexity'):
                complexity_values = filters['complexity'] if isinstance(filters['complexity'], list) else [filters['complexity']]
                tag_conditions.append(f"(t.category = 'complexity' AND t.value IN ({','.join(['?'] * len(complexity_values))}))") 
                params.extend(complexity_values)
                
            if filters.get('technology'):
                tech_values = filters['technology'] if isinstance(filters['technology'], list) else [filters['technology']]
                tag_conditions.append(f"(t.category = 'technology' AND t.value IN ({','.join(['?'] * len(tech_values))}))") 
                params.extend(tech_values)
                
            if tag_conditions:
                where_conditions.append(f"({' OR '.join(tag_conditions)})")
        
        # Add text search
        if filters.get('search'):
            search_term = f"%{filters['search']}%"
            where_conditions.append("(i.title LIKE ? OR i.summary LIKE ? OR i.description LIKE ?)")
            params.extend([search_term, search_term, search_term])
        
        # Add date filters
        if filters.get('date_from'):
            where_conditions.append("i.generated_date >= ?")
            params.append(filters['date_from'])
            
        if filters.get('date_to'):
            where_conditions.append("i.generated_date <= ?")
            params.append(filters['date_to'])
        
        # Build complete query
        if joins:
            query += " " + " ".join(joins)
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
            
        query += " ORDER BY i.generated_date DESC"
        
        # Add pagination
        limit = filters.get('limit', 50)
        offset = filters.get('offset', 0)
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        ideas = [dict(row) for row in cursor.fetchall()]
        
        # Enrich with tags for each idea
        for idea in ideas:
            cursor.execute(
                """
                SELECT t.category, t.value 
                FROM tags t
                JOIN idea_tags it ON t.id = it.tag_id
                WHERE it.idea_id = ?
                """,
                (idea['id'],)
            )
            idea['tags'] = [{'category': row[0], 'value': row[1]} for row in cursor.fetchall()]
            
        return ideas


def get_available_tags() -> Dict[str, List[str]]:
    """
    Get all available tags grouped by category.
    
    Returns:
        Dict[str, List[str]]: Tags grouped by category
    """
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            SELECT category, GROUP_CONCAT(value, ',') as tag_values, COUNT(*) as count
            FROM tags t
            JOIN idea_tags it ON t.id = it.tag_id
            GROUP BY category
            ORDER BY category
            """
        )
        
        result = {}
        for row in cursor.fetchall():
            category = row[0]
            tag_values = row[1].split(',') if row[1] else []
            result[category] = sorted(list(set(tag_values)))  # Remove duplicates and sort
            
        return result


def get_system_stats() -> Dict[str, Any]:
    """
    Get system statistics and status information.
    
    Returns:
        Dict[str, Any]: System statistics
    """
    with get_db_cursor() as cursor:
        # Get total idea count
        cursor.execute("SELECT COUNT(*) FROM ideas")
        total_ideas = cursor.fetchone()[0]
        
        # Get last generation info
        cursor.execute(
            "SELECT timestamp, success FROM generation_log ORDER BY timestamp DESC LIMIT 1"
        )
        last_generation = cursor.fetchone()
        
        # Get recent generation success rate
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total_attempts,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_attempts
            FROM generation_log 
            WHERE timestamp >= datetime('now', '-7 days')
            """
        )
        recent_stats = cursor.fetchone()
        
        # Get ideas by category
        cursor.execute(
            """
            SELECT t.category, COUNT(DISTINCT it.idea_id) as count
            FROM tags t
            JOIN idea_tags it ON t.id = it.tag_id
            GROUP BY t.category
            """
        )
        category_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        stats = {
            'total_ideas': total_ideas,
            'last_generation': dict(last_generation) if last_generation else None,
            'recent_generation_success_rate': (
                recent_stats[1] / recent_stats[0] if recent_stats[0] > 0 else 0
            ),
            'ideas_by_category': category_counts,
            'database_size_mb': DATABASE_PATH.stat().st_size / (1024 * 1024) if DATABASE_PATH.exists() else 0
        }
        
        return stats


def log_generation_attempt(success: bool, error_message: Optional[str] = None, execution_time: Optional[float] = None, idea_id: Optional[int] = None) -> None:
    """
    Log idea generation attempt for monitoring.
    
    Args:
        success: Whether generation was successful
        error_message: Error details if generation failed
        execution_time: Time taken for generation in seconds
        idea_id: ID of generated idea if successful
    """
    with get_db_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO generation_log (success, error_message, execution_time_seconds, idea_id)
            VALUES (?, ?, ?, ?)
            """,
            (success, error_message, execution_time, idea_id)
        )
        
        log_level = "INFO" if success else "ERROR"
        logger.log(
            getattr(logging, log_level),
            f"Generation attempt logged: success={success}, time={execution_time}s, idea_id={idea_id}"
        )


def cleanup_old_logs(days_to_keep: int = 90) -> None:
    """
    Clean up old generation logs to prevent database bloat.
    
    Args:
        days_to_keep: Number of days of logs to retain
    """
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    with get_db_cursor() as cursor:
        cursor.execute(
            "DELETE FROM generation_log WHERE timestamp < ?",
            (cutoff_date,)
        )
        deleted_count = cursor.rowcount
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old log entries older than {days_to_keep} days")


def get_random_idea() -> Optional[Dict[str, Any]]:
    """
    Get a random idea from the database.
    
    Returns:
        Optional[Dict]: Random idea data or None if no ideas exist
    """
    with get_db_cursor() as cursor:
        cursor.execute(
            "SELECT id FROM ideas ORDER BY RANDOM() LIMIT 1"
        )
        result = cursor.fetchone()
        
        if result:
            return get_idea_by_id(result[0])
        return None


def count_ideas_with_filters(filters: Dict[str, Any]) -> int:
    """
    Count total ideas matching filters (for pagination).
    
    Args:
        filters: Dictionary of filter parameters
        
    Returns:
        int: Total count of matching ideas
    """
    # Create a modified version of the filters query for counting
    temp_filters = filters.copy()
    temp_filters.pop('limit', None)
    temp_filters.pop('offset', None)
    
    # Get the ideas (inefficient but simple for prototype)
    ideas = get_ideas_with_filters(temp_filters)
    return len(ideas)


def delete_idea(idea_id: int) -> bool:
    """
    Delete an idea and all its associated data from the database.
    
    Args:
        idea_id: ID of the idea to delete
        
    Returns:
        bool: True if idea was successfully deleted, False if not found
    """
    try:
        with get_db_cursor() as cursor:
            # Check if idea exists
            cursor.execute("SELECT title FROM ideas WHERE id = ?", (idea_id,))
            idea = cursor.fetchone()
            
            if not idea:
                logger.warning(f"Idea with ID {idea_id} not found")
                return False
            
            idea_title = idea[0]
            
            # Delete the idea (CASCADE will handle related records)
            cursor.execute("DELETE FROM ideas WHERE id = ?", (idea_id,))
            
            if cursor.rowcount > 0:
                logger.info(f"Successfully deleted idea ID {idea_id}: {idea_title}")
                return True
            else:
                logger.error(f"Failed to delete idea ID {idea_id}")
                return False
                
    except Exception as e:
        logger.error(f"Error deleting idea ID {idea_id}: {e}")
        return False