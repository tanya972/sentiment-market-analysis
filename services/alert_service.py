"""
Alert/Divergence Detection Service - ULTRA SENSITIVE FOR TESTING
"""

from typing import Optional, Dict, List
from datetime import datetime, timedelta
from services.price_service import price_service
from services.news_service import news_service
from services.sentiment_service import sentiment_service

class AlertService:
    
    def __init__(self):
        # ULTRA LOW THRESHOLDS - Will catch almost any divergence
        self.sentiment_threshold = 0.1   # Very sensitive (was 0.5)
        self.price_threshold = 0.1       # Very sensitive (was 1.0)
    
    async def detect_divergence(self, ticker: str, hours: int = 1) -> Optional[Dict]:
        print(f' Checking divergence for {ticker} (ULTRA SENSITIVE MODE)...')
        
        # 1. Get price data
        current_price_data = await price_service.get_current_price(ticker)
        if not current_price_data:
            print(f'    No price data for {ticker}')
            return None
        
        price_change = current_price_data['change_percent']
        current_price = current_price_data['price']
        
        # 2. Get news - use longer window
        articles = await news_service.get_news_for_ticker(ticker, hours=max(hours, 48))
        
        if not articles or len(articles) < 1:  # Only need 1 article now
            print(f'     No news for {ticker}')
            return None
        
        print(f'   Found {len(articles)} articles')
        
        # 3. Analyze sentiment
        headlines = [a['headline'] for a in articles[:10]]
        sentiments = sentiment_service.analyze_batch(headlines)
        aggregated = sentiment_service.aggregate_sentiment(sentiments)
        
        sentiment_score = aggregated['overall_score']
        sentiment_label = aggregated['overall_sentiment']
        
        print(f'    Sentiment: {sentiment_label} ({sentiment_score:+.2f})')
        print(f'    Price change: {price_change:+.2f}%')
        print(f'    Thresholds: sentiment={self.sentiment_threshold}, price={self.price_threshold}%')
        
        # 4. Check divergence
        divergence = self._check_divergence(
            sentiment_score=sentiment_score,
            price_change=price_change
        )
        
        if not divergence:
            print(f'   ℹ  No divergence detected')
            # Show why
            if abs(sentiment_score) < self.sentiment_threshold:
                print(f'      Reason: Sentiment too weak ({abs(sentiment_score):.2f} < {self.sentiment_threshold})')
            elif abs(price_change) < self.price_threshold:
                print(f'      Reason: Price change too small ({abs(price_change):.2f}% < {self.price_threshold}%)')
            else:
                print(f'      Reason: Sentiment and price agree (both {"positive" if sentiment_score > 0 and price_change > 0 else "negative"})')
            return None
        
        # 5. Create alert
        alert = {
            'ticker': ticker,
            'alert_type': divergence['type'],
            'detected_at': datetime.utcnow().isoformat() + 'Z',
            'sentiment': {
                'score': sentiment_score,
                'label': sentiment_label,
                'article_count': len(articles),
                'positive_count': aggregated['positive_count'],
                'negative_count': aggregated['negative_count']
            },
            'price': {
                'current': current_price,
                'change_percent': price_change
            },
            'divergence': {
                'magnitude': divergence['magnitude'],
                'signal': divergence['signal'],
                'confidence': divergence['confidence']
            },
            'message': self._create_message(
                ticker=ticker,
                divergence_type=divergence['type'],
                sentiment_score=sentiment_score,
                price_change=price_change,
                magnitude=divergence['magnitude']
            ),
            'top_headlines': [
                {'headline': s['text'], 'sentiment': s['sentiment'], 'score': s['score']}
                for s in sentiments[:3]
            ]
        }
        
        print(f'    {divergence["type"].upper()} DETECTED!')
        
        return alert
    
    def _check_divergence(self, sentiment_score: float, price_change: float) -> Optional[Dict]:
        
        # Check if sentiment is strong enough
        if abs(sentiment_score) < self.sentiment_threshold:
            return None
        
        # Check if price move is significant enough
        if abs(price_change) < self.price_threshold:
            return None
        
        # Bullish Divergence: Positive sentiment + Price drops
        if sentiment_score > self.sentiment_threshold and price_change < -self.price_threshold:
            magnitude = abs(sentiment_score) + abs(price_change) / 10
            print(f'    BULLISH DIVERGENCE! (positive news + price drop)')
            
            return {
                'type': 'bullish_divergence',
                'signal': 'BUY',
                'magnitude': round(magnitude, 2),
                'confidence': min(abs(sentiment_score), abs(price_change / 5))
            }
        
        # Bearish Divergence: Negative sentiment + Price rises
        if sentiment_score < -self.sentiment_threshold and price_change > self.price_threshold:
            magnitude = abs(sentiment_score) + abs(price_change) / 10
            print(f'    BEARISH DIVERGENCE! (negative news + price rise)')
            
            return {
                'type': 'bearish_divergence',
                'signal': 'SELL',
                'magnitude': round(magnitude, 2),
                'confidence': min(abs(sentiment_score), abs(price_change / 5))
            }
        
        return None
    
    def _create_message(self, ticker: str, divergence_type: str, sentiment_score: float, 
                       price_change: float, magnitude: float) -> str:
        if divergence_type == 'bullish_divergence':
            return (
                f" BULLISH DIVERGENCE detected for {ticker}! "
                f"Despite positive news (sentiment: {sentiment_score:+.2f}), "
                f"the stock has dropped {abs(price_change):.1f}%. "
                f"Market may have overreacted - potential buying opportunity. "
                f"Magnitude: {magnitude:.2f}"
            )
        else:
            return (
                f" BEARISH DIVERGENCE detected for {ticker}! "
                f"Despite negative news (sentiment: {sentiment_score:+.2f}), "
                f"the stock has risen {price_change:.1f}%. "
                f"Price may be unsustainable - potential selling opportunity. "
                f"Magnitude: {magnitude:.2f}"
            )
    
    async def check_multiple_tickers(self, tickers: List[str], hours: int = 1) -> List[Dict]:
        print(f'\n Checking {len(tickers)} tickers for divergences...\n')
        alerts = []
        
        for ticker in tickers:
            try:
                alert = await self.detect_divergence(ticker, hours)
                if alert:
                    alerts.append(alert)
            except Exception as e:
                print(f'    Error checking {ticker}: {e}')
        
        print(f'\n Found {len(alerts)} divergences out of {len(tickers)} tickers\n')
        return alerts

alert_service = AlertService()

async def get_alert_service():
    return alert_service
