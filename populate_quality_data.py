"""
Populate CompIQ with Quality Data
- Battle cards for all competitors
- High-quality news items (no finance spam)
- Strategic alerts (product launches, partnerships, tech updates)
"""
import os
import sys
import json
from datetime import datetime, timedelta
import random

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.database import (
    db, Competitor, NewsItem, Alert, BattleCard,
    MonitoredURL, AlertStatus, RiskLevel, SignalType
)

app = create_app()

# Competitor data with detailed info
COMPETITORS = [
    {
        'name': 'Hioki',
        'description': 'Japanese manufacturer of precision electronic measuring instruments, known for power analyzers and battery testers.',
        'website': 'https://www.hioki.com',
        'logo_url': 'https://logo.clearbit.com/hioki.com'
    },
    {
        'name': 'Keysight Technologies',
        'description': 'Leading electronic design and test solutions provider, spun off from Agilent. Strong in oscilloscopes, signal analyzers, and 5G testing.',
        'website': 'https://www.keysight.com',
        'logo_url': 'https://logo.clearbit.com/keysight.com'
    },
    {
        'name': 'Rohde & Schwarz',
        'description': 'German electronics group specializing in test & measurement, broadcast & media, and cybersecurity. Premium positioning.',
        'website': 'https://www.rohde-schwarz.com',
        'logo_url': 'https://logo.clearbit.com/rohde-schwarz.com'
    },
    {
        'name': 'National Instruments',
        'description': 'Provider of automated test equipment and virtual instrumentation software. Strong in LabVIEW ecosystem and modular instruments.',
        'website': 'https://www.ni.com',
        'logo_url': 'https://logo.clearbit.com/ni.com'
    },
    {
        'name': 'Tektronix',
        'description': 'American company best known for oscilloscopes and logic analyzers. Part of Fortive Corporation.',
        'website': 'https://www.tek.com',
        'logo_url': 'https://logo.clearbit.com/tek.com'
    },
    {
        'name': 'Amprobe',
        'description': 'Manufacturer of electrical test tools and HVAC testing equipment. Known for clamp meters and multimeters.',
        'website': 'https://www.amprobe.com',
        'logo_url': 'https://logo.clearbit.com/amprobe.com'
    },
    {
        'name': 'Klein Tools',
        'description': 'American manufacturer of hand tools and electrical testing equipment. Strong brand loyalty among electricians.',
        'website': 'https://www.kleintools.com',
        'logo_url': 'https://logo.clearbit.com/kleintools.com'
    }
]

