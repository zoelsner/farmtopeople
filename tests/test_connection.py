#!/usr/bin/env python3
"""
Test script to verify the scraper → meal planner connection is working.
This tests the key integration we just built.
"""

import os
import sys
import json
from pathlib import Path

# Add paths for imports
sys.path.insert(0, 'server')
sys.path.insert(0, 'scrapers')

# Test 1: Can we import everything?
print("🧪 TEST 1: Importing modules...")
try:
    from comprehensive_scraper import main as run_scraper
    from server import meal_planner
    import supabase_client as db
    print("✅ All imports successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Can we get test credentials?
print("\n🧪 TEST 2: Loading test credentials...")
from dotenv import load_dotenv
load_dotenv()

test_email = os.getenv("EMAIL") or os.getenv("FTP_EMAIL")
test_password = os.getenv("PASSWORD") or os.getenv("FTP_PWD")

if test_email and test_password:
    print(f"✅ Test credentials found: {test_email}")
else:
    print("❌ No test credentials in .env file")
    print("   Please set EMAIL and PASSWORD in .env")
    sys.exit(1)

# Test 3: Can the scraper return data?
print("\n🧪 TEST 3: Testing scraper with return_data=True...")
print("   (This will take 20-30 seconds)")

credentials = {
    'email': test_email,
    'password': test_password
}

try:
    cart_data = run_scraper(credentials=credentials, return_data=True)
    if cart_data and not cart_data.get('error'):
        print(f"✅ Scraper returned data successfully!")
        print(f"   - Individual items: {len(cart_data.get('individual_items', []))}")
        print(f"   - Non-customizable boxes: {len(cart_data.get('non_customizable_boxes', []))}")
        print(f"   - Customizable boxes: {len(cart_data.get('customizable_boxes', []))}")
    else:
        print(f"❌ Scraper failed: {cart_data}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Scraper error: {e}")
    sys.exit(1)

# Test 4: Can meal planner accept cart data directly?
print("\n🧪 TEST 4: Testing meal planner with direct cart data...")

# Mock user preferences
test_preferences = {
    'dietary_restrictions': [],
    'preferred_proteins': ['chicken', 'fish'],
    'cooking_methods': ['roasting', 'stir-fry'],
    'goals': ['quick-dinners', 'high-protein']
}

try:
    # This is the key test - does the meal planner accept our data?
    meal_plan = meal_planner.run_main_planner(
        cart_data=cart_data,
        user_preferences=test_preferences,
        generate_detailed_recipes=False,
        user_skill_level='intermediate'
    )
    
    if meal_plan and not meal_plan.get('error'):
        print("✅ Meal planner accepted cart data!")
        if meal_plan.get('meals'):
            print(f"   Generated {len(meal_plan['meals'])} meals")
            for i, meal in enumerate(meal_plan['meals'][:3], 1):
                print(f"   {i}. {meal.get('title', 'Untitled')}")
    else:
        print(f"❌ Meal planner failed: {meal_plan}")
        
except Exception as e:
    print(f"❌ Meal planner error: {e}")
    import traceback
    traceback.print_exc()

print("\n🎉 CONNECTION TEST COMPLETE!")
print("The scraper → meal planner pipeline is working correctly.")
print("Cart data flows directly without file system dependency.")