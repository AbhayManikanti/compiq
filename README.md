# Competitor Intelligence Monitor

A simplified POC for monitoring competitor activities and generating actionable insights.

## Architecture Overview

```
SCOPE: 1 OpCo (Fluke) | 2-3 Competitors | ~10-15 URLs total

┌─────────────────────────────────────────────────────────────┐
│  COLLECTION                                                 │
│  ├── Page Monitoring (changedetection.io style)            │
│  └── News Monitoring (RSS/NewsAPI)                         │
├─────────────────────────────────────────────────────────────┤
│  STORAGE                                                    │
│  └── SQLite Database                                        │
├─────────────────────────────────────────────────────────────┤
│  INTELLIGENCE                                               │
│  └── LLM Processing (OpenAI/Azure OpenAI)                  │
│      ├── Change summarization                               │
│      ├── Signal classification                              │
│      ├── Relevance assessment                               │
│      └── Playbook-driven responses                          │
├─────────────────────────────────────────────────────────────┤
│  OUTPUT                                                     │
│  ├── Web Dashboard (Flask)                                  │
│  ├── Email Alerts                                           │
│  └── Slack/Teams Integration                                │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
cd competitor-monitor
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Initialize Database

```bash
python -c "from app.database import init_db; init_db()"
```

### 4. Run the Application

```bash
# Start the web dashboard
python run.py

# Or run the monitor in background
python -m app.monitor
```

### 5. Access Dashboard

Open http://localhost:5000 in your browser.

## Configuration

### Adding Competitors

Edit `config/competitors.yaml` to add competitor URLs to monitor:

```yaml
competitors:
  - name: "Competitor A"
    urls:
      - url: "https://competitor-a.com/products"
        type: "product_page"
      - url: "https://competitor-a.com/pricing"
        type: "pricing_page"
```

### Fluke Context

Edit `config/fluke_context.md` to provide context about Fluke's products and positioning.

### Response Playbooks

Edit `config/playbooks.yaml` to customize automated response suggestions.

## Features

- **Real-time Monitoring**: Tracks competitor pages for changes
- **News Aggregation**: Collects news from RSS feeds and NewsAPI
- **AI-Powered Analysis**: Uses LLM to classify and assess changes
- **Risk Scoring**: Automatic risk assessment based on change type
- **Playbook Responses**: Pre-defined response templates for common scenarios
- **Dashboard**: Visual overview of all competitor activities
- **Alerts**: Email/Slack notifications for high-priority changes

## Project Structure

```
competitor-monitor/
├── app/
│   ├── __init__.py
│   ├── database.py          # SQLite models
│   ├── monitor.py            # Page monitoring
│   ├── news_collector.py     # News/RSS collection
│   ├── analyzer.py           # LLM analysis engine
│   ├── alerter.py            # Notification system
│   └── routes.py             # Flask routes
├── config/
│   ├── competitors.yaml      # Competitor URLs
│   ├── fluke_context.md      # Fluke context document
│   └── playbooks.yaml        # Response playbooks
├── templates/                # HTML templates
├── static/                   # CSS/JS assets
├── data/                     # SQLite database
├── requirements.txt
├── .env.example
└── run.py
```

## API Endpoints

- `GET /` - Dashboard home
- `GET /api/alerts` - List all alerts
- `GET /api/alerts/<id>` - Get alert details
- `POST /api/monitor/run` - Trigger manual monitoring run
- `GET /api/competitors` - List monitored competitors
- `GET /api/reports` - Generate reports

## License

Internal use only - Fortive Corporation