# Battle card templates for each competitor
BATTLE_CARDS = {
    'Hioki': {
        'elevator_pitch': 'While Hioki excels in power analyzers and battery testing, our solutions offer broader integration capabilities, better software ecosystems, and more competitive pricing for the North American market.',
        'target_segment': 'Power electronics, EV/battery manufacturers, R&D labs',
        'our_strengths': [
            'Superior software integration and API support',
            'Faster customer support response times in NA',
            'More competitive pricing on mid-range products',
            'Better cloud connectivity and data management'
        ],
        'our_weaknesses': [
            'Less specialized in ultra-high precision power analysis',
            'Smaller presence in Asian markets',
            'Fewer dedicated battery testing solutions'
        ],
        'competitor_strengths': [
            'Industry-leading accuracy in power analyzers',
            'Strong reputation in battery testing for EVs',
            'Excellent build quality and reliability',
            'Deep relationships with Japanese automakers'
        ],
        'competitor_weaknesses': [
            'Higher price point across product lines',
            'Limited software ecosystem integration',
            'Slower to adopt cloud-based solutions',
            'Weaker North American support infrastructure'
        ],
        'key_differentiators': [
            'Our connected platform reduces data silos',
            'Faster time-to-insight with built-in analytics',
            '30% lower total cost of ownership over 5 years'
        ],
        'trap_questions': [
            'How important is real-time cloud data access for your team?',
            'What percentage of your testing requires API integration?',
            'How do you currently handle multi-site data consolidation?'
        ],
        'landmine_questions': [
            'Can you match Hioki\'s power analyzer accuracy specs?',
            'Do you have dedicated battery cycling test solutions?'
        ],
        'common_objections': [
            {'objection': 'Hioki has better accuracy specs', 'response': 'For 95% of applications, our accuracy exceeds requirements. The real differentiator is what you do with the data - our platform turns measurements into insights.'},
            {'objection': 'We\'ve used Hioki for years', 'response': 'Many of our customers transitioned from Hioki. They report 40% faster test setup times and significantly better integration with their existing systems.'}
        ]
    },
    'Keysight Technologies': {
        'elevator_pitch': 'Keysight dominates high-end R&D, but our solutions deliver comparable performance for production testing at 40% lower cost, with faster deployment and better ease of use.',
        'target_segment': 'RF/Microwave testing, 5G development, semiconductor test',
        'our_strengths': [
            'More intuitive user interface and faster setup',
            'Significantly lower cost of ownership',
            'Flexible licensing models',
            'Better production-floor durability'
        ],
        'our_weaknesses': [
            'Less comprehensive high-frequency RF portfolio',
            'Smaller R&D application engineering team',
            'Fewer cutting-edge 5G mmWave solutions'
        ],
        'competitor_strengths': [
            'Broadest RF/microwave test portfolio',
            'Leading 5G and 6G test capabilities',
            'Massive application engineering resources',
            'Strong relationships with semiconductor fabs'
        ],
        'competitor_weaknesses': [
            'Premium pricing across all product lines',
            'Complex licensing structures',
            'Can be overkill for production testing needs',
            'Long lead times on custom solutions'
        ],
        'key_differentiators': [
            'Production-optimized solutions vs R&D focus',
            '60% faster first-measurement time',
            'All-inclusive licensing with no hidden costs'
        ],
        'trap_questions': [
            'What percentage of your tests are production vs R&D?',
            'How much do you spend annually on software licenses?',
            'How long does it typically take to get a new test running?'
        ],
        'common_objections': [
            {'objection': 'Keysight is the industry standard', 'response': 'For R&D, perhaps. But production testing has different needs - speed, reliability, and TCO matter more than cutting-edge specs.'},
            {'objection': 'Our engineers know Keysight tools', 'response': 'Our interface is designed to be intuitive for anyone with test experience. We offer free training and most users are productive within a day.'}
        ]
    },
    'Rohde & Schwarz': {
        'elevator_pitch': 'R&S offers premium quality at premium prices. We provide 90% of their capability at 50% of the cost, with comparable reliability and better local support.',
        'target_segment': 'Aerospace & defense, broadcast, EMC testing',
        'our_strengths': [
            'Dramatically better price-performance ratio',
            'Faster delivery times',
            'More flexible customization options',
            'Stronger Americas support presence'
        ],
        'our_weaknesses': [
            'Less established in A&D sector',
            'Smaller broadcast solutions portfolio',
            'Less brand recognition in European markets'
        ],
        'competitor_strengths': [
            'Exceptional build quality and reliability',
            'Strong government/defense certifications',
            'Comprehensive EMC and broadcast solutions',
            'German engineering reputation'
        ],
        'competitor_weaknesses': [
            'Highest prices in the industry',
            'Long lead times for complex systems',
            'Conservative approach to new technologies',
            'Complex procurement processes'
        ],
        'key_differentiators': [
            '50% cost savings with comparable performance',
            '2x faster delivery on standard configurations',
            'More agile product development cycle'
        ],
        'trap_questions': [
            'What\'s your current budget pressure situation?',
            'How critical are delivery timelines for your project?',
            'Are you required to use certified vendors, or is it preferred?'
        ],
        'common_objections': [
            {'objection': 'R&S quality is unmatched', 'response': 'Our products undergo rigorous testing and carry the same warranty. We have customers who\'ve switched and report identical reliability.'},
            {'objection': 'We need their defense certifications', 'response': 'We hold equivalent certifications for most applications. Let\'s review your specific requirements - you may be paying a premium for certs you don\'t actually need.'}
        ]
    },
    'National Instruments': {
        'elevator_pitch': 'NI\'s modular approach is powerful but complex. Our integrated solutions deliver results faster, with lower training requirements and better out-of-box functionality.',
        'target_segment': 'Automated test systems, academic/research, validation labs',
        'our_strengths': [
            'Faster deployment with integrated solutions',
            'Lower total training and support costs',
            'Better out-of-box functionality',
            'No dependency on proprietary software'
        ],
        'our_weaknesses': [
            'Less modular/flexible architecture',
            'Smaller academic/research presence',
            'Less extensive third-party ecosystem'
        ],
        'competitor_strengths': [
            'Highly modular and flexible platform',
            'Massive LabVIEW developer community',
            'Strong academic and research presence',
            'Extensive partner ecosystem'
        ],
        'competitor_weaknesses': [
            'Requires significant programming expertise',
            'High ongoing software maintenance costs',
            'Long system integration timelines',
            'Steep learning curve for new users'
        ],
        'key_differentiators': [
            'Ready-to-use solutions vs build-from-scratch',
            '70% reduction in test system deployment time',
            'Standard programming languages, no vendor lock-in'
        ],
        'trap_questions': [
            'How long did your last test system integration take?',
            'How much do you spend on LabVIEW developers?',
            'What happens when your LabVIEW expert leaves?'
        ],
        'common_objections': [
            {'objection': 'We\'re already invested in LabVIEW', 'response': 'We understand sunk cost concerns. However, our ROI calculator typically shows payback within 18 months from reduced integration and maintenance costs.'},
            {'objection': 'NI\'s flexibility is essential for us', 'response': 'Our solutions are configurable without custom programming. For truly unique needs, we offer professional services that still cost less than DIY LabVIEW development.'}
        ]
    },
    'Tektronix': {
        'elevator_pitch': 'Tektronix pioneered oscilloscopes, but hasn\'t kept pace with modern workflow needs. Our connected, AI-enhanced solutions deliver faster insights with less expertise required.',
        'target_segment': 'Electronics R&D, embedded systems, education',
        'our_strengths': [
            'Modern, cloud-connected architecture',
            'AI-assisted measurement and analysis',
            'Better collaboration features',
            'More competitive mid-range pricing'
        ],
        'our_weaknesses': [
            'Less brand recognition in oscilloscope market',
            'Smaller installed base',
            'Fewer ultra-high-bandwidth options'
        ],
        'competitor_strengths': [
            'Iconic oscilloscope brand recognition',
            'Large installed base and customer loyalty',
            'Strong education sector presence',
            'Comprehensive protocol decode options'
        ],
        'competitor_weaknesses': [
            'Aging product architecture',
            'Limited cloud and connectivity features',
            'Higher prices for comparable specs',
            'Slower innovation cycle'
        ],
        'key_differentiators': [
            'Native cloud connectivity for remote collaboration',
            'AI-powered anomaly detection and analysis',
            'Modern touch interface with faster navigation'
        ],
        'trap_questions': [
            'How do your teams collaborate on measurement data today?',
            'How much time do engineers spend on routine analysis?',
            'What\'s your strategy for remote debugging and support?'
        ],
        'common_objections': [
            {'objection': 'Tektronix is the gold standard for scopes', 'response': 'They were. But the market has evolved - modern engineering needs connected tools, not just good hardware. Our platform is built for today\'s workflows.'},
            {'objection': 'Our techs are trained on Tek', 'response': 'Our interface is intuitive for anyone with scope experience. Most users find our AI-assist features actually reduce the expertise needed.'}
        ]
    },
    'Amprobe': {
        'elevator_pitch': 'Amprobe serves the value segment well, but our products offer better durability, accuracy, and smart features for professionals who demand more from their tools.',
        'target_segment': 'Electricians, HVAC technicians, facility maintenance',
        'our_strengths': [
            'Superior build quality and durability',
            'Better accuracy specifications',
            'Smart connectivity features',
            'Comprehensive professional warranty'
        ],
        'our_weaknesses': [
            'Higher price point',
            'Less retail distribution',
            'Smaller brand awareness among DIYers'
        ],
        'competitor_strengths': [
            'Strong value proposition',
            'Wide retail availability',
            'Good brand recognition in HVAC',
            'Simple, focused product line'
        ],
        'competitor_weaknesses': [
            'Lower build quality in budget lines',
            'Limited smart/connected features',
            'Basic accuracy specifications',
            'Weaker professional warranty support'
        ],
        'key_differentiators': [
            'Professional-grade durability for demanding environments',
            'Bluetooth connectivity for data logging',
            'Lifetime accuracy guarantee on premium models'
        ],
        'trap_questions': [
            'How often do you replace damaged meters in the field?',
            'Do you need to log and report measurement data?',
            'What\'s the cost of a wrong measurement on a job?'
        ],
        'common_objections': [
            {'objection': 'Amprobe is good enough for our needs', 'response': 'Good enough until it fails on a critical job. Our meters are built to last - customers report 3x longer service life.'},
            {'objection': 'Your meters cost more', 'response': 'They do upfront. But factor in replacement costs, calibration, and downtime - our TCO is actually lower over 5 years.'}
        ]
    },
    'Klein Tools': {
        'elevator_pitch': 'Klein has incredible brand loyalty among electricians. We compete by offering equivalent quality with superior smart features and better integration with digital workflows.',
        'target_segment': 'Professional electricians, contractors, industrial maintenance',
        'our_strengths': [
            'Advanced Bluetooth and app connectivity',
            'Better digital workflow integration',
            'Innovative smart features',
            'Strong commercial/industrial focus'
        ],
        'our_weaknesses': [
            'Less brand heritage in electrical trades',
            'Smaller tool ecosystem',
            'Less retail/distributor presence'
        ],
        'competitor_strengths': [
            'Iconic American brand with 160+ year heritage',
            'Massive loyal customer base',
            'Comprehensive hand tool ecosystem',
            'Strong distributor relationships'
        ],
        'competitor_weaknesses': [
            'Slower to adopt smart/connected features',
            'Traditional product development approach',
            'Limited digital integration capabilities',
            'Premium pricing based on brand vs features'
        ],
        'key_differentiators': [
            'Industry-leading app integration for job documentation',
            'Smart alerts and measurement sharing',
            'Built for modern digital-first workflows'
        ],
        'trap_questions': [
            'How do you document measurements for compliance reports?',
            'Do your techs share measurement data with the office?',
            'How much time is spent on paperwork vs actual work?'
        ],
        'common_objections': [
            {'objection': 'My guys only use Klein', 'response': 'We respect brand loyalty. But have them try our smart meters on one job - the time saved on documentation usually wins them over.'},
            {'objection': 'Klein quality is unmatched', 'response': 'Klein makes great hand tools. But for test equipment, smart features matter as much as build quality now. We deliver both.'}
        ]
    }
}

