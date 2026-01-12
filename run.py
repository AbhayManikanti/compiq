#!/usr/bin/env python3
"""
Competitor Monitor - Main Application Runner
Starts the Flask web server and background monitoring tasks.
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/app.log', mode='a')
    ] if os.path.exists('logs') else [logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


def create_directories():
    """Ensure required directories exist."""
    directories = ['data', 'logs', 'config']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# Create directories on import
create_directories()

# Import and create app at module level for gunicorn
from app import create_app
app = create_app()


def main():
    """Main entry point for local development."""
    # Get configuration from environment
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    
    logger.info(f"Starting Competitor Monitor on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    
    # Run the Flask app
    app.run(
        host=host,
        port=port,
        debug=debug
    )


if __name__ == '__main__':
    main()
