"""
Scraper Service
===============
Orchestrates cart scraping and data processing.
Extracted from server.py to isolate scraping logic.
"""

import os
import sys
from typing import Dict, Any, Optional

# Add parent directory to path for scrapers import
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from scrapers.comprehensive_scraper import main as run_cart_scraper
import supabase_client as db


async def scrape_user_cart(
    credentials: Dict[str, str],
    phone: str = None,
    save_to_db: bool = True
) -> Dict[str, Any]:
    """
    Scrape user's Farm to People cart.
    
    Args:
        credentials: Dict with 'email' and 'password'
        phone: User's phone number for saving
        save_to_db: Whether to save results to database
        
    Returns:
        Dict with cart_data or error info
    """
    if not credentials or not credentials.get('email') or not credentials.get('password'):
        return {
            "success": False,
            "error": "Missing credentials",
            "cart_data": None
        }
    
    print(f"🛒 Starting cart scrape for: {credentials['email']}")
    
    try:
        # Run the scraper - keeping exact same call as server.py
        cart_data = await run_cart_scraper(
            credentials,
            return_data=True,
            phone_number=phone
        )
        
        if not cart_data:
            print("⚠️ Scraper returned no data")
            # Try to get stored cart as fallback (same as server.py)
            if phone:
                stored = db.get_latest_cart_data(phone)
                if stored and stored.get('cart_data'):
                    print("✅ Using stored cart data as fallback")
                    return {
                        "success": True,
                        "cart_data": stored['cart_data'],
                        "from_cache": True
                    }
            
            return {
                "success": False,
                "error": "No cart data available",
                "cart_data": None
            }
        
        # Log what we got (same as server.py)
        print(f"✅ Cart scraping completed: {len(cart_data.get('individual_items', [])) if cart_data else 0} items")
        
        # Save to database if requested
        if save_to_db and phone:
            try:
                db.save_latest_cart_data(
                    phone_number=phone,
                    cart_data=cart_data
                )
                print(f"✅ Cart data saved to database")
            except Exception as e:
                print(f"⚠️ Failed to save cart data: {e}")
        
        return {
            "success": True,
            "cart_data": cart_data,
            "from_cache": False
        }
        
    except Exception as e:
        print(f"❌ Cart scraping failed: {e}")
        
        # Try fallback to stored data (same logic as server.py)
        if phone:
            stored = db.get_latest_cart_data(phone)
            if stored and stored.get('cart_data'):
                print("✅ Using stored cart data after scrape failure")
                return {
                    "success": True,
                    "cart_data": stored['cart_data'],
                    "from_cache": True,
                    "scrape_error": str(e)
                }
        
        return {
            "success": False,
            "error": str(e),
            "cart_data": None
        }