# High-quality news items (no finance spam)
NEWS_ITEMS = [
    # Hioki news
    {'competitor': 'Hioki', 'title': 'Hioki Launches Next-Generation Power Analyzer with Enhanced EV Testing Capabilities', 'category': 'product_launch', 'source_type': 'rss', 'source': 'Hioki Press Room', 'days_ago': 2, 'summary': 'New PW8001 power analyzer offers improved accuracy and dedicated EV motor testing modes, targeting the growing electric vehicle development market.'},
    {'competitor': 'Hioki', 'title': 'Hioki Expands Battery Test Solutions for Gigafactory Applications', 'category': 'product_launch', 'source_type': 'newsapi', 'source': 'Electronics Weekly', 'days_ago': 5, 'summary': 'Company announces new high-throughput battery testing systems designed for large-scale EV battery production facilities.'},
    {'competitor': 'Hioki', 'title': 'Hioki Partners with Major Japanese Automaker on EV Development Tools', 'category': 'partnership', 'source_type': 'google_news', 'source': 'Automotive News', 'days_ago': 8, 'summary': 'Strategic partnership will integrate Hioki testing equipment into next-generation electric vehicle development workflows.'},
    
    # Keysight news
    {'competitor': 'Keysight Technologies', 'title': 'Keysight Unveils Industry-First 6G Test Platform at MWC', 'category': 'product_launch', 'source_type': 'newsapi', 'source': 'FierceWireless', 'days_ago': 1, 'summary': 'New platform supports sub-THz frequencies and AI-native testing capabilities for next-generation wireless research.'},
    {'competitor': 'Keysight Technologies', 'title': 'Keysight Acquires AI Software Company to Enhance Test Automation', 'category': 'acquisition', 'source_type': 'rss', 'source': 'Keysight Newsroom', 'days_ago': 4, 'summary': 'Strategic acquisition adds machine learning capabilities to Keysight\'s automated test portfolio.'},
    {'competitor': 'Keysight Technologies', 'title': 'Keysight and NVIDIA Collaborate on AI Chip Testing Solutions', 'category': 'partnership', 'source_type': 'google_news', 'source': 'EE Times', 'days_ago': 7, 'summary': 'Partnership aims to accelerate validation of AI accelerator chips with new automated test methodologies.'},
    {'competitor': 'Keysight Technologies', 'title': 'Keysight Introduces Cloud-Based Oscilloscope Software Platform', 'category': 'feature_update', 'source_type': 'newsapi', 'source': 'EDN Network', 'days_ago': 12, 'summary': 'PathWave platform now offers remote oscilloscope access and AI-powered waveform analysis in the cloud.'},
    
    # Rohde & Schwarz news
    {'competitor': 'Rohde & Schwarz', 'title': 'Rohde & Schwarz Wins Major European Defense Contract for Secure Communications Testing', 'category': 'other', 'source_type': 'rss', 'source': 'R&S Press Center', 'days_ago': 3, 'summary': 'Multi-year contract covers testing equipment for NATO-allied military communication systems.'},
    {'competitor': 'Rohde & Schwarz', 'title': 'R&S Launches EMC Test Solution for Electric Aircraft Certification', 'category': 'product_launch', 'source_type': 'newsapi', 'source': 'Aviation Week', 'days_ago': 6, 'summary': 'New test system addresses electromagnetic compatibility requirements for emerging eVTOL and electric aircraft markets.'},
    {'competitor': 'Rohde & Schwarz', 'title': 'Rohde & Schwarz Opens New R&D Center in Singapore', 'category': 'expansion', 'source_type': 'google_news', 'source': 'Channel News Asia', 'days_ago': 15, 'summary': 'Facility will focus on 5G/6G and automotive electronics testing solutions for Asia-Pacific customers.'},
    
    # National Instruments news
    {'competitor': 'National Instruments', 'title': 'NI Releases Major LabVIEW Update with Enhanced Python Integration', 'category': 'feature_update', 'source_type': 'rss', 'source': 'NI News', 'days_ago': 2, 'summary': 'LabVIEW 2024 introduces native Python node support and improved machine learning toolkit integration.'},
    {'competitor': 'National Instruments', 'title': 'National Instruments Launches Modular EV Powertrain Test System', 'category': 'product_launch', 'source_type': 'newsapi', 'source': 'Test & Measurement World', 'days_ago': 9, 'summary': 'Scalable PXI-based system supports complete powertrain validation from component to vehicle level.'},
    {'competitor': 'National Instruments', 'title': 'NI Partners with Leading University on Quantum Computing Test Solutions', 'category': 'partnership', 'source_type': 'google_news', 'source': 'Scientific American', 'days_ago': 18, 'summary': 'Research collaboration aims to develop new measurement techniques for quantum computer characterization.'},
    
    # Tektronix news
    {'competitor': 'Tektronix', 'title': 'Tektronix Introduces 8-Channel Oscilloscope for Complex System Debug', 'category': 'product_launch', 'source_type': 'rss', 'source': 'Tek Newsroom', 'days_ago': 4, 'summary': 'New MSO68 series offers 8 analog channels and 64 digital channels for simultaneous mixed-signal analysis.'},
    {'competitor': 'Tektronix', 'title': 'Tektronix Adds PCIe 6.0 Protocol Decode to Oscilloscope Portfolio', 'category': 'feature_update', 'source_type': 'newsapi', 'source': 'Electronic Design', 'days_ago': 11, 'summary': 'Software update enables debugging of next-generation PCIe 6.0 designs running at 64 GT/s.'},
    {'competitor': 'Tektronix', 'title': 'Fortive Announces Organizational Changes for Tektronix Division', 'category': 'leadership_change', 'source_type': 'google_news', 'source': 'Barron\'s', 'days_ago': 20, 'summary': 'New leadership team announced with focus on accelerating digital transformation initiatives.'},
    
    # Amprobe news
    {'competitor': 'Amprobe', 'title': 'Amprobe Releases New Line of Industrial-Grade Clamp Meters', 'category': 'product_launch', 'source_type': 'rss', 'source': 'Amprobe News', 'days_ago': 6, 'summary': 'AMP-420 series offers CAT IV 600V rating and improved accuracy for industrial electrical testing.'},
    {'competitor': 'Amprobe', 'title': 'Amprobe Expands HVAC Product Line with Smart Refrigerant Analyzers', 'category': 'product_launch', 'source_type': 'newsapi', 'source': 'ACHR News', 'days_ago': 14, 'summary': 'New analyzers support next-generation low-GWP refrigerants required by updated regulations.'},
    
    # Klein Tools news
    {'competitor': 'Klein Tools', 'title': 'Klein Tools Launches Bluetooth-Connected Test Meter Line', 'category': 'product_launch', 'source_type': 'rss', 'source': 'Klein Tools Blog', 'days_ago': 3, 'summary': 'New MM700 series multimeters feature Bluetooth connectivity and companion app for data logging and sharing.'},
    {'competitor': 'Klein Tools', 'title': 'Klein Tools Celebrates 165 Years of American Manufacturing', 'category': 'marketing_campaign', 'source_type': 'newsapi', 'source': 'Electrical Contractor Magazine', 'days_ago': 10, 'summary': 'Anniversary campaign highlights company\'s commitment to American-made professional tools.'},
    {'competitor': 'Klein Tools', 'title': 'Klein Tools Partners with Trade Schools on Apprenticeship Program', 'category': 'partnership', 'source_type': 'google_news', 'source': 'Construction Dive', 'days_ago': 22, 'summary': 'Initiative provides tool kits and training materials to support next generation of skilled electricians.'},
]

