"""
LLM-Powered Analysis Engine
Analyzes detected changes and generates actionable intelligence.
"""
import os
import json
import yaml
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from openai import OpenAI, AzureOpenAI
from .database import (
    db, Alert, PageSnapshot, NewsItem, Competitor,
    SignalType, RiskLevel, AlertStatus
)

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Result of LLM analysis."""
    summary: str
    signal_type: str
    risk_level: str
    risk_score: int
    confidence_score: int
    relevance_explanation: str
    assumptions: List[str]
    recommended_actions: List[Dict[str, str]]
    playbook_used: Optional[str]
    raw_analysis: Dict


class Analyzer:
    """LLM-powered competitive intelligence analyzer."""
    
    def __init__(self):
        self.client = self._init_client()
        self.fluke_context = self._load_fluke_context()
        self.playbooks = self._load_playbooks()
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
    
    def _init_client(self):
        """Initialize the OpenAI client."""
        if os.getenv('AZURE_OPENAI_ENDPOINT'):
            return AzureOpenAI(
                azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
                api_key=os.getenv('AZURE_OPENAI_KEY'),
                api_version=os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-15-preview')
            )
        else:
            return OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    def _load_fluke_context(self) -> str:
        """Load Fluke context document."""
        context_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'config', 'fluke_context.md'
        )
        try:
            with open(context_path, 'r') as f:
                return f.read()
        except FileNotFoundError:
            logger.warning("Fluke context file not found, using default")
            return self._get_default_fluke_context()
    
    def _get_default_fluke_context(self) -> str:
        """Default Fluke context if file not found."""
        return """
# Fluke Corporation - Company Context

## About Fluke
Fluke Corporation is a world leader in the manufacture, distribution, and service of 
electronic test tools, biomedical equipment, and networking solutions.

## Key Product Categories
- Digital Multimeters (DMMs)
- Clamp Meters
- Thermal Imaging Cameras
- Oscilloscopes
- Power Quality Analyzers
- Process Calibration Tools
- Insulation Testers

## Target Markets
- Industrial manufacturing
- Electrical contractors
- HVAC technicians
- Automotive diagnostics
- Healthcare/Biomedical

## Competitive Advantages
- Industry-leading accuracy and reliability
- Rugged design for field use
- Strong brand recognition
- Comprehensive warranty and support
- Integration with Fluke Connect software platform

