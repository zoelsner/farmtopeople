#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/zach/Projects/farmtopeople/server')

import supabase_client as db

# The correct phone number
correct_phone = "4254955323"

# Get the latest cart data
print(f"Checking for cart data with phone: {correct_phone}")
cart_record = db.get_latest_cart_data(correct_phone)

if cart_record:
    print(f"✅ Found cart data:")
    print(f"   Last scraped: {cart_record.get('last_scraped', 'unknown')}")
    
    # Show what's in the cart
    cart_data = cart_record.get('cart_data', {})
    if cart_data:
        print(f"\n📦 Cart contents from database:")
        
        # Check for Ground Beef (from today's scrape)
        has_ground_beef = False
        if cart_data.get('customizable_boxes'):
            for box in cart_data['customizable_boxes']:
                for item in box.get('selected_items', []):
                    if 'Ground Beef' in item.get('name', ''):
                        has_ground_beef = True
                        print(f"   ✅ Found Ground Beef (TODAY'S CART)")
                        break
        
        # Check for Seasonal Small Produce (from old cart)
        has_old_box = False
        if cart_data.get('non_customizable_boxes'):
            for box in cart_data['non_customizable_boxes']:
                if 'Seasonal Small Produce' in box.get('box_name', ''):
                    has_old_box = True
                    print(f"   ❌ Found Seasonal Small Produce Box (OLD CART)")
        
        if has_ground_beef:
            print("\n✅ Database has TODAY'S fresh cart data!")
        elif has_old_box:
            print("\n❌ Database still has OLD cart data from last week")
        
        # Show first few items
        print("\nFirst few items in cart:")
        all_items = []
        
        # Individual items
        for item in cart_data.get('individual_items', [])[:2]:
            print(f"   - {item.get('name')}: {item.get('quantity')} {item.get('unit')}")
            
        # Customizable box items
        for box in cart_data.get('customizable_boxes', []):
            for item in box.get('selected_items', [])[:3]:
                print(f"   - {item.get('name')}: {item.get('quantity')} {item.get('unit')}")
                
else:
    print(f"❌ No cart data found for {correct_phone}")