"""
Cart analysis and meal planning with GPT-5.
Generates sophisticated meal strategies based on FTP cart contents.

This module handles:
- Cart analysis summary generation
- Strategic meal planning with swap logic
- SMS summary creation
- Web view storage
"""

import os
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import openai

# Import our refactored modules
from file_utils import (
    get_latest_comprehensive_file, 
    load_cart_data,
    get_comprehensive_ingredients_and_data,
    save_analysis_result
)
from product_catalog import add_pricing_to_analysis


# Load environment variables first
from dotenv import load_dotenv
from pathlib import Path

project_root = Path(__file__).parent.parent
try:
    load_dotenv(dotenv_path=project_root / '.env')
except:
    pass  # Railway uses direct environment variables

# OpenAI client setup
api_key = os.getenv("OPENAI_API_KEY")
if api_key:
    print(f"✅ Cart Analyzer: OPENAI_API_KEY found (length: {len(api_key)})")
    client = openai.OpenAI(api_key=api_key)
else:
    print("⚠️ Cart Analyzer: OPENAI_API_KEY not found")
    client = None


def generate_cart_analysis_summary(user_id: str = None) -> str:
    """
    Generate a sophisticated cart analysis summary with GPT-5.
    
    This is the main entry point for cart analysis, handling:
    1. Cart data loading
    2. GPT-5 analysis generation
    3. Pricing post-processing
    4. SMS summary creation with web link
    
    Args:
        user_id: Optional user ID for production data retrieval
    
    Returns:
        SMS-optimized summary with web link to full analysis
    """
    try:
        # Get cart data (works for both local files and Supabase)
        latest_file_or_data = get_latest_comprehensive_file(user_id=user_id)
        
        if not latest_file_or_data:
            return "❌ No cart data found. Please make sure you have items in your Farm to People cart."
        
        # Load the data (handles both file paths and dicts)
        comprehensive_data = load_cart_data(latest_file_or_data)
        
        # Extract ingredients and structured data
        all_ingredients, analysis_data = get_comprehensive_ingredients_and_data(comprehensive_data)
        
        if not all_ingredients:
            return "❌ No ingredients found in your cart. Please add some items and try again."
        
        # Generate full analysis with GPT-5
        full_analysis = _generate_gpt5_analysis(all_ingredients, analysis_data)
        
        # Add pricing information via post-processing
        enhanced_analysis = add_pricing_to_analysis(full_analysis)
        
        # Store for web view and get ID
        analysis_id = save_analysis_result({
            'content': enhanced_analysis,
            'character_count': len(enhanced_analysis),
            'created_at': datetime.now().isoformat()
        }, user_id=user_id)
        
        # Create SMS summary
        sms_summary = create_sms_summary(enhanced_analysis, analysis_id)
        
        return sms_summary
        
    except Exception as e:
        print(f"❌ Error generating cart analysis: {e}")
        import traceback
        traceback.print_exc()
        return "❌ Sorry, there was an error analyzing your cart. Please try again."


def _generate_gpt5_analysis(ingredients: List[str], analysis_data: Dict) -> str:
    """
    Internal function to generate the GPT-5 analysis.
    
    Args:
        ingredients: List of all ingredients
        analysis_data: Structured cart data with boxes and alternatives
    
    Returns:
        Full GPT-5 generated analysis text
    """
    if not client:
        return "❌ AI service not available. Please try again later."
    
    # Build context about available swaps
    available_swaps = []
    for box in analysis_data.get('customizable_boxes', []):
        if box.get('available_alternatives'):
            available_swaps.append({
                'box_name': box['box_name'],
                'alternatives': box['available_alternatives']
            })
    
    # Construct the analysis prompt
    analysis_prompt = _build_analysis_prompt(ingredients, analysis_data, available_swaps)
    
    print("🚀 Generating cart analysis with GPT-5...")
    print(f"   -> Analyzing {len(ingredients)} ingredients")
    print(f"   -> Found {len(available_swaps)} customizable boxes with alternatives")
    
    # Call GPT-5
    response = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "user", "content": analysis_prompt}
        ]
    )
    
    return response.choices[0].message.content.strip()