# High-quality alerts (strategic, no finance spam)
ALERTS = [
    # Critical alerts
    {'competitor': 'Keysight Technologies', 'signal_type': 'product_launch', 'risk_level': 'critical', 'title': 'Keysight Announces 6G Test Platform with Sub-THz Capabilities', 
     'summary': 'Keysight unveiled an industry-first 6G test platform at MWC supporting frequencies up to 300 GHz. This positions them as the early leader in 6G test equipment, potentially locking in research relationships with major telecom equipment makers before competitors can respond.',
     'recommended_actions': ['Accelerate our 6G roadmap discussion', 'Brief sales team on competitive positioning', 'Identify key 6G research accounts at risk']},
    
    {'competitor': 'National Instruments', 'signal_type': 'feature_update', 'risk_level': 'critical', 'title': 'NI LabVIEW 2024 Adds Native Python Integration',
     'summary': 'NI has addressed one of the biggest criticisms of LabVIEW by adding seamless Python integration. This could slow customer migration to open platforms and reinforce their ecosystem lock-in for another product cycle.',
     'recommended_actions': ['Update competitive battle card', 'Prepare counter-messaging for sales team', 'Accelerate our Python tooling improvements']},
    
    # High risk alerts
    {'competitor': 'Rohde & Schwarz', 'signal_type': 'acquisition', 'risk_level': 'high', 'title': 'R&S Acquires EMC Test Startup for eVTOL Market',
     'summary': 'Rohde & Schwarz acquired a specialized EMC software company focused on electric aircraft certification. This strengthens their position in the emerging urban air mobility market where regulatory testing requirements are still being defined.',
     'recommended_actions': ['Research the acquired company capabilities', 'Assess our eVTOL market positioning', 'Connect with eVTOL prospects in pipeline']},
    
    {'competitor': 'Hioki', 'signal_type': 'partnership', 'risk_level': 'high', 'title': 'Hioki Partners with Toyota on EV Battery Testing Standards',
     'summary': 'Hioki announced a strategic partnership with Toyota to develop next-generation battery testing standards. This could influence industry standards and create preferred-vendor relationships in the growing EV battery market.',
     'recommended_actions': ['Monitor for published standards', 'Engage our automotive OEM contacts', 'Review battery test solution roadmap']},
    
    {'competitor': 'Tektronix', 'signal_type': 'product_launch', 'risk_level': 'high', 'title': 'Tektronix Launches 8-Channel MSO for Complex System Debug',
     'summary': 'New MSO68 series offers 8 analog + 64 digital channels, targeting complex multi-domain debugging. This directly competes with our MSA platform and offers more channels at a competitive price point.',
     'recommended_actions': ['Request detailed competitive analysis', 'Identify at-risk opportunities', 'Prepare feature comparison for sales']},
    
    # Medium risk alerts  
    {'competitor': 'Klein Tools', 'signal_type': 'product_launch', 'risk_level': 'medium', 'title': 'Klein Tools Enters Smart Connected Meter Market',
     'summary': 'Klein launched their first Bluetooth-connected multimeter line with companion app. While targeting the trades market, this could signal broader ambitions in connected test equipment and affect our professional electrician segment.',
     'recommended_actions': ['Evaluate app functionality', 'Brief field sales on positioning', 'Monitor customer reaction in trades segment']},
    
    {'competitor': 'Amprobe', 'signal_type': 'product_launch', 'risk_level': 'medium', 'title': 'Amprobe Releases Low-GWP Refrigerant Analyzers',
     'summary': 'New analyzers support next-generation refrigerants ahead of regulatory deadlines. Early market entry in this space could establish Amprobe as the go-to brand for HVAC technicians upgrading equipment.',
     'recommended_actions': ['Review our HVAC product roadmap', 'Assess regulatory timeline impact', 'Consider accelerating our refrigerant analyzer update']},
    
    {'competitor': 'Keysight Technologies', 'signal_type': 'partnership', 'risk_level': 'medium', 'title': 'Keysight and NVIDIA Collaborate on AI Chip Testing',
     'summary': 'Partnership will develop specialized test solutions for AI accelerator validation. While focused on cutting-edge AI chips, this reinforces Keysight\'s position as the innovation leader in semiconductor test.',
     'recommended_actions': ['Track developments in AI chip test space', 'Identify our AI/ML semiconductor customers', 'Evaluate partnership opportunities']},
    
    {'competitor': 'Rohde & Schwarz', 'signal_type': 'expansion', 'risk_level': 'medium', 'title': 'R&S Opens Major R&D Center in Singapore',
     'summary': 'New facility will focus on 5G/6G and automotive electronics testing for APAC region. This signals increased commitment to the Asian market and could strengthen their regional relationships.',
     'recommended_actions': ['Review APAC competitive strategy', 'Assess impact on regional accounts', 'Consider increased APAC investment']},
    
    # Lower risk / info alerts
    {'competitor': 'National Instruments', 'signal_type': 'partnership', 'risk_level': 'low', 'title': 'NI Partners with University on Quantum Computing Research',
     'summary': 'Academic partnership for quantum computer test research. While forward-looking, quantum computing test requirements are years from commercial relevance for most customers.',
     'recommended_actions': ['Add to technology watch list', 'No immediate action required']},
    
    {'competitor': 'Tektronix', 'signal_type': 'feature_update', 'risk_level': 'low', 'title': 'Tektronix Adds PCIe 6.0 Protocol Decode Support',
     'summary': 'Software update adds PCIe 6.0 debugging capability. Expected update as PCIe 6.0 devices begin sampling, maintaining parity with other oscilloscope vendors.',
     'recommended_actions': ['Verify our PCIe 6.0 support status', 'Routine competitive monitoring']},
    
    {'competitor': 'Klein Tools', 'signal_type': 'marketing_campaign', 'risk_level': 'info', 'title': 'Klein Tools 165th Anniversary Marketing Campaign',
     'summary': 'Brand heritage marketing campaign celebrating American manufacturing history. Reinforces their strong brand loyalty in the electrical trades segment.',
     'recommended_actions': ['Monitor campaign messaging and reach', 'Note for competitive awareness']},
]


