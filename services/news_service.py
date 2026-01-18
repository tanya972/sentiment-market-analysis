
"""
News scraping service - fetches financial news from multiple sources.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import feedparser

class NewsService:
    def __init__(self):
        self.rss_feeds = {
            'general': [
                'https://feeds.bloomberg.com/markets/news.rss',
                'https://www.cnbc.com/id/100003114/device/rss/rss.html',
                'https://www.investing.com/rss/news.rss'
            ]
        }
    
    async def get_news_for_ticker(self, ticker: str, hours: int = 24) -> List[Dict]:
        '''
        Fetch recent news articles for a specific ticker.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            hours: How many hours back to fetch news
        
        Returns:
            List of news articles with headline, source, url, published_date
        '''
        print(f'📰 Fetching news for {ticker}...')
        
        articles = []
        
        # Method 1: RSS Feeds (free, no API key needed)
        articles.extend(await self._fetch_from_rss(ticker, hours))
        
        # Method 2: Google News (as backup)
        articles.extend(await self._fetch_from_google_news(ticker, hours))
        
        # Remove duplicates (same headline)
        seen_headlines = set()
        unique_articles = []
        for article in articles:
            headline_lower = article['headline'].lower()
            if headline_lower not in seen_headlines:
                seen_headlines.add(headline_lower)
                unique_articles.append(article)
        
        print(f'✅ Found {len(unique_articles)} unique articles for {ticker}')
        return unique_articles[:20]  # Limit to 20 most recent
    
    async def _fetch_from_rss(self, ticker: str, hours: int) -> List[Dict]:
        '''Fetch from RSS feeds'''
        articles = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        try:
            for feed_url in self.rss_feeds['general']:
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:30]:  # Check first 30 entries
                    # Check if article mentions the ticker
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    
                    if ticker.upper() in (title + summary).upper():
                        # Parse published date
                        pub_date = entry.get('published_parsed')
                        if pub_date:
                            pub_datetime = datetime(*pub_date[:6])
                            if pub_datetime < cutoff_time:
                                continue  # Too old
                        
                        articles.append({
                            'headline': title,
                            'source': feed.feed.get('title', 'RSS Feed'),
                            'url': entry.get('link', ''),
                            'published_date': pub_datetime.isoformat() if pub_date else datetime.utcnow().isoformat(),
                            'summary': summary[:200] if summary else ''
                        })
        except Exception as e:
            print(f'⚠️  RSS fetch error: {e}')
        
        return articles
    
    async def _fetch_from_google_news(self, ticker: str, hours: int) -> List[Dict]:
        '''Fetch from Google News RSS (free, no API key)'''
        articles = []
        
        try:
            # Google News RSS for specific ticker
            url = f'https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en'
            
            feed = feedparser.parse(url)
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            
            for entry in feed.entries[:15]:
                pub_date = entry.get('published_parsed')
                if pub_date:
                    pub_datetime = datetime(*pub_date[:6])
                    if pub_datetime < cutoff_time:
                        continue
                else:
                    pub_datetime = datetime.utcnow()
                
                articles.append({
                    'headline': entry.get('title', ''),
                    'source': entry.get('source', {}).get('title', 'Google News'),
                    'url': entry.get('link', ''),
                    'published_date': pub_datetime.isoformat(),
                    'summary': entry.get('summary', '')[:200]
                })
        except Exception as e:
            print(f'⚠️  Google News fetch error: {e}')
        
        return articles
    
    async def get_batch_news(self, tickers: List[str], hours: int = 24) -> Dict[str, List[Dict]]:
        '''
        Fetch news for multiple tickers concurrently.
        
        Args:
            tickers: List of ticker symbols
            hours: How many hours back
        
        Returns:
            Dictionary mapping ticker -> list of articles
        '''
        print(f'📰 Batch fetching news for {len(tickers)} tickers...')
        
        # Fetch all concurrently (async magic!)
        tasks = [self.get_news_for_ticker(ticker, hours) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build result dictionary
        news_by_ticker = {}
        for ticker, result in zip(tickers, results):
            if isinstance(result, Exception):
                print(f'❌ Error fetching {ticker}: {result}')
                news_by_ticker[ticker] = []
            else:
                news_by_ticker[ticker] = result
        
        return news_by_ticker

# Singleton instance
news_service = NewsService()

async def get_news_service():
    return news_service
