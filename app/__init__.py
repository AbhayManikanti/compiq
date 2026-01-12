"""
Competitor Monitor Application Package
"""
from flask import Flask
from flask_cors import CORS
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)


def create_app():
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static'
    )
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key')
    
    # Use absolute path for SQLite database
    db_path = DATA_DIR / 'competitor_monitor.db'
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL', 
        f'sqlite:///{db_path}'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Enable CORS for frontend hosted on different domain
    cors_origins = os.getenv('CORS_ORIGINS', '*')
    CORS(app, resources={
        r"/api/*": {
            "origins": cors_origins.split(',') if cors_origins != '*' else '*',
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Initialize database
    from .database import db
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
    
    # Register blueprints
    from .routes import main_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app
