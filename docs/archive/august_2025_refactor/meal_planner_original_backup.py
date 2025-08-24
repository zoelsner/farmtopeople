"""Meal planner orchestration for Farm to People.

This module coordinates between cart analysis, product catalog,
and meal generation. It serves as the main entry point for the
server and maintains backward compatibility.
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
import openai
from typing import Dict, List, Any, Union, Optional, Tuple

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
PRODUCT_CATALOG_FILE = os.getenv(
    "PRODUCT_CATALOG_FILE",
    "/Users/zach/Projects/farmtopeople/data/farmtopeople_products.csv"
)

# Load environment variables (Railway uses direct env vars, local uses .env file)
from pathlib import Path
project_root = Path(__file__).parent.parent
# Try to load .env file, but don't fail if it doesn't exist (Railway doesn't have .env)
try:
    load_dotenv(dotenv_path=project_root / '.env')
except:
    pass  # Railway uses direct environment variables

# --- OpenAI Setup ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("⚠️ WARNING: OPENAI_API_KEY not found in environment variables.")
    print(f"   Environment check: {len(os.environ)} total env vars found")
    client = None
else:
    print(f"✅ OPENAI_API_KEY found (length: {len(api_key)})")
    client = openai.OpenAI(api_key=api_key)


def get_latest_cart_file(directory: str) -> Union[str, None]:
    """Finds the most recent cart_contents JSON file."""
    try:
        cart_files = glob.glob(os.path.join(directory, "cart_contents_*.json"))
        if not cart_files:
            return None
        return max(cart_files, key=os.path.getmtime)
    except Exception as e:
        return None

def get_latest_comprehensive_file(directory: str) -> Union[str, None]:
    """Finds the most recent comprehensive scraper results file."""
    try:
        comprehensive_files = glob.glob(os.path.join(directory, "customize_results_*.json"))
        if not comprehensive_files:
            return None
        return max(comprehensive_files, key=os.path.getmtime)
    except Exception as e:
        return None

def get_latest_box_file(directory: str, box_name_slug: str) -> Union[str, None]:
    """Finds the most recent box_contents file for a specific box."""
    try:
        search_pattern = os.path.join(directory, f"box_contents_*{box_name_slug}.json")
        box_files = glob.glob(search_pattern)
        if not box_files:
            return None
        return max(box_files, key=os.path.getmtime)
    except Exception as e:
        return None

def get_all_ingredients_from_cart(cart_data: dict, data_dir: str) -> List[str]:
    """Extracts a clean list of all available ingredients."""
    ingredients = set()

    for item in cart_data.get("items", []):
        if item.get("is_customizable"):
            # For customizable boxes, find their contents file
            box_name = item.get("name", "Unknown")
            print(f"  -> Found customizable box: '{box_name}'. Looking for contents...")
            name_slug = box_name.split('-')[-1].strip().lower()
            latest_box_file = get_latest_box_file(data_dir, name_slug)
            
            if latest_box_file:
                print(f"     Found contents file: {os.path.basename(latest_box_file)}")
                with open(latest_box_file, 'r') as f:
                    box_data = json.load(f)
                    for selected_item in box_data.get("selected_items", []):
                        ingredients.add(selected_item.get("name", "Unknown Item"))
            else:
                print(f"     Could not find a contents file for '{box_name}'.")
        else:
            # For individual items or non-customizable boxes, just add the name
            ingredients.add(item.get("name", "Unknown Item"))
            
    return sorted(list(ingredients))

def get_comprehensive_ingredients_and_data(comprehensive_data: dict) -> Tuple[List[str], dict]:
    """Extracts ingredients from comprehensive scraper format and returns analysis data."""
    ingredients = set()
    analysis_data = {
        "individual_items": comprehensive_data.get("individual_items", []),
        "non_customizable_boxes": comprehensive_data.get("non_customizable_boxes", []),
        "customizable_boxes": comprehensive_data.get("customizable_boxes", []),
        "available_alternatives": []
    }
    
    # Extract ingredients from individual items
    for item in analysis_data["individual_items"]:
        ingredients.add(item.get("name", "Unknown Item"))
    
    # Extract ingredients from non-customizable boxes
    for box in analysis_data["non_customizable_boxes"]:
        for item in box.get("selected_items", []):
            ingredients.add(item.get("name", "Unknown Item"))
    
    # Extract ingredients from customizable boxes (selected + alternatives)
    for box in analysis_data["customizable_boxes"]:
        for item in box.get("selected_items", []):
            ingredients.add(item.get("name", "Unknown Item"))
        
        # Store alternatives for swap recommendations
        analysis_data["available_alternatives"].extend(
            box.get("available_alternatives", [])
        )
    
    return sorted(list(ingredients)), analysis_data

def get_master_product_list(catalog_file: str = None) -> List[str]:
    """
    Returns the complete Farm to People product catalog for meal planning suggestions.
    Falls back to curated list if catalog file is not available.
    """
    # Try to load from comprehensive catalog first
    if catalog_file and os.path.exists(catalog_file):
        try:
            df = pd.read_csv(catalog_file)
            # Return all unique product names from the catalog
            product_names = df['name'].dropna().unique().tolist()
            print(f"✅ Loaded {len(product_names)} products from comprehensive catalog")
            return product_names
        except Exception as e:
            print(f"⚠️ Could not load catalog file {catalog_file}: {e}")
            print("📋 Falling back to curated list")
    
    # Fallback: Curated list based on most common/useful items from Farm to People catalog
    curated_items = [
        # Proteins
        "Pasture Raised Eggs",
        "Free Range Chicken Breast", 
        "Wild Salmon",
        "Wild Cod",
        "Local Halibut",
        "Ground Turkey",
        "Grass Fed Beef",
        "Pork Chops",
        
        # Vegetables - Aromatics & Bases
        "Yellow Onions",
        "Red Onions", 
        "Garlic",
        "Organic Scallions",
        "Fresh Ginger",
        
        # Vegetables - Common
        "Organic Carrots",
        "Rainbow Carrots",
        "Organic Potatoes",
        "Sweet Potatoes",
        "Organic Tomatoes",
        "Cherry Tomatoes",
        "Bell Peppers",
        "Lunchbox Peppers",
        "Organic Lettuce",
        "Mixed Greens",
        "Organic Spinach",
        "Organic Kale",
        "Organic Broccoli",
        "Brussels Sprouts",
        "Organic Cauliflower",
        "Organic Zucchini",
        "Organic Eggplant",
        "Organic Cucumber",
        "Sweet Corn",
        "Local Mushrooms",
        "Local Radishes",
        
        # Fruits
        "Organic Avocados",
        "Organic Bananas",
        "Local Apples",
        "Honeycrisp Apples",
        "Local Peaches",
        "Yellow Peaches",
        "Local Blueberries",
        "Organic Strawberries",
        "Organic Lemons",
        "Organic Limes",
        
        # Herbs & Specialty
        "Fresh Basil",
        "Fresh Cilantro", 
        "Fresh Parsley",
        "Fresh Thyme",
        "Fresh Rosemary",
        "Fresh Dill",
        
        # Nuts & Pantry/Dairy
        "Mixed Nuts",
        "Walnuts",
        "Local Cheese",
        "Organic Milk",
        "Greek Yogurt",
        "Local Bread",
        "Organic Quinoa",
        "Organic Rice",
        "Local Beans"
    ]
    
    print(f"📋 Using curated fallback list with {len(curated_items)} items")
    return curated_items

def get_enhanced_product_catalog() -> Dict[str, Dict[str, str]]:
    """
    Returns product information with pricing from the actual catalog when available.
    Falls back to curated list for items not found in catalog.
    """
    products = {}
    
    # Start with curated list as fallback
    curated_items = get_master_product_list()
    for item in curated_items:
        products[item] = {
            "name": item,
            "price": "Price available on checkout",
            "unit": "varies",
            "available": True
        }
    
    # Try to enhance with actual catalog data
    try:
        if os.path.exists("../data/farmtopeople_products.csv"):
            df = pd.read_csv("../data/farmtopeople_products.csv")
            
            for _, row in df.iterrows():
                # Use product name as-is (already cleaned by scraper)
                raw_name = str(row.get('name', '')).strip()
                if raw_name and raw_name != 'nan':
                    # Product names are already cleaned by the scraper
                    clean_name = raw_name
                    products[clean_name] = {
                            "name": clean_name,
                            "price": str(row.get('price', 'Price TBD')),
                            "unit": "item",  # Could be enhanced from description
                            "available": not bool(row.get('is_sold_out', False))
                        }
    except Exception as e:
        print(f"⚠️ Could not enhance with catalog data: {e}")
    
    return products

def fuzzy_match_product(suggestion: str, product_catalog: Dict[str, Dict[str, str]], threshold: float = 0.6) -> Optional[Dict[str, str]]:
    """
    Find the best matching product from the catalog using fuzzy string matching.
    """
    best_match = None
    best_score = 0
    
    suggestion_lower = suggestion.lower()
    
    for product_name, product_info in product_catalog.items():
        # Calculate similarity score
        score = SequenceMatcher(None, suggestion_lower, product_name.lower()).ratio()
        
        # Also check for partial matches
        if suggestion_lower in product_name.lower() or product_name.lower() in suggestion_lower:
            score = max(score, 0.7)  # Boost score for partial matches
        
        if score > best_score and score >= threshold:
            best_score = score
            best_match = product_info.copy()
            best_match["match_score"] = score
    
    return best_match

def process_ai_additions(ai_additions: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Process AI meal plan additions to include pricing and better product matching.
    """
    product_catalog = get_enhanced_product_catalog()
    processed_additions = []
    
    for addition in ai_additions:
        item_name = addition.get("item", "")
        quantity = addition.get("quantity", "1")
        usage = addition.get("usage", "")
        
        # Try to find matching product
        matched_product = fuzzy_match_product(item_name, product_catalog)
        
        if matched_product:
            processed_addition = {
                "item": matched_product["name"],
                "quantity": quantity,
                "price": matched_product["price"],
                "usage": usage,
                "available": matched_product["available"],
                "match_confidence": f"{matched_product.get('match_score', 0):.2f}"
            }
        else:
            # Fallback for unmatched items
            processed_addition = {
                "item": item_name,
                "quantity": quantity,
                "price": "Check website for pricing",
                "usage": usage,
                "available": True,
                "match_confidence": "0.00"
            }
        
        processed_additions.append(processed_addition)
    
    return processed_additions


