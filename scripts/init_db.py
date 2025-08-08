#!/usr/bin/env python3
"""
Database initialization script.

Creates database tables, indexes, and initial configuration.
Run this script once to set up the database schema.
"""

import sys
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.database import initialize_database, create_tables, create_indexes, validate_database_schema

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """
    Initialize database with all required tables and indexes.
    """
    logger.info("Starting database initialization")
    
    try:
        # Initialize database
        if initialize_database():
            logger.info("Database initialization successful")
        else:
            logger.error("Database initialization failed")
            return False
            
        # Create tables
        create_tables()
        logger.info("Database tables created")
        
        # Create indexes
        create_indexes()
        logger.info("Database indexes created")
        
        # Validate schema
        if validate_database_schema():
            logger.info("Database schema validation successful")
        else:
            logger.warning("Database schema validation failed - may need migration")
            
        logger.info("Database initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print("Database initialized successfully!")
    else:
        print("Database initialization failed. Check logs for details.")
    sys.exit(0 if success else 1)