## Strategic Priorities
1. Maintain leadership in core handheld test tool markets
2. Expand connected device ecosystem
3. Grow in emerging markets
4. Develop predictive maintenance solutions
"""
    
    def _load_playbooks(self) -> Dict:
        """Load response playbooks."""
        playbook_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'config', 'playbooks.yaml'
        )
        try:
            with open(playbook_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning("Playbooks file not found, using defaults")
            return self._get_default_playbooks()
    
    def _get_default_playbooks(self) -> Dict:
        """Default playbooks if file not found."""
        return {
            'playbooks': {
                'product_launch': {
                    'name': 'Competitor Product Launch',
                    'actions': [
                        {'action': 'Analyze product specifications', 'owner': 'Product Management', 'priority': 'high'},
                        {'action': 'Compare pricing vs Fluke products', 'owner': 'Pricing Team', 'priority': 'high'},
                        {'action': 'Assess impact on target markets', 'owner': 'Marketing', 'priority': 'medium'},
                        {'action': 'Update competitive battle cards', 'owner': 'Sales Enablement', 'priority': 'medium'},
                        {'action': 'Monitor customer reactions', 'owner': 'Customer Success', 'priority': 'low'}
                    ]
                },
                'pricing_change': {
                    'name': 'Competitor Pricing Change',
                    'actions': [
                        {'action': 'Validate pricing information', 'owner': 'Competitive Intelligence', 'priority': 'high'},
                        {'action': 'Analyze impact on win rates', 'owner': 'Sales Operations', 'priority': 'high'},
                        {'action': 'Review Fluke pricing strategy', 'owner': 'Pricing Team', 'priority': 'medium'},
                        {'action': 'Prepare sales team talking points', 'owner': 'Sales Enablement', 'priority': 'medium'}
                    ]
                },
                'partnership': {
                    'name': 'Competitor Partnership/Alliance',
                    'actions': [
                        {'action': 'Assess strategic implications', 'owner': 'Strategy', 'priority': 'high'},
                        {'action': 'Evaluate channel impact', 'owner': 'Channel Sales', 'priority': 'medium'},
                        {'action': 'Review Fluke partnership opportunities', 'owner': 'Business Development', 'priority': 'medium'}
                    ]
                },
                'acquisition': {
                    'name': 'Competitor Acquisition/Merger',
                    'actions': [
                        {'action': 'Analyze strategic rationale', 'owner': 'Strategy', 'priority': 'high'},
                        {'action': 'Assess market consolidation impact', 'owner': 'Strategy', 'priority': 'high'},
                        {'action': 'Review customer retention opportunities', 'owner': 'Sales', 'priority': 'medium'},
                        {'action': 'Monitor integration progress', 'owner': 'Competitive Intelligence', 'priority': 'low'}
                    ]
                },
                'default': {
                    'name': 'General Competitive Update',
                    'actions': [
                        {'action': 'Document and categorize change', 'owner': 'Competitive Intelligence', 'priority': 'medium'},
                        {'action': 'Assess relevance to Fluke', 'owner': 'Product Management', 'priority': 'medium'},
                        {'action': 'Determine if follow-up needed', 'owner': 'Competitive Intelligence', 'priority': 'low'}
                    ]
                }
            }
        }
    
    def _notify_teams(self, alert: Alert) -> bool:
        """Send alert notification to Teams if configured."""
        import requests
        
        webhook_url = os.environ.get('TEAMS_WEBHOOK_URL', '')
        if not webhook_url:
            return False
        
        # Check if already sent
        channels = alert.notification_channels or ''
        if 'teams' in channels:
            return True
        
        try:
            # Build Adaptive Card
            risk_emojis = {
                'critical': '🔴', 'high': '🟠', 
                'medium': '🟡', 'low': '🟢', 'info': 'ℹ️'
            }
            
            adaptive_card = {
                "type": "AdaptiveCard",
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "version": "1.4",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": f"🚨 {alert.title}",
                        "weight": "Bolder",
                        "size": "Large",
                        "wrap": True
                    },
                    {
                        "type": "FactSet",
                        "facts": [
                            {"title": "Competitor", "value": alert.competitor.name if alert.competitor else 'Unknown'},
                            {"title": "Risk Level", "value": f"{risk_emojis.get(alert.risk_level or 'medium', '⚪')} {(alert.risk_level or 'medium').upper()}"},
                            {"title": "Detected", "value": alert.detected_at.strftime('%Y-%m-%d %H:%M UTC') if alert.detected_at else 'Now'}
                        ]
                    },
                    {
                        "type": "TextBlock",
                        "text": (alert.summary or 'No details')[:300],
                        "wrap": True,
                        "spacing": "Medium"
                    }
                ],
                "actions": [
                    {
                        "type": "Action.OpenUrl",
                        "title": "View in CompIQ",
                        "url": f"https://compiq-app.azurewebsites.net/alerts/{alert.id}"
                    }
                ]
            }
            
            if alert.source_url:
                adaptive_card["actions"].append({
                    "type": "Action.OpenUrl",
                    "title": "View Source",
                    "url": alert.source_url
                })
            
            # Send raw Adaptive Card directly - Power Automate flow passes it to Teams
            response = requests.post(webhook_url, json=adaptive_card, timeout=15)
            if response.status_code in [200, 202]:
                alert.notification_sent = True
                alert.notification_channels = (channels + ',teams').strip(',')
                db.session.commit()
                logger.info(f"Sent alert {alert.id} to Teams")
                return True
            else:
                logger.warning(f"Teams webhook returned {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error sending alert {alert.id} to Teams: {e}")
            return False
    
    def _generate_insight(self, alert: Alert) -> bool:
        """Auto-generate insight for significant alerts."""
        try:
            from .insights import InsightsGenerator
            
            generator = InsightsGenerator()
            insight = generator.generate_from_alert(alert)
            
            if insight:
                logger.info(f"Auto-generated insight {insight.id} for alert {alert.id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error auto-generating insight for alert {alert.id}: {e}")
            return False
    
    def _build_analysis_prompt(
        self, 
        content: str, 
        competitor_name: str,
        source_type: str,
        additional_context: Optional[str] = None
    ) -> str:
        """Build the analysis prompt for the LLM."""
        playbook_summary = "\n".join([
            f"- {name}: {pb.get('name', name)}"
            for name, pb in self.playbooks.get('playbooks', {}).items()
        ])
        
        return f"""You are a competitive intelligence analyst for Fluke Corporation. 
