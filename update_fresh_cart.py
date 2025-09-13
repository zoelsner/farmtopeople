#!/usr/bin/env python3
import sys
import json
from datetime import datetime
sys.path.insert(0, '/Users/zach/Projects/farmtopeople/server')

import supabase_client as db

# Load the FRESH cart data
json_file = '/Users/zach/Projects/farmtopeople/farm_box_data/customize_results_20250913_140659.json'
with open(json_file, 'r') as f:
    cart_data = json.load(f)

phone = "4254955323"

# Add delivery date from scraper
cart_data['delivery_date'] = 'Mon, Sep 15, 10:00AM - 3:00PM'
cart_data['scraped_timestamp'] = datetime.now().isoformat()

print(f"📅 Updating cart for delivery: {cart_data['delivery_date']}")
print(f"⏰ Scraped at: {cart_data['scraped_timestamp']}")

# Show what's in the cart
print("\n📦 Cart contents:")
print(f"  Individual items: {len(cart_data.get('individual_items', []))}")
for item in cart_data.get('individual_items', []):
    print(f"    - {item['name']}")

print(f"\n  Boxes:")
for box in cart_data.get('customizable_boxes', []):
    print(f"    - {box['box_name']} ({len(box['selected_items'])} items)")
for box in cart_data.get('non_customizable_boxes', []):
    print(f"    - {box['box_name']} ({len(box['selected_items'])} items)")

# Update database
result = db.save_latest_cart_data(
    phone_number=phone,
    cart_data=cart_data,
    delivery_date=cart_data['delivery_date']
)

if result:
    print(f"\n✅ Successfully updated cart for Sep 15 delivery!")
else:
    print(f"\n❌ Failed to update cart")