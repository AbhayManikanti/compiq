"""
Database Models for Competitor Monitor
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from enum import Enum
import json

db = SQLAlchemy()


class SignalType(str, Enum):
    """Types of competitive signals detected."""
    PRODUCT_LAUNCH = "product_launch"
    PRICING_CHANGE = "pricing_change"
    FEATURE_UPDATE = "feature_update"
    PARTNERSHIP = "partnership"
    ACQUISITION = "acquisition"
    LEADERSHIP_CHANGE = "leadership_change"
    MARKETING_CAMPAIGN = "marketing_campaign"
    CERTIFICATION = "certification"
    EXPANSION = "expansion"
    REGULATORY = "regulatory"
    OTHER = "other"


class RiskLevel(str, Enum):
    """Risk level classification."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Status of an alert."""
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class Competitor(db.Model):
    """Competitor being monitored."""
    __tablename__ = 'competitors'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    website = db.Column(db.String(500))
    logo_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    monitored_urls = db.relationship('MonitoredURL', backref='competitor', lazy='dynamic')
    alerts = db.relationship('Alert', backref='competitor', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'website': self.website,
            'logo_url': self.logo_url,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'url_count': self.monitored_urls.count(),
            'alert_count': self.alerts.filter_by(status=AlertStatus.NEW.value).count()
        }


class MonitoredURL(db.Model):
    """URLs being monitored for changes."""
    __tablename__ = 'monitored_urls'
    
    id = db.Column(db.Integer, primary_key=True)
    competitor_id = db.Column(db.Integer, db.ForeignKey('competitors.id'), nullable=False)
    url = db.Column(db.String(1000), nullable=False)
    name = db.Column(db.String(255))
    page_type = db.Column(db.String(100))  # product_page, pricing_page, news_page, etc.
    
    # Monitoring settings
    check_interval_hours = db.Column(db.Integer, default=24)
    last_checked_at = db.Column(db.DateTime)
    last_content_hash = db.Column(db.String(64))
    last_content = db.Column(db.Text)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    last_error = db.Column(db.Text)
    consecutive_errors = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    snapshots = db.relationship('PageSnapshot', backref='monitored_url', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'competitor_id': self.competitor_id,
            'url': self.url,
            'name': self.name,
            'page_type': self.page_type,
            'check_interval_hours': self.check_interval_hours,
            'last_checked_at': self.last_checked_at.isoformat() if self.last_checked_at else None,
            'is_active': self.is_active,
            'last_error': self.last_error,
            'consecutive_errors': self.consecutive_errors
        }


class PageSnapshot(db.Model):
    """Historical snapshots of monitored pages."""
    __tablename__ = 'page_snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    monitored_url_id = db.Column(db.Integer, db.ForeignKey('monitored_urls.id'), nullable=False)
    
    content_hash = db.Column(db.String(64), nullable=False)
    content = db.Column(db.Text)
    extracted_text = db.Column(db.Text)
    
    # Change detection
    has_changes = db.Column(db.Boolean, default=False)
    diff_summary = db.Column(db.Text)
    
    captured_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'monitored_url_id': self.monitored_url_id,
            'content_hash': self.content_hash,
            'has_changes': self.has_changes,
            'diff_summary': self.diff_summary,
            'captured_at': self.captured_at.isoformat() if self.captured_at else None
        }