Analyze the following {source_type} from competitor "{competitor_name}" and provide actionable intelligence.

## FLUKE CONTEXT
{self.fluke_context}

## CONTENT TO ANALYZE
{content}

{f"## ADDITIONAL CONTEXT{chr(10)}{additional_context}" if additional_context else ""}

## AVAILABLE RESPONSE PLAYBOOKS
{playbook_summary}

## YOUR TASK
Analyze this content and provide a structured assessment. Be specific and actionable.

## PRIORITY GUIDANCE
- Partnership signals should generally be rated HIGH risk (risk_score 65-85) as they can significantly alter competitive dynamics
- Partnerships with major tech companies (Microsoft, Google, Amazon, Siemens, Schneider Electric, etc.) should be rated HIGH (risk_score 75-90)
- Partnerships with industry leaders or Fortune 500 companies warrant HIGH priority
- Only rate partnerships as CRITICAL (risk_score 85+) if they directly threaten Fluke's core markets or involve exclusive deals
- Smaller partnerships with regional distributors or niche players can remain MEDIUM (risk_score 45-65)

Respond with a JSON object containing:
{{
    "summary": "2-3 sentence executive summary of the change/news",
    "signal_type": "one of: product_launch, pricing_change, feature_update, partnership, acquisition, leadership_change, marketing_campaign, certification, expansion, regulatory, other",
    "risk_level": "one of: critical, high, medium, low, info",
    "risk_score": "0-100 integer, where 100 is highest risk to Fluke",
    "confidence_score": "0-100 integer, your confidence in this analysis",
    "relevance_to_fluke": "Explain specifically how this impacts Fluke's business",
    "key_details": ["list", "of", "important", "specific", "details"],
    "assumptions": ["list", "of", "assumptions", "you", "made"],
    "recommended_playbook": "name of the most appropriate playbook from the list above",
    "immediate_actions": [
        {{"action": "specific action to take", "owner": "team/role", "priority": "high/medium/low", "rationale": "why this matters"}}
    ],
    "questions_to_answer": ["list", "of", "questions", "that", "need", "investigation"],
    "monitoring_recommendations": "What should we continue to watch for?"
}}

