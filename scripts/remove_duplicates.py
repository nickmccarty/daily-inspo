#!/usr/bin/env python3
"""
Remove duplicate ideas from the database.

Keeps the first occurrence of each unique idea title.
"""

import sqlite3
import sys
from pathlib import Path
import logging

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.database import DATABASE_PATH, get_db_connection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_duplicates():
    """
    Find duplicate ideas in the database based on title.
    
    Returns:
        List of tuples: (title, [list of IDs with that title])
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Find titles that appear more than once
        cursor.execute("""
            SELECT title, GROUP_CONCAT(id) as ids, COUNT(*) as count
            FROM ideas
            GROUP BY LOWER(TRIM(title))
            HAVING COUNT(*) > 1
            ORDER BY title
        """)
        
        duplicates = []
        for row in cursor.fetchall():
            title = row[0]
            ids = [int(x) for x in row[1].split(',')]
            count = row[2]
            duplicates.append((title, ids, count))
            
        return duplicates

def remove_duplicates(dry_run=True):
    """
    Remove duplicate ideas, keeping the first occurrence.
    
    Args:
        dry_run: If True, only report what would be deleted
    """
    duplicates = find_duplicates()
    
    if not duplicates:
        logger.info("No duplicate ideas found!")
        return
    
    logger.info(f"Found {len(duplicates)} sets of duplicate ideas:")
    
    total_to_delete = 0
    
    for title, ids, count in duplicates:
        ids.sort()  # Sort to keep the lowest ID (first occurrence)
        keep_id = ids[0]
        delete_ids = ids[1:]
        
        logger.info(f"Title: '{title}'")
        logger.info(f"  Found {count} instances with IDs: {ids}")
        logger.info(f"  Will keep ID {keep_id}, delete IDs: {delete_ids}")
        
        total_to_delete += len(delete_ids)
        
        if not dry_run:
            # Delete the duplicate ideas
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                
                # Delete related data first (foreign key constraints)
                for delete_id in delete_ids:
                    # Delete from generation_log
                    cursor.execute("DELETE FROM generation_log WHERE idea_id = ?", (delete_id,))
                    # Delete from idea_tags
                    cursor.execute("DELETE FROM idea_tags WHERE idea_id = ?", (delete_id,))
                    # Delete from market_data
                    cursor.execute("DELETE FROM market_data WHERE idea_id = ?", (delete_id,))
                    # Finally delete the idea itself
                    cursor.execute("DELETE FROM ideas WHERE id = ?", (delete_id,))
                    logger.info(f"  Deleted idea ID {delete_id}")
                
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise
            finally:
                conn.close()
        
        logger.info("")
    
    if dry_run:
        logger.info(f"DRY RUN: Would delete {total_to_delete} duplicate ideas")
        logger.info("Run with --execute to actually perform the deletion")
    else:
        logger.info(f"Successfully deleted {total_to_delete} duplicate ideas")

def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Remove duplicate ideas from database")
    parser.add_argument("--execute", action="store_true", 
                       help="Actually delete duplicates (default is dry run)")
    
    args = parser.parse_args()
    
    logger.info("Starting duplicate removal process...")
    
    try:
        remove_duplicates(dry_run=not args.execute)
        logger.info("Duplicate removal process completed successfully")
        
    except Exception as e:
        logger.error(f"Error during duplicate removal: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())