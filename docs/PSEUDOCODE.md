# Pseudocode Documentation

## System Flow Overview

```
1. CRON_JOB_SCHEDULER
   IF current_day NOT in [Saturday, Sunday]
   AND current_time = 10:00 AM
   THEN execute generate_idea_script()

2. GENERATE_IDEA_SCRIPT
   load_claude_methodology()
   execute_claude_cli(methodology_prompt)
   parse_claude_response()
   validate_idea_data()
   store_in_database()
   log_result()

3. WEB_INTERFACE
   load_ideas_from_database()
   render_idea_cards()
   handle_filtering_requests()
   display_detailed_views()
```

## Core Algorithms

### 1. Daily Idea Generation Process

```python
def generate_daily_idea():
    """
    Main function for automated idea generation
    """
    # Load the specialized Claude methodology
    methodology = load_claude_methodology_file()
    
    # Construct the prompt for Claude CLI
    prompt = construct_idea_generation_prompt(methodology)
    
    # Execute Claude CLI command
    claude_response = execute_claude_cli(prompt)
    
    # Parse the structured response
    parsed_idea = parse_claude_response(claude_response)
    
    # Validate required fields are present
    if validate_idea_structure(parsed_idea):
        # Generate tags and metadata
        enhanced_idea = enhance_with_metadata(parsed_idea)
        
        # Store in database
        idea_id = store_idea_in_database(enhanced_idea)
        
        # Log successful generation
        log_success(idea_id, enhanced_idea['title'])
    else:
        # Handle parsing failure
        log_error("Failed to parse Claude response")
        retry_generation() if retry_count < 3
```

### 2. Database Operations

```python
def store_idea_in_database(idea_data):
    """
    Store parsed idea with all metadata
    """
    # Create database connection
    connection = get_database_connection()
    
    # Insert main idea record
    idea_id = insert_idea_record(
        title=idea_data['title'],
        summary=idea_data['summary'],
        full_description=idea_data['description'],
        supporting_logic=idea_data['rationale'],
        market_data=idea_data['market_analysis'],
        generated_date=current_timestamp()
    )
    
    # Insert associated tags
    for tag in idea_data['tags']:
        insert_tag_relationship(idea_id, tag['category'], tag['value'])
    
    # Insert factual supporting data
    insert_supporting_data(
        idea_id=idea_id,
        market_size=idea_data['market_size'],
        competitors=idea_data['competitors'],
        technical_feasibility=idea_data['feasibility'],
        timeline_estimate=idea_data['timeline']
    )
    
    return idea_id
```

### 3. Web Interface Logic

```python
def render_idea_cards(filters=None):
    """
    Generate HTML for idea card display
    """
    # Query database with optional filters
    ideas = query_ideas_with_filters(filters)
    
    # Generate card HTML for each idea
    card_html = []
    for idea in ideas:
        card_data = {
            'id': idea.id,
            'title': idea.title,
            'summary': truncate(idea.summary, 150),
            'tags': get_idea_tags(idea.id),
            'generated_date': format_date(idea.generated_date)
        }
        card_html.append(render_card_template(card_data))
    
    return combine_cards_html(card_html)

def handle_filter_request(filter_params):
    """
    Process filtering requests from frontend
    """
    # Validate filter parameters
    validated_filters = validate_filters(filter_params)
    
    # Build database query
    query_conditions = build_filter_query(validated_filters)
    
    # Execute filtered query
    filtered_ideas = execute_filtered_query(query_conditions)
    
    # Return JSON response
    return jsonify(filtered_ideas)
```

### 4. Claude CLI Integration

```python
def execute_claude_cli(prompt):
    """
    Execute Claude Code CLI with methodology prompt
    """
    # Prepare the command
    claude_command = [
        'claude',
        '--prompt', prompt,
        '--format', 'json'
    ]
    
    # Execute with timeout and error handling
    try:
        result = subprocess.run(
            claude_command,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            return result.stdout
        else:
            log_error(f"Claude CLI failed: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        log_error("Claude CLI command timed out")
        return None
```

### 5. Cron Job Management

```python
def setup_cron_job():
    """
    Configure cron job for weekday execution
    """
    # Define cron schedule (10 AM weekdays)
    cron_schedule = "0 10 * * 1-5"
    
    # Path to generation script
    script_path = get_absolute_script_path()
    
    # Create cron entry
    cron_command = f"cd {project_directory} && python {script_path}"
    
    # Add to system crontab
    add_cron_entry(cron_schedule, cron_command)
    
    # Verify cron job was added
    verify_cron_installation()

def validate_cron_environment():
    """
    Ensure cron job has proper environment
    """
    # Check Python path
    verify_python_executable()
    
    # Check project dependencies
    verify_required_packages()
    
    # Check database accessibility
    verify_database_connection()
    
    # Check Claude CLI availability
    verify_claude_cli_access()
```

## Data Flow Diagrams

### Idea Generation Flow
```
Cron Scheduler → Generate Script → Claude CLI → Response Parser → Database → Log
     ↓              ↓                ↓            ↓              ↓         ↓
   Time Check    Load Method.    Execute Prompt   Extract Data   Store    Record
```

### Web Interface Flow
```
User Request → FastAPI Router → Database Query → Data Formatter → JSON Response → Frontend Render
     ↓             ↓               ↓               ↓                ↓            ↓
   Filter Params  Route Handler   SQL Execution   Transform Data   API Response  DOM Update
```

## Error Handling Strategy

### Generation Script Errors
```python
def handle_generation_error(error_type, error_details):
    """
    Comprehensive error handling for idea generation
    """
    if error_type == "claude_cli_unavailable":
        log_error("Claude CLI not accessible")
        send_notification_email()
        
    elif error_type == "parsing_failure":
        log_error(f"Failed to parse response: {error_details}")
        attempt_manual_parsing()
        
    elif error_type == "database_error":
        log_error(f"Database operation failed: {error_details}")
        attempt_database_recovery()
        
    else:
        log_error(f"Unknown error: {error_type} - {error_details}")
        schedule_manual_review()
```

### Web Interface Error Handling
```python
def handle_web_error(request, error):
    """
    Web interface error responses
    """
    if isinstance(error, DatabaseConnectionError):
        return error_response("Database temporarily unavailable", 503)
        
    elif isinstance(error, ValidationError):
        return error_response("Invalid request parameters", 400)
        
    else:
        log_error(f"Unexpected web error: {str(error)}")
        return error_response("Internal server error", 500)
```