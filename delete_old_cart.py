#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/zach/Projects/farmtopeople/server')

import supabase_client as db

client = db.get_client()

# Delete the old cart record
print("Deleting old cart record from August 30...")
result = client.table("latest_cart_data").delete().eq("phone_number", "+14254955323").execute()
print(f"✅ Deleted old record")

# Verify only new record remains
check = client.table("latest_cart_data").select("*").eq("phone_number", "4254955323").execute()
if check.data:
    record = check.data[0]
    print(f"\n✅ Fresh cart data remains:")
    print(f"   Phone: {record.get('phone_number')}")
    print(f"   Scraped: {record.get('scraped_at')}")
    
    cart = record.get('cart_data', {})
    if cart.get('customizable_boxes'):
        print(f"   First items:")
        for item in cart['customizable_boxes'][0]['selected_items'][:3]:
            print(f"     - {item.get('name')}")
