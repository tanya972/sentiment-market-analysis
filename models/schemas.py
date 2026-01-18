from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class StockPrice(BaseModel):
    ticker: str
    price: float
    change_percent: float
    volume: int
    timestamp: str

class SentimentData(BaseModel):
    overall_sentiment: str
    score: float
    article_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    recent_headlines: Optional[List[dict]] = None

class StockWithSentiment(BaseModel):
    ticker: str
    price: StockPrice
    sentiment: Optional[SentimentData]
    source: str

class NewsArticle(BaseModel):
    headline: str
    source: str
    url: str
    published_date: str
    summary: Optional[str] = None

class NewsResponse(BaseModel):
    ticker: str
    articles_found: int
    time_range_hours: int
    articles: List[NewsArticle]

class DivergenceAlert(BaseModel):
    ticker: str
    alert_type: str
    detected_at: str
    sentiment: dict
    price: dict
    divergence: dict
    message: str
    top_headlines: List[dict]

class ScanRequest(BaseModel):
    tickers: List[str]
    hours: int = 1

class ScanResponse(BaseModel):
    scan_timestamp: str
    tickers_checked: int
    divergences_found: int
    alerts: List[DivergenceAlert]

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None

class UserCreate(BaseModel):
    email: str

class UserResponse(BaseModel):
    id: int
    email: str
    api_key: str
    created_at: datetime

class SubscriptionCreate(BaseModel):
    ticker: str
    alert_threshold: float = 0.5

class AlertResponse(BaseModel):
    id: int
    ticker: str
    alert_type: str
    message: str
    created_at: datetime
