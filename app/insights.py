"""
AI-Powered Insights Generator
Generates team-specific insights with product comparisons.
"""
import os
import json
import yaml
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from openai import OpenAI, AzureOpenAI
from .database import (
    db, Insight, Alert, NewsItem, Competitor
)

logger = logging.getLogger(__name__)


class InsightsGenerator:
    """Generates AI-powered competitive insights for different teams."""
    
    def __init__(self):
        self.client = self._init_client()
        self.fluke_products = self._load_fluke_products()
    
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
    
    def _get_model(self) -> str:
        """Get the model/deployment name."""
        if os.getenv('AZURE_OPENAI_ENDPOINT'):
            return os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4')
        return os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
    
    def _load_fluke_products(self) -> Dict:
        """Load Fluke product catalog for comparisons."""
        return {
            "multimeters": {
                "Fluke 87V": {
                    "category": "Industrial Digital Multimeter",
                    "price_range": "$400-450",
                    "key_features": ["True-RMS", "10,000 count display", "Built-in thermometer", "Low-pass filter", "IP67 rated"],
                    "target_market": "Industrial electricians, maintenance technicians"
                },
                "Fluke 117": {
                    "category": "Electrician's Digital Multimeter",
                    "price_range": "$200-250",
                    "key_features": ["True-RMS", "AutoVolt", "Non-contact voltage detection", "LoZ function"],
                    "target_market": "Commercial electricians"
                },
                "Fluke 179": {
                    "category": "Digital Multimeter",
                    "price_range": "$350-400",
                    "key_features": ["True-RMS", "Temperature measurement", "Backlit display", "Manual and auto ranging"],
                    "target_market": "Field service technicians"
                }
            },
            "clamp_meters": {
                "Fluke 376 FC": {
                    "category": "True-RMS Clamp Meter",
                    "price_range": "$500-550",
                    "key_features": ["1000A AC/DC", "Fluke Connect compatible", "iFlex probe compatible", "VFD mode"],
                    "target_market": "Industrial maintenance"
                },
                "Fluke 323": {
                    "category": "True-RMS Clamp Meter",
                    "price_range": "$150-180",
                    "key_features": ["400A AC", "True-RMS", "Slim jaw design", "CAT IV 300V"],
                    "target_market": "Residential/commercial electricians"
                }
            },
            "insulation_testers": {
                "Fluke 1587 FC": {
                    "category": "Insulation Multimeter",
                    "price_range": "$1,200-1,400",
                    "key_features": ["Insulation testing + DMM", "Fluke Connect", "PI/DAR testing", "50V to 1000V test voltages"],
                    "target_market": "Motor maintenance, industrial electricians"
                },
                "Fluke 1507": {
                    "category": "Insulation Tester",
                    "price_range": "$700-800",
                    "key_features": ["50V to 1000V", "Auto-discharge", "Remote probe", "Comparison storage"],
                    "target_market": "Electrical contractors"
                }
            },
            "power_analyzers": {
                "Fluke 435-II": {
                    "category": "Power Quality Analyzer",
                    "price_range": "$7,000-8,000",
                    "key_features": ["Energy loss analysis", "Power inverter efficiency", "Unbalance analysis", "Transient capture"],
                    "target_market": "Power quality engineers, utilities"
                },
                "Fluke 1770 Series": {
                    "category": "Power Quality Analyzer",
                    "price_range": "$10,000-15,000",
                    "key_features": ["IEC 61000-4-30 Class A", "GPS time sync", "Long-term logging", "Power quality events"],
                    "target_market": "Utilities, large industrial facilities"
                }
            },
            "thermal_imagers": {
                "Fluke Ti480 PRO": {
                    "category": "Thermal Imaging Camera",
                    "price_range": "$15,000-18,000",
                    "key_features": ["640x480 resolution", "MultiSharp Focus", "LaserSharp Auto Focus", "-20°C to 800°C"],
                    "target_market": "Predictive maintenance, electrical inspection"
                },
                "Fluke PTi120": {
                    "category": "Pocket Thermal Imager",
                    "price_range": "$600-700",
                    "key_features": ["120x90 resolution", "Pocket-sized", "-20°C to 150°C", "Fluke Connect"],
                    "target_market": "HVAC technicians, quick inspections"
                }
            }
        }
    
    def _build_insight_prompt(self, content: str, competitor_name: str, source_type: str) -> str:
        """Build the prompt for generating insights."""
        fluke_products_str = json.dumps(self.fluke_products, indent=2)
        
        prompt = f"""You are a competitive intelligence analyst for Fluke Corporation, a leader in electronic test and measurement equipment.

Analyze the following competitive intelligence about {competitor_name} and generate comprehensive insights for our teams.

CONTENT TO ANALYZE:
{content}

SOURCE TYPE: {source_type}

FLUKE PRODUCT CATALOG (for comparison):
{fluke_products_str}

Generate a detailed analysis in JSON format with the following structure:
{{
    "title": "Brief, impactful title summarizing the competitive insight",
    "executive_summary": "2-3 sentence summary for executives",
    
    "competitor_product": "Name of competitor's product mentioned (if any)",
    "fluke_product": "Most directly competing Fluke product",
    "comparison_summary": "Brief comparison of the two products",
    
    "competitor_advantages": ["List of competitor's advantages over Fluke"],
    "fluke_advantages": ["List of Fluke's advantages to emphasize"],
    
    "pricing_comparison": "Analysis of pricing differences and implications",
    
    "feature_comparison": {{
        "feature_name": {{
            "competitor": "Competitor's spec/capability",
            "fluke": "Fluke's spec/capability",
            "winner": "competitor/fluke/tie",
            "importance": "high/medium/low"
        }}
    }},
    
    "sales_insights": {{
        "summary": "Key message for sales team",
        "talking_points": ["Point 1", "Point 2"],
        "objection_handlers": ["How to handle objection 1", "How to handle objection 2"],
        "competitive_positioning": "How to position Fluke against this",
        "target_opportunities": ["Type of customer/deal to target"],
        "urgency": "high/medium/low"
    }},
    
    "marketing_insights": {{
        "summary": "Key message for marketing team",
        "messaging_recommendations": ["Message 1", "Message 2"],
        "content_ideas": ["Blog post idea", "Case study idea"],
        "campaign_suggestions": ["Campaign idea"],
        "social_media_response": "Suggested social media approach",
        "urgency": "high/medium/low"
    }},
    
    "product_insights": {{
        "summary": "Key message for product team",
        "feature_gaps": ["Feature we should consider adding"],
        "roadmap_implications": "Impact on product roadmap",
        "innovation_opportunities": ["Opportunity 1"],
        "customer_feedback_to_gather": ["Question to ask customers"],
        "urgency": "high/medium/low"
    }},
    
    "engineering_insights": {{
        "summary": "Key message for engineering team",
        "technical_analysis": "Technical comparison of capabilities",
        "r_and_d_priorities": ["Priority 1"],
        "patent_considerations": "Any IP implications",
        "urgency": "high/medium/low"
    }},
    
    "executive_insights": {{
        "summary": "Key message for executives",
        "strategic_implications": "Long-term strategic impact",
        "market_share_risk": "Estimated impact on market share",
        "investment_recommendations": ["Recommendation 1"],
        "competitive_response_options": ["Option 1", "Option 2"],
        "urgency": "high/medium/low"
    }},
    
    "immediate_actions": ["Action items for next 24-48 hours"],
    "short_term_actions": ["Action items for next 1-4 weeks"],
    "long_term_actions": ["Strategic actions for next quarter"],
    
    "impact_score": 75,  // 0-100, how impactful is this for Fluke
    "urgency_score": 80,  // 0-100, how urgently should we respond
    "confidence_score": 85  // 0-100, confidence in this analysis
}}

Be specific and actionable. Reference actual Fluke products where relevant.
If the content doesn't clearly indicate a product launch or competitive threat, still provide useful market intelligence.
"""
        return prompt
    
    def generate_insight(self, content: str, competitor_name: str, 
                        source_type: str = "news",
                        alert_id: Optional[int] = None,
                        news_item_id: Optional[int] = None,
                        competitor_id: Optional[int] = None) -> Optional[Insight]:
        """Generate an insight from content."""
        
        # Check for existing insight (deduplication)
        if alert_id:
            existing = Insight.query.filter_by(alert_id=alert_id).first()
            if existing:
                logger.info(f"Insight already exists for alert {alert_id}, skipping")
                return existing
        
        if news_item_id:
            existing = Insight.query.filter_by(news_item_id=news_item_id).first()
            if existing:
                logger.info(f"Insight already exists for news item {news_item_id}, skipping")
                return existing
        
        prompt = self._build_insight_prompt(content, competitor_name, source_type)
        
        try:
            model = self._get_model()
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a competitive intelligence analyst. Respond only with valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            result = json.loads(result_text)
            
            # Create Insight record
            insight = Insight(
                alert_id=alert_id,
                news_item_id=news_item_id,
                competitor_id=competitor_id,
                title=result.get('title', 'Competitive Intelligence Update'),
                executive_summary=result.get('executive_summary'),
                competitor_product=result.get('competitor_product'),
                fluke_product=result.get('fluke_product'),
                comparison_summary=result.get('comparison_summary'),
                competitor_advantages=json.dumps(result.get('competitor_advantages', [])),
                fluke_advantages=json.dumps(result.get('fluke_advantages', [])),
                pricing_comparison=result.get('pricing_comparison'),
                feature_comparison=json.dumps(result.get('feature_comparison', {})),
                sales_insights=json.dumps(result.get('sales_insights', {})),
                marketing_insights=json.dumps(result.get('marketing_insights', {})),
                product_insights=json.dumps(result.get('product_insights', {})),
                engineering_insights=json.dumps(result.get('engineering_insights', {})),
                executive_insights=json.dumps(result.get('executive_insights', {})),
                immediate_actions=json.dumps(result.get('immediate_actions', [])),
                short_term_actions=json.dumps(result.get('short_term_actions', [])),
                long_term_actions=json.dumps(result.get('long_term_actions', [])),
                impact_score=result.get('impact_score', 50),
                urgency_score=result.get('urgency_score', 50),
                confidence_score=result.get('confidence_score', 50)
            )
            
            db.session.add(insight)
            db.session.commit()
            
            logger.info(f"Generated insight: {insight.title}")
            return insight
            
        except Exception as e:
            logger.error(f"Error generating insight: {e}")
            return None
    
    def generate_from_alert(self, alert: Alert) -> Optional[Insight]:
        """Generate insight from an alert."""
        content = f"""
Title: {alert.title}
Summary: {alert.summary}
Source: {alert.source_url}
Signal Type: {alert.signal_type}
Risk Level: {alert.risk_level}

Raw Content:
{alert.raw_content or alert.summary}
"""
        return self.generate_insight(
            content=content,
            competitor_name=alert.competitor.name,
            source_type=alert.source_type,
            alert_id=alert.id,
            competitor_id=alert.competitor_id
        )
    
    def generate_from_news(self, news_item: NewsItem) -> Optional[Insight]:
        """Generate insight from a news item."""
        competitor = Competitor.query.get(news_item.competitor_id)
        competitor_name = competitor.name if competitor else "Unknown Competitor"
        
        content = f"""
Title: {news_item.title}
Source: {news_item.source}
Published: {news_item.published_at}

Description:
{news_item.description or ''}

Content:
{news_item.content or news_item.description or ''}
"""
        return self.generate_insight(
            content=content,
            competitor_name=competitor_name,
            source_type="news",
            news_item_id=news_item.id,
            competitor_id=news_item.competitor_id
        )
    
    def generate_batch_insights(self, limit: int = 10) -> List[Insight]:
        """Generate insights for unprocessed high-priority alerts and news."""
        insights = []
        
        # Get high-risk alerts without insights
        alerts = Alert.query.filter(
            Alert.risk_level.in_(['critical', 'high']),
            ~Alert.id.in_(db.session.query(Insight.alert_id).filter(Insight.alert_id.isnot(None)))
        ).order_by(Alert.detected_at.desc()).limit(limit // 2).all()
        
        for alert in alerts:
            insight = self.generate_from_alert(alert)
            if insight:
                insights.append(insight)
                logger.info(f"Generated insight for alert: {alert.title}")
        
        # Get recent relevant news without insights
        news_items = NewsItem.query.filter(
            NewsItem.is_relevant == True,
            ~NewsItem.id.in_(db.session.query(Insight.news_item_id).filter(Insight.news_item_id.isnot(None)))
        ).order_by(NewsItem.collected_at.desc()).limit(limit // 2).all()
        
        for news in news_items:
            insight = self.generate_from_news(news)
            if insight:
                insights.append(insight)
                logger.info(f"Generated insight for news: {news.title}")
        
        return insights


def run_insights_generator():
    """Run the insights generator as a standalone process."""
    from . import create_app
    
    app = create_app()
    
    with app.app_context():
        generator = InsightsGenerator()
        insights = generator.generate_batch_insights(limit=10)
        
        print(f"\n{'='*60}")
        print(f"GENERATED {len(insights)} INSIGHTS")
        print(f"{'='*60}\n")
        
        for insight in insights:
            print(f"\n{insight.title}")
            print(f"  Impact: {insight.impact_score}, Urgency: {insight.urgency_score}")
            if insight.competitor_product and insight.fluke_product:
                print(f"  Comparison: {insight.competitor_product} vs {insight.fluke_product}")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_insights_generator()
