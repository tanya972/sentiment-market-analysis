"""
Redis Caching Service

Implements cache-aside pattern with TTL expiration.
"""

import redis.asyncio as redis
import json
from typing import Optional, Any
from datetime import timedelta

from api.config import get_settings

settings = get_settings()


class CacheService:
    """Async Redis caching service."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis with connection pooling."""
        self.redis_client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=10
        )
        await self.redis_client.ping()
        print("✅ Connected to Redis")
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (returns None if not found)."""
        if not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            print(f"❌ Cache GET error: {key} - {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with optional TTL (seconds)."""
        if not self.redis_client:
            return False
        
        try:
            serialized = json.dumps(value)
            
            if ttl:
                await self.redis_client.setex(
                    key,
                    timedelta(seconds=ttl),
                    serialized
                )
            else:
                await self.redis_client.set(key, serialized)
            
            return True
        except Exception as e:
            print(f"❌ Cache SET error: {key} - {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"❌ Cache DELETE error: {key} - {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self.redis_client:
            return False
        
        try:
            return await self.redis_client.exists(key) > 0
        except Exception as e:
            print(f"❌ Cache EXISTS error: {key} - {e}")
            return False
    
    # Cache key helpers
    @staticmethod
    def price_key(ticker: str) -> str:
        """Generate cache key for price data."""
        return f"price:{ticker.upper()}"
    
    @staticmethod
    def sentiment_key(ticker: str) -> str:
        """Generate cache key for sentiment data."""
        return f"sentiment:{ticker.upper()}"
    
    @staticmethod
    def rate_limit_key(api_key: str, window: str = "minute") -> str:
        """Generate cache key for rate limiting."""
        return f"ratelimit:{api_key}:{window}"


# Global instance
cache = CacheService()


async def get_cache() -> CacheService:
    """Dependency injection helper."""
    return cache
