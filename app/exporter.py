"""
Export functionality for reports, alerts, and insights.
Supports PDF and CSV export.
"""
import os
import io
import csv
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY

from .database import Alert, Insight, Competitor, NewsItem

logger = logging.getLogger(__name__)


class ReportExporter:
    """Exports reports in various formats."""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Set up custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a237e')
        ))
        
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#0d47a1'),
            borderWidth=1,
            borderColor=colors.HexColor('#0d47a1'),
            borderPadding=5
        ))
        
        self.styles.add(ParagraphStyle(
            name='SubHeader',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.HexColor('#1565c0')
        ))
        
        self.styles.add(ParagraphStyle(
            name='BodyTextJustified',
            parent=self.styles['BodyText'],
            alignment=TA_JUSTIFY,
            fontSize=10,
            leading=14
        ))
        
        self.styles.add(ParagraphStyle(
            name='BulletPoint',
            parent=self.styles['BodyText'],
            fontSize=10,
            leftIndent=20,
            bulletIndent=10,
            spaceBefore=3,
            spaceAfter=3
        ))
        
        self.styles.add(ParagraphStyle(
            name='RiskCritical',
            parent=self.styles['BodyText'],
            textColor=colors.red,
            fontSize=11,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='RiskHigh',
            parent=self.styles['BodyText'],
            textColor=colors.HexColor('#ff5722'),
            fontSize=11,
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='RiskMedium',
            parent=self.styles['BodyText'],
            textColor=colors.HexColor('#ff9800'),
            fontSize=11
        ))
    
    def _get_risk_style(self, risk_level: str) -> str:
        """Get the style name for a risk level."""
        return {
            'critical': 'RiskCritical',
            'high': 'RiskHigh',
            'medium': 'RiskMedium'
        }.get(risk_level, 'BodyText')
    
    def _create_header(self, title: str, subtitle: str = None) -> List:
        """Create a report header."""
        elements = []
        
        # Title
        elements.append(Paragraph(title, self.styles['ReportTitle']))
        
        if subtitle:
            elements.append(Paragraph(subtitle, self.styles['BodyText']))
        
        # Date
        date_str = datetime.now().strftime('%B %d, %Y at %H:%M')
        elements.append(Paragraph(f"Generated: {date_str}", self.styles['BodyText']))
        
        elements.append(Spacer(1, 20))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a237e')))
        elements.append(Spacer(1, 20))
        
        return elements
    
    def export_insight_pdf(self, insight: Insight) -> io.BytesIO:
        """Export a single insight as PDF."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        elements = []
        
        # Header
        elements.extend(self._create_header(
            "Competitive Intelligence Report",
            f"Insight: {insight.title}"
        ))
        
        # Executive Summary
        elements.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
        elements.append(Paragraph(
            insight.executive_summary or "No summary available.",
            self.styles['BodyTextJustified']
        ))
        elements.append(Spacer(1, 15))
        
        # Scores
        scores_data = [
            ['Metric', 'Score', 'Level'],
            ['Impact', f"{insight.impact_score or 0}/100", self._score_level(insight.impact_score)],
            ['Urgency', f"{insight.urgency_score or 0}/100", self._score_level(insight.urgency_score)],
            ['Confidence', f"{insight.confidence_score or 0}/100", self._score_level(insight.confidence_score)]
        ]
        
        scores_table = Table(scores_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        scores_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f5f5')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#ddd'))
        ]))
        elements.append(scores_table)
        elements.append(Spacer(1, 20))
        
        # Product Comparison
        if insight.competitor_product or insight.fluke_product:
            elements.append(Paragraph("Product Comparison", self.styles['SectionHeader']))
            
            comparison_data = [
                ['Aspect', 'Fluke', insight.competitor.name if insight.competitor else 'Competitor'],
                ['Product', insight.fluke_product or 'N/A', insight.competitor_product or 'N/A']
            ]
            
            # Add feature comparison
            if insight.feature_comparison:
                try:
                    features = json.loads(insight.feature_comparison) if isinstance(insight.feature_comparison, str) else insight.feature_comparison
                    for feature, data in features.items():
                        winner_mark = lambda w, t: f"✓ {t}" if w == 'fluke' else (f"✓ {t}" if w == 'competitor' else t)
                        fluke_val = data.get('fluke', 'N/A')
                        comp_val = data.get('competitor', 'N/A')
                        winner = data.get('winner', 'tie')
                        
                        if winner == 'fluke':
                            fluke_val = f"✓ {fluke_val}"
                        elif winner == 'competitor':
                            comp_val = f"✓ {comp_val}"
                        
                        comparison_data.append([feature, fluke_val, comp_val])
                except:
                    pass
            
            comp_table = Table(comparison_data, colWidths=[2*inch, 2.25*inch, 2.25*inch])
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d47a1')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ddd')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')])
            ]))
            elements.append(comp_table)
            elements.append(Spacer(1, 10))
            
            if insight.comparison_summary:
                elements.append(Paragraph(
                    f"<b>Summary:</b> {insight.comparison_summary}",
                    self.styles['BodyTextJustified']
                ))
            elements.append(Spacer(1, 20))
        
        # Team Recommendations
        elements.append(PageBreak())
        elements.append(Paragraph("Team Recommendations", self.styles['SectionHeader']))
        
        team_sections = [
            ('Sales', insight.sales_insights),
            ('Marketing', insight.marketing_insights),
            ('Product', insight.product_insights),
            ('Engineering', insight.engineering_insights),
            ('Executive', insight.executive_insights)
        ]
        
        for team_name, team_data in team_sections:
            if team_data:
                try:
                    data = json.loads(team_data) if isinstance(team_data, str) else team_data
                    if data and data.get('summary'):
                        elements.append(Paragraph(f"{team_name} Team", self.styles['SubHeader']))
                        elements.append(Paragraph(data['summary'], self.styles['BodyTextJustified']))
                        
                        # Add key points
                        for key in ['talking_points', 'messaging_recommendations', 'feature_gaps', 
                                   'r_and_d_priorities', 'investment_recommendations']:
                            if data.get(key):
                                elements.append(Paragraph(f"<b>{key.replace('_', ' ').title()}:</b>", self.styles['BodyText']))
                                for point in data[key]:
                                    elements.append(Paragraph(f"• {point}", self.styles['BulletPoint']))
                        
                        elements.append(Spacer(1, 10))
                except:
                    pass
        
        # Action Items
        elements.append(Paragraph("Action Items", self.styles['SectionHeader']))
        
        actions_data = [['Priority', 'Action', 'Timeline']]
        
        if insight.immediate_actions:
            try:
                actions = json.loads(insight.immediate_actions) if isinstance(insight.immediate_actions, str) else insight.immediate_actions
                for action in actions:
                    actions_data.append(['Immediate', action if isinstance(action, str) else action.get('action', str(action)), '24-48 hours'])
            except:
                pass
        
        if insight.short_term_actions:
            try:
                actions = json.loads(insight.short_term_actions) if isinstance(insight.short_term_actions, str) else insight.short_term_actions
                for action in actions:
                    actions_data.append(['Short-term', action if isinstance(action, str) else action.get('action', str(action)), '1-4 weeks'])
            except:
                pass
        
        if insight.long_term_actions:
            try:
                actions = json.loads(insight.long_term_actions) if isinstance(insight.long_term_actions, str) else insight.long_term_actions
                for action in actions:
                    actions_data.append(['Long-term', action if isinstance(action, str) else action.get('action', str(action)), 'Quarter+'])
            except:
                pass
        
        if len(actions_data) > 1:
            actions_table = Table(actions_data, colWidths=[1.25*inch, 4*inch, 1.25*inch])
            actions_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e7d32')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ddd')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f1f8e9')])
            ]))
            elements.append(actions_table)
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    def _score_level(self, score: int) -> str:
        """Convert score to level text."""
        if not score:
            return "N/A"
        if score >= 70:
            return "High"
        if score >= 40:
            return "Medium"
        return "Low"
    
    def export_alert_pdf(self, alert: Alert) -> io.BytesIO:
        """Export a single alert as PDF."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        
        elements = []
        
        # Header
        elements.extend(self._create_header(
            "Competitive Alert Report",
            alert.title
        ))
        
        # Alert details
        elements.append(Paragraph("Alert Details", self.styles['SectionHeader']))
        
        risk_style = self._get_risk_style(alert.risk_level)
        elements.append(Paragraph(f"<b>Risk Level:</b> {alert.risk_level.upper()}", self.styles[risk_style]))
        elements.append(Paragraph(f"<b>Signal Type:</b> {alert.signal_type.replace('_', ' ').title()}", self.styles['BodyText']))
        elements.append(Paragraph(f"<b>Competitor:</b> {alert.competitor.name if alert.competitor else 'Unknown'}", self.styles['BodyText']))
        elements.append(Paragraph(f"<b>Source:</b> {alert.source_url}", self.styles['BodyText']))
        elements.append(Paragraph(f"<b>Detected:</b> {alert.detected_at.strftime('%B %d, %Y at %H:%M') if alert.detected_at else 'Unknown'}", self.styles['BodyText']))
        elements.append(Spacer(1, 15))
        
        # Summary
        elements.append(Paragraph("Summary", self.styles['SubHeader']))
        elements.append(Paragraph(alert.summary or "No summary available.", self.styles['BodyTextJustified']))
        elements.append(Spacer(1, 15))
        
        # Analysis
        if alert.relevance_explanation:
            elements.append(Paragraph("Relevance to Fluke", self.styles['SubHeader']))
            elements.append(Paragraph(alert.relevance_explanation, self.styles['BodyTextJustified']))
            elements.append(Spacer(1, 15))
        
        # Recommended Actions
        if alert.recommended_actions:
            elements.append(Paragraph("Recommended Actions", self.styles['SubHeader']))
            try:
                actions = json.loads(alert.recommended_actions)
                for action in actions:
                    action_text = action.get('action', str(action)) if isinstance(action, dict) else str(action)
                    owner = action.get('owner', '') if isinstance(action, dict) else ''
                    priority = action.get('priority', '') if isinstance(action, dict) else ''
                    elements.append(Paragraph(
                        f"• {action_text}" + (f" ({priority} - {owner})" if owner else ""),
                        self.styles['BulletPoint']
                    ))
            except:
                elements.append(Paragraph(alert.recommended_actions, self.styles['BodyText']))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    def export_alerts_summary_pdf(self, alerts: List[Alert], title: str = "Alerts Summary Report") -> io.BytesIO:
        """Export multiple alerts as a summary PDF."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        
        elements = []
        
        # Header
        elements.extend(self._create_header(title, f"Total Alerts: {len(alerts)}"))
        
        # Summary table
        if alerts:
            summary_data = [['#', 'Title', 'Risk', 'Type', 'Date']]
            for i, alert in enumerate(alerts, 1):
                summary_data.append([
                    str(i),
                    (alert.title[:40] + '...') if len(alert.title) > 40 else alert.title,
                    alert.risk_level.upper() if alert.risk_level else 'N/A',
                    alert.signal_type.replace('_', ' ').title() if alert.signal_type else 'N/A',
                    alert.detected_at.strftime('%m/%d/%Y') if alert.detected_at else 'N/A'
                ])
            
            table = Table(summary_data, colWidths=[0.4*inch, 3*inch, 0.8*inch, 1.2*inch, 0.8*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#ddd')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')])
            ]))
            elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    def export_csv(self, data: List[Dict], filename_prefix: str = "export") -> io.StringIO:
        """Export data as CSV."""
        buffer = io.StringIO()
        
        if not data:
            return buffer
        
        writer = csv.DictWriter(buffer, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        buffer.seek(0)
        return buffer
