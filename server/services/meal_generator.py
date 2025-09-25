"""
Meal Generator Service
======================
Generates personalized meal suggestions using GPT.
Extracted from server.py to isolate meal generation logic.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
import openai
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration - Support GPT-5 Mini with reasoning for optimal meal planning
AI_MODEL = os.getenv("AI_MODEL", "gpt-5-mini")  # Default to GPT-5 Mini for better accuracy
AI_REASONING_LEVEL = os.getenv("AI_REASONING_LEVEL", "minimal")  # Minimal reasoning for fast JSON generation
print(f"🤖 Meal Generator using model: {AI_MODEL}")
if AI_MODEL.lower().startswith("gpt-5"):
    print(f"⚡ Reasoning level: {AI_REASONING_LEVEL}")

# Function to determine if model needs max_completion_tokens
def uses_completion_tokens_param(model_name):
    """
    Determine if the model uses max_completion_tokens instead of max_tokens.
    GPT-5 and reasoning models (o1, o3) use max_completion_tokens.
    """
    model_lower = model_name.lower()
    return (
        model_lower.startswith("gpt-5") or
        model_lower.startswith("o1") or
        model_lower.startswith("o3")
    )


def build_api_params(model_name, max_tokens_value, temperature_value=None):
    """
    Build OpenAI API parameters based on model capabilities.

    Args:
        model_name: The OpenAI model name
        max_tokens_value: Maximum tokens to generate
        temperature_value: Temperature setting (None means use model default)

    Returns:
        Dict with appropriate parameters for the model
    """
    params = {}

    # Handle token parameter naming
    if uses_completion_tokens_param(model_name):
        params["max_completion_tokens"] = max_tokens_value
        print(f"📝 [MODEL COMPAT] Using max_completion_tokens for {model_name}")
    else:
        params["max_tokens"] = max_tokens_value
        print(f"📝 [MODEL COMPAT] Using max_tokens for {model_name}")

    # Add JSON format for faster parsing
    params["response_format"] = {"type": "json_object"}
    print(f"📝 [MODEL COMPAT] Using JSON response format for faster parsing")

    # Handle temperature (GPT-5 only supports default temperature=1)
    model_lower = model_name.lower()
    if model_lower.startswith("gpt-5"):
        # GPT-5 only supports temperature=1 (default), so don't specify it
        print(f"📝 [MODEL COMPAT] Skipping temperature for {model_name} (uses default)")

        # GPT-5 REQUIRES reasoning_effort parameter to avoid empty responses
        reasoning_level = os.getenv("AI_REASONING_LEVEL", "minimal")  # Fixed: now defaults to minimal
        params["reasoning_effort"] = reasoning_level  # Use configurable reasoning level
        print(f"📝 [MODEL COMPAT] Using reasoning_effort={reasoning_level} for {model_name}")
    elif temperature_value is not None:
        params["temperature"] = temperature_value
        print(f"📝 [MODEL COMPAT] Using temperature={temperature_value} for {model_name}")

    return params


def calculate_possible_meals(proteins: List[str]) -> int:
    """
    Calculate how many complete meals can realistically be made from proteins.

    Args:
        proteins: List of protein items with quantities

    Returns:
        Number of realistic meals (1-4)
    """
    if not proteins:
        return 0

    meal_count = 0

    for protein in proteins:
        protein_lower = protein.lower()

        # Individual protein sources = 1 meal each
        if any(single_protein in protein_lower for single_protein in [
            'chicken breast', 'salmon', 'bass', 'steak', 'pork chop'
        ]):
            meal_count += 1

        # Ground meats - 1 lb = 2 meals, 0.5 lb = 1 meal
        elif 'ground' in protein_lower or 'turkey' in protein_lower:
            if '1 lb' in protein_lower or 'pound' in protein_lower:
                meal_count += 2
            else:
                meal_count += 1  # Default conservative estimate

        # Eggs - dozen can support multiple meals but count as 1 protein source
        elif 'egg' in protein_lower:
            meal_count += 1

        else:
            # Default: assume each protein item = 1 meal
            meal_count += 1

    # Cap at realistic maximum for current system
    return min(meal_count, 4)


def has_snack_potential(ingredients: Dict[str, List[str]]) -> bool:
    """
    Determine if remaining ingredients can make meaningful snacks.

    Args:
        ingredients: Dict with proteins, vegetables, other_items

    Returns:
        True if snack-worthy ingredients remain
    """
    # Check for snack-friendly items
    snack_indicators = [
        'egg',        # deviled eggs, egg salad
        'avocado',    # avocado toast, guacamole
        'tomato',     # bruschetta, salsa
        'cheese',     # cheese board
        'fruit',      # fruit salad
        'berry',      # mixed berries
        'nut'         # trail mix
    ]

    all_ingredients = ingredients.get('proteins', []) + ingredients.get('vegetables', []) + ingredients.get('other_items', [])

    for item in all_ingredients:
        item_lower = item.lower()
        if any(snack_ingredient in item_lower for snack_ingredient in snack_indicators):
            return True

    return False


def calculate_remaining_after_meals(cart_data: Dict[str, Any], used_meals: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Calculate what ingredients remain after allocating to specific meals.

    Args:
        cart_data: Original cart data
        used_meals: List of meals that have been allocated

    Returns:
        Dict of remaining ingredients
    """
    # For Phase 1, return simplified remaining calculation
    # In Phase 2, we'll implement proper ingredient tracking

    original = extract_ingredients_from_cart(cart_data)

    # Simple heuristic: if we used N meals, assume major proteins are taken
    # Leave smaller items and vegetables for snacks
    remaining_proteins = []
    remaining_vegetables = original['vegetables'].copy()
    remaining_other = original['other_items'].copy()

    # Keep eggs and small proteins for snacks
    for protein in original['proteins']:
        if 'egg' in protein.lower():
            remaining_proteins.append(protein)

    return {
        'proteins': remaining_proteins,
        'vegetables': remaining_vegetables,
        'other_items': remaining_other
    }


