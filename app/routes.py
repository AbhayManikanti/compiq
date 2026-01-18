"""
Flask Routes for Web Dashboard and API
"""
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, send_file
from datetime import datetime, timedelta
import json
import io
import os
from .database import (
    db, Alert, Competitor, MonitoredURL, PageSnapshot, NewsItem, Insight,
    AlertStatus, RiskLevel, SignalType,
    BattleCard, WinLossRecord, CompetitivePlaybook, TrackedAccount, 
    AccountActivity, FeatureComparison
)

# Blueprints
main_bp = Blueprint('main', __name__)
api_bp = Blueprint('api', __name__)


# =============================================================================
# WEB ROUTES
# =============================================================================

@main_bp.route('/')
def dashboard():
    """Main dashboard page."""
    return render_template('dashboard.html')


@main_bp.route('/alerts')
def alerts_list():
    """Alerts list page."""
    return render_template('alerts.html')


@main_bp.route('/alerts/<int:alert_id>')
def alert_detail(alert_id):
    """Alert detail page."""
    alert = Alert.query.get_or_404(alert_id)
    return render_template('alert_detail.html', alert=alert)


@main_bp.route('/competitors')
def competitors_list():
    """Competitors list page."""
    return render_template('competitors.html')


@main_bp.route('/competitors/<int:competitor_id>')
def competitor_detail(competitor_id):
    """Competitor detail page."""
    competitor = Competitor.query.get_or_404(competitor_id)
    return render_template('competitor_detail.html', competitor=competitor)


@main_bp.route('/news')
def news_list():
    """News items page."""
    return render_template('news.html')


@main_bp.route('/insights')
def insights_list():
    """Insights page."""
    return render_template('insights.html')


@main_bp.route('/insights/<int:insight_id>')
def insight_detail(insight_id):
    """Insight detail page."""
    insight = Insight.query.get_or_404(insight_id)
    return render_template('insight_detail.html', insight=insight)


@main_bp.route('/settings')
def settings():
    """Settings page."""
    return render_template('settings.html')


# Battle Cards (Klue-inspired)
@main_bp.route('/battle-cards')
def battle_cards_list():
    """Battle cards list page."""
    return render_template('battle_cards.html')


@main_bp.route('/battle-cards/<int:card_id>')
def battle_card_detail(card_id):
    """Battle card detail page."""
    card = BattleCard.query.get_or_404(card_id)
    return render_template('battle_card_detail.html', card=card)


# Win/Loss Analysis (Crayon-inspired)
@main_bp.route('/win-loss')
def win_loss_list():
    """Win/Loss analysis page."""
    return render_template('win_loss.html')


# Playbooks
@main_bp.route('/playbooks')
def playbooks_list():
    """Competitive playbooks page."""
    return render_template('playbooks.html')


# Account Tracking (ABMForge-inspired)
@main_bp.route('/accounts')
def accounts_list():
    """Tracked accounts page."""
    return render_template('accounts.html')


@main_bp.route('/accounts/<int:account_id>')
def account_detail(account_id):
    """Account detail page."""
    account = TrackedAccount.query.get_or_404(account_id)
    return render_template('account_detail.html', account=account)


# Feature Comparison
@main_bp.route('/features')
def feature_comparison():
    """Feature comparison matrix page."""
    return render_template('feature_comparison.html')


# =============================================================================
# API ROUTES - Dashboard Stats
# =============================================================================

@api_bp.route('/stats')
def get_stats():
    """Get dashboard statistics."""
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    
    # Alert stats
    new_alerts_24h = Alert.query.filter(
        Alert.detected_at >= last_24h,
        Alert.status == AlertStatus.NEW.value
    ).count()
    
    total_alerts = Alert.query.count()
    unresolved_alerts = Alert.query.filter(
        Alert.status.in_([AlertStatus.NEW.value, AlertStatus.ACKNOWLEDGED.value, AlertStatus.IN_PROGRESS.value])
    ).count()
    
    # Risk distribution
    risk_distribution = {}
    for level in RiskLevel:
        count = Alert.query.filter_by(risk_level=level.value).count()
        risk_distribution[level.value] = count
    
    # Signal type distribution
    signal_distribution = {}
    for signal in SignalType:
        count = Alert.query.filter_by(signal_type=signal.value).count()
        if count > 0:
            signal_distribution[signal.value] = count
    
    # Competitor stats
    competitors = Competitor.query.filter_by(is_active=True).all()
    competitor_stats = []
    for comp in competitors:
        alerts_count = Alert.query.filter_by(
            competitor_id=comp.id,
            status=AlertStatus.NEW.value
        ).count()
        competitor_stats.append({
            'id': comp.id,
            'name': comp.name,
            'new_alerts': alerts_count,
            'urls_monitored': comp.monitored_urls.filter_by(is_active=True).count()
        })
    
    # Recent activity
    recent_alerts = Alert.query.order_by(
        Alert.detected_at.desc()
    ).limit(5).all()
    
    return jsonify({
        'summary': {
            'new_alerts_24h': new_alerts_24h,
            'total_alerts': total_alerts,
            'unresolved_alerts': unresolved_alerts,
            'competitors_monitored': len(competitors),
            'urls_monitored': MonitoredURL.query.filter_by(is_active=True).count()
        },
        'risk_distribution': risk_distribution,
        'signal_distribution': signal_distribution,
        'competitor_stats': competitor_stats,
        'recent_alerts': [a.to_dict() for a in recent_alerts]
    })


# =============================================================================
# API ROUTES - Alerts
# =============================================================================