def create_competitors():
    """Create or update competitors."""
    print("\n📊 Creating competitors...")
    competitors = {}
    
    for comp_data in COMPETITORS:
        comp = Competitor.query.filter_by(name=comp_data['name']).first()
        if not comp:
            comp = Competitor(
                name=comp_data['name'],
                description=comp_data['description'],
                website=comp_data['website'],
                logo_url=comp_data['logo_url'],
                is_active=True
            )
            db.session.add(comp)
            print(f"  ✅ Created: {comp_data['name']}")
        else:
            comp.description = comp_data['description']
            comp.website = comp_data['website']
            comp.logo_url = comp_data['logo_url']
            print(f"  🔄 Updated: {comp_data['name']}")
        
        competitors[comp_data['name']] = comp
    
    db.session.commit()
    return competitors


def create_battle_cards(competitors):
    """Create battle cards for each competitor."""
    print("\n⚔️ Creating battle cards...")
    
    for comp_name, card_data in BATTLE_CARDS.items():
        comp = competitors.get(comp_name)
        if not comp:
            print(f"  ⚠️ Competitor not found: {comp_name}")
            continue
        
        # Check if battle card exists
        existing = BattleCard.query.filter_by(competitor_id=comp.id).first()
        if existing:
            # Update existing
            card = existing
            print(f"  🔄 Updating battle card: {comp_name}")
        else:
            card = BattleCard(competitor_id=comp.id)
            db.session.add(card)
            print(f"  ✅ Creating battle card: {comp_name}")
        
        card.name = f"{comp_name} Battle Card"
        card.status = 'active'
        card.version = '1.0'
        card.elevator_pitch = card_data['elevator_pitch']
        card.target_segment = card_data['target_segment']
        card.our_strengths = json.dumps(card_data['our_strengths'])
        card.our_weaknesses = json.dumps(card_data['our_weaknesses'])
        card.competitor_strengths = json.dumps(card_data['competitor_strengths'])
        card.competitor_weaknesses = json.dumps(card_data['competitor_weaknesses'])
        card.key_differentiators = json.dumps(card_data['key_differentiators'])
        card.trap_questions = json.dumps(card_data['trap_questions'])
        card.landmine_questions = json.dumps(card_data.get('landmine_questions', []))
        card.common_objections = json.dumps(card_data['common_objections'])
        card.last_reviewed_at = datetime.utcnow()
    
    db.session.commit()


