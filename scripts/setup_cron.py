#!/usr/bin/env python3
"""
Cron job setup script.

Configures system cron job for automated daily idea generation.
Sets up weekday-only execution at 10 AM with proper environment.
"""

import sys
import os
import subprocess
import logging
import platform
from pathlib import Path
from typing import Optional

# Add parent directory to path for imports  
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_project_directory() -> Path:
    """
    Get absolute path to project directory.
    
    Returns:
        Path: Absolute path to project root
    """
    # Get the directory containing this script, then go up one level
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    return project_dir.resolve()


def get_python_executable() -> str:
    """
    Get path to Python executable.
    
    Returns:
        str: Path to Python executable
    """
    return sys.executable


def verify_claude_cli_access() -> bool:
    """
    Verify that Claude CLI is accessible from cron environment.
    
    Returns:
        bool: True if Claude CLI is accessible, False otherwise
    """
    try:
        # Try to run claude --help to verify it's available
        result = subprocess.run(
            ['claude', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            logger.info("Claude CLI is accessible")
            return True
        else:
            logger.error(f"Claude CLI returned error code {result.returncode}")
            return False
    except FileNotFoundError:
        logger.error("Claude CLI not found in PATH")
        return False
    except Exception as e:
        logger.error(f"Failed to verify Claude CLI: {str(e)}")
        return False


def verify_dependencies() -> bool:
    """
    Verify all required Python packages are available.
    
    Returns:
        bool: True if all dependencies available, False otherwise
    """
    required_packages = ['sqlite3', 'json', 'datetime', 'pathlib']
    
    try:
        for package in required_packages:
            __import__(package)
        
        # Test database access
        from app.database import initialize_database
        logger.info("All required dependencies are available")
        return True
        
    except ImportError as e:
        logger.error(f"Missing required dependency: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Dependency verification failed: {str(e)}")
        return False


def create_cron_script() -> Path:
    """
    Create wrapper script for cron execution.
    
    Returns:
        Path: Path to created wrapper script
    """
    project_dir = get_project_directory()
    python_exec = get_python_executable()
    script_path = project_dir / "run_daily_generation.sh"
    
    # Create shell script for reliable cron execution
    script_content = f"""#!/bin/bash
# Daily Inspo - Idea Generation Cron Script
# Generated automatically by setup_cron.py

# Set up environment
export PATH="$PATH:/usr/local/bin"
cd "{project_dir}"

# Log execution
echo "$(date): Starting daily idea generation" >> generation.log

# Run the generation script
"{python_exec}" scripts/generate_idea.py >> generation.log 2>&1

# Log completion
echo "$(date): Daily idea generation completed with exit code $?" >> generation.log
"""
    
    try:
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make script executable
        os.chmod(script_path, 0o755)
        
        logger.info(f"Created cron script: {script_path}")
        return script_path
        
    except Exception as e:
        logger.error(f"Failed to create cron script: {str(e)}")
        raise


def setup_unix_cron() -> bool:
    """
    Set up cron job on Unix-like systems (Linux/Mac).
    
    Returns:
        bool: True if cron setup successful, False otherwise
    """
    try:
        # Create the wrapper script
        script_path = create_cron_script()
        
        # Define cron job (10 AM weekdays)
        cron_job = f"0 10 * * 1-5 {script_path}\n"
        
        # Get existing crontab
        try:
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            existing_crontab = result.stdout if result.returncode == 0 else ""
        except:
            existing_crontab = ""
        
        # Check if our job already exists
        if 'daily_inspo' in existing_crontab or str(script_path) in existing_crontab:
            logger.warning("Cron job already exists, updating...")
            # Remove existing job
            existing_lines = existing_crontab.split('\n')
            filtered_lines = [line for line in existing_lines 
                            if 'daily_inspo' not in line.lower() and str(script_path) not in line]
            existing_crontab = '\n'.join(filtered_lines)
        
        # Add our new job
        new_crontab = existing_crontab.rstrip('\n') + '\n' + cron_job if existing_crontab else cron_job
        
        # Install the new crontab
        process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
        process.communicate(input=new_crontab)
        
        if process.returncode == 0:
            logger.info("Cron job installed successfully")
            return True
        else:
            logger.error("Failed to install cron job")
            return False
            
    except Exception as e:
        logger.error(f"Unix cron setup failed: {str(e)}")
        return False


def setup_windows_task() -> bool:
    """
    Set up scheduled task on Windows systems.
    
    Returns:
        bool: True if task setup successful, False otherwise
    """
    try:
        project_dir = get_project_directory()
        python_exec = get_python_executable()
        
        # Create batch file for Windows
        batch_path = project_dir / "run_daily_generation.bat"
        batch_content = f"""@echo off
REM Daily Inspo - Idea Generation Windows Task
REM Generated automatically by setup_cron.py

cd /d "{project_dir}"

echo %date% %time%: Starting daily idea generation >> generation.log

"{python_exec}" scripts\generate_idea.py >> generation.log 2>&1

echo %date% %time%: Daily idea generation completed with exit code %errorlevel% >> generation.log
"""
        
        with open(batch_path, 'w') as f:
            f.write(batch_content)
        
        # Create scheduled task using schtasks
        task_name = "DailyInspoGeneration"
        
        # Delete existing task if it exists
        subprocess.run([
            'schtasks', '/delete', '/tn', task_name, '/f'
        ], capture_output=True)
        
        # Create new task
        result = subprocess.run([
            'schtasks', '/create', '/tn', task_name,
            '/tr', str(batch_path),
            '/sc', 'weekly',
            '/d', 'MON,TUE,WED,THU,FRI',
            '/st', '10:00',
            '/f'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Windows scheduled task '{task_name}' created successfully")
            return True
        else:
            logger.error(f"Failed to create Windows task: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Windows task setup failed: {str(e)}")
        return False


def verify_cron_installation() -> bool:
    """
    Verify that cron job was installed correctly.
    
    Returns:
        bool: True if cron job is properly installed
    """
    try:
        if platform.system().lower() == "windows":
            # Check Windows scheduled task
            result = subprocess.run([
                'schtasks', '/query', '/tn', 'DailyInspoGeneration'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("Windows scheduled task verified")
                return True
            else:
                logger.error("Windows scheduled task not found")
                return False
        else:
            # Check Unix cron job
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            
            if result.returncode == 0 and 'daily_inspo' in result.stdout.lower():
                logger.info("Unix cron job verified")
                return True
            else:
                logger.error("Unix cron job not found")
                return False
                
    except Exception as e:
        logger.error(f"Cron verification failed: {str(e)}")
        return False


def remove_existing_cron() -> None:
    """
    Remove any existing cron jobs for this project.
    """
    try:
        if platform.system().lower() == "windows":
            # Remove Windows scheduled task
            subprocess.run([
                'schtasks', '/delete', '/tn', 'DailyInspoGeneration', '/f'
            ], capture_output=True)
            logger.info("Removed existing Windows scheduled task")
        else:
            # Remove Unix cron job
            try:
                result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
                if result.returncode == 0:
                    existing_lines = result.stdout.split('\n')
                    filtered_lines = [line for line in existing_lines 
                                    if 'daily_inspo' not in line.lower()]
                    new_crontab = '\n'.join(filtered_lines)
                    
                    process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
                    process.communicate(input=new_crontab)
                    logger.info("Removed existing Unix cron job")
            except:
                pass  # No existing crontab
                
    except Exception as e:
        logger.warning(f"Failed to remove existing cron job: {str(e)}")


def test_manual_execution() -> bool:
    """
    Test manual execution of generation script.
    
    Returns:
        bool: True if manual test successful
    """
    try:
        project_dir = get_project_directory()
        python_exec = get_python_executable()
        script_path = project_dir / "scripts" / "generate_idea.py"
        
        # Test that the script exists
        if not script_path.exists():
            logger.error(f"Generation script not found: {script_path}")
            return False
        
        # Test that we can import the required modules
        test_command = [
            python_exec, '-c',
            f'import sys; sys.path.append("{project_dir}"); from scripts.generate_idea import load_claude_methodology; print("Test passed")'
        ]
        
        result = subprocess.run(
            test_command,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_dir
        )
        
        if result.returncode == 0 and "Test passed" in result.stdout:
            logger.info("Manual execution test passed")
            return True
        else:
            logger.error(f"Manual execution test failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Manual execution test failed: {str(e)}")
        return False


def main():
    """
    Main function to set up cron job for idea generation.
    """
    logger.info("Starting cron job setup")
    
    try:
        # Verify environment
        if not verify_claude_cli_access():
            logger.error("Claude CLI not accessible - setup cannot continue")
            return False
            
        if not verify_dependencies():
            logger.error("Missing required dependencies - setup cannot continue")
            return False
            
        # Test manual execution first
        logger.info("Testing manual script execution")
        if not test_manual_execution():
            logger.error("Manual script execution failed - fixing issues before cron setup")
            return False
            
        # Remove any existing cron jobs
        logger.info("Removing existing cron jobs")
        remove_existing_cron()
        
        # Set up platform-specific scheduling
        if platform.system().lower() == "windows":
            logger.info("Setting up Windows scheduled task")
            success = setup_windows_task()
        else:
            logger.info("Setting up Unix cron job")
            success = setup_unix_cron()
            
        if not success:
            logger.error("Failed to set up scheduled task")
            return False
            
        # Verify installation
        if verify_cron_installation():
            logger.info("Cron job setup completed successfully")
            logger.info("Daily idea generation will run weekdays at 10:00 AM")
            return True
        else:
            logger.error("Cron job verification failed")
            return False
            
    except Exception as e:
        logger.error(f"Cron setup failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print("Cron job setup completed successfully!")
        print("Daily idea generation will run weekdays at 10:00 AM")
    else:
        print("Cron job setup failed. Check logs for details.")
    sys.exit(0 if success else 1)