def generate_meal_plan(ingredients: List[str], master_product_list: List[str], diet_hard: List[str] = None, dislikes: List[str] = None, time_mode: str = "standard", allow_surf_turf: bool = False) -> dict:
    """
    Generates a meal plan using the OpenAI API based on the detailed "Plan from Items" prompt.
    """
    print("\n🤖 Analyzing your ingredients to create a detailed meal plan...")
    
    # Set defaults for optional inputs
    if diet_hard is None:
        diet_hard = []
    if dislikes is None:
        dislikes = []

    if client:
        try:
            print("   -> Contacting OpenAI's GPT model with upgraded prompt...")
            MODEL = "gpt-4o" # Use a model that supports JSON mode well    
            
            # Convert inputs into a string format for the prompt
            items_str = json.dumps(ingredients)
            master_list_str = json.dumps(master_product_list)
            diet_hard_str = json.dumps(diet_hard)
            dislikes_str = json.dumps(dislikes)

            system_prompt = """
You are a comprehensive meal planner for Farm to People items that provides detailed cart analysis and meal planning.

CRITICAL: DO NOT INVENT OR MAKE UP INGREDIENTS
- For meals: Use ONLY items from the provided `items` list + basic pantry staples (salt, pepper, oil, butter, lemon/vinegar, garlic, onion, basic spices)
- For recommended swaps: Use ONLY items from the provided `available_alternatives` list
- For farm_to_people_additions: Use ONLY items from the provided `master_product_list`

Core Rules:
- Exactly ONE primary protein per dish (no surf-and-turf) unless allow_surf_turf=true
- Respect diet_hard; avoid dislikes. If conflict, swap with items from available_alternatives only
- "One-more-thing" design: each meal has a 3-step BASE and 1-3 level-ups (+time, +technique, or +ingredient)
- Time modes: quick <=15m, standard ~30m, all_in 45-60m
- Each meal MUST use >=2 items from the provided `items` list
- Do not include "Unknown Item"
- Fruit mainly as salad/salsa/dessert unless explicitly paired with protein

Comprehensive Analysis Requirements:
- Analyze ingredient quantities to verify meals are achievable with cart contents
- Suggest optimal swaps from available_alternatives based on what your meal recipes actually need
- Recommend specific items with quantities to add to Farm to People cart (from master_product_list) vs standard pantry staples
- For farm_to_people_additions, specify exact quantities needed (e.g., "2 pieces", "1 bunch", "8 oz") and explain usage
- Provide quantity status for each meal (sufficient/need_more)
- Calculate total servings across all meal suggestions

Your response must match this JSON schema exactly:
{
  "meals": [
    {
      "title": "string",
      "base": { "uses": ["Item A","Item B"], "steps": 3, "time_mode": "quick|standard|all_in" },
      "level_ups": [
        { "name": "string", "adds_minutes": 3-10, "uses": ["Optional Item"] }
      ],
      "swaps": [ { "if_oos": "Item X", "use": "Item Y" } ],
      "quantity_status": "sufficient|need_more|plenty",
      "estimated_servings": 2
    }
  ],
  "recommended_swaps": [
    {
      "swap_out": "Current selected item name",
      "swap_in": "Alternative item name", 
      "reason": "Why this swap improves the meal plan"
    }
  ],
  "farm_to_people_additions": [
    {
      "item": "Item name from master_product_list",
      "quantity": "specific quantity needed",
      "usage": "what this ingredient is for in the meal plan"
    }
  ],
  "pantry_staples": ["Basic cooking staples"],
  "total_estimated_servings": 0
}
"""
            # Get alternatives if available in context
            available_alternatives = []
            if hasattr(generate_meal_plan, '_alternatives_context'):
                available_alternatives = generate_meal_plan._alternatives_context
                
            alternatives_str = json.dumps(available_alternatives)
            
            user_prompt = f"""
Here are my constraints and available items:
items = {items_str}
available_alternatives = {alternatives_str}
master_product_list = {master_list_str}
diet_hard = {diet_hard_str}
dislikes = {dislikes_str}
time_mode = "{time_mode}"
allow_surf_turf = {str(allow_surf_turf).lower()}
"""

            prompt_messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = client.chat.completions.create(model=MODEL, messages=prompt_messages, response_format={"type": "json_object"})
            ai_response_json = json.loads(response.choices[0].message.content)
            print("   -> AI meal plan received!")
            return ai_response_json
        except Exception as e:
            print(f"   -> OpenAI API call failed: {e}. Falling back to placeholder examples.")

    # Fallback logic
    return {
        "meals": [
            {
                "title": "Placeholder Meal",
                "base": {"uses": ["Ingredient A", "Ingredient B"], "steps": 3, "time_mode": "standard"},
                "level_ups": [{"name": "Add garlic", "adds_minutes": 2, "uses": ["garlic"]}],
                "swaps": []
            }
        ],
        "shopping_addons": ["Olive Oil", "Salt", "Pepper"]
    }

