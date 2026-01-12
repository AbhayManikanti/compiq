#!/usr/bin/env python3
"""
Populate demo data for CompIQ demonstration.
Run with: python populate_demo_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta
from app import create_app
from app.database import db, Competitor, MonitoredURL, Alert, NewsItem, Insight, BattleCard, WinLossRecord, CompetitivePlaybook, TrackedAccount, FeatureComparison
import json
import random

app = create_app()

def populate_demo_data():
    """Populate the database with demo data."""
    with app.app_context():
        print("🚀 Populating demo data for CompIQ...")
        
        # Clear existing demo data (optional - comment out to keep existing)
        # db.drop_all()
        # db.create_all()
        
        # ===== COMPETITORS =====
        competitors_data = [
            {
                'name': 'Keysight Technologies',
                'description': 'Leading electronic measurement company, strong in oscilloscopes and signal analyzers',
                'website': 'https://www.keysight.com',
            },
            {
                'name': 'Hioki',
                'description': 'Japanese manufacturer specializing in electrical measuring instruments and DMMs',
                'website': 'https://www.hioki.com',
            },
            {
                'name': 'Rohde & Schwarz',
                'description': 'German technology company, strong in test & measurement and broadcast',
                'website': 'https://www.rohde-schwarz.com',
            },
            {
                'name': 'Tektronix (Fortive)',
                'description': 'Part of Fortive, leading in oscilloscopes and protocol analyzers',
                'website': 'https://www.tek.com',
            },
            {
                'name': 'National Instruments (NI)',
                'description': 'Automated test equipment and virtual instrumentation software',
                'website': 'https://www.ni.com',
            }
        ]
        
        competitors = []
        for c_data in competitors_data:
            existing = Competitor.query.filter_by(name=c_data['name']).first()
            if existing:
                competitors.append(existing)
                print(f"  ⏭️  Competitor exists: {c_data['name']}")
            else:
                c = Competitor(**c_data)
                db.session.add(c)
                db.session.flush()
                competitors.append(c)
                print(f"  ✅ Created competitor: {c_data['name']}")
        
        db.session.commit()
        
        # ===== MONITORED URLs =====
        url_types = [
            ('product_page', 'Product/Release Page'),
            ('pricing_page', 'Pricing Page'),
            ('press_room', 'Press/Newsroom'),
            ('careers', 'Job Postings'),
            ('changelog', 'Changelog/Release Notes'),
        ]
        
        for comp in competitors:
            existing_urls = MonitoredURL.query.filter_by(competitor_id=comp.id).count()
            if existing_urls == 0:
                for page_type, page_name in url_types:
                    url = MonitoredURL(
                        competitor_id=comp.id,
                        url=f"{comp.website}/{page_type.replace('_', '-')}",
                        name=f"{comp.name} - {page_name}",
                        page_type=page_type,
                        check_interval_hours=24,
                        is_active=True
                    )
                    db.session.add(url)
                print(f"  ✅ Added URLs for: {comp.name}")
        
        db.session.commit()
        
        # ===== ALERTS =====
        alert_templates = [
            {
                'signal_type': 'product_launch',
                'risk_level': 'high',
                'title': '{comp} Launches New 8-Channel Oscilloscope Series',
                'summary': 'Major product announcement - new oscilloscope family targeting automotive and aerospace markets with enhanced bandwidth.',
            },
            {
                'signal_type': 'pricing_change',
                'risk_level': 'medium',
                'title': '{comp} Announces 15% Price Reduction on Entry-Level DMMs',
                'summary': 'Competitive pricing move in the entry-level digital multimeter segment, likely to impact Q1 sales.',
            },
            {
                'signal_type': 'partnership',
                'risk_level': 'high',
                'title': '{comp} Partners with Major Semiconductor Manufacturer',
                'summary': 'Strategic partnership announced for co-development of next-gen test solutions.',
            },
            {
                'signal_type': 'feature_update',
                'risk_level': 'medium',
                'title': '{comp} Adds AI-Powered Analysis to Software Suite',
                'summary': 'Software update introduces machine learning capabilities for automated test analysis.',
            },
            {
                'signal_type': 'expansion',
                'risk_level': 'low',
                'title': '{comp} Opens New R&D Center in Austin, TX',
                'summary': 'Expansion of research capabilities focused on 5G and automotive test solutions.',
            },
            {
                'signal_type': 'leadership_change',
                'risk_level': 'medium',
                'title': '{comp} Appoints New VP of Product Development',
                'summary': 'Leadership change signals potential shift in product strategy and roadmap.',
            },
        ]
        
        existing_alerts = Alert.query.count()
        if existing_alerts < 10:
            for i, template in enumerate(alert_templates):
                comp = random.choice(competitors)
                days_ago = random.randint(0, 14)
                
                alert = Alert(
                    competitor_id=comp.id,
                    source_type='page_change',
                    signal_type=template['signal_type'],
                    risk_level=template['risk_level'],
                    title=template['title'].format(comp=comp.name),
                    summary=template['summary'],
                    status='new' if i < 3 else random.choice(['acknowledged', 'in_progress', 'resolved']),
                    detected_at=datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23)),
                    source_url=f"{comp.website}/news"
                )
                db.session.add(alert)
            print(f"  ✅ Created {len(alert_templates)} demo alerts")
        
        db.session.commit()
        
        # ===== NEWS ITEMS =====
        news_templates = [
            '{comp} Reports Strong Q4 Revenue Growth in Test & Measurement',
            '{comp} Wins Major Government Contract for Defense Testing',
            '{comp} Showcases Innovation at Embedded World 2026',
            '{comp} Introduces Cloud-Based Calibration Service',
            '{comp} Expands Distribution Network in Asia-Pacific',
            'Industry Analysis: {comp} Gains Market Share in Oscilloscope Segment',
            '{comp} Announces Sustainability Initiatives for 2026',
            '{comp} Launches Training Academy for Engineers',
        ]
        
        existing_news = NewsItem.query.count()
        if existing_news < 15:
            for template in news_templates:
                comp = random.choice(competitors)
                days_ago = random.randint(0, 30)
                
                news = NewsItem(
                    competitor_id=comp.id,
                    title=template.format(comp=comp.name),
                    source='Google News',
                    url=f"https://news.example.com/{comp.name.lower().replace(' ', '-')}/{random.randint(1000, 9999)}",
                    published_at=datetime.utcnow() - timedelta(days=days_ago),
                    collected_at=datetime.utcnow() - timedelta(days=days_ago),
                    is_processed=True,
                    is_relevant=True
                )
                db.session.add(news)
            print(f"  ✅ Created {len(news_templates)} demo news items")
        
        db.session.commit()
        
        # ===== INSIGHTS =====
        insight_templates = [
            {
                'title': '{comp} Product Strategy Analysis',
                'executive_summary': 'Based on recent announcements and job postings, {comp} appears to be pivoting towards software-defined instrumentation with increased focus on cloud connectivity and AI-powered analysis features.',
            },
            {
                'title': '{comp} Pricing Competitive Assessment',
                'executive_summary': 'Analysis of {comp}\'s recent pricing changes reveals aggressive positioning in the mid-market segment with 15% average price reductions and new subscription models.',
            },
        ]
        
        existing_insights = Insight.query.count()
        if existing_insights < 5:
            for template in insight_templates:
                comp = random.choice(competitors)
                alert = Alert.query.filter_by(competitor_id=comp.id).first()
                
                insight = Insight(
                    alert_id=alert.id if alert else None,
                    competitor_id=comp.id,
                    title=template['title'].format(comp=comp.name),
                    executive_summary=template['executive_summary'].format(comp=comp.name),
                    impact_score=random.randint(60, 95),
                    urgency_score=random.randint(50, 90),
                    confidence_score=random.randint(70, 95),
                    sales_insights=json.dumps({'talking_points': ['Emphasize our value proposition', 'Highlight TCO advantages'], 'objection_handlers': ['Address pricing concerns with ROI data']}),
                    marketing_insights=json.dumps({'messaging': ['Update competitive positioning', 'Create comparison content']}),
                    immediate_actions=json.dumps(['Update battle cards', 'Brief sales team', 'Monitor closely']),
                    created_at=datetime.utcnow() - timedelta(days=random.randint(1, 7))
                )
                db.session.add(insight)
            print(f"  ✅ Created {len(insight_templates)} demo insights")
        
        db.session.commit()
        
        # ===== BATTLE CARDS =====
        existing_cards = BattleCard.query.count()
        if existing_cards < 3:
            for comp in competitors[:3]:
                card = BattleCard(
                    competitor_id=comp.id,
                    name=f"{comp.name} Battle Card",
                    elevator_pitch=f"When competing against {comp.name}, emphasize our superior accuracy, faster time-to-measurement, and comprehensive support ecosystem.",
                    target_segment="Industrial Manufacturing, Automotive OEMs",
                    our_strengths=json.dumps([
                        "Best-in-class accuracy specifications",
                        "Industry-leading warranty program",
                        "Comprehensive training and support",
                        "Broader product portfolio"
                    ]),
                    our_weaknesses=json.dumps([
                        "Higher price point on some models",
                        "Longer delivery times for custom configurations"
                    ]),
                    competitor_strengths=json.dumps([
                        "Strong brand recognition",
                        "Competitive pricing",
                        "Good software integration"
                    ]),
                    competitor_weaknesses=json.dumps([
                        "Limited service network",
                        "Slower product refresh cycles",
                        "Less comprehensive documentation"
                    ]),
                    key_differentiators=json.dumps([
                        "Proprietary measurement technology with 20% better accuracy",
                        "24/7 technical support with 4-hour response SLA",
                        "Cloud-connected instruments with automatic calibration reminders"
                    ]),
                    trap_questions=json.dumps([
                        "Ask about their calibration interval and total cost of ownership",
                        "Inquire about support response times for critical issues",
                        "Request references from similar industry applications"
                    ]),
                    common_objections=json.dumps([
                        {"objection": "Your products are more expensive", "response": "When you factor in TCO including calibration, support, and reliability, our products deliver better value over their lifecycle."},
                        {"objection": "We've always used competitor", "response": "We'd welcome the opportunity to do a side-by-side evaluation. Many customers switching from competitor have seen 25% productivity improvements."}
                    ]),
                    status='active'
                )
                db.session.add(card)
            print(f"  ✅ Created 3 demo battle cards")
        
        db.session.commit()
        
        # ===== WIN/LOSS RECORDS =====
        existing_wl = WinLossRecord.query.count()
        if existing_wl < 5:
            wl_data = [
                {'outcome': 'won', 'deal_name': 'Automotive Tier 1 - Production Test', 'deal_value': 450000, 'customer_name': 'AutoTech Industries'},
                {'outcome': 'lost', 'deal_name': 'Aerospace MRO Equipment', 'deal_value': 320000, 'customer_name': 'AeroMaintain Corp', 'primary_loss_reason': 'pricing'},
                {'outcome': 'won', 'deal_name': 'Semiconductor Fab Expansion', 'deal_value': 890000, 'customer_name': 'ChipMakers Inc'},
                {'outcome': 'lost', 'deal_name': 'University Research Lab', 'deal_value': 75000, 'customer_name': 'State University', 'primary_loss_reason': 'feature_gap'},
                {'outcome': 'won', 'deal_name': 'Telecom Field Service', 'deal_value': 180000, 'customer_name': 'TeleNetwork Solutions'},
            ]
            
            for wl in wl_data:
                comp = random.choice(competitors)
                record = WinLossRecord(
                    competitor_id=comp.id,
                    outcome=wl['outcome'],
                    deal_name=wl['deal_name'],
                    deal_value=wl['deal_value'],
                    customer_name=wl['customer_name'],
                    customer_industry='Technology',
                    customer_region='North America',
                    outcome_date=datetime.utcnow() - timedelta(days=random.randint(10, 60)),
                    primary_loss_reason=wl.get('primary_loss_reason'),
                    key_learnings='Valuable insights gathered from this opportunity.'
                )
                db.session.add(record)
            print(f"  ✅ Created 5 demo win/loss records")
        
        db.session.commit()
        
        # ===== PLAYBOOKS =====
        existing_pb = CompetitivePlaybook.query.count()
        if existing_pb < 2:
            playbooks = [
                {
                    'name': 'Competitor Product Launch Response',
                    'slug': 'product_launch_response',
                    'description': 'Standard response plan when a competitor launches a new product',
                    'trigger_signal_types': json.dumps(['product_launch', 'feature_update']),
                    'trigger_keywords': json.dumps(['launch', 'announce', 'new product', 'release']),
                    'sales_actions': json.dumps(['Update battle cards within 48 hours', 'Brief key accounts proactively', 'Prepare competitive positioning']),
                    'marketing_actions': json.dumps(['Draft competitive blog post', 'Update comparison pages', 'Prepare social media response']),
                    'product_actions': json.dumps(['Analyze feature gaps', 'Update roadmap priorities']),
                    'executive_actions': json.dumps(['Review strategic implications', 'Approve response budget']),
                    'priority': 8,
                    'is_active': True
                },
                {
                    'name': 'Pricing Change Response',
                    'slug': 'pricing_change_response',
                    'description': 'Response plan for competitor pricing adjustments',
                    'trigger_signal_types': json.dumps(['pricing_change']),
                    'trigger_keywords': json.dumps(['price', 'discount', 'promotion', 'bundle']),
                    'sales_actions': json.dumps(['Review active proposals', 'Prepare value justification', 'Alert at-risk accounts']),
                    'marketing_actions': json.dumps(['Update TCO calculators', 'Prepare value messaging']),
                    'product_actions': json.dumps(['Review packaging options']),
                    'executive_actions': json.dumps(['Approve counter-pricing if needed']),
                    'priority': 9,
                    'is_active': True
                }
            ]
            
            for pb in playbooks:
                playbook = CompetitivePlaybook(**pb)
                db.session.add(playbook)
            print(f"  ✅ Created 2 demo playbooks")
        
        db.session.commit()
        
        # ===== FEATURE COMPARISONS =====
        existing_fc = FeatureComparison.query.count()
        if existing_fc < 5:
            features = [
                {'category': 'Accuracy', 'feature_name': 'DC Voltage Accuracy', 'importance': 9, 'our_capability': 'full', 'our_details': '0.0024% + 0.5ppm'},
                {'category': 'Accuracy', 'feature_name': 'AC Voltage Accuracy', 'importance': 8, 'our_capability': 'full', 'our_details': '0.06% of reading'},
                {'category': 'Connectivity', 'feature_name': 'Cloud Data Sync', 'importance': 7, 'our_capability': 'full', 'our_details': 'Real-time sync with Fluke Cloud'},
                {'category': 'Safety', 'feature_name': 'CAT IV Rating', 'importance': 10, 'our_capability': 'full', 'our_details': 'CAT IV 600V / CAT III 1000V'},
                {'category': 'Software', 'feature_name': 'Mobile App Integration', 'importance': 6, 'our_capability': 'full', 'our_details': 'iOS and Android apps'},
            ]
            
            for feat in features:
                fc = FeatureComparison(
                    category=feat['category'],
                    feature_name=feat['feature_name'],
                    customer_importance=feat['importance'],
                    our_capability=feat['our_capability'],
                    our_details=feat['our_details'],
                    competitor_capabilities=json.dumps({
                        str(competitors[0].id): {'capability': 'partial', 'details': 'Limited'},
                        str(competitors[1].id): {'capability': 'full', 'details': 'Comparable'},
                        str(competitors[2].id): {'capability': 'none', 'details': 'Not available'},
                    })
                )
                db.session.add(fc)
            print(f"  ✅ Created 5 demo feature comparisons")
        
        db.session.commit()
        
        print("\n✨ Demo data population complete!")
        print(f"   Competitors: {Competitor.query.count()}")
        print(f"   Monitored URLs: {MonitoredURL.query.count()}")
        print(f"   Alerts: {Alert.query.count()}")
        print(f"   News Items: {NewsItem.query.count()}")
        print(f"   Insights: {Insight.query.count()}")
        print(f"   Battle Cards: {BattleCard.query.count()}")
        print(f"   Win/Loss Records: {WinLossRecord.query.count()}")
        print(f"   Playbooks: {CompetitivePlaybook.query.count()}")
        print(f"   Feature Comparisons: {FeatureComparison.query.count()}")


if __name__ == '__main__':
    populate_demo_data()
