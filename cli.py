#!/usr/bin/env python3
"""
Competitor Monitor - Command Line Interface
Provides CLI commands for managing the monitoring system.
"""
import os
import sys
import argparse
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


def init_app():
    """Initialize the Flask app context."""
    from app import create_app
    app = create_app()
    return app


def cmd_init(args):
    """Initialize the database with sample data."""
    from app.database import init_db
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")


def cmd_monitor(args):
    """Run the page monitor."""
    from app.monitor import PageMonitor
    
    app = init_app()
    with app.app_context():
        monitor = PageMonitor()
        
        if args.url:
            # Check specific URL
            from app.database import MonitoredURL
            url_obj = MonitoredURL.query.filter_by(url=args.url).first()
            if not url_obj:
                print(f"URL not found: {args.url}")
                return
            
            print(f"Checking: {args.url}")
            snapshot = monitor.check_url(url_obj)
            
            if snapshot and snapshot.has_changes:
                print("✓ Changes detected!")
                print(f"  Summary: {snapshot.diff_summary[:200]}...")
            else:
                print("No changes detected.")
        else:
            # Check all URLs
            print("Checking all monitored URLs...")
            changes = monitor.check_all_urls(force=args.force)
            
            print(f"\nCompleted! Found {len(changes)} pages with changes.")
            
            for snapshot in changes:
                url = snapshot.monitored_url
                print(f"\n• {url.competitor.name}: {url.name}")
                print(f"  URL: {url.url}")
                if snapshot.diff_summary:
                    print(f"  Changes: {snapshot.diff_summary[:100]}...")


def cmd_news(args):
    """Collect news articles."""
    from app.news_collector import NewsCollector
    
    app = init_app()
    with app.app_context():
        collector = NewsCollector()
        
        print("Collecting news articles...")
        results = collector.collect_all_news(days_back=args.days)
        
        total = sum(len(items) for items in results.values())
        print(f"\nCollected {total} articles:")
        
        for competitor, items in results.items():
            print(f"\n• {competitor}: {len(items)} articles")
            for item in items[:3]:
                print(f"  - {item.title[:60]}...")


def cmd_analyze(args):
    """Run the LLM analyzer on pending items."""
    from app.analyzer import Analyzer
    
    app = init_app()
    with app.app_context():
        analyzer = Analyzer()
        
        print("Analyzing pending items...")
        results = analyzer.process_pending_items()
        
        print(f"\nAnalysis complete:")
        print(f"  Page changes processed: {results['page_changes_processed']}")
        print(f"  News items processed: {results['news_processed']}")
        print(f"  Alerts created: {results['alerts_created']}")


def cmd_alerts(args):
    """List or manage alerts."""
    from app.database import Alert, AlertStatus
    
    app = init_app()
    with app.app_context():
        if args.action == 'list':
            query = Alert.query
            
            if args.status:
                query = query.filter_by(status=args.status)
            if args.risk:
                query = query.filter_by(risk_level=args.risk)
            
            alerts = query.order_by(Alert.detected_at.desc()).limit(args.limit).all()
            
            print(f"\nFound {len(alerts)} alerts:\n")
            
            for alert in alerts:
                risk_emoji = {
                    'critical': '🚨',
                    'high': '🔴',
                    'medium': '🟡',
                    'low': '🟢',
                    'info': 'ℹ️'
                }.get(alert.risk_level, '⚪')
                
                print(f"{risk_emoji} [{alert.id}] {alert.title[:50]}...")
                print(f"   Competitor: {alert.competitor.name if alert.competitor else 'Unknown'}")
                print(f"   Status: {alert.status} | Risk: {alert.risk_level} ({alert.risk_score}/100)")
                print(f"   Detected: {alert.detected_at.strftime('%Y-%m-%d %H:%M')}")
                print()
        
        elif args.action == 'acknowledge':
            if not args.id:
                print("Error: --id required for acknowledge action")
                return
            
            alert = Alert.query.get(args.id)
            if not alert:
                print(f"Alert {args.id} not found")
                return
            
            alert.status = AlertStatus.ACKNOWLEDGED.value
            alert.acknowledged_at = datetime.utcnow()
            
            from app.database import db
            db.session.commit()
            
            print(f"Alert {args.id} acknowledged.")
        
        elif args.action == 'resolve':
            if not args.id:
                print("Error: --id required for resolve action")
                return
            
            alert = Alert.query.get(args.id)
            if not alert:
                print(f"Alert {args.id} not found")
                return
            
            alert.status = AlertStatus.RESOLVED.value
            alert.resolved_at = datetime.utcnow()
            alert.resolution_notes = args.notes or ''
            
            from app.database import db
            db.session.commit()
            
            print(f"Alert {args.id} resolved.")


def cmd_notify(args):
    """Send notifications for pending alerts."""
    from app.alerter import Alerter
    
    app = init_app()
    with app.app_context():
        alerter = Alerter()
        
        print(f"Sending notifications (min risk: {args.min_risk})...")
        results = alerter.send_pending_alerts(min_risk_level=args.min_risk)
        
        print(f"\nNotification results:")
        print(f"  Total pending: {results['total_pending']}")
        print(f"  Sent: {results['sent']}")
        print(f"  Failed: {results['failed']}")


