"""
Meal Generator Service
======================
Generates personalized meal suggestions using GPT.
Extracted from server.py to isolate meal generation logic.
"""

import os
import json
from typing import Dict, Any, List, Optional
import openai
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o")  # Default to gpt-4o
print(f"🤖 Meal Generator using model: {AI_MODEL}")


def extract_ingredients_from_cart(cart_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Extract and categorize ingredients from cart data.
    
    Args:
        cart_data: Cart data with individual_items, customizable_boxes, etc.
        
    Returns:
        Dict with proteins, vegetables, and other_items lists
    """
    proteins = []
    vegetables = []
    other_items = []
    
    # Individual items
    for item in cart_data.get('individual_items', []):
        name = item.get('name', '').lower()
        if 'egg' in name:
            proteins.append('eggs')
        elif 'avocado' in name:
            other_items.append('avocados')
        elif 'banana' in name:
            other_items.append('bananas')
        else:
            other_items.append(item.get('name', ''))
    
    # Customizable boxes
    for box in cart_data.get('customizable_boxes', []):
        for item in box.get('selected_items', []):
            name = item.get('name', '').lower()
            if any(meat in name for meat in ['chicken', 'beef', 'turkey', 'sausage', 'fish', 'salmon', 'bass', 'pork']):
                proteins.append(item.get('name', ''))
            elif any(veg in name for veg in ['tomato', 'pepper', 'kale', 'lettuce', 'carrot', 'zucchini', 'eggplant', 'onion', 'broccoli', 'spinach']):
                vegetables.append(item.get('name', ''))
            else:
                other_items.append(item.get('name', ''))
    
    # Non-customizable boxes
    for box in cart_data.get('non_customizable_boxes', []):
        for item in box.get('selected_items', []):
            name = item.get('name', '').lower()
            if any(fruit in name for fruit in ['plum', 'peach', 'nectarine', 'apple', 'orange', 'berry']):
                other_items.append(item.get('name', ''))
            else:
                other_items.append(item.get('name', ''))
    
    return {
        'proteins': proteins,
        'vegetables': vegetables,
        'other_items': other_items
    }


def build_meal_prompt(ingredients: Dict[str, List[str]], preferences: Dict[str, Any]) -> str:
    """
    Build GPT prompt for meal generation based on ingredients and preferences.
    
    Args:
        ingredients: Dict with proteins, vegetables, other_items
        preferences: User preferences dict
        
    Returns:
        Formatted prompt string for GPT
    """
    # Extract preferences with defaults
    household_size = preferences.get('household_size', '2 people')
    meal_focus = preferences.get('meal_timing', ['dinner'])
    dietary_restrictions = preferences.get('dietary_restrictions', [])
    health_goals = preferences.get('goals', [])
    cooking_time = 'quick (under 30 min)' if 'quick-dinners' in health_goals else 'standard'
    high_protein = 'high-protein' in health_goals
    
    # Additional preferences
    cooking_methods = preferences.get('cooking_methods', preferences.get('preferred_cooking_methods', []))
    liked_meals = preferences.get('liked_meals', [])
    dislikes = preferences.get('dislikes', [])
    
    # Calculate servings
    servings_per_meal = 2 if '1-2' in str(household_size) else 4 if '3-4' in str(household_size) else 6
    
    # Build the prompt
    prompt = f"""Analyze this cart and create meal suggestions for a household of {household_size}.

CART CONTENTS WITH EXACT QUANTITIES:
PROTEINS ({len(ingredients['proteins'])} items): {', '.join(ingredients['proteins']) if ingredients['proteins'] else 'none'}
VEGETABLES ({len(ingredients['vegetables'])} items): {', '.join(ingredients['vegetables']) if ingredients['vegetables'] else 'none'}  
OTHER ITEMS ({len(ingredients['other_items'])} items): {', '.join(ingredients['other_items']) if ingredients['other_items'] else 'none'}

PROTEIN CALCULATION REFERENCE (per 4oz cooked serving):
- Chicken breast: 35g protein
- Chicken thigh: 28g protein
- Salmon/Steelhead: 30-34g protein
- Ground beef/turkey: 28-30g protein
- Eggs: 6g per egg
- Black Sea Bass: 24g protein
- Tofu: 10g protein

USER PREFERENCES TO CONSIDER:
- Household size: {household_size} (need {servings_per_meal} servings per meal)
- Meal focus: Primarily {', '.join(meal_focus) if isinstance(meal_focus, list) else meal_focus}
- Dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}
- Foods to avoid: {', '.join(dislikes) if dislikes else 'None'}
- Cooking time preference: {cooking_time}
- Protein requirement: {'HIGH (35-40g per serving)' if high_protein else 'Standard (25-30g per serving)'}"""
    
    # Add preference guidance (not rules)
    if cooking_methods:
        prompt += f"\n- They prefer cooking with: {', '.join(cooking_methods)} methods"
    if liked_meals:
        prompt += f"\n- They particularly enjoy: {', '.join(liked_meals[:3])}"
    
    prompt += """

