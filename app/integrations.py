"""
Integration with changedetection.io for website monitoring.
Also supports Google Alerts RSS feeds.
"""
import os
import requests
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urljoin
import json

logger = logging.getLogger(__name__)


class ChangeDetectionIO:
    """
    Integration with changedetection.io self-hosted instance.
    
    Setup instructions:
    1. Run changedetection.io with Docker:
       docker run -d --restart=always -p 5555:5000 \
         -v /path/to/data:/datastore \
         --name changedetection \
         dgtlmoon/changedetection.io
    
    2. Set environment variables:
       CHANGEDETECTION_URL=http://localhost:5555
       CHANGEDETECTION_API_KEY=your-api-key (get from Settings)
    """
    
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or os.getenv('CHANGEDETECTION_URL', 'http://localhost:5555')
        self.api_key = api_key or os.getenv('CHANGEDETECTION_API_KEY', '')
        self.session = requests.Session()
        if self.api_key:
            self.session.headers['x-api-key'] = self.api_key
    
    def is_configured(self) -> bool:
        """Check if changedetection.io is configured and accessible."""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/watch", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def list_watches(self) -> List[Dict]:
        """Get all configured watches."""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/watch")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error listing watches from changedetection.io: {e}")
            return []
    
    def add_watch(self, url: str, tag: str = None, title: str = None,
                  check_interval: int = 3600) -> Optional[str]:
        """
        Add a new URL to watch.
        
        Args:
            url: The URL to monitor
            tag: Tag/category for the watch (e.g., competitor name)
            title: Display title for the watch
            check_interval: Check frequency in seconds (default: 1 hour)
        
        Returns:
            Watch UUID if successful, None otherwise
        """
        try:
            data = {
                'url': url,
                'time_between_check': {'seconds': check_interval}
            }
            
            if tag:
                data['tag'] = tag
            if title:
                data['title'] = title
            
            response = self.session.post(
                f"{self.base_url}/api/v1/watch",
                json=data
            )
            response.raise_for_status()
            result = response.json()
            return result.get('uuid')
        except Exception as e:
            logger.error(f"Error adding watch to changedetection.io: {e}")
            return None
    
    def get_watch(self, uuid: str) -> Optional[Dict]:
        """Get details for a specific watch."""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/watch/{uuid}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting watch {uuid}: {e}")
            return None
    
    def get_watch_history(self, uuid: str) -> List[Dict]:
        """Get change history for a watch."""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/watch/{uuid}/history")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting history for {uuid}: {e}")
            return []
    
    def get_latest_snapshot(self, uuid: str) -> Optional[str]:
        """Get the latest snapshot content for a watch."""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/watch/{uuid}/history/latest")
            if response.status_code == 200:
                return response.text
        except Exception as e:
            logger.error(f"Error getting latest snapshot for {uuid}: {e}")
        return None
    
    def get_diff(self, uuid: str, timestamp: str = None) -> Optional[str]:
        """Get the diff for a change."""
        try:
            url = f"{self.base_url}/api/v1/watch/{uuid}/diff"
            if timestamp:
                url += f"/{timestamp}"
            response = self.session.get(url)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            logger.error(f"Error getting diff for {uuid}: {e}")
        return None
    
    def delete_watch(self, uuid: str) -> bool:
        """Delete a watch."""
        try:
            response = self.session.delete(f"{self.base_url}/api/v1/watch/{uuid}")
            return response.status_code in [200, 204]
        except Exception as e:
            logger.error(f"Error deleting watch {uuid}: {e}")
            return False
    
    def trigger_check(self, uuid: str) -> bool:
        """Manually trigger a check for a watch."""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/watch/{uuid}/trigger")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error triggering check for {uuid}: {e}")
            return False
    
    def get_changed_watches(self) -> List[Dict]:
        """Get all watches that have changed since last view."""
        watches = self.list_watches()
        changed = []
        for uuid, watch in watches.items() if isinstance(watches, dict) else []:
            if watch.get('has_ldjson_ld_+_desktop_screenshot'):
                changed.append({'uuid': uuid, **watch})
        return changed
    
    def sync_from_config(self, competitor_name: str, urls: List[Dict]) -> Dict[str, Any]:
        """
        Sync URLs from competitors.yaml to changedetection.io.
        
        Args:
            competitor_name: Name of the competitor (used as tag)
            urls: List of URL configs from competitors.yaml
        
        Returns:
            Dict with sync results
        """
        results = {
            'added': 0,
            'skipped': 0,
            'errors': 0,
            'watches': []
        }
        
        # Get existing watches
        existing_watches = self.list_watches()
        existing_urls = set()
        
        if isinstance(existing_watches, dict):
            for uuid, watch in existing_watches.items():
                existing_urls.add(watch.get('url', ''))
        
        for url_config in urls:
            url = url_config.get('url', '')
            if not url:
                continue
            
            if url in existing_urls:
                results['skipped'] += 1
                continue
            
            check_interval = url_config.get('check_interval_hours', 24) * 3600
            
            uuid = self.add_watch(
                url=url,
                tag=competitor_name,
                title=url_config.get('name', url),
                check_interval=check_interval
            )
            
            if uuid:
                results['added'] += 1
                results['watches'].append({'uuid': uuid, 'url': url})
            else:
                results['errors'] += 1
        
        return results