def cmd_competitors(args):
    """Manage competitors."""
    from app.database import Competitor, db
    
    app = init_app()
    with app.app_context():
        if args.action == 'list':
            competitors = Competitor.query.all()
            
            print(f"\n{len(competitors)} competitors:\n")
            
            for comp in competitors:
                status = "✓ Active" if comp.is_active else "○ Inactive"
                urls = comp.monitored_urls.count()
                alerts = comp.alerts.filter_by(status='new').count()
                
                print(f"[{comp.id}] {comp.name}")
                print(f"    Website: {comp.website or 'N/A'}")
                print(f"    Status: {status}")
                print(f"    URLs: {urls} | New Alerts: {alerts}")
                print()
        
        elif args.action == 'add':
            if not args.name:
                print("Error: --name required")
                return
            
            comp = Competitor(
                name=args.name,
                website=args.website,
                description=args.description
            )
            db.session.add(comp)
            db.session.commit()
            
            print(f"Added competitor: {comp.name} (ID: {comp.id})")
        
        elif args.action == 'remove':
            if not args.id:
                print("Error: --id required")
                return
            
            comp = Competitor.query.get(args.id)
            if not comp:
                print(f"Competitor {args.id} not found")
                return
            
            comp.is_active = False
            db.session.commit()
            
            print(f"Deactivated competitor: {comp.name}")


def cmd_report(args):
    """Generate a report."""
    from app.database import Alert, Competitor
    
    app = init_app()
    with app.app_context():
        since = datetime.utcnow() - timedelta(days=args.days)
        
        alerts = Alert.query.filter(Alert.detected_at >= since).all()
        
        print(f"\n{'='*60}")
        print(f"COMPETITOR INTELLIGENCE REPORT")
        print(f"Period: Last {args.days} days")
        print(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}\n")
        
        print(f"SUMMARY")
        print(f"{'-'*40}")
        print(f"Total Alerts: {len(alerts)}")
        
        # By risk level
        risk_counts = {}
        for alert in alerts:
            risk_counts[alert.risk_level] = risk_counts.get(alert.risk_level, 0) + 1
        
        print(f"\nBy Risk Level:")
        for level in ['critical', 'high', 'medium', 'low', 'info']:
            count = risk_counts.get(level, 0)
            if count > 0:
                print(f"  {level.upper()}: {count}")
        
        # By competitor
        print(f"\nBy Competitor:")
        comp_counts = {}
        for alert in alerts:
            name = alert.competitor.name if alert.competitor else 'Unknown'
            comp_counts[name] = comp_counts.get(name, 0) + 1
        
        for name, count in sorted(comp_counts.items(), key=lambda x: -x[1]):
            print(f"  {name}: {count}")
        
        # High priority alerts
        high_priority = [a for a in alerts if a.risk_level in ['critical', 'high']]
        if high_priority:
            print(f"\nHIGH PRIORITY ALERTS")
            print(f"{'-'*40}")
            for alert in high_priority[:10]:
                print(f"\n• {alert.title}")
                print(f"  Risk: {alert.risk_level.upper()} ({alert.risk_score}/100)")
                print(f"  Summary: {alert.summary[:100]}..." if alert.summary else "")
        
        print(f"\n{'='*60}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Competitor Monitor CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # init command
    init_parser = subparsers.add_parser('init', help='Initialize database')
    init_parser.set_defaults(func=cmd_init)
    
    # monitor command
    monitor_parser = subparsers.add_parser('monitor', help='Run page monitor')
    monitor_parser.add_argument('--url', help='Check specific URL')
    monitor_parser.add_argument('--force', action='store_true', help='Force check all URLs')
    monitor_parser.set_defaults(func=cmd_monitor)
    
    # news command
    news_parser = subparsers.add_parser('news', help='Collect news')
    news_parser.add_argument('--days', type=int, default=7, help='Days back to search')
    news_parser.set_defaults(func=cmd_news)
    
    # analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze pending items')
    analyze_parser.set_defaults(func=cmd_analyze)
    
    # alerts command
    alerts_parser = subparsers.add_parser('alerts', help='Manage alerts')
    alerts_parser.add_argument('action', choices=['list', 'acknowledge', 'resolve'], help='Action')
    alerts_parser.add_argument('--id', type=int, help='Alert ID')
    alerts_parser.add_argument('--status', help='Filter by status')
    alerts_parser.add_argument('--risk', help='Filter by risk level')
    alerts_parser.add_argument('--limit', type=int, default=20, help='Max results')
    alerts_parser.add_argument('--notes', help='Resolution notes')
    alerts_parser.set_defaults(func=cmd_alerts)
    
    # notify command
    notify_parser = subparsers.add_parser('notify', help='Send notifications')
    notify_parser.add_argument('--min-risk', default='medium', help='Minimum risk level')
    notify_parser.set_defaults(func=cmd_notify)
    
    # competitors command
    comp_parser = subparsers.add_parser('competitors', help='Manage competitors')
    comp_parser.add_argument('action', choices=['list', 'add', 'remove'], help='Action')
    comp_parser.add_argument('--id', type=int, help='Competitor ID')
    comp_parser.add_argument('--name', help='Competitor name')
    comp_parser.add_argument('--website', help='Website URL')
    comp_parser.add_argument('--description', help='Description')
    comp_parser.set_defaults(func=cmd_competitors)
    
    # report command
    report_parser = subparsers.add_parser('report', help='Generate report')
    report_parser.add_argument('--days', type=int, default=7, help='Report period in days')
    report_parser.set_defaults(func=cmd_report)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    args.func(args)


if __name__ == '__main__':
    main()