@api_bp.route('/alerts')
def list_alerts():
    """List all alerts with filtering."""
    # Query parameters
    status = request.args.get('status')
    risk_level = request.args.get('risk_level')
    competitor_id = request.args.get('competitor_id', type=int)
    signal_type = request.args.get('signal_type')
    days = request.args.get('days', 30, type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Build query
    query = Alert.query
    
    if status:
        query = query.filter_by(status=status)
    if risk_level:
        query = query.filter_by(risk_level=risk_level)
    if competitor_id:
        query = query.filter_by(competitor_id=competitor_id)
    if signal_type:
        query = query.filter_by(signal_type=signal_type)
    if days:
        since = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Alert.detected_at >= since)
    
    # Order and paginate
    query = query.order_by(Alert.detected_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'alerts': [a.to_dict() for a in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@api_bp.route('/alerts/<int:alert_id>')
def get_alert(alert_id):
    """Get a specific alert."""
    alert = Alert.query.get_or_404(alert_id)
    return jsonify(alert.to_dict())


@api_bp.route('/alerts/<int:alert_id>', methods=['PATCH'])
def update_alert(alert_id):
    """Update an alert's status or assignment."""
    alert = Alert.query.get_or_404(alert_id)
    data = request.get_json()
    
    if 'status' in data:
        old_status = alert.status
        alert.status = data['status']
        
        # Set timestamps based on status
        if data['status'] == AlertStatus.ACKNOWLEDGED.value and old_status == AlertStatus.NEW.value:
            alert.acknowledged_at = datetime.utcnow()
        elif data['status'] == AlertStatus.RESOLVED.value:
            alert.resolved_at = datetime.utcnow()
    
    if 'assigned_to' in data:
        alert.assigned_to = data['assigned_to']
    
    if 'resolution_notes' in data:
        alert.resolution_notes = data['resolution_notes']
    
    db.session.commit()
    return jsonify(alert.to_dict())


@api_bp.route('/alerts/<int:alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    """Acknowledge an alert."""
    alert = Alert.query.get_or_404(alert_id)
    
    if alert.status == AlertStatus.NEW.value:
        alert.status = AlertStatus.ACKNOWLEDGED.value
        alert.acknowledged_at = datetime.utcnow()
        db.session.commit()
    
    return jsonify(alert.to_dict())


@api_bp.route('/alerts/<int:alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    """Resolve an alert."""
    alert = Alert.query.get_or_404(alert_id)
    data = request.get_json() or {}
    
    alert.status = AlertStatus.RESOLVED.value
    alert.resolved_at = datetime.utcnow()
    alert.resolution_notes = data.get('notes', '')
    db.session.commit()
    
    return jsonify(alert.to_dict())


# =============================================================================
# API ROUTES - Competitors
# =============================================================================

@api_bp.route('/competitors')
def list_competitors():
    """List all competitors."""
    competitors = Competitor.query.all()
    return jsonify([c.to_dict() for c in competitors])


@api_bp.route('/competitors', methods=['POST'])
def create_competitor():
    """Create a new competitor."""
    data = request.get_json()
    
    competitor = Competitor(
        name=data['name'],
        description=data.get('description'),
        website=data.get('website'),
        logo_url=data.get('logo_url')
    )
    
    db.session.add(competitor)
    db.session.commit()
    
    return jsonify(competitor.to_dict()), 201


@api_bp.route('/competitors/<int:competitor_id>')
def get_competitor(competitor_id):
    """Get a specific competitor with details."""
    competitor = Competitor.query.get_or_404(competitor_id)
    
    result = competitor.to_dict()
    result['monitored_urls'] = [u.to_dict() for u in competitor.monitored_urls.all()]
    result['recent_alerts'] = [
        a.to_dict() for a in competitor.alerts.order_by(Alert.detected_at.desc()).limit(10).all()
    ]
    
    return jsonify(result)


@api_bp.route('/competitors/<int:competitor_id>', methods=['PATCH'])
def update_competitor(competitor_id):
    """Update a competitor."""
    competitor = Competitor.query.get_or_404(competitor_id)
    data = request.get_json()
    
    if 'name' in data:
        competitor.name = data['name']
    if 'description' in data:
        competitor.description = data['description']
    if 'website' in data:
        competitor.website = data['website']
    if 'logo_url' in data:
        competitor.logo_url = data['logo_url']
    if 'is_active' in data:
        competitor.is_active = data['is_active']
    
    db.session.commit()
    return jsonify(competitor.to_dict())


@api_bp.route('/competitors/<int:competitor_id>', methods=['DELETE'])
def delete_competitor(competitor_id):
    """Delete a competitor (soft delete)."""
    competitor = Competitor.query.get_or_404(competitor_id)
    competitor.is_active = False
    db.session.commit()
    return '', 204


# =============================================================================
# API ROUTES - Monitored URLs
# =============================================================================

@api_bp.route('/urls')
def list_urls():
    """List all monitored URLs."""
    competitor_id = request.args.get('competitor_id', type=int)
    
    query = MonitoredURL.query
    if competitor_id:
        query = query.filter_by(competitor_id=competitor_id)
    
    urls = query.all()
    return jsonify([u.to_dict() for u in urls])


@api_bp.route('/urls', methods=['POST'])
def create_url():
    """Add a new URL to monitor."""
    data = request.get_json()
    
    url = MonitoredURL(
        competitor_id=data['competitor_id'],
        url=data['url'],
        name=data.get('name'),
        page_type=data.get('page_type', 'other'),
        check_interval_hours=data.get('check_interval_hours', 24)
    )
    
    db.session.add(url)
    db.session.commit()
    
    return jsonify(url.to_dict()), 201


@api_bp.route('/urls/<int:url_id>', methods=['PATCH'])
def update_url(url_id):
    """Update a monitored URL."""
    url = MonitoredURL.query.get_or_404(url_id)
    data = request.get_json()
    
    if 'name' in data:
        url.name = data['name']
    if 'page_type' in data:
        url.page_type = data['page_type']
    if 'check_interval_hours' in data:
        url.check_interval_hours = data['check_interval_hours']
    if 'is_active' in data:
        url.is_active = data['is_active']
    
    db.session.commit()
    return jsonify(url.to_dict())


@api_bp.route('/urls/<int:url_id>', methods=['DELETE'])
def delete_url(url_id):
    """Delete a monitored URL."""
    url = MonitoredURL.query.get_or_404(url_id)
    db.session.delete(url)
    db.session.commit()
    return '', 204


# =============================================================================
# API ROUTES - News
# =============================================================================

@api_bp.route('/news')
def list_news():
    """List news items."""
    competitor_id = request.args.get('competitor_id', type=int)
    days = request.args.get('days', 7, type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = NewsItem.query.filter_by(is_relevant=True)  # Only show relevant news
    
    if competitor_id:
        query = query.filter_by(competitor_id=competitor_id)
    
    since = datetime.utcnow() - timedelta(days=days)
    query = query.filter(NewsItem.collected_at >= since)
    
    query = query.order_by(NewsItem.published_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return jsonify({
        'news': [n.to_dict() for n in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@api_bp.route('/news/refresh', methods=['POST'])
def refresh_news():
    """
    Smart news refresh with deduplication and relevance filtering.
    Only fetches new, non-duplicate, relevant news items.
    """
    from .news_collector import NewsCollector
    
    data = request.get_json() or {}
    competitor_id = data.get('competitor_id')
    days_back = data.get('days_back', 3)
    
    collector = NewsCollector()
    results = {
        'fetched': 0,
        'duplicates_skipped': 0,
        'new_items': [],
        'competitors_processed': []
    }
    
    if competitor_id:
        competitors = [Competitor.query.get_or_404(competitor_id)]
    else:
        competitors = Competitor.query.filter_by(is_active=True).all()
    
    for competitor in competitors:
        try:
            items = collector.collect_competitor_news(competitor, days_back)
            results['fetched'] += len(items)
            results['competitors_processed'].append({
                'name': competitor.name,
                'new_items': len(items)
            })
            results['new_items'].extend([{
                'title': item.title,
                'source': item.source,
                'competitor': competitor.name
            } for item in items[:5]])  # Only return first 5 per competitor
        except Exception as e:
            import logging
            logging.error(f"Error refreshing news for {competitor.name}: {e}")
    
    return jsonify({
        'success': True,
        'results': results,
        'message': f"Collected {results['fetched']} new articles from {len(competitors)} competitors"
    })


# =============================================================================
# API ROUTES - Monitor Actions
# =============================================================================

@api_bp.route('/monitor/run', methods=['POST'])
def run_monitor():
    """Trigger a manual monitoring run."""
    from .monitor import PageMonitor
    from .news_collector import NewsCollector
    from .analyzer import Analyzer
    from .alerter import Alerter
    
    data = request.get_json() or {}
    run_pages = data.get('pages', True)
    run_news = data.get('news', True)
    run_analysis = data.get('analyze', True)
    send_alerts = data.get('alert', False)
    
    results = {
        'page_changes': [],
        'news_collected': 0,
        'alerts_created': 0,
        'notifications_sent': 0
    }
    
    try:
        # Run page monitoring
        if run_pages:
            monitor = PageMonitor()
            changes = monitor.check_all_urls(force=True)
            results['page_changes'] = [
                {
                    'url': s.monitored_url.url,
                    'competitor': s.monitored_url.competitor.name
                }
                for s in changes
            ]
        
        # Run news collection
        if run_news:
            collector = NewsCollector()
            news_results = collector.collect_all_news()
            results['news_collected'] = sum(len(items) for items in news_results.values())
        
        # Run analysis
        if run_analysis:
            analyzer = Analyzer()
            analysis_results = analyzer.process_pending_items()
            results['alerts_created'] = analysis_results['alerts_created']
        
        # Send notifications
        if send_alerts:
            alerter = Alerter()
            alert_results = alerter.send_pending_alerts()
            results['notifications_sent'] = alert_results['sent']
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@api_bp.route('/monitor/check-url', methods=['POST'])
def check_single_url():
    """Check a single URL for changes."""
    from .monitor import PageMonitor
    
    data = request.get_json()
    url_id = data.get('url_id')
    
    if not url_id:
        return jsonify({'error': 'url_id required'}), 400
    
    monitored_url = MonitoredURL.query.get_or_404(url_id)
    
    monitor = PageMonitor()
    snapshot = monitor.check_url(monitored_url)
    
    return jsonify({
        'success': True,
        'has_changes': snapshot.has_changes if snapshot else False,
        'snapshot': snapshot.to_dict() if snapshot else None
    })


# =============================================================================
# API ROUTES - Reports
# =============================================================================

@api_bp.route('/reports/summary')
def report_summary():
    """Generate a summary report."""
    days = request.args.get('days', 7, type=int)
    since = datetime.utcnow() - timedelta(days=days)
    
    # Get alerts in period
    alerts = Alert.query.filter(Alert.detected_at >= since).all()
    
    # Group by competitor
    by_competitor = {}
    for alert in alerts:
        comp_name = alert.competitor.name if alert.competitor else 'Unknown'
        if comp_name not in by_competitor:
            by_competitor[comp_name] = []
        by_competitor[comp_name].append(alert.to_dict())
    
    # Group by risk level
    by_risk = {}
    for level in RiskLevel:
        by_risk[level.value] = [a.to_dict() for a in alerts if a.risk_level == level.value]
    
    # Group by signal type
    by_signal = {}
    for alert in alerts:
        if alert.signal_type not in by_signal:
            by_signal[alert.signal_type] = []
        by_signal[alert.signal_type].append(alert.to_dict())
    
    return jsonify({
        'period': {
            'days': days,
            'start': since.isoformat(),
            'end': datetime.utcnow().isoformat()
        },
        'total_alerts': len(alerts),
        'by_competitor': by_competitor,
        'by_risk_level': by_risk,
        'by_signal_type': by_signal
    })


# =============================================================================
# API ROUTES - Insights
# =============================================================================

@api_bp.route('/insights')
def list_insights():
    """List all insights with optional filtering."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    team = request.args.get('team')
    competitor_id = request.args.get('competitor_id', type=int)
    
    query = Insight.query.order_by(Insight.created_at.desc())
    
    if competitor_id:
        query = query.filter_by(competitor_id=competitor_id)
    
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    insights = []
    for insight in pagination.items:
        data = insight.to_dict()
        if team:
            # Include only the requested team's insights
            team_data = insight.get_team_insights(team)
            data['team_insights'] = team_data
        insights.append(data)
    
    return jsonify({
        'insights': insights,
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages,
        'per_page': per_page
    })


@api_bp.route('/insights/<int:insight_id>')
def get_insight(insight_id):
    """Get a specific insight."""
    insight = Insight.query.get_or_404(insight_id)
    return jsonify(insight.to_dict())


@api_bp.route('/insights/<int:insight_id>/team/<team>')
def get_insight_for_team(insight_id, team):
    """Get insight with focus on a specific team."""
    insight = Insight.query.get_or_404(insight_id)
    data = insight.to_dict()
    data['focused_team'] = team
    data['team_insights'] = insight.get_team_insights(team)
    return jsonify(data)


@api_bp.route('/insights/generate', methods=['POST'])
def generate_insight():
    """Generate insight from provided content or news item."""
    from .insights import InsightsGenerator
    
    data = request.get_json()
    
    generator = InsightsGenerator()
    
    if data.get('news_item_id'):
        news_item = NewsItem.query.get_or_404(data['news_item_id'])
        insight = generator.generate_from_news(news_item)
    elif data.get('alert_id'):
        alert = Alert.query.get_or_404(data['alert_id'])
        insight = generator.generate_from_alert(alert)
    elif data.get('content'):
        competitor_id = data.get('competitor_id')
        competitor = Competitor.query.get(competitor_id) if competitor_id else None
        competitor_name = competitor.name if competitor else data.get('competitor_name', 'Unknown')
        
        insight = generator.generate_insight(
            content=data['content'],
            competitor_name=competitor_name,
            source_type=data.get('source_type', 'manual'),
            competitor_id=competitor_id
        )
    else:
        return jsonify({'error': 'Provide news_item_id, alert_id, or content'}), 400
    
    if insight:
        return jsonify({
            'success': True,
            'insight': insight.to_dict()
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to generate insight'
        }), 500


@api_bp.route('/insights/generate-batch', methods=['POST'])
def generate_batch_insights():
    """Generate insights for multiple unprocessed items."""
    from .insights import InsightsGenerator
    
    data = request.get_json() or {}
    limit = data.get('limit', 10)
    
    generator = InsightsGenerator()
    insights = generator.generate_batch_insights(limit=limit)
    
    return jsonify({
        'success': True,
        'count': len(insights),
        'insights': [i.to_dict() for i in insights]
    })


@api_bp.route('/insights/<int:insight_id>/review', methods=['POST'])
def review_insight(insight_id):
    """Mark an insight as reviewed."""
    insight = Insight.query.get_or_404(insight_id)
    data = request.get_json() or {}
    
    insight.is_reviewed = True
    insight.reviewed_by = data.get('reviewed_by', 'Anonymous')
    insight.reviewed_at = datetime.utcnow()
    insight.notes = data.get('notes')
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'insight': insight.to_dict()
    })


@api_bp.route('/insights/summary')
def insights_summary():
    """Get summary of insights for dashboard."""
    total = Insight.query.count()
    unreviewed = Insight.query.filter_by(is_reviewed=False).count()
    
    # Recent high-impact insights
    high_impact = Insight.query.filter(
        Insight.impact_score >= 70
    ).order_by(Insight.created_at.desc()).limit(5).all()
    
    # Insights by urgency
    urgent = Insight.query.filter(Insight.urgency_score >= 70).count()
    
    return jsonify({
        'total': total,
        'unreviewed': unreviewed,
        'urgent': urgent,
        'high_impact_recent': [i.to_dict() for i in high_impact]
    })


# =============================================================================
# API ROUTES - Export (PDF/CSV)
# =============================================================================

@api_bp.route('/export/insight/<int:insight_id>/pdf')
def export_insight_pdf(insight_id):
    """Export an insight as PDF."""
    from .exporter import ReportExporter
    
    insight = Insight.query.get_or_404(insight_id)
    exporter = ReportExporter()
    
    pdf_buffer = exporter.export_insight_pdf(insight)
    
    filename = f"insight_{insight_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@api_bp.route('/export/alert/<int:alert_id>/pdf')
def export_alert_pdf(alert_id):
    """Export an alert as PDF."""
    from .exporter import ReportExporter
    
    alert = Alert.query.get_or_404(alert_id)
    exporter = ReportExporter()
    
    pdf_buffer = exporter.export_alert_pdf(alert)
    
    filename = f"alert_{alert_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@api_bp.route('/export/alerts/pdf')
def export_alerts_summary_pdf():
    """Export alerts summary as PDF."""
    from .exporter import ReportExporter
    
    # Get filters
    days = request.args.get('days', 7, type=int)
    risk_level = request.args.get('risk_level')
    competitor_id = request.args.get('competitor_id', type=int)
    
    query = Alert.query
    
    if days:
        since = datetime.utcnow() - timedelta(days=days)
        query = query.filter(Alert.detected_at >= since)
    
    if risk_level:
        query = query.filter_by(risk_level=risk_level)
    
    if competitor_id:
        query = query.filter_by(competitor_id=competitor_id)
    
    alerts = query.order_by(Alert.detected_at.desc()).all()
    
    exporter = ReportExporter()
    pdf_buffer = exporter.export_alerts_summary_pdf(alerts, f"Alerts Report - Last {days} Days")
    
    filename = f"alerts_summary_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )


@api_bp.route('/export/alerts/csv')
def export_alerts_csv():
    """Export alerts as CSV."""
    from .exporter import ReportExporter
    
    days = request.args.get('days', 30, type=int)
    since = datetime.utcnow() - timedelta(days=days)
    
    alerts = Alert.query.filter(Alert.detected_at >= since).order_by(Alert.detected_at.desc()).all()
    
    data = []
    for alert in alerts:
        data.append({
            'id': alert.id,
            'title': alert.title,
            'competitor': alert.competitor.name if alert.competitor else 'Unknown',
            'risk_level': alert.risk_level,
            'signal_type': alert.signal_type,
            'risk_score': alert.risk_score,
            'summary': alert.summary,
            'source_url': alert.source_url,
            'status': alert.status,
            'detected_at': alert.detected_at.isoformat() if alert.detected_at else ''
        })
    
    exporter = ReportExporter()
    csv_buffer = exporter.export_csv(data)
    
    filename = f"alerts_export_{datetime.now().strftime('%Y%m%d')}.csv"
    return send_file(
        io.BytesIO(csv_buffer.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@api_bp.route('/export/news/csv')
def export_news_csv():
    """Export news items as CSV."""
    from .exporter import ReportExporter
    
    days = request.args.get('days', 30, type=int)
    since = datetime.utcnow() - timedelta(days=days)
    
    news_items = NewsItem.query.filter(NewsItem.collected_at >= since).order_by(NewsItem.collected_at.desc()).all()
    
    data = []
    for item in news_items:
        data.append({
            'id': item.id,
            'title': item.title,
            'source': item.source,
            'url': item.url,
            'published_at': item.published_at.isoformat() if item.published_at else '',
            'collected_at': item.collected_at.isoformat() if item.collected_at else '',
            'is_processed': item.is_processed,
            'is_relevant': item.is_relevant
        })
    
    exporter = ReportExporter()
    csv_buffer = exporter.export_csv(data)
    
    filename = f"news_export_{datetime.now().strftime('%Y%m%d')}.csv"
    return send_file(
        io.BytesIO(csv_buffer.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@api_bp.route('/export/features/csv')
def export_features_csv():
    """Export feature comparison matrix as CSV."""
    from .exporter import ReportExporter
    
    features = FeatureComparison.query.order_by(FeatureComparison.category, FeatureComparison.feature_name).all()
    competitors = Competitor.query.filter_by(is_active=True).order_by(Competitor.name).all()
    
    data = []
    for f in features:
        row = {
            'category': f.category,
            'feature': f.feature_name,
            'description': f.description or '',
            'importance': f.customer_importance,
            'our_capability': f.our_capability or '',
            'our_details': f.our_details or ''
        }
        # Add competitor columns
        comp_caps = json.loads(f.competitor_capabilities) if f.competitor_capabilities else {}
        for c in competitors:
            cap_data = comp_caps.get(str(c.id), {})
            row[f'{c.name}_capability'] = cap_data.get('capability', '')
            row[f'{c.name}_details'] = cap_data.get('details', '')
        data.append(row)
    
    exporter = ReportExporter()
    csv_buffer = exporter.export_csv(data)
    
    filename = f"feature_matrix_{datetime.now().strftime('%Y%m%d')}.csv"
    return send_file(
        io.BytesIO(csv_buffer.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


# =============================================================================
# INTEGRATIONS API
# =============================================================================

@api_bp.route('/integrations/changedetection/status')
def changedetection_status():
    """Get changedetection.io connection status."""
    from .integrations import ChangeDetectionIntegration
    import os
    
    cd_url = os.environ.get('CHANGEDETECTION_URL', '')
    if not cd_url:
        return jsonify({
            'configured': False,
            'message': 'CHANGEDETECTION_URL not configured'
        })
    
    try:
        integration = ChangeDetectionIntegration(cd_url, os.environ.get('CHANGEDETECTION_API_KEY'))
        watches = integration.get_watches()
        return jsonify({
            'configured': True,
            'connected': True,
            'watch_count': len(watches),
            'url': cd_url
        })
    except Exception as e:
        return jsonify({
            'configured': True,
            'connected': False,
            'error': str(e)
        })


@api_bp.route('/integrations/changedetection/watches')
def changedetection_watches():
    """Get all watches from changedetection.io."""
    from .integrations import ChangeDetectionIntegration
    import os
    
    cd_url = os.environ.get('CHANGEDETECTION_URL')
    if not cd_url:
        return jsonify({'error': 'CHANGEDETECTION_URL not configured'}), 400
    
    try:
        integration = ChangeDetectionIntegration(cd_url, os.environ.get('CHANGEDETECTION_API_KEY'))
        watches = integration.get_watches()
        return jsonify({'watches': watches})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/integrations/changedetection/add', methods=['POST'])
def changedetection_add_watch():
    """Add a new watch to changedetection.io."""
    from .integrations import ChangeDetectionIntegration
    import os
    
    cd_url = os.environ.get('CHANGEDETECTION_URL')
    if not cd_url:
        return jsonify({'error': 'CHANGEDETECTION_URL not configured'}), 400
    
    data = request.get_json()
    url = data.get('url')
    tag = data.get('tag', 'competitor-monitor')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    try:
        integration = ChangeDetectionIntegration(cd_url, os.environ.get('CHANGEDETECTION_API_KEY'))
        result = integration.add_watch(url, tag)
        return jsonify({'success': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/integrations/changedetection/sync', methods=['POST'])
def changedetection_sync():
    """Sync monitored URLs with changedetection.io and import changes."""
    from .integrations import ChangeDetectionIntegration
    import os
    
    cd_url = os.environ.get('CHANGEDETECTION_URL')
    if not cd_url:
        return jsonify({'error': 'CHANGEDETECTION_URL not configured'}), 400
    
    try:
        integration = ChangeDetectionIntegration(cd_url, os.environ.get('CHANGEDETECTION_API_KEY'))
        
        # Sync our URLs to changedetection
        urls = MonitoredURL.query.filter_by(is_active=True).all()
        url_list = [(u.url, u.competitor.name if u.competitor else 'general') for u in urls]
        sync_result = integration.sync_with_monitored_urls(url_list)
        
        # Import any detected changes
        import_result = integration.import_changes()
        
        return jsonify({
            'success': True,
            'synced': sync_result,
            'imported_changes': import_result
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/integrations/google-alerts/status')
def google_alerts_status():
    """Get Google Alerts configuration status."""
    from .integrations import GoogleAlertsIntegration
    import os
    import yaml
    
    # Check for configured alert keywords in competitors.yaml
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'competitors.yaml')
    
    configured_alerts = []
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        for comp in config.get('competitors', []):
            for keyword in comp.get('keywords', []):
                configured_alerts.append({
                    'competitor': comp['name'],
                    'keyword': keyword
                })
    
    return jsonify({
        'configured': len(configured_alerts) > 0,
        'alert_count': len(configured_alerts),
        'alerts': configured_alerts
    })


@api_bp.route('/integrations/google-alerts/sync', methods=['POST'])
def google_alerts_sync():
    """Fetch and process Google Alerts."""
    from .integrations import GoogleAlertsIntegration
    import os
    import yaml
    
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'competitors.yaml')
    
    if not os.path.exists(config_path):
        return jsonify({'error': 'competitors.yaml not found'}), 400
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    integration = GoogleAlertsIntegration()
    all_alerts = []
    
    for comp_config in config.get('competitors', []):
        competitor = Competitor.query.filter_by(name=comp_config['name']).first()
        if not competitor:
            continue
        
        for keyword in comp_config.get('keywords', []):
            alerts = integration.fetch_alerts(keyword)
            for alert in alerts:
                alert['competitor_id'] = competitor.id
                alert['competitor_name'] = competitor.name
            all_alerts.extend(alerts)
    
    # Process alerts into news items (deduplication handled by news collector)
    processed = 0
    for alert in all_alerts:
        # Check if already exists
        existing = NewsItem.query.filter_by(url=alert['url']).first()
        if not existing:
            news_item = NewsItem(
                competitor_id=alert.get('competitor_id'),
                source='google_alerts',
                title=alert['title'],
                url=alert['url'],
                published_at=alert.get('published_at'),
                collected_at=datetime.utcnow(),
                is_processed=False,
                is_relevant=True
            )
            db.session.add(news_item)
            processed += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'fetched': len(all_alerts),
        'new_items': processed
    })


@main_bp.route('/integrations')
def integrations_page():
    """Integrations management page."""
    return render_template('integrations.html')


# =============================================================================
# MICROSOFT TEAMS INTEGRATION API
# =============================================================================

@api_bp.route('/integrations/teams/status')
def teams_status():
    """Get Microsoft Teams webhook configuration status."""
    webhook_url = os.environ.get('TEAMS_WEBHOOK_URL', '')
    
    return jsonify({
        'configured': bool(webhook_url),
        'webhook_url': webhook_url[:50] + '...' if len(webhook_url) > 50 else webhook_url
    })


@api_bp.route('/integrations/teams/configure', methods=['POST'])
def teams_configure():
    """Configure Microsoft Teams webhook URL."""
    data = request.get_json()
    webhook_url = data.get('webhook_url', '').strip()
    
    if not webhook_url:
        return jsonify({'success': False, 'error': 'Webhook URL is required'}), 400
    
    # Validate it looks like a Teams webhook or Power Automate webhook
    valid_domains = ['webhook.office.com', 'logic.azure.com', 'powerplatform.com', 'flow.microsoft.com']
    if not any(domain in webhook_url for domain in valid_domains):
        return jsonify({'success': False, 'error': 'Invalid webhook URL format. Must be Teams or Power Automate webhook.'}), 400
    
    # Store in environment (in production, this would go to a config store)
    os.environ['TEAMS_WEBHOOK_URL'] = webhook_url
    
    return jsonify({'success': True, 'message': 'Webhook configured successfully'})


@api_bp.route('/integrations/teams/test', methods=['POST'])
def teams_test():
    """Send a test message to Microsoft Teams or Power Automate."""
    import requests
    
    webhook_url = os.environ.get('TEAMS_WEBHOOK_URL', '')
    
    if not webhook_url:
        return jsonify({'success': False, 'error': 'Webhook not configured'}), 400
    
    # Check if it's a Power Automate webhook (Teams webhook trigger)
    is_power_automate = 'powerplatform.com' in webhook_url or 'flow.microsoft.com' in webhook_url
    
    if is_power_automate:
        # Power Automate with Teams webhook trigger expects Adaptive Card format
        # The flow extracts "body" and posts it as an Adaptive Card
        adaptive_card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "🔔 CompIQ Test Notification",
                    "weight": "Bolder",
                    "size": "Large",
                    "color": "Accent"
                },
                {
                    "type": "TextBlock",
                    "text": "This is a test message from CompIQ Competitive Intelligence",
                    "wrap": True
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Status", "value": "✅ Connected Successfully"},
                        {"title": "Time", "value": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
                    ]
                }
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "Open CompIQ",
                    "url": "https://compiq-app.azurewebsites.net"
                }
            ]
        }
        
        # Send as the body content that the flow expects
        message = {
            "body": {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": adaptive_card
            }
        }
    else:
        # Standard Teams Incoming Webhook (MessageCard format)
        message = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "0076D7",
            "summary": "CompIQ Test Alert",
            "sections": [{
                "activityTitle": "🔔 CompIQ Test Notification",
                "activitySubtitle": "This is a test message from CompIQ Competitive Intelligence",
                "facts": [{
                    "name": "Status",
                    "value": "Connected Successfully"
                }, {
                    "name": "Time",
                    "value": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                }],
                "markdown": True
            }]
        }
    
    try:
        response = requests.post(webhook_url, json=message, timeout=15)
        # Power Automate returns 202 Accepted, Teams returns 200 OK
        if response.status_code in [200, 202]:
            return jsonify({'success': True, 'message': 'Test message sent successfully!'})
        else:
            return jsonify({'success': False, 'error': f'Webhook returned status {response.status_code}: {response.text[:200]}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api_bp.route('/integrations/teams/send-alert', methods=['POST'])
def teams_send_alert():
    """Send an alert notification to Microsoft Teams or Power Automate."""
    import requests
    
    webhook_url = os.environ.get('TEAMS_WEBHOOK_URL', '')
    
    if not webhook_url:
        return jsonify({'success': False, 'error': 'Webhook not configured'}), 400
    
    data = request.get_json()
    alert_id = data.get('alert_id')
    
    if alert_id:
        alert = Alert.query.get_or_404(alert_id)
        title = alert.title
        summary = alert.summary
        risk_level = alert.risk_level
        competitor = alert.competitor.name if alert.competitor else 'Unknown'
        source_url = alert.source_url
    else:
        title = data.get('title', 'New Alert')
        summary = data.get('summary', '')
        risk_level = data.get('risk_level', 'medium')
        competitor = data.get('competitor', 'Unknown')
        source_url = data.get('source_url', '')
    
    # Check if it's a Power Automate webhook
    is_power_automate = 'powerplatform.com' in webhook_url or 'flow.microsoft.com' in webhook_url
    
    # Risk level colors and emojis
    risk_colors = {
        'critical': 'Attention',
        'high': 'Warning', 
        'medium': 'Accent',
        'low': 'Good'
    }
    risk_emojis = {
        'critical': '🔴',
        'high': '🟠', 
        'medium': '🟡',
        'low': '🟢'
    }
    
    if is_power_automate:
        # Power Automate with Teams webhook - send Adaptive Card
        adaptive_card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": f"🚨 {title}",
                    "weight": "Bolder",
                    "size": "Large",
                    "wrap": True
                },
                {
                    "type": "FactSet",
                    "facts": [
                        {"title": "Competitor", "value": competitor},
                        {"title": "Risk Level", "value": f"{risk_emojis.get(risk_level, '⚪')} {risk_level.upper()}"},
                        {"title": "Time", "value": datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
                    ]
                },
                {
                    "type": "TextBlock",
                    "text": summary[:300] if summary else 'No details available',
                    "wrap": True,
                    "spacing": "Medium"
                }
            ],
            "actions": [
                {
                    "type": "Action.OpenUrl",
                    "title": "View in CompIQ",
                    "url": f"https://compiq-app.azurewebsites.net/alerts/{alert_id}" if alert_id else "https://compiq-app.azurewebsites.net/alerts"
                }
            ]
        }
        
        if source_url:
            adaptive_card["actions"].append({
                "type": "Action.OpenUrl",
                "title": "View Source",
                "url": source_url
            })
        
        message = {
            "body": {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": adaptive_card
            }
        }
    else:
        # Standard Teams Incoming Webhook (MessageCard format)
        colors = {
            'critical': 'FF0000',
            'high': 'FFA500', 
            'medium': 'FFFF00',
            'low': '00FF00'
        }
        
        message = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": colors.get(risk_level, '0076D7'),
            "summary": f"CompIQ Alert: {title}",
            "sections": [{
                "activityTitle": f"🚨 {title}",
                "activitySubtitle": f"Competitor: {competitor}",
                "facts": [{
                    "name": "Risk Level",
                    "value": risk_level.upper()
                }, {
                    "name": "Summary",
                    "value": summary[:200] if summary else 'No details'
                }],
                "markdown": True
            }],
            "potentialAction": [{
                "@type": "OpenUri",
                "name": "View in CompIQ",
                "targets": [{
                    "os": "default",
                    "uri": f"https://compiq-app.azurewebsites.net/alerts/{alert_id}" if alert_id else "https://compiq-app.azurewebsites.net/alerts"
                }]
            }]
        }
        
        if source_url:
            message["potentialAction"].append({
                "@type": "OpenUri",
                "name": "View Source",
                "targets": [{"os": "default", "uri": source_url}]
            })
    
    try:
        response = requests.post(webhook_url, json=message, timeout=15)
        # Power Automate returns 202 Accepted, Teams returns 200 OK
        if response.status_code in [200, 202]:
            # Mark alert as sent to Teams
            if alert_id:
                alert.notification_sent = True
                channels = alert.notification_channels or ''
                if 'teams' not in channels:
                    alert.notification_channels = (channels + ',teams').strip(',')
                db.session.commit()
            return jsonify({'success': True, 'message': 'Alert sent successfully!'})
        else:
            return jsonify({'success': False, 'error': f'Webhook returned status {response.status_code}: {response.text[:200]}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def send_alert_to_teams(alert: Alert) -> bool:
    """
    Internal helper function to send an alert to Teams.
    Returns True if sent successfully, False otherwise.
    """
    import requests as req
    
    webhook_url = os.environ.get('TEAMS_WEBHOOK_URL', '')
    
    if not webhook_url:
        return False
    
    # Check if already sent to Teams
    channels = alert.notification_channels or ''
    if 'teams' in channels:
        return True  # Already sent
    
    title = alert.title
    summary = alert.summary
    risk_level = alert.risk_level or 'medium'
    competitor = alert.competitor.name if alert.competitor else 'Unknown'
    source_url = alert.source_url
    alert_id = alert.id
    detected_at = alert.detected_at.strftime('%Y-%m-%d %H:%M UTC') if alert.detected_at else 'Unknown'
    
    # Risk level emojis
    risk_emojis = {
        'critical': '🔴',
        'high': '🟠', 
        'medium': '🟡',
        'low': '🟢',
        'info': 'ℹ️'
    }
    
    # Build Adaptive Card for Power Automate
    adaptive_card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": [
            {
                "type": "TextBlock",
                "text": f"🚨 {title}",
                "weight": "Bolder",
                "size": "Large",
                "wrap": True
            },
            {
                "type": "FactSet",
                "facts": [
                    {"title": "Competitor", "value": competitor},
                    {"title": "Risk Level", "value": f"{risk_emojis.get(risk_level, '⚪')} {risk_level.upper()}"},
                    {"title": "Detected", "value": detected_at}
                ]
            },
            {
                "type": "TextBlock",
                "text": summary[:300] if summary else 'No details available',
                "wrap": True,
                "spacing": "Medium"
            }
        ],
        "actions": [
            {
                "type": "Action.OpenUrl",
                "title": "View in CompIQ",
                "url": f"https://compiq-app.azurewebsites.net/alerts/{alert_id}"
            }
        ]
    }
    
    if source_url:
        adaptive_card["actions"].append({
            "type": "Action.OpenUrl",
            "title": "View Source",
            "url": source_url
        })
    
    # Power Automate expects this structure
    message = {
        "body": {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": adaptive_card
        }
    }
    
    try:
        response = req.post(webhook_url, json=message, timeout=15)
        if response.status_code in [200, 202]:
            # Mark as sent
            alert.notification_sent = True
            channels = alert.notification_channels or ''
            if 'teams' not in channels:
                alert.notification_channels = (channels + ',teams').strip(',')
            db.session.commit()
            return True
        return False
    except Exception as e:
        logging.getLogger(__name__).error(f"Error sending alert {alert_id} to Teams: {e}")
        return False


@api_bp.route('/integrations/teams/sync-all', methods=['POST'])
def teams_sync_all():
    """Send all alerts that haven't been sent to Teams yet."""
    import requests as req
    
    webhook_url = os.environ.get('TEAMS_WEBHOOK_URL', '')
    
    if not webhook_url:
        return jsonify({'success': False, 'error': 'Webhook not configured'}), 400
    
    # Get all alerts that haven't been sent to Teams
    all_alerts = Alert.query.order_by(Alert.detected_at.asc()).all()
    
    sent_count = 0
    skipped_count = 0
    failed_count = 0
    
    for alert in all_alerts:
        # Check if already sent to Teams
        channels = alert.notification_channels or ''
        if 'teams' in channels:
            skipped_count += 1
            continue
        
        # Send to Teams
        if send_alert_to_teams(alert):
            sent_count += 1
            # Small delay to avoid rate limiting
            import time
            time.sleep(0.5)
        else:
            failed_count += 1
    
    return jsonify({
        'success': True,
        'sent': sent_count,
        'skipped': skipped_count,
        'failed': failed_count,
        'message': f'Sent {sent_count} alerts to Teams ({skipped_count} already sent, {failed_count} failed)'
    })


@api_bp.route('/integrations/teams/stats')
def teams_stats():
    """Get Teams notification statistics."""
    total_alerts = Alert.query.count()
    
    # Count alerts sent to Teams
    sent_to_teams = Alert.query.filter(
        Alert.notification_channels.like('%teams%')
    ).count()
    
    not_sent = total_alerts - sent_to_teams
    
    return jsonify({
        'total_alerts': total_alerts,
        'sent_to_teams': sent_to_teams,
        'not_sent': not_sent,
        'webhook_configured': bool(os.environ.get('TEAMS_WEBHOOK_URL', ''))
    })


# =============================================================================
# BATTLE CARDS API (Klue-inspired)
# =============================================================================

@api_bp.route('/battle-cards')
def get_battle_cards():
    """Get all battle cards."""
    competitor_id = request.args.get('competitor_id', type=int)
    status = request.args.get('status')
    
    query = BattleCard.query
    if competitor_id:
        query = query.filter_by(competitor_id=competitor_id)
    if status:
        query = query.filter_by(status=status)
    
    cards = query.order_by(BattleCard.updated_at.desc()).all()
    return jsonify([card.to_dict() for card in cards])


@api_bp.route('/battle-cards/<int:card_id>')
def get_battle_card(card_id):
    """Get a specific battle card."""
    card = BattleCard.query.get_or_404(card_id)
    return jsonify(card.to_dict())


@api_bp.route('/battle-cards', methods=['POST'])
def create_battle_card():
    """Create a new battle card."""
    data = request.get_json()
    
    card = BattleCard(
        competitor_id=data['competitor_id'],
        name=data['name'],
        elevator_pitch=data.get('elevator_pitch'),
        target_segment=data.get('target_segment'),
        our_strengths=json.dumps(data.get('our_strengths', [])),
        our_weaknesses=json.dumps(data.get('our_weaknesses', [])),
        competitor_strengths=json.dumps(data.get('competitor_strengths', [])),
        competitor_weaknesses=json.dumps(data.get('competitor_weaknesses', [])),
        key_differentiators=json.dumps(data.get('key_differentiators', [])),
        trap_questions=json.dumps(data.get('trap_questions', [])),
        landmine_questions=json.dumps(data.get('landmine_questions', [])),
        common_objections=json.dumps(data.get('common_objections', [])),
        pricing_comparison=json.dumps(data.get('pricing_comparison', {})),
        feature_comparison=json.dumps(data.get('feature_comparison', {})),
        status='draft'
    )
    
    db.session.add(card)
    db.session.commit()
    
    return jsonify(card.to_dict()), 201


@api_bp.route('/battle-cards/<int:card_id>', methods=['PUT'])
def update_battle_card(card_id):
    """Update a battle card."""
    card = BattleCard.query.get_or_404(card_id)
    data = request.get_json()
    
    if 'name' in data:
        card.name = data['name']
    if 'elevator_pitch' in data:
        card.elevator_pitch = data['elevator_pitch']
    if 'target_segment' in data:
        card.target_segment = data['target_segment']
    if 'our_strengths' in data:
        card.our_strengths = json.dumps(data['our_strengths'])
    if 'our_weaknesses' in data:
        card.our_weaknesses = json.dumps(data['our_weaknesses'])
    if 'competitor_strengths' in data:
        card.competitor_strengths = json.dumps(data['competitor_strengths'])
    if 'competitor_weaknesses' in data:
        card.competitor_weaknesses = json.dumps(data['competitor_weaknesses'])
    if 'key_differentiators' in data:
        card.key_differentiators = json.dumps(data['key_differentiators'])
    if 'trap_questions' in data:
        card.trap_questions = json.dumps(data['trap_questions'])
    if 'landmine_questions' in data:
        card.landmine_questions = json.dumps(data['landmine_questions'])
    if 'common_objections' in data:
        card.common_objections = json.dumps(data['common_objections'])
    if 'pricing_comparison' in data:
        card.pricing_comparison = json.dumps(data['pricing_comparison'])
    if 'feature_comparison' in data:
        card.feature_comparison = json.dumps(data['feature_comparison'])
    if 'status' in data:
        card.status = data['status']
    
    db.session.commit()
    return jsonify(card.to_dict())


@api_bp.route('/battle-cards/<int:card_id>/generate', methods=['POST'])
def generate_battle_card(card_id):
    """Use AI to generate/enhance battle card content."""
    card = BattleCard.query.get_or_404(card_id)
    
    # Get recent insights and alerts for this competitor
    recent_alerts = Alert.query.filter_by(competitor_id=card.competitor_id).order_by(Alert.detected_at.desc()).limit(10).all()
    recent_insights = Insight.query.filter_by(competitor_id=card.competitor_id).order_by(Insight.created_at.desc()).limit(5).all()
    
    from .llm_analyzer import LLMAnalyzer
    analyzer = LLMAnalyzer()
    
    # Build context for AI
    context = f"""
    Competitor: {card.competitor.name}
    
    Recent Alerts:
    {chr(10).join([f"- {a.title}: {a.summary}" for a in recent_alerts])}
    
    Recent Insights:
    {chr(10).join([f"- {i.title}: {i.executive_summary}" for i in recent_insights])}
    """
    
    prompt = f"""Based on this competitive intelligence, generate battle card content for sales teams.
    
    {context}
    
    Generate:
    1. A compelling elevator pitch positioning against {card.competitor.name}
    2. 3-5 key differentiators (our advantages)
    3. 3-5 trap questions to ask prospects that highlight competitor weaknesses
    4. 3-5 landmine questions prospects might ask (with suggested responses)
    5. 3-5 common objections and responses
    
    Return as JSON with keys: elevator_pitch, key_differentiators, trap_questions, landmine_questions, objections
    """
    
    try:
        result = analyzer._call_llm(prompt)
        generated = json.loads(result)
        
        # Update card with generated content
        if generated.get('elevator_pitch'):
            card.elevator_pitch = generated['elevator_pitch']
        if generated.get('key_differentiators'):
            card.key_differentiators = json.dumps(generated['key_differentiators'])
        if generated.get('trap_questions'):
            card.trap_questions = json.dumps(generated['trap_questions'])
        if generated.get('landmine_questions'):
            card.landmine_questions = json.dumps(generated['landmine_questions'])
        if generated.get('objections'):
            card.common_objections = json.dumps(generated['objections'])
        
        db.session.commit()
        return jsonify({'success': True, 'card': card.to_dict()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# WIN/LOSS ANALYSIS API (Crayon-inspired)
# =============================================================================

@api_bp.route('/win-loss')
def get_win_loss_records():
    """Get win/loss records with optional filters."""
    competitor_id = request.args.get('competitor_id', type=int)
    outcome = request.args.get('outcome')
    days = request.args.get('days', 90, type=int)
    
    since = datetime.utcnow() - timedelta(days=days)
    query = WinLossRecord.query.filter(WinLossRecord.outcome_date >= since)
    
    if competitor_id:
        query = query.filter_by(competitor_id=competitor_id)
    if outcome:
        query = query.filter_by(outcome=outcome)
    
    records = query.order_by(WinLossRecord.outcome_date.desc()).all()
    return jsonify([r.to_dict() for r in records])


@api_bp.route('/win-loss/stats')
def get_win_loss_stats():
    """Get win/loss statistics."""
    competitor_id = request.args.get('competitor_id', type=int)
    days = request.args.get('days', 90, type=int)
    
    since = datetime.utcnow() - timedelta(days=days)
    query = WinLossRecord.query.filter(WinLossRecord.outcome_date >= since)
    
    if competitor_id:
        query = query.filter_by(competitor_id=competitor_id)
    
    records = query.all()
    
    wins = sum(1 for r in records if r.outcome == 'won')
    losses = sum(1 for r in records if r.outcome == 'lost')
    no_decision = sum(1 for r in records if r.outcome == 'no_decision')
    
    total_won_value = sum(r.deal_value or 0 for r in records if r.outcome == 'won')
    total_lost_value = sum(r.deal_value or 0 for r in records if r.outcome == 'lost')
    
    # Loss reasons breakdown
    loss_reasons = {}
    for r in records:
        if r.outcome == 'lost' and r.primary_loss_reason:
            loss_reasons[r.primary_loss_reason] = loss_reasons.get(r.primary_loss_reason, 0) + 1
    
    return jsonify({
        'total_records': len(records),
        'wins': wins,
        'losses': losses,
        'no_decision': no_decision,
        'win_rate': round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0,
        'total_won_value': total_won_value,
        'total_lost_value': total_lost_value,
        'loss_reasons': loss_reasons
    })


@api_bp.route('/win-loss', methods=['POST'])
def create_win_loss_record():
    """Create a new win/loss record."""
    data = request.get_json()
    
    record = WinLossRecord(
        competitor_id=data.get('competitor_id'),
        deal_name=data.get('deal_name'),
        deal_value=data.get('deal_value'),
        outcome=data['outcome'],
        outcome_date=datetime.fromisoformat(data['outcome_date']) if data.get('outcome_date') else datetime.utcnow(),
        customer_name=data.get('customer_name'),
        customer_industry=data.get('customer_industry'),
        customer_size=data.get('customer_size'),
        customer_region=data.get('customer_region'),
        primary_loss_reason=data.get('primary_loss_reason'),
        loss_reasons=json.dumps(data.get('loss_reasons', [])),
        win_reasons=json.dumps(data.get('win_reasons', [])),
        competitor_positioning=data.get('competitor_positioning'),
        key_learnings=data.get('key_learnings'),
        sales_rep=data.get('sales_rep')
    )
    
    db.session.add(record)
    db.session.commit()
    
    return jsonify(record.to_dict()), 201


# =============================================================================
# COMPETITIVE PLAYBOOKS API
# =============================================================================

@api_bp.route('/playbooks')
def get_playbooks():
    """Get all active playbooks."""
    active_only = request.args.get('active', 'true').lower() == 'true'
    
    query = CompetitivePlaybook.query
    if active_only:
        query = query.filter_by(is_active=True)
    
    playbooks = query.order_by(CompetitivePlaybook.priority.desc()).all()
    return jsonify([p.to_dict() for p in playbooks])


@api_bp.route('/playbooks/<int:playbook_id>')
def get_playbook(playbook_id):
    """Get a specific playbook."""
    playbook = CompetitivePlaybook.query.get_or_404(playbook_id)
    return jsonify(playbook.to_dict())


@api_bp.route('/playbooks', methods=['POST'])
def create_playbook():
    """Create a new playbook."""
    data = request.get_json()
    
    playbook = CompetitivePlaybook(
        name=data['name'],
        slug=data.get('slug', data['name'].lower().replace(' ', '_')),
        description=data.get('description'),
        trigger_signal_types=json.dumps(data.get('trigger_signal_types', [])),
        trigger_keywords=json.dumps(data.get('trigger_keywords', [])),
        sales_actions=json.dumps(data.get('sales_actions', [])),
        marketing_actions=json.dumps(data.get('marketing_actions', [])),
        product_actions=json.dumps(data.get('product_actions', [])),
        executive_actions=json.dumps(data.get('executive_actions', [])),
        email_templates=json.dumps(data.get('email_templates', [])),
        talk_tracks=json.dumps(data.get('talk_tracks', [])),
        priority=data.get('priority', 5)
    )
    
    db.session.add(playbook)
    db.session.commit()
    
    return jsonify(playbook.to_dict()), 201


# =============================================================================
# TRACKED ACCOUNTS API (ABMForge-inspired)
# =============================================================================

@api_bp.route('/accounts')
def get_tracked_accounts():
    """Get tracked accounts."""
    tier = request.args.get('tier')
    stage = request.args.get('stage')
    competitor_id = request.args.get('competitor_id', type=int)
    
    query = TrackedAccount.query
    if tier:
        query = query.filter_by(account_tier=tier)
    if stage:
        query = query.filter_by(deal_stage=stage)
    if competitor_id:
        query = query.filter_by(incumbent_competitor_id=competitor_id)
    
    accounts = query.order_by(TrackedAccount.deal_value.desc().nullslast()).all()
    return jsonify([a.to_dict() for a in accounts])


@api_bp.route('/accounts/<int:account_id>')
def get_tracked_account(account_id):
    """Get a specific account."""
    account = TrackedAccount.query.get_or_404(account_id)
    return jsonify(account.to_dict())


@api_bp.route('/accounts', methods=['POST'])
def create_tracked_account():
    """Create a new tracked account."""
    data = request.get_json()
    
    account = TrackedAccount(
        account_name=data['account_name'],
        website=data.get('website'),
        industry=data.get('industry'),
        size=data.get('size'),
        region=data.get('region'),
        account_tier=data.get('account_tier', 'standard'),
        deal_stage=data.get('deal_stage'),
        deal_value=data.get('deal_value'),
        account_owner=data.get('account_owner'),
        incumbent_competitor_id=data.get('incumbent_competitor_id'),
        competing_vendors=json.dumps(data.get('competing_vendors', [])),
        competitive_status=data.get('competitive_status'),
        tech_stack=json.dumps(data.get('tech_stack', [])),
        notes=data.get('notes')
    )
    
    db.session.add(account)
    db.session.commit()
    
    return jsonify(account.to_dict()), 201


@api_bp.route('/accounts/<int:account_id>', methods=['PUT'])
def update_tracked_account(account_id):
    """Update a tracked account."""
    account = TrackedAccount.query.get_or_404(account_id)
    data = request.get_json()
    
    for field in ['account_name', 'website', 'industry', 'size', 'region', 
                  'account_tier', 'deal_stage', 'deal_value', 'account_owner',
                  'incumbent_competitor_id', 'competitive_status', 'notes',
                  'next_action', 'next_action_date']:
        if field in data:
            if field == 'next_action_date' and data[field]:
                setattr(account, field, datetime.fromisoformat(data[field]))
            else:
                setattr(account, field, data[field])
    
    if 'competing_vendors' in data:
        account.competing_vendors = json.dumps(data['competing_vendors'])
    if 'tech_stack' in data:
        account.tech_stack = json.dumps(data['tech_stack'])
    
    account.last_activity_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(account.to_dict())


@api_bp.route('/accounts/<int:account_id>/activities')
def get_account_activities(account_id):
    """Get activities for an account."""
    account = TrackedAccount.query.get_or_404(account_id)
    activities = account.activities.order_by(AccountActivity.activity_date.desc()).limit(50).all()
    return jsonify([a.to_dict() for a in activities])


@api_bp.route('/accounts/<int:account_id>/activities', methods=['POST'])
def create_account_activity(account_id):
    """Log an activity for an account."""
    account = TrackedAccount.query.get_or_404(account_id)
    data = request.get_json()
    
    activity = AccountActivity(
        account_id=account_id,
        activity_type=data['activity_type'],
        description=data.get('description'),
        outcome=data.get('outcome'),
        competitor_mentioned=data.get('competitor_mentioned'),
        competitive_insight=data.get('competitive_insight'),
        logged_by=data.get('logged_by'),
        activity_date=datetime.fromisoformat(data['activity_date']) if data.get('activity_date') else datetime.utcnow()
    )
    
    db.session.add(activity)
    account.last_activity_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify(activity.to_dict()), 201


# =============================================================================
# FEATURE COMPARISON API
# =============================================================================

@api_bp.route('/features')
def get_features():
    """Get feature comparisons."""
    category = request.args.get('category')
    
    query = FeatureComparison.query
    if category:
        query = query.filter_by(category=category)
    
    features = query.order_by(FeatureComparison.category, FeatureComparison.customer_importance.desc()).all()
    return jsonify([f.to_dict() for f in features])


@api_bp.route('/features/categories')
def get_feature_categories():
    """Get all feature categories."""
    categories = db.session.query(FeatureComparison.category).distinct().all()
    return jsonify([c[0] for c in categories if c[0]])


@api_bp.route('/features', methods=['POST'])
def create_feature():
    """Create a feature comparison entry."""
    data = request.get_json()
    
    feature = FeatureComparison(
        category=data['category'],
        feature_name=data['feature_name'],
        description=data.get('description'),
        our_capability=data.get('our_capability', 'none'),
        our_details=data.get('our_details'),
        competitor_capabilities=json.dumps(data.get('competitor_capabilities', {})),
        customer_importance=data.get('customer_importance', 5),
        differentiation_level=data.get('differentiation_level')
    )
    
    db.session.add(feature)
    db.session.commit()
    
    return jsonify(feature.to_dict()), 201


@api_bp.route('/features/<int:feature_id>', methods=['PUT'])
def update_feature(feature_id):
    """Update a feature comparison."""
    feature = FeatureComparison.query.get_or_404(feature_id)
    data = request.get_json()
    
    for field in ['category', 'feature_name', 'description', 'our_capability', 
                  'our_details', 'customer_importance', 'differentiation_level']:
        if field in data:
            setattr(feature, field, data[field])
    
    if 'competitor_capabilities' in data:
        feature.competitor_capabilities = json.dumps(data['competitor_capabilities'])
    
    feature.last_verified = datetime.utcnow()
    feature.verified_by = data.get('verified_by')
    db.session.commit()
    
    return jsonify(feature.to_dict())


@api_bp.route('/features/matrix')
def get_feature_matrix():
    """Get feature comparison matrix for all competitors."""
    features = FeatureComparison.query.order_by(
        FeatureComparison.category, 
        FeatureComparison.customer_importance.desc()
    ).all()
    
    competitors = Competitor.query.filter_by(is_active=True).all()
    
    matrix = {
        'categories': {},
        'competitors': [{'id': c.id, 'name': c.name} for c in competitors]
    }
    
    for feature in features:
        if feature.category not in matrix['categories']:
            matrix['categories'][feature.category] = []
        
        feature_data = {
            'id': feature.id,
            'name': feature.feature_name,
            'description': feature.description,
            'importance': feature.customer_importance,
            'our_capability': feature.our_capability,
            'our_details': feature.our_details,
            'competitors': json.loads(feature.competitor_capabilities) if feature.competitor_capabilities else {}
        }
        matrix['categories'][feature.category].append(feature_data)
    
    return jsonify(matrix)


# =============================================================================
# DEMO DATA API
# =============================================================================

@api_bp.route('/demo/populate', methods=['POST'])
def populate_demo_data():
    """Populate database with demo data for demonstrations."""
    import random
    
    # Check if already populated
    if Competitor.query.count() >= 4:
        return jsonify({'message': 'Demo data already exists', 'populated': False})
    
    try:
        # Create competitors - Focus on Hioki as primary competitor, remove Tektronix
        competitors_data = [
            {'name': 'Hioki', 'description': 'Japanese manufacturer of electrical measuring instruments, primary competitor in DMM and power analyzers', 'website': 'https://www.hioki.com'},
            {'name': 'Keysight Technologies', 'description': 'Leading electronic measurement company', 'website': 'https://www.keysight.com'},
            {'name': 'Rohde & Schwarz', 'description': 'German technology company in T&M', 'website': 'https://www.rohde-schwarz.com'},
            {'name': 'National Instruments', 'description': 'Automated test equipment', 'website': 'https://www.ni.com'},
        ]
        
        competitors = []
        for c_data in competitors_data:
            existing = Competitor.query.filter_by(name=c_data['name']).first()
            if existing:
                competitors.append(existing)
            else:
                c = Competitor(**c_data)
                db.session.add(c)
                db.session.flush()
                competitors.append(c)
        
        # Get Hioki competitor for focused alerts
        hioki = next((c for c in competitors if c.name == 'Hioki'), competitors[0])
        
        # Create monitored URLs
        url_types = ['product_page', 'pricing_page', 'press_room', 'careers', 'changelog']
        for comp in competitors:
            if MonitoredURL.query.filter_by(competitor_id=comp.id).count() == 0:
                for page_type in url_types:
                    url = MonitoredURL(
                        competitor_id=comp.id,
                        url=f"{comp.website}/{page_type.replace('_', '-')}",
                        name=f"{comp.name} - {page_type.replace('_', ' ').title()}",
                        page_type=page_type,
                        check_interval_hours=24,
                        is_active=True
                    )
                    db.session.add(url)
        
        # Create Hioki-focused alerts
        hioki_alerts = [
            {'signal_type': 'product_launch', 'risk_level': 'critical', 'title': 'Hioki Launches New DT4282 Digital Multimeter', 'summary': 'Hioki has announced the DT4282, a new high-end DMM targeting industrial applications with improved accuracy.'},
            {'signal_type': 'pricing_change', 'risk_level': 'high', 'title': 'Hioki Announces 20% Price Reduction in North America', 'summary': 'Aggressive pricing move by Hioki to gain market share in the North American industrial DMM market.'},
            {'signal_type': 'feature_update', 'risk_level': 'medium', 'title': 'Hioki Adds Bluetooth Connectivity to Power Analyzers', 'summary': 'New wireless data transfer capability added to PW3390 power analyzer series.'},
        ]
        
        for template in hioki_alerts:
            alert = Alert(
                competitor_id=hioki.id,
                source_type='news',
                signal_type=template['signal_type'],
                risk_level=template['risk_level'],
                title=template['title'],
                summary=template['summary'],
                status='new',
                detected_at=datetime.utcnow() - timedelta(days=random.randint(0, 7)),
                source_url='https://www.hioki.com/news'
            )
            db.session.add(alert)
        
        # Add other competitor alerts
        other_alerts = [
            {'comp': 'Keysight Technologies', 'signal_type': 'partnership', 'risk_level': 'high', 'title': 'Keysight Partners with Major Semiconductor Manufacturer'},
            {'comp': 'Rohde & Schwarz', 'signal_type': 'expansion', 'risk_level': 'low', 'title': 'Rohde & Schwarz Opens New R&D Center in Austin'},
        ]
        for template in other_alerts:
            comp = next((c for c in competitors if c.name == template['comp']), competitors[1])
            alert = Alert(
                competitor_id=comp.id,
                source_type='page_change',
                signal_type=template['signal_type'],
                risk_level=template['risk_level'],
                title=template['title'],
                summary='Competitive intelligence alert.',
                status='acknowledged',
                detected_at=datetime.utcnow() - timedelta(days=random.randint(5, 14)),
                source_url=comp.website
            )
            db.session.add(alert)
        
        # Create Hioki news items
        hioki_news = [
            {'title': 'Hioki Reports Strong Q4 Growth in Test & Measurement', 'source': 'Google News'},
            {'title': 'Hioki Showcases New Power Analyzer at Embedded World 2026', 'source': 'Trade Publication'},
            {'title': 'Hioki Expands Distribution Network in Southeast Asia', 'source': 'Company Press Release'},
            {'title': 'Hioki DT4282 Review: A Serious Contender for Industrial DMM Market', 'source': 'Electronics Weekly'},
            {'title': 'Hioki Announces Partnership with EV Battery Manufacturer', 'source': 'Industry News'},
        ]
        for news_data in hioki_news:
            news = NewsItem(
                competitor_id=hioki.id,
                title=news_data['title'],
                source=news_data['source'],
                url=f"https://news.example.com/hioki/{random.randint(1000, 9999)}",
                published_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
                collected_at=datetime.utcnow(),
                is_processed=True,
                is_relevant=True
            )
            db.session.add(news)
        
        # Create battle cards - Focus on Hioki
        hioki_card = BattleCard(
            competitor_id=hioki.id,
            name="Hioki vs Fluke Battle Card",
            elevator_pitch="When competing against Hioki, emphasize Fluke's superior ruggedness, industry-leading accuracy in harsh environments, and unmatched global service network. Hioki excels in lab settings but Fluke wins in the field.",
            target_segment="Industrial Manufacturing, Field Service, Utilities",
            our_strengths=json.dumps([
                "Best-in-class CAT IV safety ratings",
                "Industry-leading drop test durability",
                "Superior low-impedance voltage detection",
                "Global service network with 24/7 support",
                "Extensive accessory ecosystem"
            ]),
            our_weaknesses=json.dumps([
                "Higher price point on some models",
                "Fewer connectivity options on entry-level models"
            ]),
            competitor_strengths=json.dumps([
                "Strong presence in Japanese market",
                "Good accuracy specifications",
                "Lower price point on comparable models",
                "Strong in power analysis segment"
            ]),
            competitor_weaknesses=json.dumps([
                "Limited global service network",
                "Less rugged for field use",
                "Smaller accessory ecosystem",
                "Weaker brand recognition outside Asia"
            ]),
            key_differentiators=json.dumps([
                "Fluke DMMs survive 3-meter drop tests; Hioki typically rated for 1m",
                "Fluke FieldSense technology for non-contact voltage measurement",
                "True-RMS accuracy in noisy electrical environments",
                "Lifetime warranty on most models vs Hioki's 3-year warranty"
            ]),
            trap_questions=json.dumps([
                "Ask about drop test ratings and field durability",
                "Inquire about global service and calibration network",
                "Ask about low-impedance voltage detection for ghost voltage",
                "Request references from similar harsh-environment applications"
            ]),
            landmine_questions=json.dumps([
                "If they mention Hioki's lower price, pivot to TCO and reliability",
                "If they mention Hioki's accuracy, discuss real-world vs lab conditions"
            ]),
            common_objections=json.dumps([
                {"objection": "Hioki is cheaper", "response": "When you factor in durability, calibration costs, and downtime, Fluke delivers 30% lower TCO over 5 years."},
                {"objection": "We've used Hioki before", "response": "Many customers switching from Hioki report fewer tool replacements and faster troubleshooting with Fluke's FieldSense technology."}
            ]),
            status='active'
        )
        db.session.add(hioki_card)
        
        # Add cards for other competitors
        for comp in competitors[1:3]:
            card = BattleCard(
                competitor_id=comp.id,
                name=f"{comp.name} Battle Card",
                elevator_pitch=f"When competing against {comp.name}, emphasize Fluke's field-proven reliability and comprehensive support.",
                target_segment="Industrial Manufacturing",
                our_strengths=json.dumps(["Best-in-class durability", "Industry-leading warranty", "Global support"]),
                competitor_weaknesses=json.dumps(["Limited field service", "Less rugged designs"]),
                key_differentiators=json.dumps(["Superior drop test ratings", "FieldSense technology"]),
                trap_questions=json.dumps(["Ask about field durability", "Inquire about service network"]),
                status='active'
            )
            db.session.add(card)
        
        # Create win/loss records - Include Hioki wins and losses
        wl_data = [
            {'outcome': 'won', 'deal_name': 'Automotive Tier 1 - Production Line Test', 'deal_value': 450000, 'comp': 'Hioki', 'win_reasons': 'Fluke won on durability and service network'},
            {'outcome': 'lost', 'deal_name': 'University Research Lab', 'deal_value': 75000, 'comp': 'Hioki', 'primary_loss_reason': 'pricing', 'key_learnings': 'Hioki won on price; need better academic pricing'},
            {'outcome': 'won', 'deal_name': 'Utility Field Service Fleet', 'deal_value': 320000, 'comp': 'Hioki', 'win_reasons': 'FieldSense and ruggedness were key differentiators'},
            {'outcome': 'won', 'deal_name': 'Semiconductor Fab Expansion', 'deal_value': 890000, 'comp': 'Keysight Technologies'},
            {'outcome': 'lost', 'deal_name': 'Telecom Test Lab', 'deal_value': 180000, 'comp': 'Rohde & Schwarz', 'primary_loss_reason': 'feature_gap'},
        ]
        for wl in wl_data:
            comp = next((c for c in competitors if c.name == wl['comp']), competitors[0])
            record = WinLossRecord(
                competitor_id=comp.id,
                outcome=wl['outcome'],
                deal_name=wl['deal_name'],
                deal_value=wl['deal_value'],
                customer_name='Enterprise Customer',
                customer_industry='Manufacturing',
                outcome_date=datetime.utcnow() - timedelta(days=random.randint(10, 90)),
                primary_loss_reason=wl.get('primary_loss_reason'),
                key_learnings=wl.get('key_learnings', '')
            )
            db.session.add(record)
        
        # Create feature comparisons - Hioki focused
        features = [
            {'category': 'Durability', 'feature_name': 'Drop Test Rating', 'importance': 10, 'our_capability': 'full', 'our_details': '3-meter drop test', 'hioki': 'partial', 'hioki_details': '1-meter drop test'},
            {'category': 'Accuracy', 'feature_name': 'DC Voltage Accuracy', 'importance': 9, 'our_capability': 'full', 'our_details': '0.025% + 2 counts', 'hioki': 'full', 'hioki_details': '0.025% + 3 counts'},
            {'category': 'Safety', 'feature_name': 'CAT IV 600V Rating', 'importance': 10, 'our_capability': 'full', 'our_details': 'Standard on industrial models', 'hioki': 'partial', 'hioki_details': 'Limited models'},
            {'category': 'Features', 'feature_name': 'Non-Contact Voltage', 'importance': 8, 'our_capability': 'full', 'our_details': 'FieldSense technology', 'hioki': 'none', 'hioki_details': 'Not available'},
            {'category': 'Support', 'feature_name': 'Global Service Network', 'importance': 7, 'our_capability': 'full', 'our_details': '100+ countries', 'hioki': 'partial', 'hioki_details': 'Limited outside Asia'},
        ]
        for feat in features:
            fc = FeatureComparison(
                category=feat['category'],
                feature_name=feat['feature_name'],
                customer_importance=feat['importance'],
                our_capability=feat['our_capability'],
                our_details=feat['our_details'],
                competitor_capabilities=json.dumps({
                    str(hioki.id): {'capability': feat['hioki'], 'details': feat['hioki_details']},
                })
            )
            db.session.add(fc)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Demo data populated successfully',
            'populated': True,
            'counts': {
                'competitors': Competitor.query.count(),
                'urls': MonitoredURL.query.count(),
                'alerts': Alert.query.count(),
                'news': NewsItem.query.count(),
                'battle_cards': BattleCard.query.count(),
                'win_loss': WinLossRecord.query.count(),
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@api_bp.route('/demo/reset', methods=['POST'])
def reset_demo_data():
    """Reset all demo data."""
    try:
        # Delete all data
        FeatureComparison.query.delete()
        WinLossRecord.query.delete()
        BattleCard.query.delete()
        Insight.query.delete()
        NewsItem.query.delete()
        Alert.query.delete()
        MonitoredURL.query.delete()
        Competitor.query.delete()
        db.session.commit()
        
        return jsonify({'message': 'All data reset successfully', 'reset': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