def extract_ingredients_from_cart(cart_data: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Extract and categorize ingredients from cart data WITH QUANTITY INFORMATION.

    Args:
        cart_data: Cart data with individual_items, customizable_boxes, etc.

    Returns:
        Dict with proteins, vegetables, and other_items lists including quantities
    """
    proteins = []
    vegetables = []
    other_items = []

    def format_item_with_quantity(item):
        """Format item name with quantity and unit information."""
        name = item.get('name', '')
        unit = item.get('unit', '')
        quantity = item.get('quantity', 1)

        if unit and quantity:
            if quantity == 1:
                return f"{name} ({unit})"
            else:
                return f"{name} ({quantity}x {unit})"
        return name

    # Individual items
    for item in cart_data.get('individual_items', []):
        name = item.get('name', '').lower()
        formatted_item = format_item_with_quantity(item)

        if 'egg' in name:
            proteins.append(formatted_item)
        elif 'avocado' in name:
            other_items.append(formatted_item)
        elif 'banana' in name:
            other_items.append(formatted_item)
        else:
            other_items.append(formatted_item)

    # Customizable boxes
    for box in cart_data.get('customizable_boxes', []):
        for item in box.get('selected_items', []):
            name = item.get('name', '').lower()
            formatted_item = format_item_with_quantity(item)

            if any(meat in name for meat in ['chicken', 'beef', 'turkey', 'sausage', 'fish', 'salmon', 'bass', 'pork']):
                proteins.append(formatted_item)
            elif any(veg in name for veg in ['tomato', 'pepper', 'kale', 'lettuce', 'carrot', 'zucchini', 'eggplant', 'onion', 'broccoli', 'spinach', 'arugula']):
                vegetables.append(formatted_item)
            else:
                other_items.append(formatted_item)

    # Non-customizable boxes
    for box in cart_data.get('non_customizable_boxes', []):
        for item in box.get('selected_items', []):
            name = item.get('name', '').lower()
            formatted_item = format_item_with_quantity(item)

            if any(fruit in name for fruit in ['plum', 'peach', 'nectarine', 'apple', 'orange', 'berry']):
                other_items.append(formatted_item)
            else:
                other_items.append(formatted_item)

    return {
        'proteins': proteins,
        'vegetables': vegetables,
        'other_items': other_items
    }


def build_meal_prompt(ingredients: Dict[str, List[str]], preferences: Dict[str, Any], meal_count: int = 4) -> str:
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

CRITICAL QUANTITY & SERVING RULES:
1. **PROTEIN PORTIONS (for this household size):**
   - MINIMUM REQUIREMENT: Every meal MUST have at least 20g protein per serving
   - 8 oz salmon/fish = 1 serving (ONE meal only - don't split across meals)
   - 1 lb ground turkey = 2 servings (can make 2 separate meals)
   - 1 chicken breast = 1 serving (ONE meal only)
   - 1 dozen eggs = can use across multiple meals (3-4 eggs per meal for 20g+ protein)
   - IMPORTANT: "Leftover" meals STILL contain full protein (e.g., turkey hash with leftover veggies = 28g protein from turkey)
   - NEVER return less than 20g protein for any meal - combine proteins if needed

2. **VEGETABLE PORTIONS:**
   - 5 oz arugula = very small amount (1-2 side salads, not main ingredient)
   - 1 bunch kale = 2-3 meals (hearty green, substantial amount)
   - 2 zucchini pieces = 1-2 meals realistically
   - 1 pint cherry tomatoes = 2-3 meals (accent ingredient)

3. **INGREDIENT DISTRIBUTION RULES:**
   - Don't use small quantities (5 oz arugula) in multiple meals
   - Each meal should have one dedicated protein (don't split 8 oz salmon)
   - Distribute vegetables based on actual amounts, not just variety
   - Large quantities (1+ lb) can span multiple meals
   - Small quantities (under 8 oz) should be used in 1 meal max

4. **REALISTIC MEAL PLANNING:**
   - Calculate how many complete dinners this cart can actually make
   - Be honest about portions - don't overstretch small quantities
   - Create meal names that reflect the actual ingredients available
   - Each meal should be substantial and satisfying for the household size

Return {meal_count} meal suggestions focusing on dinner meals.

When possible, align with their preferences while respecting ingredient quantities.
Prioritize variety but don't sacrifice realism for the sake of using every ingredient.

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


def build_snack_prompt(ingredients: Dict[str, List[str]], preferences: Dict[str, Any]) -> str:
    """
    Build GPT prompt for snack generation using remaining ingredients.

    Args:
        ingredients: Dict with remaining proteins, vegetables, other_items
        preferences: User preferences dict

    Returns:
        Formatted prompt string for GPT snack generation
    """
    household_size = preferences.get('household_size', '2 people')
    dietary_restrictions = preferences.get('dietary_restrictions', [])

    prompt = f"""Create 1-2 quick SNACKS using these remaining ingredients:

AVAILABLE INGREDIENTS:
PROTEINS: {', '.join(ingredients['proteins']) if ingredients['proteins'] else 'none'}
VEGETABLES: {', '.join(ingredients['vegetables']) if ingredients['vegetables'] else 'none'}
OTHER ITEMS: {', '.join(ingredients['other_items']) if ingredients['other_items'] else 'none'}

SNACK REQUIREMENTS:
- Quick prep time (under 10 minutes) OR can be prepped ahead and stored
- Something you can eat on-the-go or between meals
- Household size: {household_size}
- Dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}
- Use only ingredients listed above
- Focus on grab-and-go convenience
- Examples: deviled eggs, veggie bites, cheese plates, protein balls
- Can be high protein - that's fine! Protein amount doesn't determine if it's a snack
- The key: minimal prep when you want to eat it (prep-ahead is encouraged)