class NewsItem(db.Model):
    """News articles and mentions collected."""
    __tablename__ = 'news_items'
    
    id = db.Column(db.Integer, primary_key=True)
    competitor_id = db.Column(db.Integer, db.ForeignKey('competitors.id'))
    
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text)
    url = db.Column(db.String(1000))
    source = db.Column(db.String(255))
    author = db.Column(db.String(255))
    
    published_at = db.Column(db.DateTime)
    collected_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Processing status
    is_processed = db.Column(db.Boolean, default=False)
    is_relevant = db.Column(db.Boolean)
    
    # Relationship to Competitor
    competitor = db.relationship('Competitor', backref=db.backref('news_items', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'competitor_id': self.competitor_id,
            'title': self.title,
            'description': self.description,
            'url': self.url,
            'source': self.source,
            'author': self.author,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'collected_at': self.collected_at.isoformat() if self.collected_at else None,
            'is_processed': self.is_processed,
            'is_relevant': self.is_relevant
        }


class Alert(db.Model):
    """Alerts generated from detected changes."""
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    competitor_id = db.Column(db.Integer, db.ForeignKey('competitors.id'), nullable=False)
    
    # Source reference
    source_type = db.Column(db.String(50))  # 'page_change', 'news', 'manual'
    source_id = db.Column(db.Integer)  # ID of PageSnapshot or NewsItem
    source_url = db.Column(db.String(1000))
    
    # Alert content
    title = db.Column(db.String(500), nullable=False)
    summary = db.Column(db.Text)
    raw_content = db.Column(db.Text)
    diff_content = db.Column(db.Text)
    
    # Classification
    signal_type = db.Column(db.String(50))
    risk_level = db.Column(db.String(20))
    risk_score = db.Column(db.Integer)  # 0-100
    confidence_score = db.Column(db.Integer)  # 0-100
    
    # LLM Analysis
    analysis = db.Column(db.Text)  # JSON with full LLM analysis
    relevance_explanation = db.Column(db.Text)
    assumptions = db.Column(db.Text)
    
    # Playbook Response
    recommended_actions = db.Column(db.Text)  # JSON array
    playbook_used = db.Column(db.String(100))
    
    # Status
    status = db.Column(db.String(20), default=AlertStatus.NEW.value)
    assigned_to = db.Column(db.String(255))
    resolution_notes = db.Column(db.Text)
    
    # Timestamps
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    acknowledged_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    
    # Notification tracking
    notification_sent = db.Column(db.Boolean, default=False)
    notification_channels = db.Column(db.String(255))  # comma-separated
    
    def to_dict(self):
        return {
            'id': self.id,
            'competitor_id': self.competitor_id,
            'competitor_name': self.competitor.name if self.competitor else None,
            'source_type': self.source_type,
            'source_url': self.source_url,
            'title': self.title,
            'summary': self.summary,
            'signal_type': self.signal_type,
            'risk_level': self.risk_level,
            'risk_score': self.risk_score,
            'confidence_score': self.confidence_score,
            'analysis': json.loads(self.analysis) if self.analysis else None,
            'relevance_explanation': self.relevance_explanation,
            'assumptions': self.assumptions,
            'recommended_actions': json.loads(self.recommended_actions) if self.recommended_actions else None,
            'playbook_used': self.playbook_used,
            'status': self.status,
            'assigned_to': self.assigned_to,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }
    
    def get_analysis(self):
        """Get parsed analysis JSON."""
        if self.analysis:
            return json.loads(self.analysis)
        return {}
    
    def get_recommended_actions(self):
        """Get parsed recommended actions."""
        if self.recommended_actions:
            return json.loads(self.recommended_actions)
        return []


class AuditLog(db.Model):
    """Audit log for tracking all activities."""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.Text)
    user = db.Column(db.String(255))
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'details': self.details,
            'user': self.user,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class TeamType(str, Enum):
    """Teams that receive insights."""
    SALES = "sales"
    MARKETING = "marketing"
    PRODUCT = "product"
    ENGINEERING = "engineering"
    EXECUTIVE = "executive"
    PRICING = "pricing"
    SUPPORT = "support"


