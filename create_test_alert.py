#!/usr/bin/env python3
"""Create a test alert to test insights generation."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.database import db, Alert, Competitor, AlertStatus, SignalType, RiskLevel
import json

app = create_app()

with app.app_context():
    # Get or create competitor
    competitor = Competitor.query.first()
    if not competitor:
        competitor = Competitor(
            name="Hioki",
            description="Test and measurement equipment manufacturer",
            website="https://www.hioki.com"
        )
        db.session.add(competitor)
        db.session.commit()
        print(f"Created competitor: {competitor.name}")
    
    # Check if we already have alerts
    existing_alerts = Alert.query.count()
    print(f"Existing alerts: {existing_alerts}")
    
    if existing_alerts == 0:
        # Create a test alert
        test_alert = Alert(
            competitor_id=competitor.id,
            source_type='news',
            source_url='https://www.hioki.com/news/test',
            title=f"Hioki: New DT4282 Digital Multimeter Launch",
            summary="Hioki has announced the launch of their new DT4282 Digital Multimeter, featuring improved accuracy, Bluetooth connectivity, and IP67 water resistance. This product directly competes with Fluke's 87V and 289 series in the industrial multimeter market.",
            raw_content="Hioki announced today the release of DT4282, their flagship digital multimeter targeting industrial professionals. The new device features 0.025% DC accuracy, Bluetooth connectivity for data logging, and IP67 water resistance.",
            signal_type=SignalType.PRODUCT_LAUNCH.value,
            risk_level=RiskLevel.HIGH.value,
            risk_score=75,
            confidence_score=85,
            analysis=json.dumps({
                "summary": "Hioki launches new flagship DMM with features competing directly with Fluke 87V and 289",
                "signal_type": "product_launch",
                "risk_level": "high",
                "key_details": [
                    "0.025% DC accuracy - matches Fluke 87V",
                    "Bluetooth connectivity - similar to Fluke Connect",
                    "IP67 water resistance - exceeds most Fluke models",
                    "Price point approximately 15% lower than Fluke 289"
                ]
            }),
            relevance_explanation="This product directly competes with Fluke's flagship 87V and 289 series in the industrial multimeter market. The combination of comparable accuracy, Bluetooth connectivity, and better water resistance at a lower price point poses a significant competitive threat.",
            assumptions="• Pricing based on preliminary announcement\n• Availability assumed for Q2 2025\n• Accuracy claims need verification",
            recommended_actions=json.dumps([
                {"action": "Compare specifications vs Fluke 87V and 289", "owner": "Product Management", "priority": "high"},
                {"action": "Prepare competitive battle card", "owner": "Sales Enablement", "priority": "high"},
                {"action": "Review pricing strategy for 87V series", "owner": "Pricing Team", "priority": "medium"},
                {"action": "Monitor customer feedback on social media", "owner": "Marketing", "priority": "medium"}
            ]),
            playbook_used="product_launch",
            status=AlertStatus.NEW.value
        )
        db.session.add(test_alert)
        db.session.commit()
        print(f"Created test alert: {test_alert.id} - {test_alert.title}")
    else:
        print(f"Alerts already exist, skipping creation")
    
    # Show all alerts
    alerts = Alert.query.all()
    for alert in alerts:
        print(f"  Alert {alert.id}: {alert.title[:60]}... (status: {alert.status})")