Be concise but thorough. Focus on actionable intelligence."""

    def analyze_content(
        self,
        content: str,
        competitor_name: str,
        source_type: str = "update",
        additional_context: Optional[str] = None
    ) -> AnalysisResult:
        """
        Analyze content using LLM and return structured results.
        
        Args:
            content: The content to analyze (page diff, news article, etc.)
            competitor_name: Name of the competitor
            source_type: Type of content (page_change, news, etc.)
            additional_context: Optional additional context
            
        Returns:
            AnalysisResult with structured analysis
        """
        prompt = self._build_analysis_prompt(
            content, competitor_name, source_type, additional_context
        )
        
        try:
            if os.getenv('AZURE_OPENAI_ENDPOINT'):
                deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4')
                response = self.client.chat.completions.create(
                    model=deployment,
                    messages=[
                        {"role": "system", "content": "You are a competitive intelligence analyst. Respond only with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a competitive intelligence analyst. Respond only with valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
            
            result_text = response.choices[0].message.content
            result_json = json.loads(result_text)
            
            # Map signal type
            signal_type = result_json.get('signal_type', 'other')
            if signal_type not in [st.value for st in SignalType]:
                signal_type = SignalType.OTHER.value
            
            # Map risk level
            risk_level = result_json.get('risk_level', 'medium')
            if risk_level not in [rl.value for rl in RiskLevel]:
                risk_level = RiskLevel.MEDIUM.value
            
            # Get playbook actions
            playbook_name = result_json.get('recommended_playbook', 'default')
            playbook = self.playbooks.get('playbooks', {}).get(playbook_name, {})
            playbook_actions = playbook.get('actions', [])
            
            # Combine LLM actions with playbook actions
            immediate_actions = result_json.get('immediate_actions', [])
            all_actions = immediate_actions + playbook_actions
            
            return AnalysisResult(
                summary=result_json.get('summary', 'Analysis completed'),
                signal_type=signal_type,
                risk_level=risk_level,
                risk_score=min(100, max(0, int(result_json.get('risk_score', 50)))),
                confidence_score=min(100, max(0, int(result_json.get('confidence_score', 70)))),
                relevance_explanation=result_json.get('relevance_to_fluke', ''),
                assumptions=result_json.get('assumptions', []),
                recommended_actions=all_actions,
                playbook_used=playbook_name,
                raw_analysis=result_json
            )
            
        except Exception as e:
            logger.error(f"Error during LLM analysis: {e}")
            # Return a default result on error
            return AnalysisResult(
                summary=f"Error analyzing content: {str(e)}",
                signal_type=SignalType.OTHER.value,
                risk_level=RiskLevel.MEDIUM.value,
                risk_score=50,
                confidence_score=0,
                relevance_explanation="Analysis failed",
                assumptions=["Analysis could not be completed"],
                recommended_actions=[{
                    "action": "Manual review required",
                    "owner": "Competitive Intelligence",
                    "priority": "high"
                }],
                playbook_used=None,
                raw_analysis={"error": str(e)}
            )
    
    def analyze_page_change(self, snapshot: PageSnapshot) -> Alert:
        """Analyze a page change and create an alert."""
        monitored_url = snapshot.monitored_url
        competitor = monitored_url.competitor
        
        # Prepare content for analysis
        content = f"""
## Page Changed
URL: {monitored_url.url}
Page Type: {monitored_url.page_type}
Change Detected: {snapshot.captured_at}

## Changes Detected
{snapshot.diff_summary or 'Full page content changed'}

## Current Page Content (excerpt)
{snapshot.extracted_text[:3000] if snapshot.extracted_text else 'Content not available'}
"""
        
        # Run analysis
        result = self.analyze_content(
            content=content,
            competitor_name=competitor.name,
            source_type="page change",
            additional_context=f"This is a {monitored_url.page_type} page"
        )
        
        # Create alert
        alert = Alert(
            competitor_id=competitor.id,
            source_type='page_change',
            source_id=snapshot.id,
            source_url=monitored_url.url,
            title=f"{competitor.name}: {result.signal_type.replace('_', ' ').title()} Detected",
            summary=result.summary,
            raw_content=snapshot.extracted_text[:10000] if snapshot.extracted_text else None,
            diff_content=snapshot.diff_summary,
            signal_type=result.signal_type,
            risk_level=result.risk_level,
            risk_score=result.risk_score,
            confidence_score=result.confidence_score,
            analysis=json.dumps(result.raw_analysis),
            relevance_explanation=result.relevance_explanation,
            assumptions='\n'.join(f"• {a}" for a in result.assumptions),
            recommended_actions=json.dumps(result.recommended_actions),
            playbook_used=result.playbook_used,
            status=AlertStatus.NEW.value
        )
        
        db.session.add(alert)
        db.session.commit()
        
        # Auto-send to Teams if configured
        self._notify_teams(alert)
        
        # Auto-generate insight for significant alerts
        if result.risk_level in ['critical', 'high']:
            self._generate_insight(alert)
        
        logger.info(f"Created alert {alert.id} for page change on {monitored_url.url}")
        return alert
    
    def _has_recent_alert(self, source_url: str, hours: int = 6) -> bool:
        """Check if an alert was created for this source URL within the specified hours."""
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        existing_alert = Alert.query.filter(
            Alert.source_url == source_url,
            Alert.detected_at >= cutoff_time
        ).first()
        
        return existing_alert is not None
    
    def analyze_news_item(self, news_item: NewsItem) -> Optional[Alert]:
        """Analyze a news item and optionally create an alert."""
        # Rate limit: Only one alert per source URL every 6 hours
        if self._has_recent_alert(news_item.url, hours=6):
            logger.info(f"Skipping news item (rate limited - recent alert exists): {news_item.title[:50]}")
            news_item.is_processed = True
            db.session.commit()
            return None
        
        competitor = news_item.competitor if news_item.competitor_id else None
        competitor_name = competitor.name if competitor else "Unknown"
        
        # Prepare content for analysis
        content = f"""
