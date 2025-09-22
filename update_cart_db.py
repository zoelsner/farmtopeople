#!/usr/bin/env python3
"""
Update database with latest cart data from JSON file
"""

import json
import sys
import os
from datetime import datetime
sys.path.insert(0, '/Users/zach/Projects/farmtopeople/server')

import supabase_client as db

# Load the latest cart data
json_file = '/Users/zach/Projects/farmtopeople/farm_box_data/customize_results_20250904_062319.json'
with open(json_file, 'r') as f:
    cart_data = json.load(f)

# Your phone number (update if needed)
phone = "4254955323"

# Check if user exists
user = db.get_user_by_phone(phone)
if not user:
    print(f"❌ No user found for phone: {phone}")
    sys.exit(1)

print(f"✅ Found user: {user.get('name', 'Unknown')}")

# Update the cart data using the save function
try:
    # Store the cart data with delivery date
    delivery_date = cart_data.get('delivery_date', 'Sun, Sep 7, 10:00AM - 4:00PM')
    result = db.save_latest_cart_data(
        phone_number=phone,
        cart_data=cart_data,
        delivery_date=delivery_date
    )
    
    print(f"✅ Successfully updated cart data for {phone}")
    print(f"   - Individual items: {len(cart_data.get('individual_items', []))}")
    print(f"   - Customizable boxes: {len(cart_data.get('customizable_boxes', []))}")
    print(f"   - Non-customizable boxes: {len(cart_data.get('non_customizable_boxes', []))}")
    
except Exception as e:
    print(f"❌ Error updating cart: {e}")