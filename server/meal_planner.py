import os
import json
import glob
import re
from datetime import datetime
from dotenv import load_dotenv
import openai
from typing import Dict, List, Any, Union, Optional
import pandas as pd

# --- Configuration ---
FARM_BOX_DATA_DIR = "farm_box_data"
PRODUCT_CATALOG_FILE = "../data/farmtopeople_products.csv"
load_dotenv()

# --- OpenAI Setup ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("⚠️ WARNING: OPENAI_API_KEY not found in .env file.")
    client = None
else:
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

def get_latest_box_file(directory: str, box_name_slug: str) -> str | None:
    """Finds the most recent box_contents file for a specific box."""
    try:
        search_pattern = os.path.join(directory, f"box_contents_*{box_name_slug}.json")
        box_files = glob.glob(search_pattern)
        if not box_files:
            return None
        return max(box_files, key=os.path.getmtime)
    except Exception as e:
        return None

def get_all_ingredients_from_cart(cart_data: dict, data_dir: str) -> list[str]:
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

def get_master_product_list(catalog_file: str) -> List[str]:
    """
    Reads the full product catalog and returns a list of all product names.
    """
    try:
        df = pd.read_csv(catalog_file)
        # Clean up names by removing farm info, similar to other functions
        product_names = df['Name'].str.split(r'([A-Z][a-z]+){2,}').str[0].str.strip().tolist()
        return list(set(product_names)) # Return unique names
    except FileNotFoundError:
        print(f"⚠️ Product catalog '{catalog_file}' not found. Proceeding without it.")
        return []
    except Exception as e:
        print(f"Error reading product catalog: {e}")
        return []


def generate_meal_plan(ingredients: list[str], master_product_list: list[str], diet_hard: list[str] = None, dislikes: list[str] = None, time_mode: str = "standard", allow_surf_turf: bool = False) -> dict:
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
            MODEL = "gpt-5-mini" # Use a model that supports JSON mode well    
            
            # Convert inputs into a string format for the prompt
            items_str = json.dumps(ingredients)
            master_list_str = json.dumps(master_product_list)
            diet_hard_str = json.dumps(diet_hard)
            dislikes_str = json.dumps(dislikes)

            system_prompt = """
You are a strict meal planner for Farm to People items.
Rules:
- Use ONLY the items I provide + these pantry staples: salt, pepper, oil, butter, lemon or vinegar, garlic, onion, basic dried spices.
- Exactly ONE primary protein per dish (no surf-and-turf) unless allow_surf_turf=true.
- Respect diet_hard; avoid dislikes. If conflict, swap with a CLOSE item from my list or its alternates only.
- "One-more-thing" design: each meal has a 3-step BASE and 1-3 level-ups (+time, +technique, or +ingredient).
- Time modes: quick <=15m, standard ~30m, all_in 45-60m.
- Return valid JSON ONLY. Do not invent items.
- Each meal MUST use >=2 items from the provided `items` list.
- Do not include "Unknown Item".
- Fruit mainly as salad/salsa/dessert unless explicitly paired with protein as a topping.
- Keep `shopping_addons` <= 5 total.
- For `shopping_addons`, you MUST choose items from the `master_product_list`.

Your response must match this JSON schema exactly:
{
  "meals": [
    {
      "title": "string",
      "base": { "uses": ["Item A","Item B"], "steps": 3, "time_mode": "quick|standard|all_in" },
      "level_ups": [
        { "name": "string", "adds_minutes": 3-10, "uses": ["Optional Item"] }
      ],
      "swaps": [ { "if_oos": "Item X", "use": "Item Y" } ]
    }
  ],
  "shopping_addons": ["Item 1","Item 2","Item 3"]
}
"""
            user_prompt = f"""
Here are my constraints and available items:
items = {items_str}
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
            response = client.chat.completions.create(model=MODEL, messages=prompt_messages, response_format={"type": "json_object"}, temperature=0.5)
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


def run_main_planner():
    """
    A helper function to run the main meal planning logic and return the plan.
    This is designed to be called from other scripts like the server.
    """
    master_product_list = get_master_product_list(PRODUCT_CATALOG_FILE)
    latest_cart_file = get_latest_cart_file(FARM_BOX_DATA_DIR)
    
    if not latest_cart_file:
        return {"error": "Could not find cart data."}
        
    with open(latest_cart_file, 'r') as f:
        cart_data = json.load(f)
        
    all_ingredients = get_all_ingredients_from_cart(cart_data, FARM_BOX_DATA_DIR)
    
    # Use default preferences for now
    user_diet_hard = ["no_shellfish"]
    user_dislikes = ["beets", "turnips"]
    user_time_mode = "standard"
    
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
        
    print("\n🛒 Suggested Supplemental Shopping List:")
    for item in meal_plan.get("shopping_addons", []):
        print(f"  - {item}")
        
    print("\nEnjoy your meals!")

if __name__ == "__main__":
    main()