def validate_meal_plan(meal_plan: Dict[str, Any], available_ingredients: List[str], master_product_list: List[str]) -> List[str]:
    """
    (Section I: Validator)
    Checks if the AI's meal plan only uses ingredients from the master product list.
    """
    invalid_items = []
    used_ingredients = set()

    for meal in meal_plan.get("meals", []):
        for item in meal.get("base", {}).get("uses", []):
            if isinstance(item, str):
                used_ingredients.add(item)
            elif isinstance(item, dict) and 'item' in item:
                used_ingredients.add(item['item'])
        for level_up in meal.get("level_ups", []):
            for item in level_up.get("uses", []):
                if isinstance(item, str):
                    used_ingredients.add(item)
                elif isinstance(item, dict) and 'item' in item:
                    used_ingredients.add(item['item'])

    # Check against the master list, which is the source of truth
    available_set = set(master_product_list)
    for item in used_ingredients:
        if item not in available_set:
            invalid_items.append(item)
            
    return invalid_items

def run_repair_prompt(faulty_plan: Dict[str, Any], invalid_items: List[str], available_ingredients: List[str], master_product_list: List[str]) -> Dict[str, Any]:
    """
    (Section F: Repair) - UPGRADED WITH AI
    Asks the AI to correct a meal plan using the master product list.
    """
    print("\n⚠️ Meal plan validation failed. Running AI repair prompt...")
    print(f"   Invalid items found: {', '.join(invalid_items)}")

    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not client.api_key:
        print("   -> WARNING: OPENAI_API_KEY not found. Cannot run repair.")
        return faulty_plan

    try:
        MODEL = "gpt-5-mini"
        
        faulty_plan_str = json.dumps(faulty_plan)
        invalid_items_str = json.dumps(invalid_items)
        available_ingredients_str = json.dumps(available_ingredients)
        master_product_list_str = json.dumps(master_product_list)

        system_prompt = """
You are a repair technician for a meal planning AI.
Your job is to fix a JSON meal plan that failed validation.
The user will provide the faulty JSON, a list of `invalid_items` that were used, a list of `available_ingredients` they have on hand, and a `master_product_list` of all possible items.

Your task:
1.  Analyze the `faulty_plan`.
2.  For each `invalid_item`, find the CLOSEST match in the `master_product_list`.
3.  You MUST replace the invalid items with their correct counterparts from the `master_product_list`.
4.  Return the corrected meal plan in the exact same JSON schema as the original. Do not change the structure.

Example: If an invalid item is "Organic Kale Farm...", and a valid item in the master list is "Organic Green Kale", you must replace it.
"""
        user_prompt = f"""
Here is the data:
faulty_plan = {faulty_plan_str}
invalid_items = {invalid_items_str}
available_ingredients = {available_ingredients_str}
master_product_list = {master_product_list_str}

Please correct the `faulty_plan` and return the fixed JSON.
"""

        print("   -> Contacting OpenAI to repair the meal plan...")
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        repaired_plan = json.loads(response.choices[0].message.content)
        print("   -> AI repair complete.")
        return repaired_plan

    except Exception as e:
        print(f"   -> An error occurred during AI repair: {e}")
        return faulty_plan


