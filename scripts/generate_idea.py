#!/usr/bin/env python3
"""
Daily idea generation script.

Executed by cron job to generate new app ideas using Claude CLI.
Handles Claude integration, response parsing, and database storage.
"""

import subprocess
import json
import logging
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from app.database import insert_idea, log_generation_attempt, get_ideas_with_filters

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('generation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_claude_methodology() -> str:
    """
    Load the specialized Claude methodology file.
    
    Returns:
        str: Methodology content for prompt construction
    """
    methodology_path = Path("idea_generation/IDEA_GENERATION_METHODOLOGY.md")
    
    try:
        with open(methodology_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Methodology file not found: {methodology_path}")
        raise
    except Exception as e:
        logger.error(f"Failed to load methodology file: {str(e)}")
        raise


def get_existing_ideas_context(limit: int = 20) -> str:
    """
    Get a summary of existing ideas to avoid duplicates.
    
    Args:
        limit: Maximum number of existing ideas to include
        
    Returns:
        str: Formatted string of existing idea titles and summaries
    """
    try:
        existing_ideas = get_ideas_with_filters({'limit': limit, 'offset': 0})
        
        if not existing_ideas:
            return "No existing ideas in database."
        
        context_lines = ["EXISTING IDEAS TO AVOID DUPLICATING:"]
        for i, idea in enumerate(existing_ideas[:limit], 1):
            title = idea.get('title', 'Unknown')
            summary = idea.get('summary', 'No summary')[:100] + '...' if len(idea.get('summary', '')) > 100 else idea.get('summary', '')
            context_lines.append(f"{i}. {title}: {summary}")
        
        context_lines.append("\nPlease generate something completely different from these existing ideas.")
        return "\n".join(context_lines)
        
    except Exception as e:
        logger.warning(f"Could not load existing ideas context: {str(e)}")
        return "Could not load existing ideas - please generate a unique concept."


def construct_idea_generation_prompt(methodology: str) -> str:
    """
    Construct the complete prompt for Claude CLI.
    
    Args:
        methodology: Loaded methodology content
        
    Returns:
        str: Complete prompt for idea generation
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    existing_ideas_context = get_existing_ideas_context()
    
    prompt = f"""{methodology}

--- GENERATION REQUEST ---

Date: {current_date}

{existing_ideas_context}

Please generate exactly one outstanding app idea following the methodology above. 

IMPORTANT: Respond with valid JSON only, no additional text or explanation. The JSON should exactly match the structure specified in the methodology.

Ensure the idea:
1. Addresses a real market need
2. Has strong business potential
3. Includes factual supporting data
4. Is technically feasible
5. Has clear differentiation
6. Is completely different from any existing ideas listed above

Generate the idea now:"""

    return prompt


def execute_claude_cli(prompt: str) -> Optional[str]:
    """
    Execute Claude CLI with the generated prompt.
    
    Args:
        prompt: Complete prompt for Claude
        
    Returns:
        Optional[str]: Claude's response or None if failed
    """
    try:
        # Execute claude CLI command
        result = subprocess.run(
            ['claude', prompt],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=Path.cwd()
        )
        
        if result.returncode == 0:
            logger.info("Claude CLI executed successfully")
            return result.stdout.strip()
        else:
            logger.error(f"Claude CLI failed with return code {result.returncode}: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error("Claude CLI execution timed out")
        return None
    except FileNotFoundError:
        logger.error("Claude CLI not found - ensure 'claude' is in PATH")
        return None
    except Exception as e:
        logger.error(f"Unexpected error executing Claude CLI: {str(e)}")
        return None


def parse_claude_response(response: str) -> Optional[Dict[str, Any]]:
    """
    Parse structured response from Claude CLI.
    
    Args:
        response: Raw response from Claude CLI
        
    Returns:
        Optional[Dict[str, Any]]: Parsed idea data or None if parsing failed
    """
    try:
        # Clean up response - sometimes Claude adds extra text
        response = response.strip()
        
        # Find JSON content - look for first { and last }
        start_idx = response.find('{')
        end_idx = response.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            logger.error("No JSON content found in response")
            return None
            
        json_content = response[start_idx:end_idx]
        
        # Parse JSON
        idea_data = json.loads(json_content)
        
        logger.info(f"Successfully parsed idea: {idea_data.get('title', 'Unknown title')}")
        return idea_data
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing failed: {str(e)}")
        logger.error(f"Response content: {response[:500]}...")  # Log first 500 chars
        return None
    except Exception as e:
        logger.error(f"Unexpected error parsing response: {str(e)}")
        return None


def validate_idea_structure(idea_data: Dict[str, Any]) -> bool:
    """
    Validate that parsed idea contains required fields.
    
    Args:
        idea_data: Parsed idea dictionary
        
    Returns:
        bool: True if structure is valid, False otherwise
    """
    required_fields = ['title', 'summary', 'description', 'supporting_logic', 'tags', 'market_analysis']
    
    try:
        # Check required top-level fields
        for field in required_fields:
            if field not in idea_data:
                logger.error(f"Missing required field: {field}")
                return False
            if not idea_data[field]:  # Check for empty values
                logger.error(f"Empty value for required field: {field}")
                return False
                
        # Validate tags structure
        tags = idea_data['tags']
        if not isinstance(tags, list) or len(tags) == 0:
            logger.error("Tags must be a non-empty list")
            return False
            
        for tag in tags:
            if not isinstance(tag, dict) or 'category' not in tag or 'value' not in tag:
                logger.error("Invalid tag structure - must have 'category' and 'value' fields")
                return False
                
        # Validate market_analysis structure
        market_analysis = idea_data['market_analysis']
        if not isinstance(market_analysis, dict):
            logger.error("Market analysis must be a dictionary")
            return False
            
        # Check string field lengths
        if len(idea_data['title']) > 200:
            logger.error("Title too long (max 200 characters)")
            return False
            
        if len(idea_data['summary']) > 500:
            logger.error("Summary too long (max 500 characters)")
            return False
            
        logger.info("Idea structure validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Error validating idea structure: {str(e)}")
        return False


def enhance_with_metadata(idea_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhance idea data with additional metadata and processing.
    
    Args:
        idea_data: Basic parsed idea data
        
    Returns:
        Dict[str, Any]: Enhanced idea data with metadata
    """
    enhanced = idea_data.copy()
    
    # Add generation timestamp
    enhanced['generated_date'] = datetime.now()
    
    # Ensure market_analysis has required structure for database
    market_analysis = enhanced.get('market_analysis', {})
    enhanced['market_data'] = {
        'market_size': market_analysis.get('market_size', 'Not specified'),
        'competitors': market_analysis.get('competitors', []),
        'technical_feasibility': market_analysis.get('technical_feasibility', 'Not assessed'),
        'development_timeline': market_analysis.get('development_timeline', 'Not estimated')
    }
    
    # Ensure all required tag categories are present
    required_categories = {'industry', 'target_market', 'complexity', 'technology'}
    existing_categories = {tag['category'] for tag in enhanced['tags']}
    
    # Add default tags for missing categories
    missing_categories = required_categories - existing_categories
    for category in missing_categories:
        if category == 'complexity' and 'complexity' not in existing_categories:
            enhanced['tags'].append({'category': 'complexity', 'value': 'medium'})
        elif category == 'target_market' and 'target_market' not in existing_categories:
            enhanced['tags'].append({'category': 'target_market', 'value': 'b2c'})
    
    logger.info("Idea enhanced with metadata")
    return enhanced


def store_idea_in_database(idea_data: Dict[str, Any]) -> Optional[int]:
    """
    Store complete idea data in database.
    
    Args:
        idea_data: Complete idea data with metadata
        
    Returns:
        Optional[int]: Idea ID if successful, None if failed
    """
    try:
        # Use the database function to insert the idea
        idea_id = insert_idea(idea_data)
        
        if idea_id:
            logger.info(f"Stored idea in database with ID: {idea_id}")
            return idea_id
        else:
            logger.error("Failed to store idea in database")
            return None
            
    except Exception as e:
        logger.error(f"Database storage error: {str(e)}")
        return None


def store_idea_in_database(idea_data: Dict[str, Any]) -> Optional[int]:
    """
    Store enhanced idea data in database with retry logic for locks.
    
    Args:
        idea_data: Enhanced idea data dictionary
        
    Returns:
        Optional[int]: Idea ID if successful, None if failed
    """
    import sqlite3
    from app.database import DATABASE_PATH
    
    max_retries = 5
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting to store idea in database (attempt {attempt + 1}/{max_retries})")
            
            # Use a direct connection with immediate timeout
            conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
            conn.execute("PRAGMA busy_timeout = 30000")  # 30 second timeout
            conn.execute("PRAGMA journal_mode = WAL")
            
            try:
                # Manual implementation to avoid database module conflicts
                cursor = conn.cursor()
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
                        datetime.now()
                    )
                )
                idea_id = cursor.lastrowid
                
                # Insert tags if provided
                if 'tags' in idea_data and idea_data['tags']:
                    for tag in idea_data['tags']:
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
                        tag_result = cursor.fetchone()
                        if tag_result:
                            tag_id = tag_result[0]
                            # Link idea to tag
                            cursor.execute(
                                "INSERT OR IGNORE INTO idea_tags (idea_id, tag_id) VALUES (?, ?)",
                                (idea_id, tag_id)
                            )
                
                conn.commit()
                logger.info(f"Successfully stored idea with ID {idea_id}")
                return idea_id
                
            finally:
                conn.close()
                
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower() or "busy" in str(e).lower():
                logger.warning(f"Database busy on attempt {attempt + 1}, waiting {retry_delay}s...")
                if attempt < max_retries - 1:  # Don't sleep on last attempt
                    time.sleep(retry_delay)
                    retry_delay *= 1.5  # Gradual backoff
                continue
            else:
                logger.error(f"Database storage error: {str(e)}")
                return None
        except Exception as e:
            logger.error(f"Unexpected error storing idea: {str(e)}")
            return None
                
    logger.error("Failed to store idea after all retry attempts")
    return None


