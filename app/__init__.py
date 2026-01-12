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

# On Azure App Service, use /home for persistent storage
# Otherwise use local data directory
if os.path.exists('/home') and os.environ.get('WEBSITE_SITE_NAME'):
    DATA_DIR = Path('/home/data')
else:
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
        # Use checkfirst=True to avoid errors on existing tables
        try:
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if not existing_tables:
                # Only create all tables if database is empty
                db.create_all()
            else:
                # Database exists, let SQLAlchemy handle incremental updates
                db.create_all(checkfirst=True)
        except Exception as e:
            app.logger.warning(f"Database initialization note: {e}")
            # Try a simple create_all with checkfirst
            try:
                db.create_all()
            except:
                pass  # Tables already exist, which is fine
    
    # Register blueprints
    from .routes import main_bp, api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # Register custom Jinja filters
    import json
    
    @app.template_filter('from_json')
    def from_json_filter(value):
        """Parse JSON string to Python object."""
        if not value:
            return []
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []
    
    return app
