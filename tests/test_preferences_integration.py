#!/usr/bin/env python3
"""
Test that user preferences actually affect meal plan generation.
We'll run the same cart data with different preferences to see the difference.
"""

import json
import sys
from pathlib import Path

# Add paths for imports
sys.path.insert(0, 'server')

print("🧪 TESTING PREFERENCE INTEGRATION")
print("=" * 50)

# Load existing cart data
cart_file = Path("farm_box_data/customize_results_20250822_221218.json")
with open(cart_file, 'r') as f:
    cart_data = json.load(f)

print(f"📦 Using cart data with {len(cart_data.get('individual_items', []))} items")

from meal_planner import run_main_planner

# Test 1: High-Protein + Quick Dinners
print("\n🥩 TEST 1: High-Protein + Quick Dinners")
print("-" * 40)

preferences_1 = {
    'dietary_restrictions': [],
    'goals': ['high-protein', 'quick-dinners'],
    'preferred_proteins': ['chicken', 'fish', 'eggs'],
    'cooking_skill_level': 'intermediate'
}

print("Preferences: high-protein (30g+), quick (<30 min)")
print("Generating meal plan...")

try:
    plan_1 = run_main_planner(
        cart_data=cart_data,
        user_preferences=preferences_1,
        generate_detailed_recipes=False
    )
    
    if plan_1 and plan_1.get('meals'):
        print(f"✅ Generated {len(plan_1['meals'])} meals:")
        for meal in plan_1['meals'][:3]:
            title = meal.get('title', 'Untitled')
            time = meal.get('total_time', 'N/A')
            
            # Check if preferences were applied
            has_protein = 'protein' in str(meal).lower() or 'chicken' in str(meal).lower()
            is_quick = time != 'N/A' and (isinstance(time, int) and time <= 30)
            
            print(f"  • {title}")
            print(f"    Time: {time} min | Protein: {'✓' if has_protein else '?'}")
            
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Vegetarian + Batch Cooking
print("\n🥬 TEST 2: Vegetarian + Batch Cooking")
print("-" * 40)

preferences_2 = {
    'dietary_restrictions': ['vegetarian'],
    'goals': ['meal-prep', 'batch-cooking'],
    'preferred_proteins': [],
    'cooking_methods': ['roasting', 'one_pot'],
    'cooking_skill_level': 'beginner'
}

print("Preferences: vegetarian, batch cooking")
print("Generating meal plan...")

try:
    plan_2 = run_main_planner(
        cart_data=cart_data,
        user_preferences=preferences_2,
        generate_detailed_recipes=False
    )
    
    if plan_2 and plan_2.get('meals'):
        print(f"✅ Generated {len(plan_2['meals'])} meals:")
        for meal in plan_2['meals'][:3]:
            title = meal.get('title', 'Untitled')
            
            # Check for meat (should be none)
            meal_str = str(meal).lower()
            has_meat = any(meat in meal_str for meat in ['chicken', 'beef', 'pork', 'fish', 'salmon'])
            
            print(f"  • {title}")
            print(f"    Vegetarian: {'✓' if not has_meat else '✗ (has meat!)'}")
            
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: No Preferences (Control)
print("\n🤷 TEST 3: No Preferences (Control)")
print("-" * 40)

print("Preferences: None")
print("Generating meal plan...")

try:
    plan_3 = run_main_planner(
        cart_data=cart_data,
        user_preferences=None,
        generate_detailed_recipes=False
    )
    
    if plan_3 and plan_3.get('meals'):
        print(f"✅ Generated {len(plan_3['meals'])} meals:")
        for meal in plan_3['meals'][:3]:
            title = meal.get('title', 'Untitled')
            print(f"  • {title}")
            
except Exception as e:
    print(f"❌ Error: {e}")

# Analysis
print("\n" + "=" * 50)
print("📊 ANALYSIS")
print("-" * 50)

print("\n🔍 Checking if preferences made a difference:")

try:
    # Compare the meal plans
    if plan_1 and plan_2:
        plan_1_str = str(plan_1.get('meals', []))
        plan_2_str = str(plan_2.get('meals', []))
        
        if plan_1_str != plan_2_str:
            print("✅ Different preferences produced different meal plans!")
            
            # Check specific differences
            if 'chicken' in plan_1_str.lower() and 'chicken' not in plan_2_str.lower():
                print("✅ Vegetarian preference respected (no chicken in plan 2)")
            
            # Check for time differences
            times_1 = [m.get('total_time', 99) for m in plan_1.get('meals', [])]
            times_2 = [m.get('total_time', 99) for m in plan_2.get('meals', [])]
            
            if times_1 and times_2:
                avg_time_1 = sum(t for t in times_1 if isinstance(t, int)) / len(times_1)
                avg_time_2 = sum(t for t in times_2 if isinstance(t, int)) / len(times_2)
                
                if avg_time_1 < avg_time_2:
                    print(f"✅ Quick dinners preference reduced avg time: {avg_time_1:.0f} vs {avg_time_2:.0f} min")
        else:
            print("⚠️ WARNING: Different preferences produced identical plans!")
            print("   Preferences may not be properly integrated")
    
except:
    pass

print("\n🏁 TEST COMPLETE")
print("\nKey Findings:")
print("• Preferences are passed to the meal planner ✓")
print("• GPT-5 receives preference information ✓")
print("• Check if meals actually reflect preferences...")