def add_pricing_to_analysis(analysis_text: str) -> str:
    """
    Post-process the GPT-5 analysis to add pricing from the catalog.
    Finds suggested items and replaces them with catalog prices.
    """
    try:
        # Load the product catalog with pricing
        if not os.path.exists(PRODUCT_CATALOG_FILE):
            print("⚠️ Product catalog not found, skipping pricing")
            return analysis_text
            
        df = pd.read_csv(PRODUCT_CATALOG_FILE)
        product_catalog = {}
        
        # Build product lookup dictionary
        for _, row in df.iterrows():
            name = row.get('name', '')
            price = row.get('price', 'Price TBD')
            if name and name not in product_catalog:
                product_catalog[name] = price
        
        print(f"💰 Loaded {len(product_catalog)} products for pricing lookup")
        
        # Hardcoded preferred proteins (exact matches)
        preferred_proteins = {
            "chicken breast": ("Locust Point Farm Boneless Skinless Chicken Breast", "$12.99", "0.7-1 lb"),
            "chicken thighs": ("Locust Point Farm Boneless Skinless Chicken Thighs", "$8.99", "0.6-1 lb"),
            "bone-in chicken thighs": ("Locust Point Farm Bone-in Chicken Thighs", "$7.59", "0.7-1 lb"),
            "ground beef": ("100% Grass-fed Ground Beef", "$9.99", "1.0 lb"),
        }
        
        # Find and replace items with pricing
        enhanced_text = analysis_text
        replacements_made = []
        
        # Look for protein suggestions
        for generic_name, (full_name, price, weight) in preferred_proteins.items():
            if generic_name in enhanced_text.lower():
                # Replace with full details
                pattern = generic_name
                replacement = f"{full_name} ({weight}) - {price}"
                enhanced_text = enhanced_text.replace(pattern, replacement)
                replacements_made.append(f"{generic_name} → {replacement}")
        
        # Look for common fresh items and find catalog matches
        fresh_items_to_find = [
            "garlic", "lemon", "lemons", "onion", "onions", "basil", "parsley", 
            "cilantro", "lime", "limes", "ginger", "scallions", "herbs"
        ]
        
        for item in fresh_items_to_find:
            if item in enhanced_text.lower():
                # Find best match in catalog
                best_match = find_best_catalog_match(item, product_catalog)
                if best_match:
                    catalog_name, catalog_price = best_match
                    # Only replace if we found a good match and it's not already priced
                    if "$" not in enhanced_text[enhanced_text.lower().find(item):enhanced_text.lower().find(item)+50]:
                        pattern = item
                        replacement = f"{catalog_name} - {catalog_price}"
                        enhanced_text = enhanced_text.replace(pattern, replacement, 1)  # Replace only first occurrence
                        replacements_made.append(f"{item} → {replacement}")
        
        if replacements_made:
            print(f"💰 Added pricing for: {', '.join([r.split(' → ')[0] for r in replacements_made])}")
        
        return enhanced_text
        
    except Exception as e:
        print(f"❌ Error adding pricing: {e}")
        return analysis_text  # Return original if pricing fails