## News Article
Title: {news_item.title}
Source: {news_item.source}
Published: {news_item.published_at}
URL: {news_item.url}

## Article Content
{news_item.description or ''}

{news_item.content or ''}
"""
        
        # Run analysis
        result = self.analyze_content(
            content=content,
            competitor_name=competitor_name,
            source_type="news article"
        )
        
        # Mark as processed
        news_item.is_processed = True
        news_item.is_relevant = result.risk_score >= int(os.getenv('MIN_CONFIDENCE_THRESHOLD', 40))
        
        # Only create alert if relevant enough
        if not news_item.is_relevant:
            db.session.commit()
            return None
        
        # Create alert
        alert = Alert(
            competitor_id=news_item.competitor_id,
            source_type='news',
            source_id=news_item.id,
            source_url=news_item.url,
            title=f"{competitor_name}: {news_item.title[:100]}",
            summary=result.summary,
            raw_content=f"{news_item.description or ''}\n\n{news_item.content or ''}",
            signal_type=result.signal_type,
            risk_level=result.risk_level,
            risk_score=result.risk_score,
            confidence_score=result.confidence_score,
            analysis=json.dumps(result.raw_analysis),
            relevance_explanation=result.relevance_explanation,
            assumptions='\n'.join(f"• {a}" for a in result.assumptions),
            recommended_actions=json.dumps(result.recommended_actions),
            playbook_used=result.playbook_used,
            status=AlertStatus.NEW.value
        )
        
        db.session.add(alert)
        db.session.commit()
        
        # Auto-send to Teams if configured
        self._notify_teams(alert)
        
        # Auto-generate insight for significant alerts
        if result.risk_level in ['critical', 'high']:
            self._generate_insight(alert)
        
        logger.info(f"Created alert {alert.id} for news item: {news_item.title[:50]}")
        return alert
    
    def process_pending_items(self) -> Dict[str, int]:
        """Process all pending page changes and news items."""
        results = {
            'page_changes_processed': 0,
            'news_processed': 0,
            'alerts_created': 0
        }
        
        # Process page changes that don't have alerts yet
        unprocessed_snapshots = PageSnapshot.query.filter(
            PageSnapshot.has_changes == True
        ).outerjoin(
            Alert, 
            (Alert.source_type == 'page_change') & (Alert.source_id == PageSnapshot.id)
        ).filter(Alert.id == None).all()
        
        for snapshot in unprocessed_snapshots:
            try:
                alert = self.analyze_page_change(snapshot)
                results['page_changes_processed'] += 1
                results['alerts_created'] += 1
            except Exception as e:
                logger.error(f"Error processing snapshot {snapshot.id}: {e}")
        
        # Process unprocessed news items
        unprocessed_news = NewsItem.query.filter_by(is_processed=False).all()
        
        for news_item in unprocessed_news:
            try:
                alert = self.analyze_news_item(news_item)
                results['news_processed'] += 1
                if alert:
                    results['alerts_created'] += 1
            except Exception as e:
                logger.error(f"Error processing news item {news_item.id}: {e}")
        
        return results


def run_analyzer():
    """Run the analyzer as a standalone process."""
    from . import create_app
    
    app = create_app()
    
    with app.app_context():
        analyzer = Analyzer()
        results = analyzer.process_pending_items()
        
        print(f"\n{'='*60}")
        print("ANALYSIS COMPLETE")
        print(f"{'='*60}")
        print(f"Page changes processed: {results['page_changes_processed']}")
        print(f"News items processed: {results['news_processed']}")
        print(f"Alerts created: {results['alerts_created']}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_analyzer()
