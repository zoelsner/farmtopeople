#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/zach/Projects/farmtopeople/server')

import supabase_client as db
from datetime import datetime

# Check ALL cart records for this user
client = db.get_client()

# Try both phone formats
phones = ['+14254955323', '4254955323', '14254955323']

print("Checking all cart records in database:\n")

for phone in phones:
    result = client.table("latest_cart_data").select("*").eq("phone_number", phone).execute()
    
    if result.data:
        for record in result.data:
            scraped_at = record.get('scraped_at', 'unknown')
            cart = record.get('cart_data', {})
            
            # Check what's in the cart
            has_ground_beef = False
            has_old_items = False
            
            if cart.get('customizable_boxes'):
                for box in cart['customizable_boxes']:
                    for item in box.get('selected_items', []):
                        if 'Ground Beef' in item.get('name', ''):
                            has_ground_beef = True
                        if 'Rainbow Carrot' in item.get('name', ''):
                            has_old_items = True
            
            print(f"Phone: {phone}")
            print(f"  Scraped: {scraped_at}")
            print(f"  Has Ground Beef (NEW): {has_ground_beef}")
            print(f"  Has Rainbow Carrots (OLD): {has_old_items}")
            print()

print("\n=== SOLUTION ===")
print("Need to delete old record and ensure new record is found first")