def find_best_catalog_match(suggestion: str, product_catalog: dict) -> Optional[tuple]:
    """Find the best matching product in the catalog with fuzzy matching"""
    if not suggestion or not product_catalog:
        return None
    
    best_match = None
    best_score = 0.0
    suggestion_lower = suggestion.lower().strip()
    
    for product_name, price in product_catalog.items():
        if not product_name:
            continue
            
        product_lower = product_name.lower()
        
        # Calculate similarity score
        score = SequenceMatcher(None, suggestion_lower, product_lower).ratio()
        
        # Boost score for partial matches
        if suggestion_lower in product_lower:
            score = max(score, 0.8)
        elif any(word in product_lower for word in suggestion_lower.split()):
            score = max(score, 0.7)
        
        # Update best match if this is better
        if score > best_score and score > 0.6:  # Minimum threshold
            best_score = score
            best_match = (product_name, price)
    
    return best_match

def generate_cart_analysis_summary() -> str:
    """
    Generate a sophisticated cart analysis summary with proper swap logic.
    Only suggests swaps from available alternatives in the same customizable box.
    """
    try:
        # Get the latest cart data
        latest_comprehensive_file = get_latest_comprehensive_file(FARM_BOX_DATA_DIR)
        
        if not latest_comprehensive_file:
            return "❌ No cart data found. Please make sure you have items in your Farm to People cart."
        
        with open(latest_comprehensive_file, 'r') as f:
            comprehensive_data = json.load(f)
        
        all_ingredients, analysis_data = get_comprehensive_ingredients_and_data(comprehensive_data)
        
        if not all_ingredients:
            return "❌ No ingredients found in your cart. Please add some items and try again."
        
        # Build cart summary with swap options
        cart_analysis = []
        available_swaps = []
        
        # Individual items (no swaps possible)
        individual_items = analysis_data.get('individual_items', [])
        if individual_items:
            cart_analysis.append("**Individual Items:**")
            for item in individual_items:
                name = item.get('name', 'Unknown item')
                qty = item.get('quantity', 1)
                unit = item.get('unit', '')
                price = item.get('price', 'Price TBD')
                cart_analysis.append(f"- {name} ({qty} {unit}) - {price}")
        
        # Non-customizable boxes (no swaps possible)
        non_custom_boxes = analysis_data.get('non_customizable_boxes', [])
        for box in non_custom_boxes:
            box_name = box.get('box_name', 'Unknown box')
            cart_analysis.append(f"\n**{box_name} (Non-customizable):**")
            for item in box.get('selected_items', []):
                name = item.get('name', 'Unknown item')
                qty = item.get('quantity', 1)
                unit = item.get('unit', '')
                cart_analysis.append(f"- {name} ({qty} {unit})")
        
        # Customizable boxes (with available swaps)
        custom_boxes = analysis_data.get('customizable_boxes', [])
        for box in custom_boxes:
            box_name = box.get('box_name', 'Unknown box')
            selected_items = box.get('selected_items', [])
            available_alternatives = box.get('available_alternatives', [])
            
            cart_analysis.append(f"\n**{box_name} (Customizable):**")
            cart_analysis.append(f"Selected Items ({len(selected_items)}):")
            for item in selected_items:
                name = item.get('name', 'Unknown item')
                qty = item.get('quantity', 1)
                unit = item.get('unit', '')
                cart_analysis.append(f"- {name} ({qty} {unit})")
            
            # Add available alternatives for this box
            if available_alternatives:
                swap_info = {
                    'box_name': box_name,
                    'selected_items': [item.get('name', '') for item in selected_items],
                    'available_alternatives': [item.get('name', '') for item in available_alternatives]
                }
                available_swaps.append(swap_info)
        
        cart_summary = "\n".join(cart_analysis)
        
        # Build swap options text
        swap_options_text = ""
        if available_swaps:
            swap_options_text = "\n**AVAILABLE SWAP OPTIONS:**\n"
            for swap_info in available_swaps:
                box_name = swap_info['box_name']
                alternatives = swap_info['available_alternatives']
                swap_options_text += f"{box_name} alternatives: {', '.join(alternatives[:5])}{'...' if len(alternatives) > 5 else ''}\n"
        
        # Create the AI prompt (clean, no catalog data)
        analysis_prompt = f"""You are an expert meal planning strategist analyzing a Farm to People cart. Provide a sophisticated meal plan analysis.

CURRENT CART CONTENTS:
{cart_summary}

{swap_options_text}

IMPORTANT RULES:
- You can ONLY suggest swaps using the available alternatives listed above
- Each swap must be from the SAME customizable box
- Focus on strategic swaps that improve meal flexibility
- When recommending protein additions, suggest healthy options (chicken, fish, turkey, eggs) with approximate quantities
- When recommending fresh items, suggest specific items and rough quantities (e.g., "2 lemons", "1 bulb garlic")

Please provide analysis in exactly this format:

## Your Cart Analysis & Strategic Meal Plan

### Current Cart Overview
[Brief summary of what they have - individual items, boxes, total variety]

### Recommended Swaps for Better Meal Flexibility
[Suggest 2-3 strategic swaps ONLY from available alternatives within same box]

Priority Swap #1: [Box name] - Swap [current item] → [available alternative]
Reasoning: [Why this swap improves meal options]

Priority Swap #2: [Box name] - Swap [current item] → [available alternative]  
Reasoning: [Strategic benefit]

Optional Swap #3: [Box name] - Swap [current item] → [available alternative]
Reasoning: [Additional benefit]

### Recommended Protein Additions to Cart
Healthy protein options (no beef):
- [Specific proteins that work with these ingredients]

### Strategic Meal Plan (5 balanced meals)

Meal 1: [Creative name] (X servings)
Using: [Specific cart ingredients]
Status: ✅ [Brief completeness note]

Meal 2: [Creative name] (X servings)  
Using: [Specific cart ingredients]
Status: ✅ [Brief completeness note]

[Continue for 5 total meals]

### Additional Fresh Items Needed
- [Essential additions like garlic, herbs, citrus]

### Pantry Staples Needed
- [Basic pantry items for the recipes]

### Summary
With recommended proteins: You'll have X-Y complete servings with excellent variety and no food waste!

Focus on maximizing ingredient usage across multiple meals while maintaining balanced nutrition."""

        # Call GPT-5
        if not client:
            return "❌ AI service not available. Please try again later."
        
        print("🚀 Generating cart analysis with GPT-5...")
        print(f"   -> Analyzing {len(all_ingredients)} ingredients")
        print(f"   -> Found {len(available_swaps)} customizable boxes with alternatives")
        
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "user", "content": analysis_prompt}
            ]
        )
        
        analysis_result = response.choices[0].message.content.strip()
        
        # Post-process to add pricing from catalog
        enhanced_analysis = add_pricing_to_analysis(analysis_result)
        
        # Store the full analysis for web view
        analysis_id = store_analysis_for_web_view(enhanced_analysis)
        
        # Create SMS summary
        sms_summary = create_sms_summary(enhanced_analysis, analysis_id)
        
        return sms_summary
        
    except Exception as e:
        print(f"❌ Error generating cart analysis: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error analyzing your cart. Please try again in a moment."

def run_main_planner(generate_detailed_recipes: bool = False, user_skill_level: str = "intermediate"):
    """
    A helper function to run the main meal planning logic and return the plan.
    This is designed to be called from other scripts like the server.
    
    Args:
        generate_detailed_recipes: If True, enhance meals with professional recipe details
        user_skill_level: Cooking skill level for recipe generation ("beginner", "intermediate", "advanced")
    """
    master_product_list = get_master_product_list(PRODUCT_CATALOG_FILE)
    
    # Try comprehensive format first, fallback to legacy
    latest_comprehensive_file = get_latest_comprehensive_file(FARM_BOX_DATA_DIR)
    
    if latest_comprehensive_file:
        with open(latest_comprehensive_file, 'r') as f:
            comprehensive_data = json.load(f)
        
        all_ingredients, analysis_data = get_comprehensive_ingredients_and_data(comprehensive_data)
        
        # Set alternatives context for the AI prompt
        alternatives = []
        for box in analysis_data.get("customizable_boxes", []):
            alternatives.extend(box.get("available_alternatives", []))
        
        # Store alternatives in function context for prompt
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
    
    # For now, use default settings; later this can be customized per user from Supabase
    user_diet_hard = []  # e.g., ["vegetarian", "gluten-free"] - will come from Supabase
    user_dislikes = []   # e.g., ["mushrooms", "cilantro"] - will come from Supabase
    user_time_mode = "standard"  # "quick", "standard", or "all_in"
    
    meal_plan = generate_meal_plan(
        all_ingredients, master_product_list,
        diet_hard=user_diet_hard, dislikes=user_dislikes, time_mode=user_time_mode
    )
    
    invalid_items = validate_meal_plan(meal_plan, all_ingredients, master_product_list)
    if invalid_items:
        repaired_plan = run_repair_prompt(meal_plan, invalid_items, all_ingredients, master_product_list)
        final_invalid_items = validate_meal_plan(repaired_plan, all_ingredients, master_product_list)
        if not final_invalid_items:
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
    """Main function to run the meal planner from the command line."""
    print("===== AI Meal Planner =====")
    
    meal_plan = run_main_planner() # Call the helper
    
    if meal_plan.get("error"):
        print(meal_plan["error"])
        return

    # Print the results to the console (the original `main` logic)
    print("\n--- Initial AI Response (Pre-Validation) ---")
    print(json.dumps(meal_plan, indent=2))
    print("------------------------------------------")

    print("\n💡 Here are some meal ideas based on your items:")
    for meal in meal_plan.get("meals", []):
        print(f"\n  - MEAL: {meal.get('title', 'N/A')}")
        base_info = meal.get("base", {})
        uses = ", ".join(base_info.get("uses", []))
        print(f"    Base ({base_info.get('time_mode', '?')}): Uses {uses}")
        
        for level_up in meal.get("level_ups", []):
            lu_uses = f"(uses: {', '.join(level_up.get('uses', []))})" if level_up.get('uses') else ""
            print(f"      + Level-up: {level_up.get('name', 'N/A')} (+{level_up.get('adds_minutes', 0)}m) {lu_uses}")
        
    # Enhanced Farm to People additions with pricing
    ftp_additions = meal_plan.get("farm_to_people_additions", [])
    if ftp_additions:
        print("\n🛒 Farm to People Cart Additions:")
        
        # Process additions if they're in the new detailed format
        if ftp_additions and isinstance(ftp_additions[0], dict):
            processed_additions = process_ai_additions(ftp_additions)
            total_cost = 0
            
            for addition in processed_additions:
                item_name = addition["item"]
                quantity = addition["quantity"]
                price = addition["price"]
                usage = addition["usage"]
                available = addition["available"]
                
                status_emoji = "✅" if available else "❌"
                print(f"  {status_emoji} **{item_name}** ({quantity}) - {price}")
                if usage:
                    print(f"      For: {usage}")
                
                # Try to extract numeric price for total
                price_match = re.search(r'\$(\d+\.?\d*)', price)
                if price_match:
                    total_cost += float(price_match.group(1))
            
            if total_cost > 0:
                print(f"\n💰 Estimated additional cost: ${total_cost:.2f}")
        else:
            # Fallback for old format
            for item in ftp_additions:
                print(f"  - {item}")
    
    # Show pantry staples separately
    pantry_staples = meal_plan.get("pantry_staples", [])
    if pantry_staples:
        print("\n🥄 Pantry Staples Needed:")
        for staple in pantry_staples:
            print(f"  - {staple}")
        
    print("\nEnjoy your meals!")

if __name__ == "__main__":
    main()