class Insight(db.Model):
    """AI-generated insights with team-specific recommendations."""
    __tablename__ = 'insights'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Source reference
    alert_id = db.Column(db.Integer, db.ForeignKey('alerts.id'))
    news_item_id = db.Column(db.Integer, db.ForeignKey('news_items.id'))
    competitor_id = db.Column(db.Integer, db.ForeignKey('competitors.id'))
    
    # Insight content
    title = db.Column(db.String(500), nullable=False)
    executive_summary = db.Column(db.Text)
    
    # Product comparison
    competitor_product = db.Column(db.String(255))
    fluke_product = db.Column(db.String(255))
    comparison_summary = db.Column(db.Text)
    competitor_advantages = db.Column(db.Text)  # JSON array
    fluke_advantages = db.Column(db.Text)  # JSON array
    pricing_comparison = db.Column(db.Text)
    feature_comparison = db.Column(db.Text)  # JSON object
    
    # Team-specific recommendations (JSON objects)
    sales_insights = db.Column(db.Text)
    marketing_insights = db.Column(db.Text)
    product_insights = db.Column(db.Text)
    engineering_insights = db.Column(db.Text)
    executive_insights = db.Column(db.Text)
    
    # Action items
    immediate_actions = db.Column(db.Text)  # JSON array
    short_term_actions = db.Column(db.Text)  # JSON array
    long_term_actions = db.Column(db.Text)  # JSON array
    
    # Metadata
    impact_score = db.Column(db.Integer)  # 0-100
    urgency_score = db.Column(db.Integer)  # 0-100
    confidence_score = db.Column(db.Integer)  # 0-100
    
    # Status
    is_reviewed = db.Column(db.Boolean, default=False)
    reviewed_by = db.Column(db.String(255))
    reviewed_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    alert = db.relationship('Alert', backref='insights')
    news_item = db.relationship('NewsItem', backref='insights')
    competitor = db.relationship('Competitor', backref='insights')
    
    def to_dict(self):
        return {
            'id': self.id,
            'alert_id': self.alert_id,
            'news_item_id': self.news_item_id,
            'competitor_id': self.competitor_id,
            'competitor_name': self.competitor.name if self.competitor else None,
            'title': self.title,
            'executive_summary': self.executive_summary,
            'competitor_product': self.competitor_product,
            'fluke_product': self.fluke_product,
            'comparison_summary': self.comparison_summary,
            'competitor_advantages': json.loads(self.competitor_advantages) if self.competitor_advantages else [],
            'fluke_advantages': json.loads(self.fluke_advantages) if self.fluke_advantages else [],
            'pricing_comparison': self.pricing_comparison,
            'feature_comparison': json.loads(self.feature_comparison) if self.feature_comparison else {},
            'sales_insights': json.loads(self.sales_insights) if self.sales_insights else {},
            'marketing_insights': json.loads(self.marketing_insights) if self.marketing_insights else {},
            'product_insights': json.loads(self.product_insights) if self.product_insights else {},
            'engineering_insights': json.loads(self.engineering_insights) if self.engineering_insights else {},
            'executive_insights': json.loads(self.executive_insights) if self.executive_insights else {},
            'immediate_actions': json.loads(self.immediate_actions) if self.immediate_actions else [],
            'short_term_actions': json.loads(self.short_term_actions) if self.short_term_actions else [],
            'long_term_actions': json.loads(self.long_term_actions) if self.long_term_actions else [],
            'impact_score': self.impact_score,
            'urgency_score': self.urgency_score,
            'confidence_score': self.confidence_score,
            'is_reviewed': self.is_reviewed,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def get_team_insights(self, team: str):
        """Get insights for a specific team."""
        team_map = {
            'sales': self.sales_insights,
            'marketing': self.marketing_insights,
            'product': self.product_insights,
            'engineering': self.engineering_insights,
            'executive': self.executive_insights
        }
        data = team_map.get(team.lower())
        return json.loads(data) if data else {}


# =============================================================================
# KLUE-INSPIRED: BATTLE CARDS
# =============================================================================

class BattleCard(db.Model):
    """
    Sales battle cards for competitive positioning (Klue-inspired).
    Provides sales teams with ready-to-use competitive intelligence.
    """
    __tablename__ = 'battle_cards'
    
    id = db.Column(db.Integer, primary_key=True)
    competitor_id = db.Column(db.Integer, db.ForeignKey('competitors.id'), nullable=False)
    
    # Card metadata
    name = db.Column(db.String(255), nullable=False)
    version = db.Column(db.String(50), default='1.0')
    status = db.Column(db.String(50), default='draft')  # draft, active, archived
    
    # Overview
    elevator_pitch = db.Column(db.Text)  # Quick competitive positioning statement
    target_segment = db.Column(db.String(255))  # Which customer segment
    
    # Strengths & Weaknesses
    our_strengths = db.Column(db.Text)  # JSON array
    our_weaknesses = db.Column(db.Text)  # JSON array
    competitor_strengths = db.Column(db.Text)  # JSON array
    competitor_weaknesses = db.Column(db.Text)  # JSON array
    
    # Win Themes
    key_differentiators = db.Column(db.Text)  # JSON array
    trap_questions = db.Column(db.Text)  # JSON array - questions to ask prospects
    landmine_questions = db.Column(db.Text)  # JSON array - questions they'll ask
    
    # Objection Handling
    common_objections = db.Column(db.Text)  # JSON array with objection + response
    
    # Proof Points
    customer_wins = db.Column(db.Text)  # JSON array of relevant wins
    case_studies = db.Column(db.Text)  # JSON array of case study links
    
    # Quick Facts
    pricing_comparison = db.Column(db.Text)  # JSON comparison
    feature_comparison = db.Column(db.Text)  # JSON comparison matrix
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(255))
    last_reviewed_at = db.Column(db.DateTime)
    
    # Relationships
    competitor = db.relationship('Competitor', backref=db.backref('battle_cards', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'competitor_id': self.competitor_id,
            'competitor_name': self.competitor.name if self.competitor else None,
            'name': self.name,
            'version': self.version,
            'status': self.status,
            'elevator_pitch': self.elevator_pitch,
            'target_segment': self.target_segment,
            'our_strengths': json.loads(self.our_strengths) if self.our_strengths else [],
            'our_weaknesses': json.loads(self.our_weaknesses) if self.our_weaknesses else [],
            'competitor_strengths': json.loads(self.competitor_strengths) if self.competitor_strengths else [],
            'competitor_weaknesses': json.loads(self.competitor_weaknesses) if self.competitor_weaknesses else [],
            'key_differentiators': json.loads(self.key_differentiators) if self.key_differentiators else [],
            'trap_questions': json.loads(self.trap_questions) if self.trap_questions else [],
            'landmine_questions': json.loads(self.landmine_questions) if self.landmine_questions else [],
            'common_objections': json.loads(self.common_objections) if self.common_objections else [],
            'customer_wins': json.loads(self.customer_wins) if self.customer_wins else [],
            'pricing_comparison': json.loads(self.pricing_comparison) if self.pricing_comparison else {},
            'feature_comparison': json.loads(self.feature_comparison) if self.feature_comparison else {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_reviewed_at': self.last_reviewed_at.isoformat() if self.last_reviewed_at else None
        }


# =============================================================================
# CRAYON-INSPIRED: WIN/LOSS ANALYSIS
# =============================================================================

class WinLossRecord(db.Model):
    """
    Win/Loss tracking for competitive deals (Crayon-inspired).
    Track competitive outcomes to improve win rates.
    """
    __tablename__ = 'win_loss_records'
    
    id = db.Column(db.Integer, primary_key=True)
    competitor_id = db.Column(db.Integer, db.ForeignKey('competitors.id'))
    
    # Deal Info
    deal_name = db.Column(db.String(500))
    deal_value = db.Column(db.Float)
    deal_currency = db.Column(db.String(10), default='USD')
    
    # Outcome
    outcome = db.Column(db.String(50), nullable=False)  # won, lost, no_decision
    outcome_date = db.Column(db.DateTime)
    
    # Customer Info
    customer_name = db.Column(db.String(255))
    customer_industry = db.Column(db.String(100))
    customer_size = db.Column(db.String(50))  # SMB, mid-market, enterprise
    customer_region = db.Column(db.String(100))
    
    # Decision Factors
    primary_loss_reason = db.Column(db.String(100))  # price, features, relationship, etc.
    loss_reasons = db.Column(db.Text)  # JSON array of all contributing factors
    win_reasons = db.Column(db.Text)  # JSON array
    decision_makers = db.Column(db.Text)  # JSON array of roles involved
    
    # Competitive Intel
    competitor_positioning = db.Column(db.Text)  # How competitor positioned
    competitor_pricing = db.Column(db.Text)  # What they offered
    competitor_tactics = db.Column(db.Text)  # Sales tactics used
    
    # Our Performance
    our_strengths_cited = db.Column(db.Text)  # JSON array
    our_weaknesses_cited = db.Column(db.Text)  # JSON array
    
    # Lessons Learned
    key_learnings = db.Column(db.Text)
    recommended_changes = db.Column(db.Text)
    
    # Metadata
    sales_rep = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    competitor = db.relationship('Competitor', backref=db.backref('win_loss_records', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'competitor_id': self.competitor_id,
            'competitor_name': self.competitor.name if self.competitor else None,
            'deal_name': self.deal_name,
            'deal_value': self.deal_value,
            'deal_currency': self.deal_currency,
            'outcome': self.outcome,
            'outcome_date': self.outcome_date.isoformat() if self.outcome_date else None,
            'customer_name': self.customer_name,
            'customer_industry': self.customer_industry,
            'customer_size': self.customer_size,
            'customer_region': self.customer_region,
            'primary_loss_reason': self.primary_loss_reason,
            'loss_reasons': json.loads(self.loss_reasons) if self.loss_reasons else [],
            'win_reasons': json.loads(self.win_reasons) if self.win_reasons else [],
            'decision_makers': json.loads(self.decision_makers) if self.decision_makers else [],
            'competitor_positioning': self.competitor_positioning,
            'key_learnings': self.key_learnings,
            'sales_rep': self.sales_rep,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# =============================================================================
# COMPETITIVE PLAYBOOKS
# =============================================================================

class CompetitivePlaybook(db.Model):
    """
    Strategic playbooks for different competitive scenarios.
    Provides team-specific responses to competitive situations.
    """
    __tablename__ = 'competitive_playbooks'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Playbook identity
    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(100), unique=True)
    description = db.Column(db.Text)
    
    # Trigger conditions
    trigger_signal_types = db.Column(db.Text)  # JSON array of signal types
    trigger_keywords = db.Column(db.Text)  # JSON array of keywords
    
    # Response actions by team
    sales_actions = db.Column(db.Text)  # JSON array
    marketing_actions = db.Column(db.Text)  # JSON array
    product_actions = db.Column(db.Text)  # JSON array
    executive_actions = db.Column(db.Text)  # JSON array
    
    # Templates
    email_templates = db.Column(db.Text)  # JSON array of email templates
    talk_tracks = db.Column(db.Text)  # JSON array of talk tracks
    
    # Escalation
    escalation_criteria = db.Column(db.Text)
    escalation_contacts = db.Column(db.Text)  # JSON array
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=5)  # 1-10
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'trigger_signal_types': json.loads(self.trigger_signal_types) if self.trigger_signal_types else [],
            'trigger_keywords': json.loads(self.trigger_keywords) if self.trigger_keywords else [],
            'sales_actions': json.loads(self.sales_actions) if self.sales_actions else [],
            'marketing_actions': json.loads(self.marketing_actions) if self.marketing_actions else [],
            'product_actions': json.loads(self.product_actions) if self.product_actions else [],
            'executive_actions': json.loads(self.executive_actions) if self.executive_actions else [],
            'email_templates': json.loads(self.email_templates) if self.email_templates else [],
            'talk_tracks': json.loads(self.talk_tracks) if self.talk_tracks else [],
            'is_active': self.is_active,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# =============================================================================
# ABMFORGE-INSPIRED: ACCOUNT TRACKING
# =============================================================================

class TrackedAccount(db.Model):
    """
    Account-based competitive tracking (ABMForge-inspired).
    Track specific high-value accounts and competitive activity.
    """
    __tablename__ = 'tracked_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Account Info
    account_name = db.Column(db.String(255), nullable=False)
    website = db.Column(db.String(500))
    industry = db.Column(db.String(100))
    size = db.Column(db.String(50))  # SMB, mid-market, enterprise
    region = db.Column(db.String(100))
    annual_revenue = db.Column(db.String(100))
    
    # Account Status
    account_tier = db.Column(db.String(20), default='standard')  # strategic, key, standard
    deal_stage = db.Column(db.String(50))  # prospect, qualified, proposal, negotiation
    deal_value = db.Column(db.Float)
    
    # Ownership
    account_owner = db.Column(db.String(255))
    sales_rep = db.Column(db.String(255))
    
    # Competitive Landscape
    incumbent_competitor_id = db.Column(db.Integer, db.ForeignKey('competitors.id'))
    competing_vendors = db.Column(db.Text)  # JSON array of competitor IDs
    competitive_status = db.Column(db.String(50))  # greenfield, displacement, retention
    
    # Intelligence
    tech_stack = db.Column(db.Text)  # JSON array of known technologies
    key_contacts = db.Column(db.Text)  # JSON array
    notes = db.Column(db.Text)
    
    # Engagement
    last_activity_at = db.Column(db.DateTime)
    next_action = db.Column(db.String(500))
    next_action_date = db.Column(db.DateTime)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    incumbent = db.relationship('Competitor', backref=db.backref('incumbent_accounts', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_name': self.account_name,
            'website': self.website,
            'industry': self.industry,
            'size': self.size,
            'region': self.region,
            'account_tier': self.account_tier,
            'deal_stage': self.deal_stage,
            'deal_value': self.deal_value,
            'account_owner': self.account_owner,
            'incumbent_competitor_id': self.incumbent_competitor_id,
            'incumbent_name': self.incumbent.name if self.incumbent else None,
            'competing_vendors': json.loads(self.competing_vendors) if self.competing_vendors else [],
            'competitive_status': self.competitive_status,
            'tech_stack': json.loads(self.tech_stack) if self.tech_stack else [],
            'last_activity_at': self.last_activity_at.isoformat() if self.last_activity_at else None,
            'next_action': self.next_action,
            'next_action_date': self.next_action_date.isoformat() if self.next_action_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class AccountActivity(db.Model):
    """Activity log for tracked accounts."""
    __tablename__ = 'account_activities'
    
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('tracked_accounts.id'), nullable=False)
    
    activity_type = db.Column(db.String(50))  # meeting, email, intel, competitor_mention
    description = db.Column(db.Text)
    outcome = db.Column(db.Text)
    
    # Competitive Intel
    competitor_mentioned = db.Column(db.Integer, db.ForeignKey('competitors.id'))
    competitive_insight = db.Column(db.Text)
    
    # Metadata
    logged_by = db.Column(db.String(255))
    activity_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    account = db.relationship('TrackedAccount', backref=db.backref('activities', lazy='dynamic'))
    competitor = db.relationship('Competitor')
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'activity_type': self.activity_type,
            'description': self.description,
            'outcome': self.outcome,
            'competitor_mentioned': self.competitor_mentioned,
            'competitor_name': self.competitor.name if self.competitor else None,
            'competitive_insight': self.competitive_insight,
            'logged_by': self.logged_by,
            'activity_date': self.activity_date.isoformat() if self.activity_date else None
        }


# =============================================================================
# FEATURE COMPARISON MATRIX
# =============================================================================

class FeatureComparison(db.Model):
    """
    Product feature comparison matrix.
    Allows detailed feature-by-feature comparison with competitors.
    """
    __tablename__ = 'feature_comparisons'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Feature details
    category = db.Column(db.String(100), nullable=False)
    feature_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # Our capability
    our_capability = db.Column(db.String(50))  # full, partial, planned, none
    our_details = db.Column(db.Text)
    
    # Competitor capabilities (JSON: {competitor_id: {capability, details}})
    competitor_capabilities = db.Column(db.Text)
    
    # Importance
    customer_importance = db.Column(db.Integer, default=5)  # 1-10
    differentiation_level = db.Column(db.String(50))  # unique, better, parity, weaker
    
    # Metadata
    last_verified = db.Column(db.DateTime)
    verified_by = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'feature_name': self.feature_name,
            'description': self.description,
            'our_capability': self.our_capability,
            'our_details': self.our_details,
            'competitor_capabilities': json.loads(self.competitor_capabilities) if self.competitor_capabilities else {},
            'customer_importance': self.customer_importance,
            'differentiation_level': self.differentiation_level,
            'last_verified': self.last_verified.isoformat() if self.last_verified else None
        }


def init_db():
    """Initialize the database with Hioki as the competitor."""
    from . import create_app
    app = create_app()
    
    with app.app_context():
        db.create_all()
        
        # Check if we already have data
        if Competitor.query.first():
            print("Database already initialized.")
            return
        
        # Add Hioki as the primary competitor
        hioki = Competitor(
            name="Hioki",
            description="Japanese test and measurement equipment manufacturer. Major competitor in digital multimeters, clamp meters, power analyzers, and insulation testers.",
            website="https://www.hioki.com"
        )
        db.session.add(hioki)
        db.session.commit()
        
        # Add Hioki monitored URLs (real product pages)
        sample_urls = [
            MonitoredURL(
                competitor_id=hioki.id,
                url="https://www.hioki.com/global/products/testers",
                name="Handheld Digital Multimeters (DMMs)",
                page_type="product_page"
            ),
            MonitoredURL(
                competitor_id=hioki.id,
                url="https://www.hioki.com/global/products/clamp-meters",
                name="Clamp Meters",
                page_type="product_page"
            ),
            MonitoredURL(
                competitor_id=hioki.id,
                url="https://www.hioki.com/global/products/insulation-testers",
                name="Insulation Testers / Megohmmeters",
                page_type="product_page"
            ),
            MonitoredURL(
                competitor_id=hioki.id,
                url="https://www.hioki.com/global/products/power-meters",
                name="Power Meters / Power Analyzers",
                page_type="product_page"
            ),
            MonitoredURL(
                competitor_id=hioki.id,
                url="https://www.hioki.com/global/products/benchtop-dmm",
                name="Benchtop Digital Multimeters",
                page_type="product_page"
            ),
            MonitoredURL(
                competitor_id=hioki.id,
                url="https://www.hioki.com/global/products/resistance-meters",
                name="Resistance Meters / Battery Testers",
                page_type="product_page"
            ),
            MonitoredURL(
                competitor_id=hioki.id,
                url="https://www.hioki.com/global/products/new",
                name="New Products",
                page_type="product_page"
            ),
            MonitoredURL(
                competitor_id=hioki.id,
                url="https://www.hioki.com/global/news",
                name="Newsroom",
                page_type="news_page"
            ),
        ]
        
        for url in sample_urls:
            db.session.add(url)
        
        db.session.commit()
        print("Database initialized with Hioki as competitor.")


if __name__ == '__main__':
    init_db()
