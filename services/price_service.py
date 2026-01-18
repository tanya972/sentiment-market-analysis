from typing import Optional, Dict
from datetime import datetime, timedelta
import random

class PriceService:
    
    async def get_current_price(self, ticker: str) -> Optional[Dict]:
        mock_data = {
            'AAPL': 185.50, 'SPY': 478.25, 'MSFT': 420.75,
            'GOOGL': 142.30, 'TSLA': 248.90, 'NVDA': 505.20,
            'META': 388.65, 'AMZN': 178.40, 'JPM': 195.80
        }
        
        ticker_upper = ticker.upper()
        base = mock_data.get(ticker_upper, 100.0)
        price = base + random.uniform(-2, 2)
        change = random.uniform(-3, 3)
        
        return {
            'ticker': ticker_upper,
            'price': round(price, 2),
            'change_percent': round(change, 2),
            'volume': random.randint(5000000, 50000000),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    
    async def get_historical_prices(self, ticker: str, hours: int = 24):
        return []

price_service = PriceService()
async def get_price_service():
    return price_service
