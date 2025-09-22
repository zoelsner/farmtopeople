#!/usr/bin/env python3
"""Test script to check what cart data is stored in Supabase."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from server import supabase_client as db
import json

phone = "4254955323"
print(f"Checking stored cart data for {phone}...")

# Get stored cart data
stored = db.get_latest_cart_data(phone)

if stored:
    print(f"\n✅ Found stored cart data")
    print(f"Scraped at: {stored.get('scraped_at')}")
    print(f"Delivery date: {stored.get('delivery_date')}")
    
    cart_data = stored.get('cart_data', {})
    
    # Check individual items
    individual_items = cart_data.get('individual_items', [])
    print(f"\nIndividual items: {len(individual_items)}")
    for item in individual_items[:5]:  # Show first 5
        print(f"  - {item.get('name')} ({item.get('quantity')} {item.get('unit')})")
    if len(individual_items) > 5:
        print(f"  ... and {len(individual_items) - 5} more")
    
    # Check customizable boxes
    customizable_boxes = cart_data.get('customizable_boxes', [])
    print(f"\nCustomizable boxes: {len(customizable_boxes)}")
    for box in customizable_boxes:
        selected_items = box.get('selected_items', [])
        print(f"  - {box.get('box_name')}: {len(selected_items)} items")
        for item in selected_items[:3]:  # Show first 3 items
            print(f"    • {item.get('name')}")
        if len(selected_items) > 3:
            print(f"    ... and {len(selected_items) - 3} more")
    
    # Check non-customizable boxes
    non_customizable = cart_data.get('non_customizable_boxes', [])
    print(f"\nNon-customizable boxes: {len(non_customizable)}")
    for box in non_customizable:
        print(f"  - {box.get('box_name')}")
    
    # Save to file for inspection
    with open('supabase_cart_data.json', 'w') as f:
        json.dump(cart_data, f, indent=2)
    print("\n💾 Full cart data saved to supabase_cart_data.json")
    
else:
    print("❌ No stored cart data found")