def create_news_items(competitors):
    """Create quality news items."""
    print("\n📰 Creating news items...")
    
    for news_data in NEWS_ITEMS:
        comp = competitors.get(news_data['competitor'])
        if not comp:
            print(f"  ⚠️ Competitor not found: {news_data['competitor']}")
            continue
        
        # Check for duplicate by title
        existing = NewsItem.query.filter_by(title=news_data['title']).first()
        if existing:
            print(f"  ⏭️ Skipping duplicate: {news_data['title'][:50]}...")
            continue
        
        published_at = datetime.utcnow() - timedelta(days=news_data['days_ago'])
        collected_at = published_at + timedelta(hours=random.randint(1, 12))
        
        news = NewsItem(
            competitor_id=comp.id,
            title=news_data['title'],
            summary=news_data['summary'],
            description=news_data['summary'],
            content=f"{news_data['summary']}\n\nThis article discusses {news_data['competitor']}'s latest developments in the test and measurement industry.",
            source=news_data['source'],
            source_type=news_data['source_type'],
            category=news_data['category'],
            url=f"https://example.com/news/{news_data['title'].lower().replace(' ', '-')[:50]}",
            published_at=published_at,
            collected_at=collected_at,
            is_processed=True,
            is_relevant=True
        )
        db.session.add(news)
        print(f"  ✅ Created: {news_data['title'][:50]}...")
    
    db.session.commit()