def retry_generation(max_attempts: int = 3) -> bool:
    """
    Retry idea generation if initial attempt failed.
    
    Args:
        max_attempts: Maximum number of retry attempts
        
    Returns:
        bool: True if retry successful, False otherwise
    """
    logger.info(f"Starting retry generation (max {max_attempts} attempts)")
    
    for attempt in range(max_attempts):
        try:
            logger.info(f"Retry attempt {attempt + 1}/{max_attempts}")
            
            # Load methodology
            methodology = load_claude_methodology()
            
            # Construct prompt with retry context
            base_prompt = construct_idea_generation_prompt(methodology)
            retry_prompt = f"{base_prompt}\n\nNote: This is retry attempt {attempt + 1}. Please ensure the response is valid JSON."
            
            # Execute Claude CLI
            response = execute_claude_cli(retry_prompt)
            if not response:
                logger.warning(f"Retry attempt {attempt + 1} failed - no response from Claude CLI")
                continue
                
            # Parse and validate
            idea_data = parse_claude_response(response)
            if not idea_data:
                logger.warning(f"Retry attempt {attempt + 1} failed - parsing error")
                continue
                
            if not validate_idea_structure(idea_data):
                logger.warning(f"Retry attempt {attempt + 1} failed - validation error")
                continue
                
            # Success - enhance and store
            enhanced_idea = enhance_with_metadata(idea_data)
            idea_id = store_idea_in_database(enhanced_idea)
            
            if idea_id:
                logger.info(f"Retry successful on attempt {attempt + 1} - stored idea {idea_id}")
                log_generation_attempt(True, idea_id=idea_id)
                return True
            else:
                logger.warning(f"Retry attempt {attempt + 1} failed - storage error")
                
        except Exception as e:
            logger.error(f"Retry attempt {attempt + 1} failed with exception: {str(e)}")
            
        # Wait between retries
        if attempt < max_attempts - 1:
            time.sleep(10)  # Wait 10 seconds between retries
            
    logger.error(f"All {max_attempts} retry attempts failed")
    return False