CRITICAL ANALYSIS REQUIRED:
1. Calculate REALISTICALLY how many complete dinners this cart can make
2. Protein portion reality check:
   - 0.6-1lb chicken thighs = ONE meal for 2 people
   - 1lb sausage = ONE meal for 3-4 people
   - Don't overcount - be honest about portions
3. Create meal names that reflect the actual ingredients
4. Be clear: "Makes 1 dinner" vs "Makes 2 dinners"

Return 4 meal suggestions focusing on dinner meals.

When possible, lean toward meals that align with their preferences,
but feel free to suggest variety and new ideas they might enjoy.

Format as JSON:
[{
  "name": "Specific Meal Name Using Actual Ingredients",
  "servings": """ + str(servings_per_meal) + """,
  "time": "X min",
  "protein_per_serving": X,
  "protein_calculation": "Show your math: X lb protein / Y servings = Z grams per serving",
  "makes_x_dinners": "This recipe makes X dinners for your family",
  "ingredients_used": ["list", "actual", "cart", "items"],
  "note": "optional note about what to add from store"
}]"""
    
    return prompt


async def generate_meals(cart_data: Dict[str, Any], preferences: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate meal suggestions from cart data and preferences.
    
    Args:
        cart_data: Cart data dict
        preferences: User preferences dict (optional)
        
    Returns:
        Dict with success status and meals array or error
    """
    try:
        print(f"🍽️ Starting meal generation...")
        
        # Extract ingredients
        ingredients = extract_ingredients_from_cart(cart_data)
        
        total = len(ingredients['proteins']) + len(ingredients['vegetables']) + len(ingredients['other_items'])
        print(f"📊 Found {total} total ingredients")
        print(f"  ✅ Proteins: {ingredients['proteins'][:3]}...")
        print(f"  ✅ Vegetables: {ingredients['vegetables'][:3]}...")
        print(f"  ✅ Other: {ingredients['other_items'][:3]}...")
        
        # Build prompt
        prompt = build_meal_prompt(ingredients, preferences or {})
        
        # Call GPT
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            return {"success": False, "error": "OpenAI API key not configured"}
        
        client = openai.OpenAI(api_key=openai_key)
        print(f"🤖 Calling {AI_MODEL} for meal generation...")
        
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a creative chef who specializes in making delicious meals from specific available ingredients. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        # Parse response
        gpt_response = response.choices[0].message.content.strip()
        
        # Clean up response
        if "```json" in gpt_response:
            gpt_response = gpt_response.split("```json")[1].split("```")[0].strip()
        elif "```" in gpt_response:
            gpt_response = gpt_response.split("```")[1].strip()
        
        # Parse JSON
        meals = json.loads(gpt_response)
        
        print(f"✅ Generated {len(meals)} meal suggestions")
        
        return {
            "success": True,
            "meals": meals
        }
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return {
            "success": False,
            "error": "Failed to parse meal suggestions",
            "raw_response": gpt_response if 'gpt_response' in locals() else None
        }
        
    except Exception as e:
        print(f"❌ Meal generation error: {e}")
        return {
            "success": False,
            "error": str(e)
        }