def create_alerts(competitors):
    """Create high-quality strategic alerts."""
    print("\n🚨 Creating alerts...")
    
    for alert_data in ALERTS:
        comp = competitors.get(alert_data['competitor'])
        if not comp:
            print(f"  ⚠️ Competitor not found: {alert_data['competitor']}")
            continue
        
        # Check for duplicate by title
        existing = Alert.query.filter_by(title=alert_data['title']).first()
        if existing:
            print(f"  ⏭️ Skipping duplicate: {alert_data['title'][:50]}...")
            continue
        
        # Determine detected time based on risk level
        if alert_data['risk_level'] == 'critical':
            days_ago = random.randint(0, 2)
        elif alert_data['risk_level'] == 'high':
            days_ago = random.randint(1, 5)
        elif alert_data['risk_level'] == 'medium':
            days_ago = random.randint(3, 10)
        else:
            days_ago = random.randint(5, 20)
        
        detected_at = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23))
        
        alert = Alert(
            competitor_id=comp.id,
            title=alert_data['title'],
            summary=alert_data['summary'],
            signal_type=alert_data['signal_type'],
            risk_level=alert_data['risk_level'],
            risk_score=random.randint(60, 95) if alert_data['risk_level'] in ['critical', 'high'] else random.randint(30, 65),
            confidence_score=random.randint(75, 95),
            status=AlertStatus.NEW.value,
            source_type='news',
            recommended_actions=json.dumps(alert_data['recommended_actions']),
            detected_at=detected_at
        )
        db.session.add(alert)
        print(f"  ✅ Created [{alert_data['risk_level'].upper()}]: {alert_data['title'][:50]}...")
    
    db.session.commit()


