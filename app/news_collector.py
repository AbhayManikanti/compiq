"""
News Collection System
Collects news from RSS feeds, NewsAPI, and other sources.
"""
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
import os
import re
import ssl
import certifi
import yaml
from pathlib import Path
from .database import db, NewsItem, Competitor

logger = logging.getLogger(__name__)


class NewsCollector:
    """Collects competitor news from various sources."""
    
    # Keywords to filter out stock/finance related news
    FINANCE_KEYWORDS = [
        'stock price', 'share price', 'stock market', 'nasdaq', 'nyse', 
        'market cap', 'earnings report', 'quarterly earnings', 'fiscal quarter',
        'investor', 'shareholders', 'dividend', 'eps', 'revenue forecast',
        'stock analysis', 'buy rating', 'sell rating', 'hold rating',
        'price target', 'analyst rating', 'market outlook', 'trading volume',
        'stock split', 'ipo', 'market value', 'equity research',
        'wall street', 'hedge fund', 'mutual fund', 'etf',
        'bull market', 'bear market', 'stock performance', 'valuation',
        'p/e ratio', 'market capitalization', 'stock forecast',
        'financial results', 'quarterly results', 'annual report',
        'sec filing', '10-k', '10-q', 'earnings call', 'guidance'
    ]
    
    def __init__(self):
        self.newsapi_key = os.getenv('NEWSAPI_KEY')
        # Don't use NewsAPI if it's still the placeholder value
        if self.newsapi_key and 'your-' in self.newsapi_key.lower():
            self.newsapi_key = None
            
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        # Use certifi for SSL verification
        self.session.verify = certifi.where()
        
        # Load RSS feeds from config
        self.rss_feeds = self._load_rss_feeds()
        
        # Default RSS feeds for Klein Tools news
        self.default_feeds = [
            'https://news.google.com/rss/search?q=Klein+Tools',
            'https://news.google.com/rss/search?q=Klein+Tools+electrical',
        ]
    
    def _load_rss_feeds(self) -> List[Dict]:
        """Load RSS feeds from config file."""
        config_path = Path(__file__).parent.parent / 'config' / 'competitors.yaml'
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
            return config.get('news_sources', {}).get('rss_feeds', [])
        except Exception as e:
            logger.warning(f"Could not load RSS feeds from config: {e}")
            return []
    
    def get_competitor_search_terms(self, competitor: Competitor) -> List[str]:
        """Generate search terms for a competitor."""
        terms = [competitor.name]
        
        # Add common variations
        name_parts = competitor.name.split()
        if len(name_parts) > 1:
            terms.append(name_parts[0])  # First word (e.g., "Keysight" from "Keysight Technologies")
        
        return terms
    
    def fetch_rss_feed(self, feed_url: str) -> List[Dict]:
        """Fetch and parse an RSS feed."""
        import ssl
        import urllib.request
        
        try:
            # Create SSL context that doesn't verify certificates (for development)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Fetch with custom SSL context
            request = urllib.request.Request(
                feed_url,
                headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
            )
            response = urllib.request.urlopen(request, context=ssl_context, timeout=30)
            feed_data = response.read()
            
            feed = feedparser.parse(feed_data)
            
            if feed.bozo and not feed.entries:
                logger.warning(f"Feed parsing issue for {feed_url}: {feed.bozo_exception}")
            
            items = []
            for entry in feed.entries:
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6])
                
                items.append({
                    'title': entry.get('title', ''),
                    'description': entry.get('summary', entry.get('description', '')),
                    'url': entry.get('link', ''),
                    'source': feed.feed.get('title', 'RSS Feed'),
                    'author': entry.get('author', ''),
                    'published_at': published
                })
            
            return items
            
        except Exception as e:
            logger.error(f"Error fetching RSS feed {feed_url}: {e}")
            return []
    
    def fetch_newsapi(self, query: str, from_date: Optional[datetime] = None) -> List[Dict]:
        """Fetch news from NewsAPI."""
        if not self.newsapi_key:
            logger.warning("NewsAPI key not configured")
            return []
        
        try:
            params = {
                'q': query,
                'apiKey': self.newsapi_key,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': 20
            }
            
            if from_date:
                params['from'] = from_date.strftime('%Y-%m-%d')
            
            response = self.session.get(
                'https://newsapi.org/v2/everything',
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'ok':
                logger.error(f"NewsAPI error: {data.get('message')}")
                return []
            
            items = []
            for article in data.get('articles', []):
                published = None
                if article.get('publishedAt'):
                    try:
                        published = datetime.fromisoformat(
                            article['publishedAt'].replace('Z', '+00:00')
                        ).replace(tzinfo=None)
                    except:
                        pass
                
                items.append({
                    'title': article.get('title', ''),
                    'description': article.get('description', ''),
                    'content': article.get('content', ''),
                    'url': article.get('url', ''),
                    'source': article.get('source', {}).get('name', 'NewsAPI'),
                    'author': article.get('author', ''),
                    'published_at': published
                })
            
            return items
            
        except Exception as e:
            logger.error(f"Error fetching from NewsAPI: {e}")
            return []
    
    def fetch_google_news_rss(self, query: str) -> List[Dict]:
        """Fetch news from Google News RSS."""
        encoded_query = requests.utils.quote(query)
        feed_url = f'https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en'
        return self.fetch_rss_feed(feed_url)
    
    def is_duplicate(self, title: str, url: str) -> bool:
        """Check if a news item already exists."""
        # Check by URL first
        existing = NewsItem.query.filter_by(url=url).first()
        if existing:
            return True
        
        # Check by similar title (basic deduplication)
        normalized_title = re.sub(r'[^\w\s]', '', title.lower())
        recent_items = NewsItem.query.filter(
            NewsItem.collected_at >= datetime.utcnow() - timedelta(days=7)
        ).all()
        
        for item in recent_items:
            existing_normalized = re.sub(r'[^\w\s]', '', item.title.lower())
            # Simple similarity check - if 80% of words match
            title_words = set(normalized_title.split())
            existing_words = set(existing_normalized.split())
            if title_words and existing_words:
                overlap = len(title_words & existing_words)
                similarity = overlap / max(len(title_words), len(existing_words))
                if similarity > 0.8:
                    return True
        
        return False
    
    def is_finance_news(self, title: str, description: str = '') -> bool:
        """Check if the news article is about stock prices or finance."""
        text = (title + ' ' + (description or '')).lower()
        
        for keyword in self.FINANCE_KEYWORDS:
            if keyword in text:
                logger.debug(f"Filtered finance news: {title[:50]}... (matched: {keyword})")
                return True
        
        return False
    
    def collect_competitor_news(self, competitor: Competitor, days_back: int = 7) -> List[NewsItem]:
        """Collect news for a specific competitor."""
        collected_items = []
        search_terms = self.get_competitor_search_terms(competitor)
        from_date = datetime.utcnow() - timedelta(days=days_back)
        
        # First, collect from configured RSS feeds
        for feed_config in self.rss_feeds:
            feed_url = feed_config.get('url', '')
            feed_name = feed_config.get('name', 'RSS Feed')
            logger.info(f"Fetching from RSS feed: {feed_name}")
            
            articles = self.fetch_rss_feed(feed_url)
            logger.info(f"Found {len(articles)} articles from {feed_name}")
            
            for article in articles:
                if not article['title'] or not article['url']:
                    continue
                
                # Check for duplicates
                if self.is_duplicate(article['title'], article['url']):
                    continue
                
                # Filter out stock/finance news
                if self.is_finance_news(article['title'], article.get('description', '')):
                    continue
                
                # Create news item
                news_item = NewsItem(
                    competitor_id=competitor.id,
                    title=article['title'][:500],
                    description=article.get('description', '')[:2000] if article.get('description') else None,
                    content=article.get('content', '')[:10000] if article.get('content') else None,
                    url=article['url'][:1000],
                    source=article.get('source', feed_name)[:255],
                    author=article.get('author', '')[:255] if article.get('author') else None,
                    published_at=article.get('published_at'),
                    is_processed=False
                )
                
                db.session.add(news_item)
                collected_items.append(news_item)
        
        # Then search for competitor by name using Google News RSS
        for term in search_terms:
            # Use Google News RSS (always works without API key)
            articles = self.fetch_google_news_rss(term)
            logger.info(f"Found {len(articles)} articles from Google News for '{term}'")
            
            for article in articles:
                if not article['title'] or not article['url']:
                    continue
                
                # Check for duplicates
                if self.is_duplicate(article['title'], article['url']):
                    continue
                
                # Filter out stock/finance news
                if self.is_finance_news(article['title'], article.get('description', '')):
                    continue
                
                # Create news item
                news_item = NewsItem(
                    competitor_id=competitor.id,
                    title=article['title'][:500],
                    description=article.get('description', '')[:2000] if article.get('description') else None,
                    content=article.get('content', '')[:10000] if article.get('content') else None,
                    url=article['url'][:1000],
                    source=article.get('source', '')[:255],
                    author=article.get('author', '')[:255] if article.get('author') else None,
                    published_at=article.get('published_at'),
                    is_processed=False
                )
                
                db.session.add(news_item)
                collected_items.append(news_item)
        
        db.session.commit()
        logger.info(f"Collected {len(collected_items)} new articles for {competitor.name}")
        return collected_items
    
    def collect_all_news(self, days_back: int = 7) -> Dict[str, List[NewsItem]]:
        """Collect news for all active competitors."""
        results = {}
        
        competitors = Competitor.query.filter_by(is_active=True).all()
        
        for competitor in competitors:
            try:
                items = self.collect_competitor_news(competitor, days_back)
                results[competitor.name] = items
            except Exception as e:
                logger.error(f"Error collecting news for {competitor.name}: {e}")
                results[competitor.name] = []
        
        return results
    
    def get_unprocessed_news(self, limit: int = 50) -> List[NewsItem]:
        """Get news items that haven't been processed yet."""
        return NewsItem.query.filter_by(
            is_processed=False
        ).order_by(NewsItem.collected_at.desc()).limit(limit).all()
    
    def get_recent_news(self, hours: int = 24, competitor_id: Optional[int] = None) -> List[Dict]:
        """Get recent news items."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        query = NewsItem.query.filter(NewsItem.collected_at >= since)
        
        if competitor_id:
            query = query.filter_by(competitor_id=competitor_id)
        
        items = query.order_by(NewsItem.published_at.desc()).all()
        
        return [item.to_dict() for item in items]


def run_collector():
    """Run the news collector as a standalone process."""
    from . import create_app
    
    app = create_app()
    
    with app.app_context():
        collector = NewsCollector()
        results = collector.collect_all_news()
        
        total = sum(len(items) for items in results.values())
        print(f"\n{'='*60}")
        print(f"COLLECTED {total} NEWS ITEMS")
        print(f"{'='*60}\n")
        
        for competitor_name, items in results.items():
            print(f"\n{competitor_name}: {len(items)} items")
            for item in items[:5]:
                print(f"  - {item.title[:80]}...")
                print(f"    Source: {item.source}")
                print(f"    URL: {item.url[:60]}...")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_collector()
