# Daily Inspo - Deployment Guide

This guide provides step-by-step instructions for deploying and running the Daily Inspo automated app idea generation system.

## Prerequisites

### Required Software
- **Python 3.8+**: Core runtime environment
- **Claude Code CLI**: For idea generation
- **Git**: For version control (optional)

### System Requirements
- **Operating System**: Windows, macOS, or Linux
- **Memory**: 512MB RAM minimum, 1GB recommended
- **Storage**: 100MB free disk space minimum
- **Network**: Internet connection for Claude CLI

## Installation Steps

### 1. Setup Project Environment

```bash
# Clone or download the project
cd /path/to/your/projects
# (Assuming project is already in daily-inspo directory)

# Navigate to project directory
cd daily-inspo

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Initialize Database

```bash
# Create and setup the SQLite database
python scripts/init_db.py
```

**Expected Output:**
```
Database initialized successfully!
```

### 3. Verify System Components

```bash
# Test that all components work
python test_generation_simple.py
```

**Expected Output:**
```
[OK] Methodology loaded (5066 characters)
[OK] Prompt constructed (5546 characters)
[OK] Database accessible (total ideas: 0)
[OK] All generation system components working correctly
```

### 4. Start Web Interface

```bash
# Start the FastAPI development server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload
```

**Access the application:**
- Open browser to: http://localhost:8002
- API documentation: http://localhost:8002/docs

### 5. Setup Automated Idea Generation (Optional)

```bash
# Setup cron job for daily idea generation
python scripts/setup_cron.py
```

**Note:** This requires Claude CLI to be properly configured and accessible.

## Manual Idea Generation

To manually generate an idea (useful for testing):

```bash
# Run the generation script manually
python scripts/generate_idea.py
```

## Configuration

### Environment Variables

Create a `.env` file in the project root (optional):

```env
# Development settings
FASTAPI_ENV=development
LOG_LEVEL=INFO

# Database settings (using defaults)
DATABASE_PATH=daily_ideas.db

# Server settings
SERVER_HOST=127.0.0.1
SERVER_PORT=8002
```

### Customizing Idea Generation

Edit the methodology file to customize idea generation:

[idea_generation/IDEA_GENERATION_METHODOLOGY.md](https://github.com/nickmccarty/daily-inspo/blob/main/docs/DEPLOYMENT.md)

## Directory Structure

After deployment, your directory should look like this:

```
daily-inspo/
├── app/                    # FastAPI application
│   ├── main.py            # Main app entry point
│   ├── database.py        # Database operations
│   ├── models.py          # Data models
│   └── api/               # API routes
├── scripts/               # Automation scripts
│   ├── init_db.py        # Database initialization
│   ├── generate_idea.py   # Idea generation
│   └── setup_cron.py     # Cron job setup
├── static/                # Frontend files
│   ├── index.html        # Main UI
│   ├── css/styles.css    # Styling
│   └── js/app.js         # JavaScript app
├── idea_generation/       # Generation methodology
├── docs/                  # Documentation
├── daily_ideas.db         # SQLite database (created)
├── requirements.txt       # Python dependencies
└── README.md             # Project overview
```

## Troubleshooting

### Common Issues

**1. Database Locked Error**
```
Database operation failed: database is locked
```
**Solution:** Stop the FastAPI server and try the operation again.

**2. Claude CLI Not Found**
```
Claude CLI not found in PATH
```
**Solution:** Ensure Claude Code CLI is installed and accessible in your system PATH.

**3. Port Already in Use**
```
Error: Port 8000 is already in use
```
**Solution:** Use a different port:
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8002
```

**4. Permission Denied (Cron Setup)**
**Solution:** Run the setup script with appropriate permissions or manually configure the scheduled task.

### Logs and Debugging

- **Application logs**: Check console output when running uvicorn
- **Generation logs**: Check `generation.log` file (created after first run)
- **Database issues**: Use SQLite browser tools to inspect `daily_ideas.db`

### Performance Optimization

**For Production Use:**
1. Use a production ASGI server (gunicorn + uvicorn)
2. Set up proper logging configuration
3. Configure database connection pooling
4. Set up monitoring and alerting
5. Use environment variables for configuration
6. Set up proper backup procedures

## API Endpoints

Once deployed, the following API endpoints are available:

- `GET /api/ideas/` - Get paginated list of ideas
- `GET /api/ideas/{id}` - Get specific idea details  
- `GET /api/ideas/search/` - Search and filter ideas
- `GET /api/ideas/random/` - Get random idea
- `GET /api/ideas/stats/` - Get system statistics
- `GET /api/filters/industries/` - Get available industries
- `GET /api/filters/technologies/` - Get available technologies
- `GET /api/filters/complexity-levels/` - Get complexity options
- `GET /api/filters/target-markets/` - Get target market options

## Security Considerations

### For Development
- Application runs on localhost only
- No authentication required
- SQLite database with file-level permissions

### For Production
- Implement proper authentication
- Use HTTPS/TLS encryption
- Set up proper firewall rules
- Regular security updates
- Database access controls
- Input validation and sanitization

## Backup and Maintenance

### Database Backup
```bash
# Create database backup
cp daily_ideas.db daily_ideas_backup_$(date +%Y%m%d).db
```

### Log Cleanup
```bash
# Clean old generation logs
find . -name "generation.log" -mtime +30 -delete
```

### System Health Check
```bash
# Check system status
curl http://localhost:8002/api/ideas/stats/
```

## Support

For issues and questions:
1. Check this deployment guide
2. Review the troubleshooting section
3. Check log files for error details
4. Verify all prerequisites are met

The Daily Inspo system is designed to be lightweight and easy to deploy for personal use and prototyping.