def create_monitored_urls(competitors):
    """Create monitored URLs for each competitor."""
    print("\n🔗 Creating monitored URLs...")
    
    url_templates = [
        ('Products Page', '/products', 'product_page'),
        ('Pricing Page', '/pricing', 'pricing_page'),
        ('News/Press', '/news', 'news_page'),
        ('About/Company', '/about', 'about_page'),
    ]
    
    for comp_name, comp in competitors.items():
        for name, path, page_type in url_templates:
            url = f"{comp.website}{path}"
            existing = MonitoredURL.query.filter_by(competitor_id=comp.id, url=url).first()
            if not existing:
                monitored = MonitoredURL(
                    competitor_id=comp.id,
                    url=url,
                    name=f"{comp_name} {name}",
                    page_type=page_type,
                    is_active=True,
                    check_interval_hours=24
                )
                db.session.add(monitored)
    
    db.session.commit()
    print(f"  ✅ Created monitored URLs for {len(competitors)} competitors")


def main():
    """Main function to populate all data."""
    with app.app_context():
        print("=" * 60)
        print("🚀 CompIQ Quality Data Population")
        print("=" * 60)
        
        # Create competitors
        competitors = create_competitors()
        
        # Create battle cards
        create_battle_cards(competitors)
        
        # Create news items
        create_news_items(competitors)
        
        # Create alerts
        create_alerts(competitors)
        
        # Create monitored URLs
        create_monitored_urls(competitors)
        
        print("\n" + "=" * 60)
        print("✅ Data population complete!")
        print("=" * 60)
        
        # Print summary
        print(f"\n📊 Summary:")
        print(f"   Competitors: {Competitor.query.count()}")
        print(f"   Battle Cards: {BattleCard.query.count()}")
        print(f"   News Items: {NewsItem.query.count()}")
        print(f"   Alerts: {Alert.query.count()}")
        print(f"   Monitored URLs: {MonitoredURL.query.count()}")


if __name__ == '__main__':
    main()
