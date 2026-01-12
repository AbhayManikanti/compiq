"""
Page Monitoring System
Monitors competitor web pages for changes and detects updates.
"""
import requests
from bs4 import BeautifulSoup
import html2text
import xxhash
from datetime import datetime, timedelta
from difflib import unified_diff
import logging
import time
from typing import Optional, Tuple, List, Dict
from .database import db, MonitoredURL, PageSnapshot, Competitor

logger = logging.getLogger(__name__)


class PageMonitor:
    """Monitors web pages for changes."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = True
        self.html_converter.ignore_emphasis = False
        self.html_converter.body_width = 0
    
    def fetch_page(self, url: str, timeout: int = 30) -> Tuple[Optional[str], Optional[str]]:
        """
        Fetch a web page and return its content.
        
        Returns:
            Tuple of (html_content, error_message)
        """
        try:
            response = self.session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return response.text, None
        except requests.exceptions.Timeout:
            return None, f"Timeout after {timeout} seconds"
        except requests.exceptions.TooManyRedirects:
            return None, "Too many redirects"
        except requests.exceptions.RequestException as e:
            return None, str(e)
    
    def extract_text(self, html_content: str) -> str:
        """Extract readable text from HTML content."""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Remove script, style, and other non-content elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 
                                'aside', 'noscript', 'iframe', 'svg']):
                element.decompose()
            
            # Try to find main content area
            main_content = (
                soup.find('main') or 
                soup.find('article') or 
                soup.find('div', {'class': ['content', 'main-content', 'page-content']}) or
                soup.find('body')
            )
            
            if main_content:
                text = self.html_converter.handle(str(main_content))
            else:
                text = self.html_converter.handle(str(soup))
            
            # Clean up whitespace
            lines = [line.strip() for line in text.split('\n')]
            text = '\n'.join(line for line in lines if line)
            
            return text
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            return ""
    
    def compute_hash(self, content: str) -> str:
        """Compute a hash of the content for change detection."""
        # Normalize whitespace before hashing
        normalized = ' '.join(content.split())
        return xxhash.xxh64(normalized.encode()).hexdigest()
    
    def compute_diff(self, old_content: str, new_content: str) -> str:
        """Compute a diff between old and new content."""
        old_lines = old_content.split('\n')
        new_lines = new_content.split('\n')
        
        diff = unified_diff(
            old_lines, 
            new_lines, 
            fromfile='previous', 
            tofile='current',
            lineterm=''
        )
        
        return '\n'.join(diff)
    
    def summarize_changes(self, diff: str) -> str:
        """Create a human-readable summary of changes."""
        if not diff:
            return "No changes detected"
        
        added_lines = []
        removed_lines = []
        
        for line in diff.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line[1:].strip())
            elif line.startswith('-') and not line.startswith('---'):
                removed_lines.append(line[1:].strip())
        
        # Filter out empty lines
        added_lines = [l for l in added_lines if l]
        removed_lines = [l for l in removed_lines if l]
        
        summary_parts = []
        
        if added_lines:
            summary_parts.append(f"Added ({len(added_lines)} lines):\n" + 
                               '\n'.join(f"  + {line[:100]}" for line in added_lines[:10]))
            if len(added_lines) > 10:
                summary_parts.append(f"  ... and {len(added_lines) - 10} more lines")
        
        if removed_lines:
            summary_parts.append(f"Removed ({len(removed_lines)} lines):\n" + 
                               '\n'.join(f"  - {line[:100]}" for line in removed_lines[:10]))
            if len(removed_lines) > 10:
                summary_parts.append(f"  ... and {len(removed_lines) - 10} more lines")
        
        return '\n\n'.join(summary_parts) if summary_parts else "Minor formatting changes only"
    
    def check_url(self, monitored_url: MonitoredURL) -> Optional[PageSnapshot]:
        """
        Check a single URL for changes.
        
        Returns:
            PageSnapshot if changes detected, None otherwise
        """
        logger.info(f"Checking URL: {monitored_url.url}")
        
        # Fetch the page
        html_content, error = self.fetch_page(monitored_url.url)
        
        if error:
            logger.error(f"Error fetching {monitored_url.url}: {error}")
            monitored_url.last_error = error
            monitored_url.consecutive_errors += 1
            monitored_url.last_checked_at = datetime.utcnow()
            db.session.commit()
            return None
        
        # Reset error count on success
        monitored_url.consecutive_errors = 0
        monitored_url.last_error = None
        monitored_url.last_checked_at = datetime.utcnow()
        
        # Extract text
        extracted_text = self.extract_text(html_content)
        
        # Compute hash
        content_hash = self.compute_hash(extracted_text)
        
        # Check if content changed
        has_changes = False
        diff_summary = None
        
        if monitored_url.last_content_hash:
            if content_hash != monitored_url.last_content_hash:
                has_changes = True
                if monitored_url.last_content:
                    diff = self.compute_diff(monitored_url.last_content, extracted_text)
                    diff_summary = self.summarize_changes(diff)
                logger.info(f"Changes detected on {monitored_url.url}")
        else:
            # First time checking this URL
            logger.info(f"Initial capture for {monitored_url.url}")
        
        # Create snapshot
        snapshot = PageSnapshot(
            monitored_url_id=monitored_url.id,
            content_hash=content_hash,
            content=html_content[:50000],  # Limit stored content
            extracted_text=extracted_text[:50000],
            has_changes=has_changes,
            diff_summary=diff_summary
        )
        
        # Update monitored URL
        monitored_url.last_content_hash = content_hash
        monitored_url.last_content = extracted_text[:50000]
        
        db.session.add(snapshot)
        db.session.commit()
        
        return snapshot if has_changes else None
    
    def check_all_urls(self, force: bool = False) -> List[PageSnapshot]:
        """
        Check all active monitored URLs for changes.
        
        Args:
            force: If True, check all URLs regardless of last check time
            
        Returns:
            List of PageSnapshots with detected changes
        """
        changed_snapshots = []
        
        # Get all active URLs
        urls = MonitoredURL.query.filter_by(is_active=True).all()
        
        for monitored_url in urls:
            # Check if we should skip based on interval
            if not force and monitored_url.last_checked_at:
                next_check = monitored_url.last_checked_at + timedelta(
                    hours=monitored_url.check_interval_hours
                )
                if datetime.utcnow() < next_check:
                    logger.debug(f"Skipping {monitored_url.url}, not due for check yet")
                    continue
            
            try:
                snapshot = self.check_url(monitored_url)
                if snapshot and snapshot.has_changes:
                    changed_snapshots.append(snapshot)
                
                # Be nice to servers
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error checking {monitored_url.url}: {e}")
                continue
        
        logger.info(f"Checked {len(urls)} URLs, found {len(changed_snapshots)} with changes")
        return changed_snapshots
    
    def get_recent_changes(self, hours: int = 24, limit: int = 50) -> List[Dict]:
        """Get recent page changes."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        snapshots = PageSnapshot.query.filter(
            PageSnapshot.has_changes == True,
            PageSnapshot.captured_at >= since
        ).order_by(PageSnapshot.captured_at.desc()).limit(limit).all()
        
        results = []
        for snapshot in snapshots:
            monitored_url = snapshot.monitored_url
            competitor = monitored_url.competitor
            
            results.append({
                'snapshot_id': snapshot.id,
                'url': monitored_url.url,
                'url_name': monitored_url.name,
                'page_type': monitored_url.page_type,
                'competitor_id': competitor.id,
                'competitor_name': competitor.name,
                'diff_summary': snapshot.diff_summary,
                'captured_at': snapshot.captured_at.isoformat()
            })
        
        return results


def run_monitor():
    """Run the page monitor as a standalone process."""
    from . import create_app
    
    app = create_app()
    
    with app.app_context():
        monitor = PageMonitor()
        changes = monitor.check_all_urls()
        
        if changes:
            print(f"\n{'='*60}")
            print(f"DETECTED {len(changes)} PAGE CHANGES")
            print(f"{'='*60}\n")
            
            for snapshot in changes:
                url = snapshot.monitored_url
                print(f"URL: {url.url}")
                print(f"Competitor: {url.competitor.name}")
                print(f"Summary:\n{snapshot.diff_summary}")
                print("-" * 40)
        else:
            print("No changes detected.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_monitor()
