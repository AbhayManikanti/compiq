"""
Alerting and Notification System
Sends alerts via email, Slack, and Teams.
"""
import os
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
import requests
from .database import db, Alert, RiskLevel

logger = logging.getLogger(__name__)


class Alerter:
    """Handles sending notifications for alerts."""
    
    def __init__(self):
        # Slack configuration
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        self.slack_channel = os.getenv('SLACK_CHANNEL', '#competitor-alerts')
        
        # Teams configuration
        self.teams_webhook = os.getenv('TEAMS_WEBHOOK_URL')
        
        # Email configuration
        self.smtp_host = os.getenv('SMTP_HOST')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.alert_email_to = os.getenv('ALERT_EMAIL_TO')
    
    def _get_risk_emoji(self, risk_level: str) -> str:
        """Get emoji for risk level."""
        return {
            RiskLevel.CRITICAL.value: '🚨',
            RiskLevel.HIGH.value: '🔴',
            RiskLevel.MEDIUM.value: '🟡',
            RiskLevel.LOW.value: '🟢',
            RiskLevel.INFO.value: 'ℹ️'
        }.get(risk_level, '⚪')
    
    def _get_risk_color(self, risk_level: str) -> str:
        """Get color for risk level (for Slack/Teams)."""
        return {
            RiskLevel.CRITICAL.value: '#FF0000',
            RiskLevel.HIGH.value: '#FF4444',
            RiskLevel.MEDIUM.value: '#FFAA00',
            RiskLevel.LOW.value: '#00AA00',
            RiskLevel.INFO.value: '#0088FF'
        }.get(risk_level, '#888888')
    
    def send_slack_alert(self, alert: Alert) -> bool:
        """Send alert to Slack."""
        if not self.slack_webhook:
            logger.warning("Slack webhook not configured")
            return False
        
        try:
            emoji = self._get_risk_emoji(alert.risk_level)
            color = self._get_risk_color(alert.risk_level)
            
            # Get recommended actions
            actions = alert.get_recommended_actions()
            actions_text = "\n".join([
                f"• {a.get('action', 'N/A')} ({a.get('priority', 'N/A')} - {a.get('owner', 'N/A')})"
                for a in actions[:5]
            ]) if actions else "No specific actions recommended"
            
            payload = {
                "channel": self.slack_channel,
                "username": "Competitor Monitor",
                "icon_emoji": ":mag:",
                "attachments": [
                    {
                        "color": color,
                        "blocks": [
                            {
                                "type": "header",
                                "text": {
                                    "type": "plain_text",
                                    "text": f"{emoji} {alert.title}"
                                }
                            },
                            {
                                "type": "section",
                                "fields": [
                                    {
                                        "type": "mrkdwn",
                                        "text": f"*Competitor:*\n{alert.competitor.name if alert.competitor else 'Unknown'}"
                                    },
                                    {
                                        "type": "mrkdwn",
                                        "text": f"*Signal Type:*\n{alert.signal_type.replace('_', ' ').title()}"
                                    },
                                    {
                                        "type": "mrkdwn",
                                        "text": f"*Risk Level:*\n{alert.risk_level.upper()} ({alert.risk_score}/100)"
                                    },
                                    {
                                        "type": "mrkdwn",
                                        "text": f"*Confidence:*\n{alert.confidence_score}%"
                                    }
                                ]
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*Summary:*\n{alert.summary}"
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*Relevance to Fluke:*\n{alert.relevance_explanation}"
                                }
                            },
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"*Recommended Actions:*\n{actions_text}"
                                }
                            },
                            {
                                "type": "actions",
                                "elements": [
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "View Source"
                                        },
                                        "url": alert.source_url
                                    },
                                    {
                                        "type": "button",
                                        "text": {
                                            "type": "plain_text",
                                            "text": "View in Dashboard"
                                        },
                                        "url": f"{os.getenv('APP_URL', 'http://localhost:5000')}/alerts/{alert.id}"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(
                self.slack_webhook,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"Slack alert sent for alert {alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Slack alert: {e}")
            return False
    
    def send_teams_alert(self, alert: Alert) -> bool:
        """Send alert to Microsoft Teams."""
        if not self.teams_webhook:
            logger.warning("Teams webhook not configured")
            return False
        
        try:
            emoji = self._get_risk_emoji(alert.risk_level)
            color = self._get_risk_color(alert.risk_level)
            
            # Get recommended actions
            actions = alert.get_recommended_actions()
            actions_text = "\n\n".join([
                f"- **{a.get('action', 'N/A')}** ({a.get('priority', 'N/A')}) - Owner: {a.get('owner', 'N/A')}"
                for a in actions[:5]
            ]) if actions else "No specific actions recommended"
            
            payload = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "themeColor": color.replace('#', ''),
                "summary": alert.title,
                "sections": [
                    {
                        "activityTitle": f"{emoji} {alert.title}",
                        "facts": [
                            {"name": "Competitor", "value": alert.competitor.name if alert.competitor else "Unknown"},
                            {"name": "Signal Type", "value": alert.signal_type.replace('_', ' ').title()},
                            {"name": "Risk Level", "value": f"{alert.risk_level.upper()} ({alert.risk_score}/100)"},
                            {"name": "Confidence", "value": f"{alert.confidence_score}%"},
                            {"name": "Detected", "value": alert.detected_at.strftime('%Y-%m-%d %H:%M UTC')}
                        ],
                        "markdown": True
                    },
                    {
                        "title": "Summary",
                        "text": alert.summary
                    },
                    {
                        "title": "Relevance to Fluke",
                        "text": alert.relevance_explanation
                    },
                    {
                        "title": "Recommended Actions",
                        "text": actions_text
                    }
                ],
                "potentialAction": [
                    {
                        "@type": "OpenUri",
                        "name": "View Source",
                        "targets": [{"os": "default", "uri": alert.source_url}]
                    },
                    {
                        "@type": "OpenUri",
                        "name": "View in Dashboard",
                        "targets": [{"os": "default", "uri": f"{os.getenv('APP_URL', 'http://localhost:5000')}/alerts/{alert.id}"}]
                    }
                ]
            }
            
            response = requests.post(
                self.teams_webhook,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"Teams alert sent for alert {alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Teams alert: {e}")
            return False
    
    def send_email_alert(self, alert: Alert, to_addresses: Optional[List[str]] = None) -> bool:
        """Send alert via email."""
        if not all([self.smtp_host, self.smtp_user, self.smtp_password]):
            logger.warning("Email not fully configured")
            return False
        
        to_addresses = to_addresses or [self.alert_email_to]
        if not to_addresses or not to_addresses[0]:
            logger.warning("No email recipients configured")
            return False
        
        try:
            emoji = self._get_risk_emoji(alert.risk_level)
            
            # Get recommended actions
            actions = alert.get_recommended_actions()
            actions_html = "<ul>" + "".join([
                f"<li><strong>{a.get('action', 'N/A')}</strong> "
                f"({a.get('priority', 'N/A')} priority) - Owner: {a.get('owner', 'N/A')}</li>"
                for a in actions[:5]
            ]) + "</ul>" if actions else "<p>No specific actions recommended</p>"
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"{emoji} [{alert.risk_level.upper()}] {alert.title}"
            msg['From'] = self.smtp_user
            msg['To'] = ', '.join(to_addresses)
            
            # Plain text version
            text_content = f"""
COMPETITOR INTELLIGENCE ALERT
{'='*50}

{alert.title}

Competitor: {alert.competitor.name if alert.competitor else 'Unknown'}
Signal Type: {alert.signal_type.replace('_', ' ').title()}
Risk Level: {alert.risk_level.upper()} ({alert.risk_score}/100)
Confidence: {alert.confidence_score}%
Detected: {alert.detected_at.strftime('%Y-%m-%d %H:%M UTC')}

SUMMARY
{'-'*50}
{alert.summary}

RELEVANCE TO FLUKE
{'-'*50}
{alert.relevance_explanation}

SOURCE
{'-'*50}
{alert.source_url}

View in Dashboard: {os.getenv('APP_URL', 'http://localhost:5000')}/alerts/{alert.id}
"""
            
            # HTML version
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background-color: {self._get_risk_color(alert.risk_level)}; color: white; padding: 20px; }}
        .content {{ padding: 20px; }}
        .section {{ margin-bottom: 20px; }}
        .section h3 {{ color: #555; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
        .facts {{ display: flex; flex-wrap: wrap; gap: 20px; }}
        .fact {{ min-width: 150px; }}
        .fact-label {{ font-weight: bold; color: #666; }}
        .actions {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .btn {{ display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; 
                text-decoration: none; border-radius: 5px; margin-right: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{emoji} {alert.title}</h1>
    </div>
    <div class="content">
        <div class="section">
            <div class="facts">
                <div class="fact">
                    <div class="fact-label">Competitor</div>
                    <div>{alert.competitor.name if alert.competitor else 'Unknown'}</div>
                </div>
                <div class="fact">
                    <div class="fact-label">Signal Type</div>
                    <div>{alert.signal_type.replace('_', ' ').title()}</div>
                </div>
                <div class="fact">
                    <div class="fact-label">Risk Level</div>
                    <div>{alert.risk_level.upper()} ({alert.risk_score}/100)</div>
                </div>
                <div class="fact">
                    <div class="fact-label">Confidence</div>
                    <div>{alert.confidence_score}%</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h3>Summary</h3>
            <p>{alert.summary}</p>
        </div>
        
        <div class="section">
            <h3>Relevance to Fluke</h3>
            <p>{alert.relevance_explanation}</p>
        </div>
        
        <div class="section actions">
            <h3>Recommended Actions</h3>
            {actions_html}
        </div>
        
        <div class="section">
            <a href="{alert.source_url}" class="btn">View Source</a>
            <a href="{os.getenv('APP_URL', 'http://localhost:5000')}/alerts/{alert.id}" class="btn">View in Dashboard</a>
        </div>
    </div>
</body>
</html>
"""
            
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email alert sent for alert {alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
            return False
    
    def send_alert(self, alert: Alert, channels: Optional[List[str]] = None) -> dict:
        """
        Send alert through specified channels.
        
        Args:
            alert: The alert to send
            channels: List of channels ('slack', 'teams', 'email'). 
                     If None, uses all configured channels.
        
        Returns:
            Dict with results for each channel
        """
        results = {}
        
        if channels is None:
            channels = []
            if self.slack_webhook:
                channels.append('slack')
            if self.teams_webhook:
                channels.append('teams')
            if self.smtp_host and self.alert_email_to:
                channels.append('email')
        
        for channel in channels:
            if channel == 'slack':
                results['slack'] = self.send_slack_alert(alert)
            elif channel == 'teams':
                results['teams'] = self.send_teams_alert(alert)
            elif channel == 'email':
                results['email'] = self.send_email_alert(alert)
        
        # Update alert with notification status
        sent_channels = [ch for ch, success in results.items() if success]
        if sent_channels:
            alert.notification_sent = True
            alert.notification_channels = ','.join(sent_channels)
            db.session.commit()
        
        return results
    
    def send_pending_alerts(self, min_risk_level: str = RiskLevel.MEDIUM.value) -> dict:
        """
        Send notifications for all pending alerts above a risk threshold.
        
        Returns:
            Summary of sent notifications
        """
        risk_priority = {
            RiskLevel.CRITICAL.value: 5,
            RiskLevel.HIGH.value: 4,
            RiskLevel.MEDIUM.value: 3,
            RiskLevel.LOW.value: 2,
            RiskLevel.INFO.value: 1
        }
        
        min_priority = risk_priority.get(min_risk_level, 3)
        
        # Get unsent alerts
        pending_alerts = Alert.query.filter(
            Alert.notification_sent == False
        ).all()
        
        # Filter by risk level
        pending_alerts = [
            a for a in pending_alerts 
            if risk_priority.get(a.risk_level, 0) >= min_priority
        ]
        
        summary = {
            'total_pending': len(pending_alerts),
            'sent': 0,
            'failed': 0,
            'details': []
        }
        
        for alert in pending_alerts:
            results = self.send_alert(alert)
            
            if any(results.values()):
                summary['sent'] += 1
            else:
                summary['failed'] += 1
            
            summary['details'].append({
                'alert_id': alert.id,
                'title': alert.title,
                'results': results
            })
        
        return summary


def run_alerter():
    """Run the alerter as a standalone process."""
    from . import create_app
    
    app = create_app()
    
    with app.app_context():
        alerter = Alerter()
        summary = alerter.send_pending_alerts()
        
        print(f"\n{'='*60}")
        print("ALERT NOTIFICATIONS SENT")
        print(f"{'='*60}")
        print(f"Total pending: {summary['total_pending']}")
        print(f"Successfully sent: {summary['sent']}")
        print(f"Failed: {summary['failed']}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_alerter()
