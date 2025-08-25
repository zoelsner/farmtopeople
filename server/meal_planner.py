"""
Meal planner orchestration for Farm to People.

This module coordinates between cart analysis, product catalog,
and meal generation. It serves as the main entry point for the
server and maintains backward compatibility.

Architecture:
- Imports from specialized modules (file_utils, product_catalog, cart_analyzer)
- Maintains legacy meal generation for backward compatibility
- Provides main orchestration functions called by server.py
"""

import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import openai
from typing import Dict, List, Any, Optional

# Import our refactored modules
from file_utils import (
    get_latest_cart_file,
    get_latest_comprehensive_file,
    get_latest_box_file,
    get_comprehensive_ingredients_and_data,
    load_cart_data
)
from product_catalog import (
    get_product_catalog,
    get_curated_items_list,
    fuzzy_match_product,
    add_pricing_to_analysis
)
from cart_analyzer import (
    generate_cart_analysis_summary as _generate_cart_analysis,
    create_sms_summary
)

# --- Configuration ---
FARM_BOX_DATA_DIR = os.getenv("FARM_BOX_DATA_DIR", "../farm_box_data")

# Load environment variables
project_root = Path(__file__).parent.parent
try:
    load_dotenv(dotenv_path=project_root / '.env')
except:
    pass  # Railway uses direct environment variables

# OpenAI Setup
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"✅ OPENAI_API_KEY found (length: {len(api_key)})")
    client = openai.OpenAI(api_key=api_key)
else:
    print("⚠️ WARNING: OPENAI_API_KEY not found")
    client = None


def generate_cart_analysis_summary(user_id: str = None) -> str:
    """
    Wrapper function for backward compatibility with server.py.
    
    This function is called by server.py, so we maintain it here
    but delegate to the cart_analyzer module.
    
    Args:
        user_id: Optional user ID for production data retrieval
    
    Returns:
        SMS-optimized summary with web link to full analysis
    """
    return _generate_cart_analysis(user_id=user_id)


def get_master_product_list(catalog_file: str = None) -> List[str]:
    """
    Legacy function for backward compatibility.
    Returns list of product names from catalog.
    
    Args:
        catalog_file: Path to catalog file (ignored, uses env var)
    
    Returns:
        List of product names
    """
    catalog = get_product_catalog()
    if catalog:
        return list(catalog.keys())
    
    # Fallback to curated list
    return get_curated_items_list()


def get_all_ingredients_from_cart(cart_data: dict, data_dir: str) -> List[str]:
    """
    Legacy function maintained for backward compatibility.
    Extracts all ingredients from cart data.
    
    Args:
        cart_data: Cart data dictionary
        data_dir: Directory containing box files
    
    Returns:
        List of ingredient names
    """
    ingredients = []
    
    # Get items from main cart
    for item in cart_data.get("cart_items", []):
        if item.get("selected", False):
            name = item.get("name", "")
            if name:
                ingredients.append(name)
    
    # Try to get box contents
    for box_name in ["cook", "organic_produce", "produce", "fruit"]:
        box_file = get_latest_box_file(data_dir, box_name)
        if box_file and os.path.exists(box_file):
            try:
                with open(box_file, 'r') as f:
                    box_data = json.load(f)
                    for item in box_data.get("selected_items", []):
                        if item.get("selected", False):
                            name = item.get("name", "")
                            if name:
                                ingredients.append(name)
            except:
                continue
    
    # Deduplicate
    return list(dict.fromkeys(ingredients))


def generate_meal_plan(
    ingredients: List[str], 
    master_product_list: List[str], 
    diet_hard: List[str] = None, 
    dislikes: List[str] = None, 
    time_mode: str = "standard", 
    allow_surf_turf: bool = False
) -> dict:
    """
    Legacy meal plan generation using GPT-4.
    Maintained for backward compatibility with run_main_planner().
    
    For new cart analysis, use generate_cart_analysis_summary() instead.
    """
    if not client:
        return {"error": "OpenAI API key not configured"}
    
    # Set defaults
    diet_hard = diet_hard or []
    dislikes = dislikes or []
    
    # Build enhanced prompt with preferences
    prompt = f"""Create a personalized meal plan using these ingredients:
{', '.join(ingredients)}

Available products from Farm to People:
{', '.join(master_product_list[:50])}  # Limit to avoid token overload

USER PREFERENCES (MUST FOLLOW):
Dietary restrictions: {', '.join(diet_hard) if diet_hard else 'None'}
Dislikes: {', '.join(dislikes) if dislikes else 'None'}
Time preference: {time_mode}

REQUIREMENTS:
1. Use the available ingredients efficiently
2. Respect ALL dietary restrictions and preferences
3. If "high-protein" is specified, ensure 30g+ protein per meal
4. If "quick meals" is specified, keep total time under 30 minutes
5. Create balanced, nutritious meals
6. Give each meal a descriptive, appetizing title

Format as JSON with:
- meals: array of meal objects with name, ingredients, servings
- additional_items: items to add from catalog
- pantry_staples: basic pantry needs
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-5",  # Using GPT-5 as requested
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Error generating meal plan: {e}")
        return {"error": str(e)}


def validate_meal_plan(
    meal_plan: Dict[str, Any], 
    available_ingredients: List[str], 
    master_product_list: List[str]
) -> List[str]:
    """
    Validates that meal plan only uses available ingredients.
    Legacy function for backward compatibility.
    """
    invalid_items = []
    all_available = set(available_ingredients + master_product_list)
    
    # Check meals
    for meal in meal_plan.get("meals", []):
        for ingredient in meal.get("ingredients", []):
            if ingredient not in all_available:
                invalid_items.append(ingredient)
    
    # Check additional items
    for item in meal_plan.get("additional_items", []):
        item_name = item if isinstance(item, str) else item.get("name", "")
        if item_name and item_name not in master_product_list:
            invalid_items.append(item_name)
    
    return list(set(invalid_items))


def run_repair_prompt(
    faulty_plan: Dict[str, Any], 
    invalid_items: List[str], 
    available_ingredients: List[str], 
    master_product_list: List[str]
) -> Dict[str, Any]:
    """
    Attempts to repair a meal plan with invalid items.
    Legacy function for backward compatibility.
    """
    if not client:
        return faulty_plan
    
    repair_prompt = f"""Fix this meal plan by replacing invalid items:
Invalid items: {', '.join(invalid_items)}
Available ingredients: {', '.join(available_ingredients)}
Available products: {', '.join(master_product_list[:50])}

Current plan: {json.dumps(faulty_plan, indent=2)}

Return corrected JSON with same structure."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-5",  # Using GPT-5
            messages=[{"role": "user", "content": repair_prompt}],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        print(f"Error repairing meal plan: {e}")
        return faulty_plan


def run_main_planner(cart_data: dict = None, user_preferences: dict = None, generate_detailed_recipes: bool = False, user_skill_level: str = "intermediate"):
    """
    Main orchestration function called by server.py.
    Generates a complete meal plan with optional recipe enhancement.
    
    This is the legacy meal planner - for new cart analysis,
    use generate_cart_analysis_summary() instead.
    
    Args:
        generate_detailed_recipes: If True, enhance with professional recipes
        user_skill_level: Cooking skill level for recipes
    
    Returns:
        Meal plan dictionary
    """
    # Get product list
    master_product_list = get_master_product_list()
    
    # Use passed cart_data if available, otherwise read from file
    if cart_data:
        print("✅ Using passed cart data directly")
        all_ingredients, analysis_data = get_comprehensive_ingredients_and_data(cart_data)
        
        # Set alternatives context for the AI
        alternatives = []
        for box in analysis_data.get("customizable_boxes", []):
            alternatives.extend(box.get("available_alternatives", []))
        
        generate_meal_plan._alternatives_context = [alt.get("name", "") for alt in alternatives]
        
    else:
        # Fallback to reading from file
        print("⚠️ No cart data passed, reading from file")
        latest_file = get_latest_comprehensive_file(FARM_BOX_DATA_DIR)
    
        if latest_file:
            comprehensive_data = load_cart_data(latest_file)
            all_ingredients, analysis_data = get_comprehensive_ingredients_and_data(comprehensive_data)
            
            # Set alternatives context for the AI
            alternatives = []
            for box in analysis_data.get("customizable_boxes", []):
                alternatives.extend(box.get("available_alternatives", []))
            
            # Store alternatives for prompt context (hacky but maintains compatibility)
            generate_meal_plan._alternatives_context = [alt.get("name", "") for alt in alternatives]
            
        else:
            # Fallback to legacy cart format
            latest_cart_file = get_latest_cart_file(FARM_BOX_DATA_DIR)
            if not latest_cart_file:
                return {"error": "Could not find cart data."}
                
            with open(latest_cart_file, 'r') as f:
                cart_data = json.load(f)
            
            all_ingredients = get_all_ingredients_from_cart(cart_data, FARM_BOX_DATA_DIR)
            generate_meal_plan._alternatives_context = []
    
    # Extract preferences for meal planning
    if user_preferences:
        diet_hard = user_preferences.get('dietary_restrictions', [])
        dislikes = user_preferences.get('dislikes', [])
        # Add protein requirements based on goals
        if 'high-protein' in user_preferences.get('goals', []):
            diet_hard.append('high-protein (30g+ per meal)')
        if 'quick-dinners' in user_preferences.get('goals', []):
            diet_hard.append('quick meals (under 30 minutes)')
    else:
        diet_hard = []
        dislikes = []
    
    # Generate meal plan with preferences
    meal_plan = generate_meal_plan(
        all_ingredients, 
        master_product_list,
        diet_hard=diet_hard,
        dislikes=dislikes,
        time_mode="standard"
    )
    
    # Validate and repair if needed
    invalid_items = validate_meal_plan(meal_plan, all_ingredients, master_product_list)
    if invalid_items:
        repaired_plan = run_repair_prompt(meal_plan, invalid_items, all_ingredients, master_product_list)
        final_invalid = validate_meal_plan(repaired_plan, all_ingredients, master_product_list)
        if not final_invalid:
            meal_plan = repaired_plan
    
    # Optionally enhance with detailed recipes
    if generate_detailed_recipes:
        try:
            from recipe_generator import enhance_meal_plan_with_recipes
            meal_plan = enhance_meal_plan_with_recipes(meal_plan, user_skill_level)
            print("✅ Enhanced meal plan with professional recipe details")
        except Exception as e:
            print(f"⚠️ Could not enhance recipes: {e}")
    
    return meal_plan


def main():
    """
    Command-line interface for testing meal planner.
    """
    print("===== AI Meal Planner =====")
    
    # Test cart analysis (new approach)
    print("\n🧪 Testing cart analysis...")
    analysis = generate_cart_analysis_summary()
    print(f"Analysis length: {len(analysis)} characters")
    print("\nSMS Summary:")
    print(analysis)
    
    # Also test legacy meal planner
    print("\n🧪 Testing legacy meal planner...")
    meal_plan = run_main_planner()
    
    if meal_plan.get("error"):
        print(f"Error: {meal_plan['error']}")
    else:
        print(f"Generated {len(meal_plan.get('meals', []))} meals")
        for meal in meal_plan.get("meals", [])[:3]:
            print(f"  - {meal.get('name', 'Unnamed meal')}")


if __name__ == "__main__":
    main()