class GoogleAlertsRSS:
    """
    Helper for Google Alerts RSS feeds.
    
    Setup instructions:
    1. Go to https://www.google.com/alerts
    2. Create alerts for competitor names and products
    3. Set delivery to "RSS feed"
    4. Copy the RSS feed URLs
    """
    
    @staticmethod
    def create_alert_url(query: str, language: str = 'en', region: str = 'US') -> str:
        """
        Generate a Google Alerts RSS URL for a query.
        
        Note: This uses Google News RSS as a workaround since 
        Google Alerts RSS requires account setup.
        
        Args:
            query: Search query
            language: Language code (default: en)
            region: Region code (default: US)
        
        Returns:
            RSS feed URL
        """
        from urllib.parse import quote_plus
        encoded_query = quote_plus(query)
        return f"https://news.google.com/rss/search?q={encoded_query}&hl={language}-{region}&gl={region}&ceid={region}:{language}"
    
    @staticmethod
    def generate_competitor_feeds(competitor_name: str, products: List[str] = None) -> List[Dict]:
        """
        Generate a list of RSS feed configurations for a competitor.
        
        Args:
            competitor_name: Name of the competitor
            products: List of product names to monitor
        
        Returns:
            List of feed configurations
        """
        feeds = []
        
        # Main competitor feed
        feeds.append({
            'url': GoogleAlertsRSS.create_alert_url(competitor_name),
            'name': f'{competitor_name} - General News'
        })
        
        # Competitor + industry terms
        industry_terms = ['new product', 'launch', 'announcement', 'partnership', 'acquisition']
        for term in industry_terms:
            feeds.append({
                'url': GoogleAlertsRSS.create_alert_url(f'{competitor_name} {term}'),
                'name': f'{competitor_name} - {term.title()}'
            })
        
        # Product-specific feeds
        if products:
            for product in products:
                feeds.append({
                    'url': GoogleAlertsRSS.create_alert_url(f'{competitor_name} {product}'),
                    'name': f'{competitor_name} - {product}'
                })
        
        return feeds


class DataCollectionManager:
    """
    Unified manager for data collection from multiple sources:
    - changedetection.io (page monitoring)
    - Google Alerts/News RSS (news monitoring)
    - Direct page scraping (fallback)
    """
    
    def __init__(self):
        self.changedetection = ChangeDetectionIO()
        self.use_changedetection = self.changedetection.is_configured()
        
        if self.use_changedetection:
            logger.info("changedetection.io is configured and will be used for page monitoring")
        else:
            logger.info("changedetection.io not configured, using built-in page monitoring")
    
    def setup_competitor_monitoring(self, competitor_name: str, urls: List[Dict], 
                                   products: List[str] = None) -> Dict:
        """
        Set up comprehensive monitoring for a competitor.
        
        Args:
            competitor_name: Name of the competitor
            urls: List of URLs to monitor
            products: List of product names for news alerts
        
        Returns:
            Setup results
        """
        results = {
            'page_monitoring': None,
            'news_feeds': [],
            'recommendations': []
        }
        
        # Set up page monitoring
        if self.use_changedetection:
            results['page_monitoring'] = self.changedetection.sync_from_config(competitor_name, urls)
            results['recommendations'].append(
                f"✓ Page monitoring configured in changedetection.io for {len(urls)} URLs"
            )
        else:
            results['page_monitoring'] = {'method': 'built-in', 'urls': len(urls)}
            results['recommendations'].append(
                "Consider setting up changedetection.io for more reliable page monitoring"
            )
        
        # Generate news feed configurations
        news_feeds = GoogleAlertsRSS.generate_competitor_feeds(competitor_name, products)
        results['news_feeds'] = news_feeds
        results['recommendations'].append(
            f"Generated {len(news_feeds)} Google News RSS feeds for news monitoring"
        )
        
        # Additional recommendations
        results['recommendations'].extend([
            "Set up Google Alerts (google.com/alerts) for email notifications",
            "Consider adding social media monitoring (Twitter/LinkedIn)",
            "Review and adjust check intervals based on competitor activity"
        ])
        
        return results
    
    def get_status(self) -> Dict:
        """Get the status of all data collection sources."""
        status = {
            'changedetection': {
                'configured': self.use_changedetection,
                'url': self.changedetection.base_url if self.use_changedetection else None,
                'watches': 0
            },
            'builtin_monitor': {
                'active': True
            },
            'news_sources': {
                'google_news_rss': True,
                'newsapi': bool(os.getenv('NEWSAPI_KEY'))
            }
        }
        
        if self.use_changedetection:
            watches = self.changedetection.list_watches()
            status['changedetection']['watches'] = len(watches) if isinstance(watches, dict) else 0
        
        return status


# Aliases for backward compatibility
ChangeDetectionIntegration = ChangeDetectionIO
GoogleAlertsIntegration = GoogleAlertsRSS
