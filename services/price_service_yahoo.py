"""
Stock Price Fetching Service

Fetches stock prices from Yahoo Finance.
"""

import yfinance as yf
from typing import Optional, Dict
from datetime import datetime


class PriceService:
    """Service for fetching stock market data."""
    
    async def get_current_price(self, ticker: str) -> Optional[Dict]:
        """
        Fetch current stock price.
        
        Returns:
            Dict with price data or None if not found
            {
                "ticker": "AAPL",
                "price": 150.25,
                "change_percent": 2.5,
                "volume": 50000000,
                "timestamp": "2026-01-16T00:00:00Z"
            }
        """
        try:
            stock = yf.Ticker(ticker.upper())
            info = stock.info
            
            if not info or 'currentPrice' not in info:
                print(f"⚠️  No data for {ticker}")
                return None
            
            current = info.get('currentPrice')
            previous = info.get('previousClose', current)
            
            # Calculate percent change
            change = 0.0
            if previous and previous > 0:
                change = ((current - previous) / previous) * 100
            
            return {
                "ticker": ticker.upper(),
                "price": float(current),
                "change_percent": round(change, 2),
                "volume": info.get('volume', 0),
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
        except Exception as e:
            print(f"❌ Price fetch error for {ticker}: {e}")
            return None
    
    async def get_historical_prices(self, ticker: str, hours: int = 24) -> Optional[list]:
        """
        Fetch historical prices for trend analysis.
        
        Returns:
            List of price records with timestamps
        """
        try:
            stock = yf.Ticker(ticker.upper())
            period = "1d" if hours <= 24 else "5d"
            hist = stock.history(period=period, interval="1h")
            
            if hist.empty:
                return None
            
            prices = []
            for timestamp, row in hist.iterrows():
                prices.append({
                    "price": float(row['Close']),
                    "volume": int(row['Volume']),
                    "timestamp": timestamp.isoformat()
                })
            
            return prices
            
        except Exception as e:
            print(f"❌ Historical fetch error for {ticker}: {e}")
            return None


# Global instance
price_service = PriceService()


async def get_price_service() -> PriceService:
    """Dependency injection helper."""
    return price_service
