"""
Competitor Monitor Application Package
"""
from flask import Flask
from flask_cors import CORS
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base directory for the project
BASE_DIR = Path(__file__).resolve().parent.parent

# On Azure App Service, use /home for persistent storage
# Otherwise use local data directory
if os.path.exists('/home') and os.environ.get('WEBSITE_SITE_NAME'):
    DATA_DIR = Path('/home/data')
else:
    DATA_DIR = BASE_DIR / 'data'

# Ensure data directory exists with parents
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Global scheduler instance
scheduler = None


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
        db_path = DATA_DIR / 'competitor_monitor.db'
        
        # Ensure data directory exists before any database operations
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Check if we need to reset the database (due to corruption)
        should_reset = os.environ.get('RESET_DATABASE') == 'true' or os.environ.get('DELETE_DB_ON_START') == 'true'
        
        if should_reset and db_path.exists():
            app.logger.warning("RESET_DATABASE flag detected - deleting existing database")
            try:
                db_path.unlink()
                app.logger.info("Database file deleted successfully")
            except Exception as e:
                app.logger.error(f"Failed to delete database: {e}")
        
        # Create all tables
        try:
            db.create_all()
            app.logger.info("Database initialized successfully")
        except Exception as e:
            error_msg = str(e).lower()
            app.logger.error(f"Database initialization error: {e}")
            
            # If database is corrupted, try to delete and let next restart recreate it
            if 'malformed' in error_msg or 'corrupt' in error_msg:
                app.logger.error("Database corrupted - deleting for next restart")
                try:
                    if db_path.exists():
                        db_path.unlink()
                except Exception as e2:
                    app.logger.error(f"Could not delete corrupted database: {e2}")
    
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
    
    # Initialize background scheduler for auto-updates
    init_scheduler(app)
    
    return app


def init_scheduler(app):
    """Initialize APScheduler for background tasks."""
    global scheduler
    
    # Only run scheduler in main worker process (not in reloader subprocess)
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.interval import IntervalTrigger
            
            scheduler = BackgroundScheduler()
            
            # Get schedule intervals from environment
            monitor_hours = int(os.getenv('MONITOR_SCHEDULE_HOURS', 6))
            news_hours = int(os.getenv('NEWS_CHECK_HOURS', 6))
            
            # Add news collection job
            scheduler.add_job(
                func=lambda: run_scheduled_job(app, 'news'),
                trigger=IntervalTrigger(hours=news_hours),
                id='scheduled_news_collection',
                name='News Collection',
                replace_existing=True
            )
            
            # Add page monitoring job
            scheduler.add_job(
                func=lambda: run_scheduled_job(app, 'pages'),
                trigger=IntervalTrigger(hours=monitor_hours),
                id='scheduled_page_monitor',
                name='Page Monitor',
                replace_existing=True
            )
            
            scheduler.start()
            logger.info(f"Scheduler started: News every {news_hours}h, Pages every {monitor_hours}h")
            
        except Exception as e:
            logger.warning(f"Could not start scheduler: {e}")


def run_scheduled_job(app, job_type):
    """Run a scheduled monitoring job."""
    with app.app_context():
        try:
            if job_type == 'news':
                from .news_collector import NewsCollector
                from .analyzer import Analyzer
                
                logger.info("Running scheduled news collection...")
                collector = NewsCollector()
                results = collector.collect_all_news()
                total = sum(len(items) for items in results.values())
                logger.info(f"Collected {total} news items")
                
                # Run analysis on new items
                if total > 0:
                    analyzer = Analyzer()
                    analysis = analyzer.process_pending_items()
                    logger.info(f"Created {analysis['alerts_created']} alerts")
                    
            elif job_type == 'pages':
                from .monitor import PageMonitor
                from .analyzer import Analyzer
                
                logger.info("Running scheduled page monitoring...")
                monitor = PageMonitor()
                changes = monitor.check_all_urls()
                logger.info(f"Found {len(changes)} page changes")
                
                # Run analysis on changes
                if changes:
                    analyzer = Analyzer()
                    analysis = analyzer.process_pending_items()
                    logger.info(f"Created {analysis['alerts_created']} alerts")
                    
        except Exception as e:
            logger.error(f"Scheduled job error ({job_type}): {e}")
