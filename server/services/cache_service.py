"""
Cache Service
=============
Simple Redis caching for expensive operations.
Works with Railway's Redis service.
"""

import os
import json
import redis
from typing import Any, Optional
from datetime import datetime


# Initialize Redis connection
# Railway automatically provides REDIS_URL when you add Redis service
REDIS_URL = os.getenv("REDIS_URL") or os.getenv("REDIS_PUBLIC_URL")

if REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        print("✅ Redis connected successfully")
    except Exception as e:
        print(f"⚠️ Redis connection failed: {e}")
        redis_client = None
else:
    print("ℹ️ Redis not configured (REDIS_URL not found)")
    redis_client = None


class CacheService:
    """
    Simple caching service for Farm to People.
    """
    
    @staticmethod
    def is_available() -> bool:
        """Check if Redis is available."""
        return redis_client is not None
    
    @staticmethod
    def get_cart(phone: str) -> Optional[dict]:
        """
        Get cached cart data for a user.
        
        Args:
            phone: User's phone number
            
        Returns:
            Cart data or None if not cached
        """
        if not redis_client:
            return None
        
        try:
            cached = redis_client.get(f"cart:{phone}")
            if cached:
                print(f"✅ Cache hit for cart:{phone}")
                return json.loads(cached)
        except Exception as e:
            print(f"⚠️ Cache get error: {e}")
        
        return None
    
    @staticmethod
    def set_cart(phone: str, cart_data: dict, ttl: int = 3600):
        """
        Cache cart data for a user.
        
        Args:
            phone: User's phone number
            cart_data: Cart data to cache
            ttl: Time to live in seconds (default 1 hour)
        """
        if not redis_client:
            return
        
        try:
            redis_client.setex(
                f"cart:{phone}",
                ttl,
                json.dumps(cart_data)
            )
            print(f"✅ Cached cart:{phone} for {ttl} seconds")
        except Exception as e:
            print(f"⚠️ Cache set error: {e}")

    @staticmethod
    def set_cart_response(phone: str, cart_response: dict, ttl: int = 7200):
        """
        Cache complete cart response including swaps and addons.

        Args:
            phone: User's phone number
            cart_response: Complete response with cart_data, swaps, addons
            ttl: Time to live in seconds (default 2 hours)
        """
        if not redis_client:
            return

        try:
            redis_client.setex(
                f"cart_response:{phone}",
                ttl,
                json.dumps(cart_response)
            )
            print(f"✅ Cached complete cart response:{phone} for {ttl} seconds")
        except Exception as e:
            print(f"⚠️ Cart response cache set error: {e}")

    @staticmethod
    def get_cart_response(phone: str) -> Optional[dict]:
        """
        Get cached complete cart response for a user.

        Args:
            phone: User's phone number

        Returns:
            Complete cart response or None if not cached
        """
        if not redis_client:
            return None

        try:
            cached = redis_client.get(f"cart_response:{phone}")
            if cached:
                print(f"✅ Cache hit for cart_response:{phone}")
                return json.loads(cached)
        except Exception as e:
            print(f"⚠️ Cart response cache get error: {e}")

        return None

    @staticmethod
    def invalidate_cart_response(phone: str):
        """
        Invalidate cached complete cart response.

        Args:
            phone: User's phone number
        """
        if not redis_client:
            return

        try:
            redis_client.delete(f"cart_response:{phone}")
            print(f"✅ Invalidated cart response cache for cart_response:{phone}")
        except Exception as e:
            print(f"⚠️ Cart response cache delete error: {e}")

    @staticmethod
    def invalidate_cart(phone: str):
        """
        Invalidate cached cart data.
        
        Args:
            phone: User's phone number
        """
        if not redis_client:
            return
        
        try:
            redis_client.delete(f"cart:{phone}")
            print(f"✅ Invalidated cache for cart:{phone}")
        except Exception as e:
            print(f"⚠️ Cache delete error: {e}")
    
    @staticmethod
    def get_meal_plan(phone: str) -> Optional[dict]:
        """Get cached meal plan."""
        if not redis_client:
            return None
        
        try:
            cached = redis_client.get(f"meals:{phone}")
            if cached:
                return json.loads(cached)
        except Exception as e:
            print(f"⚠️ Cache get error: {e}")
        
        return None
    
    @staticmethod
    def set_meal_plan(phone: str, meals: dict, ttl: int = 7200):
        """Cache meal plan for 2 hours."""
        if not redis_client:
            return
        
        try:
            redis_client.setex(
                f"meals:{phone}",
                ttl,
                json.dumps(meals)
            )
            print(f"✅ Cached meals:{phone} for {ttl} seconds")
        except Exception as e:
            print(f"⚠️ Cache set error: {e}")
    
    @staticmethod
    def get_stats():
        """Get cache statistics."""
        if not redis_client:
            return {"available": False}
        
        try:
            info = redis_client.info()
            return {
                "available": True,
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_keys": redis_client.dbsize()
            }
        except:
            return {"available": False}


# Simple helper functions for easy use
def cache_cart(phone: str, cart_data: dict):
    """Helper to cache cart data."""
    CacheService.set_cart(phone, cart_data)


def get_cached_cart(phone: str) -> Optional[dict]:
    """Helper to get cached cart."""
    return CacheService.get_cart(phone)


def clear_user_cache(phone: str):
    """Clear all caches for a user."""
    if redis_client:
        redis_client.delete(f"cart:{phone}")
        redis_client.delete(f"meals:{phone}")
        print(f"✅ Cleared all caches for {phone}")