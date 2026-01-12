#!/usr/bin/env python3
"""
Competitor Monitor - Background Scheduler
Runs periodic monitoring tasks for page changes and news collection.
"""
import os
import sys
import logging
import signal
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create scheduler
scheduler = BlockingScheduler()


def run_page_monitor():
    """Run the page monitoring job."""
    logger.info("Starting scheduled page monitoring run...")
    
    try:
        from app import create_app
        from app.monitor import PageMonitor
        from app.analyzer import Analyzer
        from app.alerter import Alerter
        
        app = create_app()
        
        with app.app_context():
            # Check pages for changes
            monitor = PageMonitor()
            changes = monitor.check_all_urls()
            
            logger.info(f"Page monitoring complete. Found {len(changes)} changes.")
            
            if changes:
                # Analyze changes
                analyzer = Analyzer()
                results = analyzer.process_pending_items()
                
                logger.info(f"Analysis complete. Created {results['alerts_created']} alerts.")
                
                # Send notifications for high-priority alerts
                alerter = Alerter()
                alert_results = alerter.send_pending_alerts(min_risk_level='medium')
                
                logger.info(f"Notifications sent: {alert_results['sent']} alerts")
    
    except Exception as e:
        logger.error(f"Error in page monitoring job: {e}", exc_info=True)


def run_news_collector():
    """Run the news collection job."""
    logger.info("Starting scheduled news collection run...")
    
    try:
        from app import create_app
        from app.news_collector import NewsCollector
        from app.analyzer import Analyzer
        from app.alerter import Alerter
        
        app = create_app()
        
        with app.app_context():
            # Collect news
            collector = NewsCollector()
            results = collector.collect_all_news()
            
            total_items = sum(len(items) for items in results.values())
            logger.info(f"News collection complete. Collected {total_items} items.")
            
            if total_items > 0:
                # Analyze news items
                analyzer = Analyzer()
                analysis_results = analyzer.process_pending_items()
                
                logger.info(f"Analysis complete. Created {analysis_results['alerts_created']} alerts.")
                
                # Send notifications
                alerter = Alerter()
                alert_results = alerter.send_pending_alerts(min_risk_level='medium')
                
                logger.info(f"Notifications sent: {alert_results['sent']} alerts")
    
    except Exception as e:
        logger.error(f"Error in news collection job: {e}", exc_info=True)


def run_daily_digest():
    """Send daily digest of all alerts."""
    logger.info("Preparing daily digest...")
    
    try:
        from app import create_app
        from app.database import Alert
        from datetime import timedelta
        
        app = create_app()
        
        with app.app_context():
            # Get yesterday's alerts
            yesterday = datetime.utcnow() - timedelta(days=1)
            alerts = Alert.query.filter(
                Alert.detected_at >= yesterday
            ).all()
            
            logger.info(f"Daily digest: {len(alerts)} alerts in last 24 hours")
            
            # TODO: Send digest email/notification
    
    except Exception as e:
        logger.error(f"Error in daily digest job: {e}", exc_info=True)


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("Received shutdown signal, stopping scheduler...")
    scheduler.shutdown(wait=False)
    sys.exit(0)


def main():
    """Main entry point for the scheduler."""
    logger.info("Starting Competitor Monitor Scheduler")
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Get intervals from environment
    page_monitor_hours = int(os.getenv('MONITOR_SCHEDULE_HOURS', 24))
    news_check_hours = int(os.getenv('NEWS_CHECK_HOURS', 6))
    
    # Schedule page monitoring
    scheduler.add_job(
        run_page_monitor,
        trigger=IntervalTrigger(hours=page_monitor_hours),
        id='page_monitor',
        name='Page Monitoring',
        replace_existing=True,
        next_run_time=datetime.now()  # Run immediately on start
    )
    
    # Schedule news collection
    scheduler.add_job(
        run_news_collector,
        trigger=IntervalTrigger(hours=news_check_hours),
        id='news_collector',
        name='News Collection',
        replace_existing=True,
        next_run_time=datetime.now()  # Run immediately on start
    )
    
    # Schedule daily digest at 8 AM UTC
    scheduler.add_job(
        run_daily_digest,
        trigger='cron',
        hour=8,
        minute=0,
        id='daily_digest',
        name='Daily Digest',
        replace_existing=True
    )
    
    logger.info(f"Scheduled jobs:")
    logger.info(f"  - Page monitoring: every {page_monitor_hours} hours")
    logger.info(f"  - News collection: every {news_check_hours} hours")
    logger.info(f"  - Daily digest: 8:00 AM UTC")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == '__main__':
    main()