def main():
    """
    Main execution function for idea generation.
    """
    start_time = time.time()
    logger.info("Starting daily idea generation")
    
    try:
        # Load methodology
        methodology = load_claude_methodology()
        logger.info("Methodology loaded successfully")
        
        # Construct prompt
        prompt = construct_idea_generation_prompt(methodology)
        logger.info("Prompt constructed")
        
        # Execute Claude CLI
        response = execute_claude_cli(prompt)
        if not response:
            logger.error("Claude CLI execution failed")
            execution_time = time.time() - start_time
            log_generation_attempt(False, "Claude CLI execution failed", execution_time)
            return retry_generation()
            
        # Parse response
        idea_data = parse_claude_response(response)
        if not idea_data:
            logger.error("Failed to parse Claude response")
            execution_time = time.time() - start_time
            log_generation_attempt(False, "Response parsing failed", execution_time)
            return retry_generation()
            
        # Validate structure
        if not validate_idea_structure(idea_data):
            logger.error("Idea structure validation failed")
            execution_time = time.time() - start_time
            log_generation_attempt(False, "Invalid idea structure", execution_time)
            return retry_generation()
            
        # Enhance with metadata
        enhanced_idea = enhance_with_metadata(idea_data)
        
        # Store in database
        idea_id = store_idea_in_database(enhanced_idea)
        execution_time = time.time() - start_time
        
        if idea_id:
            logger.info(f"Successfully generated and stored idea {idea_id}: {enhanced_idea.get('title', 'Unknown')}")
            log_generation_attempt(True, execution_time=execution_time, idea_id=idea_id)
            # Output the idea ID to stdout for API capture
            print(f"GENERATED_IDEA_ID:{idea_id}")
            return True
        else:
            logger.error("Failed to store idea in database")
            log_generation_attempt(False, "Database storage failed", execution_time)
            return False
            
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Unexpected error during generation: {str(e)}")
        log_generation_attempt(False, f"Unexpected error: {str(e)}", execution_time)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)