Examples of good snacks:
- Deviled eggs (if eggs available)
- Vegetable chips with dip
- Quick salad or bruschetta
- Fruit/veggie combination
- Simple appetizer

Format as JSON:
[{{
  "name": "Snack Name",
  "time": "X min",
  "protein_per_serving": X,
  "servings": 2,
  "type": "snack",
  "ingredients_used": ["list", "of", "ingredients"],
  "description": "Brief preparation method"
}}]"""

    return prompt


async def generate_meals(cart_data: Dict[str, Any], preferences: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate smart meal suggestions: realistic meal count + snacks with remaining ingredients.

    Args:
        cart_data: Cart data dict
        preferences: User preferences dict (optional)

    Returns:
        Dict with success status and meals array (meals + snacks) or error
    """
    try:
        print(f"🍽️ Starting SMART meal generation... (NEW LOGIC v2)")

        # Extract ingredients
        ingredients = extract_ingredients_from_cart(cart_data)

        # Step 1: Calculate realistic meal count
        possible_meal_count = calculate_possible_meals(ingredients['proteins'])
        actual_meal_count = min(possible_meal_count, 4)  # Cap at 4 for now

        print(f"📊 Smart analysis: Can make {possible_meal_count} meals from proteins, generating {actual_meal_count}")
        print(f"  ✅ Proteins available: {len(ingredients['proteins'])} items")
        print(f"  ✅ Will generate: {actual_meal_count} complete meals")
        
        # Step 2: Generate complete meals first
        if actual_meal_count > 0:
            meal_prompt = build_meal_prompt(ingredients, preferences or {}, actual_meal_count)

            # Call GPT for meals
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                return {"success": False, "error": "OpenAI API key not configured"}

            client = openai.OpenAI(api_key=openai_key)
            print(f"🤖 Calling {AI_MODEL} for {actual_meal_count} meal generation...")
            api_start_time = time.time()

            # Build parameters for meals - GPT-5 Mini optimized token allocation
            if AI_MODEL.lower().startswith("gpt-5"):
                token_limit = 4000  # 4K output tokens for detailed meal plans (reduced for speed)
                print(f"📝 [GPT-5 MEAL CONFIG] Using {token_limit} output tokens for {actual_meal_count} meals")
            else:
                token_limit = 800  # Standard GPT-4o limit
            api_params = build_api_params(AI_MODEL, max_tokens_value=token_limit, temperature_value=0.7)

            response = client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a creative chef who specializes in making delicious meals from specific available ingredients. Always return valid JSON."},
                    {"role": "user", "content": meal_prompt}
                ],
                **api_params
            )

            api_response_time = time.time() - api_start_time
            print(f"⏱️ [MEAL API DEBUG] {AI_MODEL} meal generation took: {api_response_time:.2f} seconds")

            # Parse meal response
            gpt_response = response.choices[0].message.content.strip()
            print(f"📥 [MEAL API DEBUG] Raw meals response length: {len(gpt_response)} characters")

            # Clean up response
            if "```json" in gpt_response:
                gpt_response = gpt_response.split("```json")[1].split("```")[0].strip()
            elif "```" in gpt_response:
                gpt_response = gpt_response.split("```")[1].strip()

            # Parse JSON
            parsed_response = json.loads(gpt_response)

            # Handle both direct array and object with meals key (GPT-4o returns object format)
            if isinstance(parsed_response, dict) and 'meals' in parsed_response:
                meals = parsed_response['meals']
            elif isinstance(parsed_response, list):
                meals = parsed_response
            else:
                raise ValueError(f"Unexpected GPT response format: {type(parsed_response)}")

            # Add type field, ensure protein compatibility, and categorize by protein content
            for i, meal in enumerate(meals):
                # Ensure protein field exists
                if 'protein_per_serving' in meal and 'protein' not in meal:
                    meal['protein'] = meal['protein_per_serving']

                # Validate minimum protein requirement (20g)
                protein_value = meal.get('protein', 0)
                if isinstance(protein_value, str):
                    # Extract numeric value from string like "35g"
                    import re
                    match = re.search(r'(\d+)', str(protein_value))
                    if match:
                        protein_value = int(match.group(1))
                    else:
                        protein_value = 0

                # Enforce 20g minimum - if less, bump it up with explanation
                if protein_value < 20:
                    print(f"  ⚠️ Meal '{meal.get('name', 'Unknown')}' has only {protein_value}g protein - adjusting to 20g minimum")
                    meal['protein'] = 20
                    meal['protein_per_serving'] = 20
                    meal['note'] = meal.get('note', '') + ' (protein adjusted to meet 20g minimum)'

                # Categorize as meal or snack based on cooking time/complexity, not just protein
                cook_time = meal.get('time', '').lower()
                meal_name = meal.get('name', '').lower()

                # Extract time in minutes - handle ranges like "10-12 min"
                time_minutes = 0
                if 'min' in cook_time:
                    try:
                        time_part = cook_time.split('min')[0].strip()
                        if '-' in time_part:
                            # Handle ranges: "10-12" → take first number "10"
                            time_minutes = int(time_part.split('-')[0].strip())
                        else:
                            # Handle single numbers: "25" → 25
                            time_minutes = int(''.join(filter(str.isdigit, time_part)))
                    except:
                        time_minutes = 0

                # Snack indicators: quick prep (<20 min), no cooking words, snack-like names
                snack_indicators = [
                    time_minutes < 20 and time_minutes > 0,  # Quick prep time
                    any(word in meal_name for word in ['slice', 'cup', 'plate', 'mix', 'blend', 'raw', 'bowl', 'parfait', 'smoothie']),
                    any(word in cook_time for word in ['no cook', 'assembly', 'mix', 'combine', 'layer']),
                    'yogurt' in meal_name or 'berries' in meal_name or 'fruit' in meal_name  # Common snack ingredients
                ]

                # Meal indicators: longer cook time, cooking methods mentioned
                meal_indicators = [
                    time_minutes >= 20,  # Longer cook time
                    any(word in meal_name for word in ['roast', 'sear', 'grill', 'braise', 'stir-fry', 'skillet', 'pan'])
                ]

                # Default to meal unless clear snack indicators
                if any(snack_indicators) and not any(meal_indicators):
                    meal['type'] = 'snack'
                else:
                    meal['type'] = 'meal'

                meal['id'] = i

                protein_amount = meal.get('protein', 0)
                print(f"  📊 {meal.get('name', 'Unknown')}: {protein_amount}g protein, {cook_time} → {meal['type']}")

            print(f"✅ Generated {len(meals)} complete meals")
        else:
            meals = []
            print(f"⚠️ No proteins available for complete meals")

        # Step 3: Generate snacks with remaining ingredients
        snacks = []
        remaining = calculate_remaining_after_meals(cart_data, meals)

        if has_snack_potential(remaining) and len(meals) < 4:
            print(f"🍿 Generating snacks with remaining ingredients...")

            snack_prompt = build_snack_prompt(remaining, preferences or {})

            # Call GPT for snacks
            snack_response = client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a creative chef who makes quick, healthy snacks. Always return valid JSON."},
                    {"role": "user", "content": snack_prompt}
                ],
                **api_params
            )

            snack_gpt_response = snack_response.choices[0].message.content.strip()

            # Clean and parse snack response
            if "```json" in snack_gpt_response:
                snack_gpt_response = snack_gpt_response.split("```json")[1].split("```")[0].strip()
            elif "```" in snack_gpt_response:
                snack_gpt_response = snack_gpt_response.split("```")[1].strip()

            try:
                snacks = json.loads(snack_gpt_response)

                # Add IDs and ensure type is set
                for i, snack in enumerate(snacks):
                    snack['type'] = 'snack'
                    snack['id'] = len(meals) + i
                    if 'protein_per_serving' in snack and 'protein' not in snack:
                        snack['protein'] = snack['protein_per_serving']

                print(f"✅ Generated {len(snacks)} snacks")
            except json.JSONDecodeError:
                print(f"⚠️ Could not parse snack suggestions, continuing with meals only")
                snacks = []

        # Combine meals and snacks
        all_suggestions = meals + snacks

        # Count actual meals vs snacks based on type field
        actual_meals = [item for item in all_suggestions if item.get('type') == 'meal']
        actual_snacks = [item for item in all_suggestions if item.get('type') == 'snack']

        print(f"🍽️ SMART GENERATION COMPLETE:")
        print(f"  📊 Total suggestions: {len(all_suggestions)}")
        print(f"  🥘 Meals: {len(actual_meals)}")
        print(f"  🍿 Snacks: {len(actual_snacks)}")

        for item in all_suggestions:
            print(f"    {item.get('type', 'unknown').upper()}: {item.get('name', 'Unknown')} ({item.get('protein', 'Unknown')}g protein)")

        # Add-ons are now generated separately in server.py to avoid duplication
        # This keeps meal generation focused on meals only

        return {
            "success": True,
            "meals": all_suggestions,  # Contains both meals and snacks
            "addons": [],  # Add-ons handled separately in server.py
            "meal_count": len(actual_meals),
            "snack_count": len(actual_snacks),
            "total_suggestions": len(all_suggestions),
            "addon_count": 0  # Add-ons handled separately now
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


async def generate_single_meal(cart_data: Dict[str, Any], preferences: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Generate a single meal suggestion for the simple meal card.

    Args:
        cart_data: Cart data with ingredients
        preferences: User preferences (optional)

    Returns:
        Dict with success status and meal data
    """
    try:
        print("🍽️ Generating single meal suggestion...")

        # Extract ingredients
        ingredients = extract_ingredients_from_cart(cart_data)
        all_ingredients = ingredients['proteins'] + ingredients['vegetables'] + ingredients['other_items']

        if not all_ingredients:
            return {
                "success": False,
                "error": "No ingredients found in cart"
            }

        # Build simplified prompt for single meal
        protein_preference = ""
        cooking_preference = ""

        if preferences:
            proteins = preferences.get('preferred_proteins', [])
            if proteins:
                protein_preference = f"Prefer these proteins: {', '.join(proteins[:3])}"

            cooking_methods = preferences.get('cooking_methods', [])
            if cooking_methods:
                cooking_preference = f"Cooking style: {', '.join(cooking_methods[:2])}"

        ingredient_list = ", ".join(all_ingredients[:10])  # Limit for prompt size

        prompt = f"""Create ONE simple meal using these Farm to People ingredients: {ingredient_list}

{protein_preference}
{cooking_preference}

Requirements:
- Use available ingredients creatively
- 30+ grams protein per serving
- Quick cooking method (under 30 minutes)
- Include cooking time and protein content
- Return valid JSON only

Format:
{{
    "name": "Meal Name with 35g protein",
    "cooking_time": "20 minutes",
    "protein": "35g",
    "ingredients_used": ["ingredient1", "ingredient2"],
    "quick_description": "Brief cooking method"
}}"""

        # Call OpenAI
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # Build parameters compatible with the specific model (for single meal generation)
        # GPT-5 Mini gets more tokens for detailed single meal with reasoning
        if AI_MODEL.lower().startswith("gpt-5"):
            token_limit = 2000  # 2K tokens for detailed single meal with reasoning
            print(f"📝 [GPT-5 SINGLE CONFIG] Using {token_limit} tokens for single meal")
        else:
            token_limit = 400  # Standard GPT-4o limit
        api_params = build_api_params(AI_MODEL, max_tokens_value=token_limit, temperature_value=0.8)
        print(f"📝 [SINGLE MEAL DEBUG] Using token limit: {token_limit} for {AI_MODEL}")

        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            **api_params
        )

        gpt_response = response.choices[0].message.content.strip()
        print(f"🤖 GPT Response: {gpt_response[:100]}...")

        # Clean up response if wrapped in markdown
        if "```json" in gpt_response:
            gpt_response = gpt_response.split("```json")[1].split("```")[0].strip()
        elif "```" in gpt_response:
            gpt_response = gpt_response.split("```")[1].strip()

        # Parse JSON
        meal = json.loads(gpt_response)

        print(f"✅ Generated single meal: {meal.get('name', 'Unknown')}")

        return {
            "success": True,
            "meal": meal,
            "ingredients_used": meal.get('ingredients_used', [])
        }

    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error in single meal: {e}")
        return {
            "success": False,
            "error": "Failed to parse meal suggestion",
            "raw_response": gpt_response if 'gpt_response' in locals() else None
        }

    except Exception as e:
        print(f"❌ Single meal generation error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def generate_meal_addons(meals: List[Dict], cart_data: Dict, preferences: Dict = None) -> List[Dict]:
    """
    Generate add-on items using AI to suggest ingredients that complement meals.
    Uses fixed product catalog for consistent pricing and availability.

    Args:
        meals: List of generated meal suggestions
        cart_data: Current cart contents (to avoid suggesting existing items)
        preferences: User preferences for personalization

    Returns:
        List of add-on product dictionaries with real prices
    """
    import time
    from services.addon_catalog import get_available_addon_keys, map_suggestions_to_products

    addon_gen_start = time.time()

    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("⚠️ No OpenAI API key for add-on generation")
            return []

        client = openai.OpenAI(api_key=openai_key)

        # Extract current cart items to avoid duplicates
        current_items = []
        for box in cart_data.get("customizable_boxes", []):
            current_items.extend([item["name"] for item in box.get("selected_items", [])])
        for box in cart_data.get("non_customizable_boxes", []):
            current_items.extend([item["name"] for item in box.get("selected_items", [])])
        for item in cart_data.get("individual_items", []):
            current_items.append(item["name"])

        # Extract full meal context, not just names
        meal_list = [meal for meal in meals if meal.get('type') == 'meal']

        if not meal_list:
            print("⚠️ No meals found for add-on generation")
            return []

        # Format meal context with all available information
        def format_meal_context(meals):
            """Build rich context from meal objects"""
            context_lines = []
            for i, meal in enumerate(meals, 1):
                context_lines.append(f"MEAL {i}: {meal.get('name', 'Unknown')}")
                if meal.get('ingredients_used'):
                    context_lines.append(f"  Ingredients: {', '.join(meal['ingredients_used'])}")
                if meal.get('description'):
                    context_lines.append(f"  Description: {meal['description']}")
                if meal.get('cooking_time'):
                    context_lines.append(f"  Cooking time: {meal['cooking_time']}")
            return '\n'.join(context_lines)

        # Get household context from preferences
        household_size = preferences.get('household_size', '2 people') if preferences else '2 people'
        dietary_restrictions = preferences.get('dietary_restrictions', []) if preferences else []
        cooking_skill = preferences.get('skill_level', 'intermediate') if preferences else 'intermediate'
        dislikes = preferences.get('dislikes', []) if preferences else []

        # Get available add-on options from catalog
        available_items = get_available_addon_keys()

        # Build dynamic master prompt
        prompt = f"""You help home cooks remember fresh ingredients they often forget but NEED for their meals.

MEALS BEING PREPARED:
{format_meal_context(meal_list)}

HOUSEHOLD CONTEXT:
- Size: {household_size}
- Dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}
- Cooking skill: {cooking_skill}
- Dislikes: {', '.join(dislikes) if dislikes else 'None'}

ALREADY IN CART:
{', '.join(current_items[:15])}

YOUR TASK:
Analyze what fresh ingredients are CRITICAL for these specific meals but might be forgotten.

RULES:
1. Read each meal's ingredients and description carefully
2. Identify cuisine type from context (don't assume)
3. Consider what fresh herbs/aromatics are ESSENTIAL (not optional)
4. Scale quantities: if multiple meals need same herb, suggest 2 bunches
5. NEVER suggest items already in cart or their close variants
6. Respect dietary restrictions - never suggest restricted items
7. Focus on fresh items that would significantly impact the meal if missing

AVAILABLE ITEMS TO CHOOSE FROM:
{', '.join(available_items)}

CRITICAL THINKING:
- What fresh herb defines this dish? (based on actual cuisine, not assumptions)
- What acid brightens it? (lime for Mexican/Thai, lemon for Mediterranean)
- What aromatics are foundational? (garlic, ginger, shallots based on cuisine)
- What accompaniment is essential? (bread for soup, tortillas for Mexican dishes)

Return 2-3 items as JSON array with specific reasoning tied to the actual meals above:
[
  {{"item": "item_key", "reason": "specific reason related to meal name and why it's essential"}}
]"""

        # Call AI for suggestions
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful chef focused on fresh ingredients people often forget. Think herbs, fresh produce, and items that make meals special. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        # Parse AI response
        ai_response = response.choices[0].message.content.strip()

        # Handle various response formats from GPT
        try:
            parsed = json.loads(ai_response)
            if isinstance(parsed, dict):
                # Could be {"suggestions": [...]} or {"addons": [...]} or direct items
                ai_suggestions = parsed.get('suggestions', parsed.get('addons', []))
                # If still no list found, check if it's a single-level dict with items
                if not ai_suggestions and 'item' in parsed:
                    ai_suggestions = [parsed]  # Single item response
            elif isinstance(parsed, list):
                ai_suggestions = parsed
            else:
                # Unexpected format
                print(f"⚠️ Unexpected AI response format: {type(parsed)}")
                ai_suggestions = []
        except json.JSONDecodeError:
            print(f"⚠️ Failed to parse AI response as JSON")
            ai_suggestions = []

        if not ai_suggestions:
            # Fallback suggestions
            ai_suggestions = [
                {"item": "lemons", "reason": "brightens flavors"},
                {"item": "garlic", "reason": "essential aromatic base"}
            ]

        # Map AI suggestions to real products
        addon_products = map_suggestions_to_products(ai_suggestions)

        # Filter out items already in cart (case-insensitive)
        current_items_lower = [item.lower() for item in current_items]
        filtered_addons = []
        for addon in addon_products:
            addon_name_lower = addon['name'].lower()
            if not any(cart_item in addon_name_lower for cart_item in current_items_lower):
                filtered_addons.append(addon)

        elapsed = time.time() - addon_gen_start
        print(f"⏱️ AI suggested {len(filtered_addons)} add-ons in {elapsed:.2f}s")

        return filtered_addons[:3]  # Return max 3 add-ons

    except Exception as e:
        print(f"❌ Error generating AI add-ons: {e}")
        # Fallback to simple suggestions
        from services.addon_catalog import ADDON_CATALOG
        fallback = [
            ADDON_CATALOG['lemons'].copy(),
            ADDON_CATALOG['garlic'].copy()
        ]
        for item in fallback:
            item['reason'] = item.pop('reason_template', 'Essential ingredient')
        return fallback[:2]


def check_protein_gap(current_items: List[str], meal_names: List[str], preferences: Dict = None) -> List[Dict]:
    """
    Check if cart has sufficient protein for planned meals.

    Args:
        current_items: List of current cart items
        meal_names: List of planned meal names
        preferences: User preferences for protein types

    Returns:
        List of protein add-on suggestions if gap detected, empty list otherwise
    """
    try:
        # Count proteins in current cart
        protein_count = 0
        for item in current_items:
            if is_protein_item(item):
                protein_count += 1

        meals_count = len(meal_names)

        print(f"🥩 Protein analysis: {protein_count} proteins in cart, {meals_count} meals planned")

        # If we have sufficient proteins (at least 1 per meal), no gap
        if protein_count >= meals_count:
            return []

        # Calculate protein gap
        protein_gap = meals_count - protein_count

        # Get user's preferred protein types
        preferred_proteins = get_preferred_proteins(preferences)

        # Generate protein add-on suggestions
        protein_addons = []

        if protein_gap >= 1:
            # Suggest primary protein
            protein_addons.append({
                "item": f"{preferred_proteins[0]} (2 servings)",
                "price": "$12.99",
                "reason": f"Complete protein for {protein_gap} meal{'s' if protein_gap > 1 else ''}",
                "category": "protein"
            })

        if protein_gap >= 2:
            # Suggest secondary protein for variety
            protein_addons.append({
                "item": f"{preferred_proteins[1]} (1-2 servings)",
                "price": "$9.99",
                "reason": "Add variety to your protein choices",
                "category": "protein"
            })

        if protein_gap >= 3:
            # Suggest quick protein option
            protein_addons.append({
                "item": "Farm Fresh Eggs (1 dozen)",
                "price": "$6.99",
                "reason": "Quick protein option for breakfasts or adding to meals",
                "category": "protein"
            })

        return protein_addons[:3]  # Cap at 3 suggestions

    except Exception as e:
        print(f"❌ Error checking protein gap: {e}")
        return []


def is_protein_item(item_name: str) -> bool:
    """Check if an item is a protein source."""
    name = item_name.lower()
    protein_keywords = [
        'chicken', 'beef', 'turkey', 'pork', 'lamb', 'fish', 'salmon',
        'tuna', 'cod', 'bass', 'steelhead', 'shrimp', 'egg', 'tofu',
        'tempeh', 'seitan', 'beans', 'lentils', 'quinoa', 'sausage',
        'kielbasa', 'bacon', 'ham', 'duck', 'goat', 'bison'
    ]
    return any(keyword in name for keyword in protein_keywords)


# Function removed - now using AI-driven add-on generation with fixed catalog mapping


def get_preferred_proteins(preferences: Dict = None) -> List[str]:
    """Get user's preferred protein types based on dietary restrictions."""
    if not preferences:
        return ["Organic Chicken Breast", "Wild-Caught Salmon", "Grass-Fed Ground Beef"]

    dietary_restrictions = preferences.get('dietary_restrictions', [])

    # Handle vegetarian/vegan preferences
    if 'vegetarian' in dietary_restrictions or 'vegan' in dietary_restrictions:
        return ["Organic Extra-Firm Tofu", "Tempeh", "Black Beans"]

    # Handle pescatarian
    if 'pescatarian' in dietary_restrictions:
        return ["Wild-Caught Salmon", "Fresh Cod Fillets", "Sustainable Shrimp"]

    # Default omnivore options
    return ["Organic Chicken Breast", "Wild-Caught Salmon", "Grass-Fed Ground Beef"]


def get_real_meal_addons(meal_names: List[str], current_items: List[str]) -> List[Dict]:
    """
    Get real Farm to People add-on products based on meal types.

    Args:
        meal_names: List of meal names to analyze
        current_items: Items already in cart to avoid duplicates

    Returns:
        List of real FTP add-on suggestions
    """
    try:
        from server.product_catalog import get_product_catalog
        catalog = get_product_catalog()

        # Convert current items to lowercase for comparison
        current_items_lower = [item.lower() for item in current_items]

        addons = []

        # Analyze meal types and suggest appropriate items
        meal_text = ' '.join(meal_names).lower()

        # Asian/Stir-fry meals
        if any(keyword in meal_text for keyword in ['stir-fry', 'asian', 'soy', 'sesame', 'ginger', 'teriyaki']):
            if not any('ginger' in item for item in current_items_lower):
                ginger_product = find_product_by_name(catalog, "Organic Ginger Root")
                if ginger_product:
                    addons.append({
                        "item": ginger_product['name'],
                        "price": ginger_product['price'],
                        "reason": "Essential for authentic Asian stir-fry flavors",
                        "category": "produce",
                        "vendor": ginger_product.get('vendor', 'Farm to People')
                    })

        # Italian meals
        if any(keyword in meal_text for keyword in ['italian', 'pasta', 'tomato', 'basil', 'parmesan']):
            if not any('basil' in item for item in current_items_lower):
                basil_product = find_product_by_name(catalog, "Organic Fresh Basil")
                if basil_product:
                    addons.append({
                        "item": basil_product['name'],
                        "price": basil_product['price'],
                        "reason": "Fresh herbs elevate Italian dishes",
                        "category": "produce",
                        "vendor": basil_product.get('vendor', 'Farm to People')
                    })

        # Fish/Seafood meals
        if any(keyword in meal_text for keyword in ['salmon', 'fish', 'seafood', 'cod', 'bass']):
            if not any('lemon' in item for item in current_items_lower):
                lemon_product = find_product_by_name(catalog, "Organic Lemons")
                if lemon_product:
                    addons.append({
                        "item": lemon_product['name'],
                        "price": lemon_product['price'],
                        "reason": "Fresh citrus brightens seafood dishes",
                        "category": "produce",
                        "vendor": lemon_product.get('vendor', 'Farm to People')
                    })

        # Mexican/Latin meals
        if any(keyword in meal_text for keyword in ['mexican', 'cilantro', 'lime', 'salsa', 'taco']):
            if not any('cilantro' in item for item in current_items_lower):
                cilantro_product = find_product_by_name(catalog, "Organic Cilantro")
                if cilantro_product:
                    addons.append({
                        "item": cilantro_product['name'],
                        "price": cilantro_product['price'],
                        "reason": "Fresh cilantro for authentic Mexican flavors",
                        "category": "produce",
                        "vendor": cilantro_product.get('vendor', 'Farm to People')
                    })

        # Roasted/Grilled meals
        if any(keyword in meal_text for keyword in ['roasted', 'roast', 'grilled', 'herb']):
            if not any('rosemary' in item for item in current_items_lower):
                rosemary_product = find_product_by_name(catalog, "Organic Bunched Rosemary")
                if rosemary_product:
                    addons.append({
                        "item": rosemary_product['name'],
                        "price": rosemary_product['price'],
                        "reason": "Aromatic herbs for roasted dishes",
                        "category": "produce",
                        "vendor": rosemary_product.get('vendor', 'Farm to People')
                    })

        # General cooking - garlic is universal
        if not any('garlic' in item for item in current_items_lower) and len(addons) < 3:
            garlic_product = find_product_by_name(catalog, "Organic Garlic")
            if garlic_product:
                addons.append({
                    "item": garlic_product['name'],
                    "price": garlic_product['price'],
                    "reason": "Essential aromatic for most cuisines",
                    "category": "produce",
                    "vendor": garlic_product.get('vendor', 'Farm to People')
                })

        return addons[:3]  # Return max 3 suggestions

    except Exception as e:
        print(f"❌ Error getting real add-ons: {e}")
        return []


def get_universal_addons() -> List[Dict]:
    """
    Get universal add-on items that work with any meal.

    Returns:
        List of universal add-on suggestions with real FTP products
    """
    try:
        from server.product_catalog import get_product_catalog
        catalog = get_product_catalog()

        # Universal items that enhance most dishes
        universal_items = [
            ("Organic Italian Parsley", "Versatile herb for garnishing any dish"),
            ("Organic Lemons", "Brightens flavors in any cuisine"),
            ("Organic Garlic", "Essential aromatic base for cooking")
        ]

        addons = []
        for item_name, reason in universal_items:
            product = find_product_by_name(catalog, item_name)
            if product:
                addons.append({
                    "item": product['name'],
                    "price": product['price'],
                    "reason": reason,
                    "category": "produce",
                    "vendor": product.get('vendor', 'Farm to People')
                })

        return addons

    except Exception as e:
        print(f"❌ Error getting universal add-ons: {e}")
        # Hard-coded fallback with known prices
        return [
            {"item": "Organic Italian Parsley", "price": "$3.29", "reason": "Versatile herb for garnishing", "category": "produce"},
            {"item": "Organic Lemons", "price": "$1.99", "reason": "Brightens any dish", "category": "produce"},
            {"item": "Organic Garlic", "price": "$1.00", "reason": "Essential cooking aromatic", "category": "produce"}
        ]


def find_product_by_name(catalog: Dict, search_name: str) -> Optional[Dict]:
    """
    Find a product in the catalog by partial name match.

    Args:
        catalog: Product catalog dictionary
        search_name: Name to search for

    Returns:
        Product dict if found, None otherwise
    """
    search_lower = search_name.lower()

    # Try exact match first
    for name, product in catalog.items():
        if search_lower == name.lower():
            return product

    # Try partial match
    for name, product in catalog.items():
        if search_lower in name.lower() or any(word in name.lower() for word in search_lower.split()):
            return product

    return None