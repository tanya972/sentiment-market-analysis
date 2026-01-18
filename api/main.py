from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import time
from typing import List

from api.config import get_settings
from models.database import create_tables
from models.schemas import (
    StockWithSentiment, NewsResponse, DivergenceAlert,
    ScanRequest, ScanResponse, ErrorResponse
)
from services.cache import cache
from services.price_service import price_service
from services.news_service import news_service
from services.sentiment_service import sentiment_service
from services.alert_service import alert_service

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(' Starting Sentiment Market Alerts API...')
    create_tables()
    await cache.connect()
    print(' Application started!')
    print(f' API Docs: http://localhost:8000/docs')
    print(f' Web UI: http://localhost:8000/ui')
    yield
    print('Shutting down...')
    await cache.close()

app = FastAPI(
    title='Sentiment Market Alerts API',
    version='1.0.0',
    description='Real-time stock sentiment analysis and divergence detection',
    docs_url='/docs',
    redoc_url='/redoc',
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.middleware('http')
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers['X-Process-Time'] = f'{process_time * 1000:.2f}ms'
    if process_time > 1.0:
        print(f'  Slow: {request.method} {request.url.path} ({process_time:.2f}s)')
    return response

@app.get('/')
async def root():
    return {
        'name': 'Sentiment Market Alerts API',
        'version': '1.0.0',
        'description': 'Real-time market sentiment analysis with divergence detection',
        'docs': '/docs',
        'ui': '/ui',
        'endpoints': {
            'health': '/health',
            'stock_data': '/api/v1/stocks/{ticker}',
            'news': '/api/v1/news/{ticker}',
            'alerts': '/api/v1/alerts/{ticker}',
            'scan': '/api/v1/alerts/scan'
        }
    }

@app.get('/ui', include_in_schema=False)
async def serve_ui():
    try:
        return FileResponse('/app/index.html')
    except:
        return JSONResponse({'message': 'UI not found'})

@app.get('/health')
async def health_check():
    cache_healthy = True
    try:
        await cache.exists('health_check')
    except:
        cache_healthy = False
    
    return {
        'status': 'healthy',
        'timestamp': time.time(),
        'checks': {
            'cache': 'healthy' if cache_healthy else 'degraded',
            'database': 'healthy'
        }
    }

@app.get('/api/v1/stocks/{ticker}')
async def get_stock(ticker: str):
    ticker = ticker.upper()
    cache_key = cache.price_key(ticker)
    cached = await cache.get(cache_key)
    
    if cached:
        price_data = cached
        source = 'cache'
    else:
        price_data = await price_service.get_current_price(ticker)
        if not price_data:
            raise HTTPException(status_code=404, detail='TICKER_NOT_FOUND')
        await cache.set(cache_key, price_data, ttl=settings.cache_ttl_seconds)
        source = 'live'
    
    sentiment_data = None
    try:
        articles = await news_service.get_news_for_ticker(ticker, hours=24)
        if articles and len(articles) >= 3:
            headlines = [a['headline'] for a in articles[:10]]
            sentiments = sentiment_service.analyze_batch(headlines)
            aggregated = sentiment_service.aggregate_sentiment(sentiments)
            
            sentiment_data = {
                'overall_sentiment': aggregated['overall_sentiment'],
                'score': aggregated['overall_score'],
                'article_count': len(articles),
                'positive_count': aggregated['positive_count'],
                'negative_count': aggregated['negative_count'],
                'neutral_count': aggregated['neutral_count'],
                'recent_headlines': [
                    {'headline': s['text'], 'sentiment': s['sentiment'], 'score': s['score']}
                    for s in sentiments[:5]
                ]
            }
    except Exception as e:
        print(f'Sentiment error for {ticker}: {e}')
    
    return {
        'ticker': ticker,
        'price': price_data,
        'sentiment': sentiment_data,
        'source': source
    }

@app.get('/api/v1/news/{ticker}')
async def get_news(ticker: str, hours: int = 24):
    ticker = ticker.upper()
    articles = await news_service.get_news_for_ticker(ticker, hours)
    if not articles:
        raise HTTPException(status_code=404, detail='NO_NEWS_FOUND')
    return {
        'ticker': ticker,
        'articles_found': len(articles),
        'time_range_hours': hours,
        'articles': articles
    }

@app.get('/api/v1/alerts/{ticker}')
async def check_alert(ticker: str, hours: int = 1):
    """
    Check for divergence alert with proper error handling.
    """
    ticker = ticker.upper()
    
    try:
        alert = await alert_service.detect_divergence(ticker, hours)
        
        if not alert:
            # Return 404 with proper JSON response
            return JSONResponse(
                status_code=404,
                content={
                    'error': 'NO_DIVERGENCE_FOUND',
                    'message': f'No divergence detected for {ticker}. Sentiment and price are aligned.',
                    'ticker': ticker,
                    'hours_checked': hours
                }
            )
        
        return alert
        
    except Exception as e:
        print(f'Error in check_alert: {e}')
        import traceback
        traceback.print_exc()
        
        # Return 500 with proper JSON response
        return JSONResponse(
            status_code=500,
            content={
                'error': 'INTERNAL_ERROR',
                'message': str(e),
                'ticker': ticker
            }
        )

@app.post('/api/v1/alerts/scan')
async def scan_for_alerts(request: ScanRequest):
    try:
        alerts = await alert_service.check_multiple_tickers(
            tickers=request.tickers,
            hours=request.hours
        )
        return {
            'scan_timestamp': datetime.utcnow().isoformat() + 'Z',
            'tickers_checked': len(request.tickers),
            'divergences_found': len(alerts),
            'alerts': alerts
        }
    except Exception as e:
        print(f'Error in scan: {e}')
        return JSONResponse(
            status_code=500,
            content={'error': 'SCAN_ERROR', 'message': str(e)}
        )

@app.get('/api/v1/alerts/scan/{tickers}')
async def quick_scan(tickers: str, hours: int = 1):
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(',')]
        if len(ticker_list) > 20:
            raise HTTPException(status_code=400, detail='Maximum 20 tickers per scan')
        
        alerts = await alert_service.check_multiple_tickers(
            tickers=ticker_list,
            hours=hours
        )
        return {
            'scan_timestamp': datetime.utcnow().isoformat() + 'Z',
            'tickers_checked': len(ticker_list),
            'divergences_found': len(alerts),
            'alerts': alerts
        }
    except Exception as e:
        print(f'Error in quick_scan: {e}')
        return JSONResponse(
            status_code=500,
            content={'error': 'SCAN_ERROR', 'message': str(e)}
        )
