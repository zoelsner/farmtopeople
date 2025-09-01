"""
Cart Service - Handles cart analysis and scraping
==================================================
Extracted from server.py to centralize cart operations.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from typing import Dict, Any, Optional
from services.phone_service import normalize_phone
import supabase_client as db
from scrapers.comprehensive_scraper import main as run_cart_scraper
import base64


async def analyze_user_cart(phone: str, use_mock: bool = False) -> Dict[str, Any]:
    """
    Analyze a user's cart - either from live scraping or stored data.
    
    Args:
        phone: User's phone number (will be normalized)
        use_mock: Whether to use mock data (for testing)
    
    Returns:
        Dict with cart_data, swaps, addons, or error info
    """
    # Normalize phone for consistent lookups
    normalized_phone = normalize_phone(phone)
    
    if not normalized_phone:
        return {
            "success": False,
            "error": "Invalid phone number format",
            "debug_info": f"Could not normalize: {phone}"
        }
    
    print(f"📞 Analyzing cart for: {normalized_phone}")
    
    # Try to get stored cart data first (as fallback)
    stored_cart = db.get_latest_cart_data(normalized_phone)
    if stored_cart and stored_cart.get('cart_data'):
        print(f"📦 Found stored cart data for {normalized_phone}")
    
    cart_data = None
    
    # Try to get fresh cart data by scraping
    user_record = db.get_user_by_phone(normalized_phone)
    
    if user_record and user_record.get('ftp_email'):
        email = user_record['ftp_email']
        
        # Decrypt password
        encoded_pwd = user_record.get('ftp_password_encrypted', '')
        password = base64.b64decode(encoded_pwd).decode('utf-8') if encoded_pwd else None
        
        if email and password:
            print(f"🛒 Running live scraper for {email}")
            credentials = {'email': email, 'password': password}
            
            # Run the scraper
            cart_data = await run_cart_scraper(
                credentials, 
                return_data=True, 
                phone_number=normalized_phone
            )
            
            if cart_data:
                print("✅ Successfully scraped live cart data!")
                
                # Check if cart appears empty/locked
                has_customizable = (
                    cart_data.get('customizable_boxes') and 
                    len(cart_data['customizable_boxes']) > 0
                )
                
                if not has_customizable and stored_cart:
                    # Cart might be locked, use stored if it has more data
                    stored_has_customizable = (
                        stored_cart['cart_data'].get('customizable_boxes') and
                        len(stored_cart['cart_data']['customizable_boxes']) > 0
                    )
                    
                    if stored_has_customizable:
                        print("✅ Using stored cart data (current cart appears locked)")
                        cart_data = stored_cart['cart_data']
            elif stored_cart and stored_cart.get('cart_data'):
                # Scraper failed, use stored data
                print("✅ Using stored cart data as fallback")
                cart_data = stored_cart['cart_data']
    
    if not cart_data:
        return {
            "success": False,
            "error": "No cart data available. Please check your Farm to People account.",
            "debug_info": "Unable to scrape or find stored data"
        }
    
    # Generate swaps and addons (simplified for now)
    swaps = []
    addons = []
    
    # Get user preferences for personalized suggestions
    user_preferences = {}
    if user_record:
        user_preferences = user_record.get('preferences', {})
    
    return {
        "success": True,
        "cart_data": cart_data,
        "swaps": swaps,
        "addons": addons,
        "preferences": user_preferences
    }