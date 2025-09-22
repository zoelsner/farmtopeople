#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/zach/Projects/farmtopeople/server')

import supabase_client as db
from datetime import datetime

# Force refresh cart from database
phone = "4254955323"
cart = db.get_latest_cart_data(phone)

if cart:
    print(f"✅ Found cart data scraped at: {cart.get('last_scraped', 'unknown')}")
    print(f"   Delivery date: {cart.get('delivery_date', 'unknown')}")
    
    # Print summary
    cart_data = cart.get('cart_data', {})
    print(f"\n📦 Cart contents:")
    print(f"   Individual items: {len(cart_data.get('individual_items', []))}")
    print(f"   Customizable boxes: {len(cart_data.get('customizable_boxes', []))}")
    print(f"   Non-customizable boxes: {len(cart_data.get('non_customizable_boxes', []))}")
    
    # Show some items
    if cart_data.get('customizable_boxes'):
        box = cart_data['customizable_boxes'][0]
        print(f"\n   First box items:")
        for item in box.get('selected_items', [])[:5]:
            print(f"     - {item.get('name', 'Unknown')}: {item.get('quantity', 0)} {item.get('unit', '')}")
else:
    print("❌ No cart data found")