def _build_analysis_prompt(ingredients: List[str], analysis_data: Dict, available_swaps: List[Dict]) -> str:
    """
    Builds the prompt for GPT-5 cart analysis.
    
    This prompt is carefully designed to:
    - Generate strategic meal plans
    - Only suggest swaps from available alternatives
    - Focus on healthy options (no beef bias)
    - Create balanced, waste-reducing meals
    """
    # Build cart summary
    cart_summary = []
    
    # Individual items
    if analysis_data.get('individual_items'):
        cart_summary.append("Individual Items:")
        for item in analysis_data['individual_items']:
            qty = item.get('quantity', 1)
            cart_summary.append(f"  - {item['name']} (qty: {qty})")
    
    # Non-customizable boxes
    if analysis_data.get('non_customizable_boxes'):
        for box in analysis_data['non_customizable_boxes']:
            cart_summary.append(f"\n{box['box_name']} (non-customizable):")
            for item in box.get('items', []):
                cart_summary.append(f"  - {item['name']}")
    
    # Customizable boxes with alternatives
    if analysis_data.get('customizable_boxes'):
        for box in analysis_data['customizable_boxes']:
            cart_summary.append(f"\n{box['box_name']} (customizable):")
            cart_summary.append("Selected items:")
            for item in box['selected_items']:
                cart_summary.append(f"  - {item['name']}")
            
            if box.get('available_alternatives'):
                cart_summary.append("Available alternatives:")
                for alt in box['available_alternatives'][:5]:  # Show first 5
                    cart_summary.append(f"  - {alt['name']}")
    
    cart_text = "\n".join(cart_summary)
    
    # Build swap options text
    swap_text = ""
    if available_swaps:
        swap_lines = []
        for swap_option in available_swaps:
            swap_lines.append(f"\n{swap_option['box_name']} alternatives:")
            for alt in swap_option['alternatives'][:10]:  # Limit to 10 alternatives
                swap_lines.append(f"  - {alt['name']}")
        swap_text = "\n".join(swap_lines)
    
    # The main prompt
    prompt = f"""You are an expert meal planner analyzing a Farm to People cart. Create a strategic meal plan that maximizes ingredient usage and minimizes waste.

CURRENT CART:
{cart_text}

{f"AVAILABLE SWAPS (can ONLY swap within the same box):{swap_text}" if swap_text else "No customizable boxes with swap options available."}

Generate a comprehensive cart analysis following this EXACT structure:

## Your Cart Analysis & Strategic Meal Plan

### Current Cart Overview
List items in the user's CURRENT cart (no prices needed here):

**Proteins:**
- Clean Product Name (quantity/unit)
Example: Chicken Breast (0.7-1 lb)

**Vegetables:**
- Clean Product Name (quantity/unit)
Example: Mixed Cherry Tomatoes (1 pint)

**Fruits:**
- Clean Product Name (quantity/unit)
Example: Organic Hass Avocados (5 pieces)

Rules:
- Use title case for product names
- Include quantity in parentheses (e.g., "2 pieces", "1 lb", "1 dozen")
- Remove redundant words and "Cook's Box" labels
- NO PRICES for current cart items

### Recommended Swaps for Better Meal Flexibility
Priority Swap #1: [Box name] - Swap [current item] → [available alternative]
Reasoning: [Why this swap improves meal options]

Priority Swap #2: [Box name] - Swap [current item] → [available alternative]
Reasoning: [How this enables better recipes]

Optional Swap #3: [Box name] - Swap [current item] → [available alternative]
Reasoning: [Additional benefit]

### Recommended Protein Additions to Cart
Healthy protein options to ADD to your order (include prices here):
- Product Name ($X.XX, size/quantity)
Example: Wild Salmon Fillet ($16.99, 8 oz)

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
    
    return prompt


def create_sms_summary(full_analysis: str, analysis_id: str) -> str:
    """
    Creates a concise SMS summary from the full analysis.
    
    This summary is designed to:
    - Fit in 2-3 SMS segments (320-480 chars)
    - Highlight key insights
    - Provide web link for full details
    - Include action options
    
    Args:
        full_analysis: Complete GPT-5 analysis with pricing
        analysis_id: Unique ID for web retrieval
    
    Returns:
        SMS-optimized summary text
    """
    lines = full_analysis.split('\n')
    
    # Extract key information
    cart_items = []
    meal_count = 0
    key_swap = ""
    
    # Parse cart overview
    in_overview = False
    for line in lines:
        if "Current Cart Overview" in line:
            in_overview = True
            continue
        elif in_overview and line.startswith('### '):
            break
        elif in_overview and line.strip() and not line.startswith('#'):
            # Clean up the line and add to cart items
            cleaned = line.strip('- ').strip()
            if cleaned:
                cart_items.append(cleaned)
    
    # Count meals
    for line in lines:
        if line.startswith("Meal ") and ":" in line:
            meal_count += 1
    
    # Find first swap recommendation
    for line in lines:
        if "Priority Swap" in line and "→" in line:
            # Extract the swap
            if "Swap" in line:
                parts = line.split("Swap", 1)
                if len(parts) > 1:
                    swap_part = parts[1].split("Reasoning:")[0].strip()
                    key_swap = f"Swap: {swap_part}"
                    break
    
    # Count pricing references
    dollar_count = full_analysis.count('$')
    
    # Build SMS summary
    summary = "🛒 **Cart Analysis Summary**\n\n"
    
    # Brief cart overview
    if cart_items:
        # Take first item or two
        brief_items = cart_items[0] if len(cart_items[0]) < 50 else cart_items[0][:47] + "..."
        summary += f"**Your cart:** {brief_items}\n"
        if len(cart_items) > 1:
            summary += f"Plus {len(cart_items)-1} more categories\n"
        summary += "\n"
    
    # Meal count
    if meal_count > 0:
        summary += f"**Plan:** {meal_count} strategic meals\n"
    
    # Key swap
    if key_swap:
        summary += f"**{key_swap}**\n"
    
    # Pricing
    if dollar_count > 0:
        summary += f"**Pricing:** {dollar_count} items with costs\n"
    
    summary += "\n"
    
    # Web link
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    summary += f"📄 **Full analysis:** {base_url}/meal-plan/{analysis_id}\n\n"
    
    # Actions
    summary += "Reply:\n"
    summary += "• CONFIRM → Get recipes\n"
    summary += "• MODIFY → Make changes"
    
    return summary


def generate_meal_titles_only(full_analysis: str) -> str:
    """
    Extracts just the meal titles from a full analysis.
    Used when user texts "MEALS" for a quick overview.
    
    Args:
        full_analysis: Complete analysis text
    
    Returns:
        Simple list of meal titles
    """
    lines = full_analysis.split('\n')
    meals = []
    
    for line in lines:
        if line.startswith("Meal ") and ":" in line:
            # Extract meal title
            meal_part = line.split(":", 1)[1].split("(")[0].strip()
            meals.append(meal_part)
    
    if meals:
        response = "📋 **Your Meal Plan:**\n\n"
        for i, meal in enumerate(meals, 1):
            response += f"{i}. {meal}\n"
        response += "\nReply CONFIRM for full recipes"
        return response
    
    return "No meals found. Reply PLAN to generate a meal plan."