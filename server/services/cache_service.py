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
    def set_meals(phone_number: str, meals: list, ttl: int = 7200) -> bool:
        """Cache meal suggestions to Redis (convenience method)"""
        try:
            CacheService.set_meal_plan(phone_number, meals, ttl)
            print(f"✅ Cached {len(meals)} meals to Redis for {phone_number}")
            return True
        except Exception as e:
            print(f"❌ Failed to cache meals: {e}")
            return False

    @staticmethod
    def get_meals(phone_number: str) -> list:
        """Get cached meal suggestions from Redis (convenience method)"""
        try:
            cached_meals = CacheService.get_meal_plan(phone_number)
            if cached_meals:
                # Handle both dict and list formats
                if isinstance(cached_meals, list):
                    meals = cached_meals
                else:
                    meals = cached_meals.get('meals', cached_meals)
                print(f"⚡ Retrieved {len(meals)} cached meals from Redis")
                return meals
        except Exception as e:
            print(f"❌ Failed to get cached meals: {e}")
        return None

    @staticmethod
    def set_browser_session(phone: str, email: str, cookies: list, ttl: int = 3600):
        """Cache browser session cookies for login persistence."""
        if not redis_client:
            return

        try:
            import hashlib
            email_hash = hashlib.md5(email.lower().encode()).hexdigest()[:8]
            session_key = f"browser_session:{phone}:{email_hash}"

            session_data = {
                "cookies": cookies,
                "email": email,
                "created_at": datetime.now().isoformat()
            }

            redis_client.setex(
                session_key,
                ttl,
                json.dumps(session_data)
            )
            print(f"✅ Cached browser session for {phone} ({ttl//60} min TTL)")
        except Exception as e:
            print(f"⚠️ Session cache set error: {e}")

    @staticmethod
    def get_browser_session(phone: str, email: str) -> Optional[dict]:
        """Get cached browser session."""
        if not redis_client:
            return None

        try:
            import hashlib
            email_hash = hashlib.md5(email.lower().encode()).hexdigest()[:8]
            session_key = f"browser_session:{phone}:{email_hash}"

            cached = redis_client.get(session_key)
            if cached:
                session_data = json.loads(cached)
                # Validate email matches (security check)
                if session_data.get('email') == email:
                    print(f"✅ Retrieved cached browser session for {phone}")
                    return session_data
                else:
                    print(f"🚨 Session email mismatch for {phone} - invalidating")
                    redis_client.delete(session_key)
        except Exception as e:
            print(f"⚠️ Session cache get error: {e}")

        return None

    @staticmethod
    def invalidate_browser_session(phone: str, email: str):
        """Invalidate cached browser session."""
        if not redis_client:
            return

        try:
            import hashlib
            email_hash = hashlib.md5(email.lower().encode()).hexdigest()[:8]
            session_key = f"browser_session:{phone}:{email_hash}"
            redis_client.delete(session_key)
            print(f"🗑️ Invalidated browser session for {phone}")
        except Exception as e:
            print(f"⚠️ Session invalidation error: {e}")

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

    # ===== MEAL LOCKING METHODS =====

    @staticmethod
    def get_meal_locks_data(phone: str) -> Optional[dict]:
        """
        Get complete meal locks data structure for a user.

        Args:
            phone: User's phone number

        Returns:
            Complete meal locks data or None if not cached
        """
        if not redis_client:
            return None

        try:
            cached = redis_client.get(f"user_meals:{phone}")
            if cached:
                print(f"✅ Retrieved meal locks data for {phone}")
                return json.loads(cached)
        except Exception as e:
            print(f"⚠️ Meal locks get error: {e}")

        return None

    @staticmethod
    def set_meal_locks_data(phone: str, meal_data: dict, ttl: int = 86400):
        """
        Set complete meal locks data structure for a user.

        Args:
            phone: User's phone number
            meal_data: Complete meal locks data structure
            ttl: Time to live in seconds (default 24 hours)
        """
        if not redis_client:
            return

        try:
            # Add timestamp if not present
            if 'generation_timestamp' not in meal_data:
                meal_data['generation_timestamp'] = datetime.now().isoformat()

            redis_client.setex(
                f"user_meals:{phone}",
                ttl,
                json.dumps(meal_data)
            )
            print(f"✅ Cached meal locks data for {phone} (24h TTL)")
        except Exception as e:
            print(f"⚠️ Meal locks set error: {e}")

    @staticmethod
    def get_meal_locks(phone: str) -> list:
        """
        Get meal lock status array for a user.

        Args:
            phone: User's phone number

        Returns:
            Lock status array [false, true, false, false] or empty list if not found
        """
        meal_data = CacheService.get_meal_locks_data(phone)
        if meal_data and 'locked_status' in meal_data:
            return meal_data['locked_status']
        return []

    @staticmethod
    def set_meal_lock(phone: str, index: int, locked: bool) -> bool:
        """
        Set lock status for a specific meal index.

        Args:
            phone: User's phone number
            index: Meal index (0-based)
            locked: Lock status (True/False)

        Returns:
            True if successful, False otherwise
        """
        if not redis_client:
            return False

        try:
            # Get current meal data
            meal_data = CacheService.get_meal_locks_data(phone)
            if not meal_data:
                print(f"⚠️ No meal data found for {phone} - cannot set lock")
                return False

            # Ensure locked_status array exists and is properly sized
            if 'locked_status' not in meal_data:
                meal_data['locked_status'] = []

            # Extend array if needed
            while len(meal_data['locked_status']) <= index:
                meal_data['locked_status'].append(False)

            # Update lock status
            meal_data['locked_status'][index] = locked

            # Update locked ingredients if locking
            if locked and 'generated_meals' in meal_data and index < len(meal_data['generated_meals']):
                meal = meal_data['generated_meals'][index]
                if 'locked_ingredients' not in meal_data:
                    meal_data['locked_ingredients'] = {"proteins": [], "vegetables": [], "other": []}

                # Add ingredients from this meal to locked ingredients
                ingredients_used = meal.get('ingredients_used', [])
                for ingredient in ingredients_used:
                    if any(protein in ingredient.lower() for protein in ['chicken', 'turkey', 'salmon', 'beef', 'pork']):
                        if ingredient not in meal_data['locked_ingredients']['proteins']:
                            meal_data['locked_ingredients']['proteins'].append(ingredient)
                    elif any(veg in ingredient.lower() for veg in ['zucchini', 'carrot', 'tomato', 'onion', 'pepper']):
                        if ingredient not in meal_data['locked_ingredients']['vegetables']:
                            meal_data['locked_ingredients']['vegetables'].append(ingredient)
                    else:
                        if ingredient not in meal_data['locked_ingredients']['other']:
                            meal_data['locked_ingredients']['other'].append(ingredient)

            # Remove ingredients if unlocking
            elif not locked and 'generated_meals' in meal_data and index < len(meal_data['generated_meals']):
                meal = meal_data['generated_meals'][index]
                if 'locked_ingredients' in meal_data:
                    ingredients_used = meal.get('ingredients_used', [])
                    for ingredient in ingredients_used:
                        # Remove from all categories
                        for category in meal_data['locked_ingredients'].values():
                            if ingredient in category:
                                category.remove(ingredient)

            # Save updated data
            CacheService.set_meal_locks_data(phone, meal_data)

            action = "locked" if locked else "unlocked"
            print(f"✅ Meal {index} {action} for {phone}")
            return True

        except Exception as e:
            print(f"⚠️ Set meal lock error: {e}")
            return False

    @staticmethod
    def clear_meal_locks(phone: str) -> bool:
        """
        Clear all meal locks for a user.

        Args:
            phone: User's phone number

        Returns:
            True if successful, False otherwise
        """
        if not redis_client:
            return False

        try:
            meal_data = CacheService.get_meal_locks_data(phone)
            if not meal_data:
                return True  # Nothing to clear

            # Reset all locks
            if 'locked_status' in meal_data:
                meal_data['locked_status'] = [False] * len(meal_data['locked_status'])

            # Clear locked ingredients
            meal_data['locked_ingredients'] = {"proteins": [], "vegetables": [], "other": []}

            # Save updated data
            CacheService.set_meal_locks_data(phone, meal_data)

            print(f"✅ Cleared all meal locks for {phone}")
            return True

        except Exception as e:
            print(f"⚠️ Clear meal locks error: {e}")
            return False

    @staticmethod
    def get_locked_ingredients(phone: str) -> dict:
        """
        Get ingredients used by locked meals.

        Args:
            phone: User's phone number

        Returns:
            Dict with proteins, vegetables, other lists
        """
        meal_data = CacheService.get_meal_locks_data(phone)
        if meal_data and 'locked_ingredients' in meal_data:
            return meal_data['locked_ingredients']
        return {"proteins": [], "vegetables": [], "other": []}

    @staticmethod
    def initialize_meal_locks(phone: str, generated_meals: list, cart_data: dict,
                            meal_count: int = 0, snack_count: int = 0) -> bool:
        """
        Initialize meal locks data structure when meals are first generated.

        Args:
            phone: User's phone number
            generated_meals: List of generated meals
            cart_data: Original cart data
            meal_count: Number of meals
            snack_count: Number of snacks

        Returns:
            True if successful, False otherwise
        """
        if not redis_client:
            return False

        try:
            meal_data = {
                "generated_meals": generated_meals,
                "locked_status": [False] * len(generated_meals),
                "locked_ingredients": {"proteins": [], "vegetables": [], "other": []},
                "cart_data": cart_data,
                "generation_timestamp": datetime.now().isoformat(),
                "generation_source": "cart",
                "previous_meals": [],
                "meal_count": meal_count,
                "snack_count": snack_count
            }

            CacheService.set_meal_locks_data(phone, meal_data)
            print(f"✅ Initialized meal locks for {phone} with {len(generated_meals)} meals")
            return True

        except Exception as e:
            print(f"⚠️ Initialize meal locks error: {e}")
            return False

    @staticmethod
    def invalidate_meal_locks(phone: str):
        """
        Invalidate meal locks data for a user.

        Args:
            phone: User's phone number
        """
        if not redis_client:
            return

        try:
            redis_client.delete(f"user_meals:{phone}")
            print(f"✅ Invalidated meal locks for {phone}")
        except Exception as e:
            print(f"⚠️ Meal locks invalidation error: {e}")


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