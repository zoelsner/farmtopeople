"""
Meal Planning API endpoints for the weekly meal calendar system.
Provides REST API for meal plan creation, management, and ingredient allocation.
"""

import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, validator

from storage.supabase_storage import SupabaseMealStorage
from storage.base import StorageError, ConflictError, NotFoundError, ValidationError
import meal_planner  # Use existing meal planner

logger = logging.getLogger(__name__)

# Initialize storage layer
storage = SupabaseMealStorage()

# Create API router
router = APIRouter(prefix="/api/meal-plans", tags=["meal-plans"])

# Pydantic models for request/response validation
class CreateMealPlanRequest(BaseModel):
    user_phone: str
    week_of: str  # ISO date string
    cart_data: Dict

class MealData(BaseModel):
    name: str
    protein: str
    cook_time: str
    servings: int
    ingredients: List[str]
    instructions: List[str]
    nutrition: Optional[Dict] = None

class IngredientAllocation(BaseModel):
    name: str
    quantity: float
    unit: str

class AssignMealRequest(BaseModel):
    day: str  # monday, tuesday, etc.
    meal_data: MealData
    allocated_ingredients: List[IngredientAllocation]

class RegenerateMealRequest(BaseModel):
    day: str
    preferences: Optional[Dict] = None

class MealPlanResponse(BaseModel):
    id: str
    user_phone: str
    week_of: str
    status: str
    meals: Dict
    ingredient_pool: Dict
    created_at: str
    updated_at: str

class IngredientPoolResponse(BaseModel):
    ingredient_pool: Dict
    total_items: int
    allocated_items: int
    remaining_items: int

class SessionResponse(BaseModel):
    session_token: str
    expires_at: str


@router.post("/", response_model=MealPlanResponse)
async def create_meal_plan(request: CreateMealPlanRequest, background_tasks: BackgroundTasks):
    """
    Create a new meal plan for the specified week.
    Initializes ingredient pool and optionally generates initial meals.
    """
    try:
        # Parse week date
        week_date = date.fromisoformat(request.week_of)
        
        # Create meal plan
        plan_id = await storage.create_meal_plan(
            user_phone=request.user_phone,
            week_of=week_date,
            cart_data=request.cart_data
        )
        
        # Get the created meal plan to return
        meal_plan = await storage.get_meal_plan(request.user_phone, week_date)
        
        if not meal_plan:
            raise HTTPException(status_code=500, detail="Failed to retrieve created meal plan")
        
        # Check for saved meal suggestions from cart analysis
        saved_suggestions = None
        try:
            import supabase_client as db
            cart_data_record = db.get_latest_cart_data(request.user_phone)
            if cart_data_record and cart_data_record.get('meal_suggestions'):
                saved_suggestions = cart_data_record['meal_suggestions']
                logger.info(f"Found {len(saved_suggestions)} saved meal suggestions for {request.user_phone}")
        except Exception as e:
            logger.warning(f"Could not retrieve saved meal suggestions: {e}")
        
        # Generate initial 5-day meal plan in background
        background_tasks.add_task(
            generate_initial_meal_plan,
            plan_id,
            request.cart_data,
            request.user_phone,
            saved_suggestions  # Pass saved suggestions
        )
        
        return meal_plan
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_phone}/{week_of}", response_model=MealPlanResponse)
async def get_meal_plan(user_phone: str, week_of: str):
    """Get meal plan for specific user and week."""
    try:
        week_date = date.fromisoformat(week_of)
        meal_plan = await storage.get_meal_plan(user_phone, week_date)
        
        if not meal_plan:
            raise HTTPException(status_code=404, detail="Meal plan not found")
        
        return meal_plan
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{plan_id}/status")
async def update_meal_plan_status(plan_id: str, status: str):
    """Update meal plan status (planning, complete, archived)."""
    try:
        success = await storage.update_meal_plan_status(plan_id, status)
        
        if not success:
            raise HTTPException(status_code=404, detail="Meal plan not found")
        
        return {"success": True, "status": status}
        
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{plan_id}/meals")
async def assign_meal(plan_id: str, request: AssignMealRequest):
    """Assign a meal to a specific day with ingredient allocation."""
    try:
        # Convert Pydantic models to dicts
        meal_data = request.meal_data.dict()
        ingredients = [ing.dict() for ing in request.allocated_ingredients]
        
        success = await storage.assign_meal(plan_id, request.day, meal_data, ingredients)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to assign meal")
        
        return {"success": True, "day": request.day, "meal": meal_data["name"]}
        
    except ConflictError as e:
        raise HTTPException(
            status_code=409, 
            detail={
                "error": "Ingredient allocation conflicts",
                "conflicts": e.conflicts
            }
        )
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{plan_id}/meals/{day}")
async def get_meal_assignment(plan_id: str, day: str):
    """Get meal assignment for a specific day."""
    try:
        meal = await storage.get_meal_assignment(plan_id, day)
        
        if not meal:
            raise HTTPException(status_code=404, detail=f"No meal assigned to {day}")
        
        return meal
        
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{plan_id}/meals/{day}")
async def remove_meal_assignment(plan_id: str, day: str):
    """Remove meal assignment and release ingredients."""
    try:
        success = await storage.remove_meal_assignment(plan_id, day)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"No meal found for {day}")
        
        return {"success": True, "message": f"Meal removed from {day}"}
        
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{plan_id}/meals/{day}/regenerate")
async def regenerate_meal(plan_id: str, day: str, request: RegenerateMealRequest, background_tasks: BackgroundTasks):
    """Regenerate meal for specific day with smart ingredient consideration."""
    try:
        # Remove current meal assignment to free up ingredients
        await storage.remove_meal_assignment(plan_id, day)
        
        # Get current ingredient pool and other meals
        ingredient_pool = await storage.get_ingredient_pool(plan_id)
        all_meals = await storage.get_all_meals(plan_id)
        
        # Generate new meal in background
        background_tasks.add_task(
            regenerate_single_meal,
            plan_id,
            day,
            ingredient_pool,
            all_meals,
            request.preferences
        )
        
        return {
            "success": True,
            "message": f"Regenerating meal for {day}",
            "status": "processing"
        }
        
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{plan_id}/ingredients", response_model=IngredientPoolResponse)
async def get_ingredient_pool(plan_id: str):
    """Get current ingredient availability for the meal plan."""
    try:
        ingredient_pool = await storage.get_ingredient_pool(plan_id)
        
        # Calculate summary stats
        total_items = len(ingredient_pool)
        allocated_items = sum(1 for ing in ingredient_pool.values() if ing['allocated'] > 0)
        remaining_items = sum(1 for ing in ingredient_pool.values() if ing['remaining'] > 0)
        
        return {
            "ingredient_pool": ingredient_pool,
            "total_items": total_items,
            "allocated_items": allocated_items,
            "remaining_items": remaining_items
        }
        
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{plan_id}/ingredients/check")
async def check_ingredient_availability(plan_id: str, ingredients: List[IngredientAllocation]):
    """Check if requested ingredients are available without allocating them."""
    try:
        ingredient_dicts = [ing.dict() for ing in ingredients]
        conflicts = await storage.check_ingredient_conflicts(plan_id, ingredient_dicts)
        
        return {
            "available": len(conflicts) == 0,
            "conflicts": conflicts
        }
        
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions", response_model=SessionResponse)
async def create_session(user_phone: str, device_info: Optional[Dict] = None):
    """Create a new session for cross-device sync."""
    try:
        session_token = await storage.create_session(user_phone, device_info)
        
        return {
            "session_token": session_token,
            "expires_at": (datetime.now() + timedelta(hours=2)).isoformat()
        }
        
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_token}")
async def validate_session(session_token: str):
    """Validate session token and return session info."""
    try:
        session = await storage.validate_session(session_token)
        
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired session")
        
        # Update last active timestamp
        await storage.update_session_activity(session_token)
        
        return session
        
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


# Background task functions
async def generate_initial_meal_plan(plan_id: str, cart_data: Dict, user_phone: str, saved_suggestions: Optional[List] = None):
    """Generate initial 5-day meal plan in background."""
    try:
        logger.info(f"Generating initial meal plan for {plan_id}")
        
        # Get user preferences for meal generation
        user_preferences = {}
        try:
            import supabase_client as db
            # Try different phone formats to find user
            phone_formats = [user_phone, f"+{user_phone}", f"+1{user_phone}", f"1{user_phone}"]
            for phone_format in phone_formats:
                user_record = db.get_user_by_phone(phone_format)
                if user_record:
                    user_preferences = user_record.get('preferences', {})
                    logger.info(f"Found user preferences for {phone_format}")
                    break
        except Exception as e:
            logger.warning(f"Could not retrieve user preferences: {e}")
        
        # Get ingredient pool
        ingredient_pool = await storage.get_ingredient_pool(plan_id)
        
        # Generate meals for Monday-Friday
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']
        
        # Use saved suggestions if available
        if saved_suggestions and len(saved_suggestions) >= 5:
            logger.info(f"Using {len(saved_suggestions)} saved meal suggestions")
            for i, day in enumerate(days):
                if i < len(saved_suggestions):
                    saved_meal = saved_suggestions[i]
                    
                    # Convert saved meal format to our format
                    meal_data = {
                        'name': saved_meal.get('title', f'Meal {i+1}'),
                        'protein': saved_meal.get('protein', ''),
                        'cook_time': saved_meal.get('cook_time', '30 min'),
                        'servings': saved_meal.get('servings', 2),
                        'ingredients': saved_meal.get('ingredients', []),
                        'instructions': saved_meal.get('instructions', []),
                        'nutrition': saved_meal.get('nutrition', {}),
                        'storage_tips': saved_meal.get('storage_tips', [])
                    }
                    
                    # Extract ingredients with quantities
                    ingredients = []
                    for ingredient in saved_meal.get('ingredients', []):
                        # Parse ingredient string to extract quantity if possible
                        # Example: "1 lb chicken thighs" -> {name: "chicken thighs", quantity: 1, unit: "lb"}
                        ingredients.append(parse_ingredient_string(ingredient))
                    
                    if meal_data and ingredients:
                        try:
                            await storage.assign_meal(plan_id, day, meal_data, ingredients)
                            logger.info(f"Assigned saved meal to {day}: {meal_data['name']}")
                        except ConflictError as e:
                            logger.warning(f"Ingredient conflict for {day}: {e.conflicts}")
                            # Fall back to generating a new meal
                            meal_data, ingredients = await generate_meal_for_day(
                                day, ingredient_pool, cart_data, user_phone, user_preferences
                            )
                            if meal_data and ingredients:
                                await storage.assign_meal(plan_id, day, meal_data, ingredients)
        else:
            # Generate new meals if no saved suggestions
            logger.info("No saved suggestions found, generating new meals")
            for day in days:
                # Generate meal for this day
                meal_data, ingredients = await generate_meal_for_day(
                    day, ingredient_pool, cart_data, user_phone, user_preferences
                )
                
                if meal_data and ingredients:
                    # Try to assign the meal
                    try:
                        await storage.assign_meal(plan_id, day, meal_data, ingredients)
                        logger.info(f"Assigned meal to {day}: {meal_data['name']}")
                    except ConflictError as e:
                        logger.warning(f"Ingredient conflict for {day}: {e.conflicts}")
                        # Could implement fallback logic here
        
        # Update meal plan status to complete
        await storage.update_meal_plan_status(plan_id, 'complete')
        
    except Exception as e:
        logger.error(f"Error generating initial meal plan: {e}")


async def regenerate_single_meal(plan_id: str, day: str, ingredient_pool: Dict, 
                                other_meals: Dict, preferences: Optional[Dict]):
    """Regenerate a single meal with current ingredient constraints."""
    try:
        logger.info(f"Regenerating meal for {day} in plan {plan_id}")
        
        # Generate new meal considering available ingredients
        meal_data, ingredients = await generate_meal_for_day(
            day, ingredient_pool, {}, "", preferences, other_meals
        )
        
        if meal_data and ingredients:
            await storage.assign_meal(plan_id, day, meal_data, ingredients)
            logger.info(f"Regenerated meal for {day}: {meal_data['name']}")
        else:
            logger.warning(f"Failed to regenerate meal for {day}")
            
    except Exception as e:
        logger.error(f"Error regenerating meal for {day}: {e}")


async def generate_meal_for_day(day: str, ingredient_pool: Dict, cart_data: Dict, 
                               user_phone: str, preferences: Optional[Dict] = None,
                               other_meals: Optional[Dict] = None) -> tuple:
    """
    Generate a single meal for a specific day using available ingredients.
    Returns (meal_data, ingredients) tuple or (None, None) if generation fails.
    """
    try:
        # Available proteins and vegetables from ingredient pool
        available_proteins = [name for name, info in ingredient_pool.items() 
                            if info['remaining'] > 0 and is_protein(name)]
        available_vegetables = [name for name, info in ingredient_pool.items() 
                              if info['remaining'] > 0 and is_vegetable(name)]
        available_other = [name for name, info in ingredient_pool.items()
                         if info['remaining'] > 0 and not is_protein(name) and not is_vegetable(name)]
        
        if not available_proteins and 'Eggs' not in available_other:
            logger.warning(f"No proteins available for {day}")
            return None, None
        
        # Extract preferences
        preferences = preferences or {}
        dietary_restrictions = preferences.get('dietary_restrictions', [])
        health_goals = preferences.get('goals', [])
        cooking_methods = preferences.get('cooking_methods', [])
        household_size = preferences.get('household_size', '1-2')
        servings_needed = 2 if '1-2' in str(household_size) else 4
        
        # Check for high-protein goal
        high_protein = 'high-protein' in health_goals
        target_protein = "35-40g" if high_protein else "28g"
        
        # Vary meals based on day of week
        day_index = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'].index(day) if day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'] else 0
        
        # Different cooking methods for variety
        cooking_styles = [
            ("Pan-Seared", "Heat pan over medium-high heat"),
            ("Grilled", "Preheat grill to medium heat"),
            ("Roasted", "Preheat oven to 425°F"),
            ("Stir-Fried", "Heat wok or large pan over high heat"),
            ("Baked", "Preheat oven to 375°F")
        ]
        
        # Choose protein based on what's available and what hasn't been used
        if available_proteins:
            # Rotate through proteins for variety
            protein_index = day_index % len(available_proteins)
            protein = available_proteins[protein_index]
            protein_quantity = 0.75 if high_protein else 0.5
            protein_unit = ingredient_pool[protein]['unit']
        elif 'Eggs' in available_other:
            protein = 'Eggs'
            protein_quantity = 4 if high_protein else 3
            protein_unit = 'piece'
        else:
            return None, None
        
        # Choose vegetables for variety
        if available_vegetables:
            # Try to use different vegetables each day
            veg_index = day_index % len(available_vegetables)
            vegetable = available_vegetables[veg_index] if available_vegetables else None
        else:
            vegetable = None
        
        # Select cooking style based on preferences or rotate for variety
        style_index = day_index % len(cooking_styles)
        cooking_style, cooking_instruction = cooking_styles[style_index]
        
        # Build meal name with variety
        if protein == 'Eggs':
            meal_names = ["Scrambled Eggs", "Eggs Frittata", "Egg Shakshuka", "Eggs Benedict Style", "Veggie Omelet"]
            meal_name = meal_names[day_index] + (f" with {vegetable}" if vegetable else "")
        else:
            meal_name = f"{cooking_style} {protein}" + (f" with {vegetable}" if vegetable else "")
        
        meal_data = {
            "name": meal_name,
            "protein": target_protein,
            "cook_time": "25 min" if cooking_style != "Roasted" else "35 min",
            "servings": servings_needed,
            "ingredients": [protein] + ([vegetable] if vegetable else []),
            "instructions": [
                f"Season {protein} with salt and pepper",
                cooking_instruction,
                f"Cook {protein} until golden brown" if protein != 'Eggs' else f"Cook eggs until {cooking_style.lower()}",
                f"Add {vegetable} and cook until tender" if vegetable else "",
                "Season to taste and serve hot"
            ]
        }
        
        # Clean up empty instructions
        meal_data["instructions"] = [inst for inst in meal_data["instructions"] if inst]
        
        # Allocate ingredients
        ingredients = [
            {"name": protein, "quantity": protein_quantity, "unit": protein_unit}
        ]
        if vegetable:
            veg_quantity = 2 if servings_needed > 2 else 1
            ingredients.append({"name": vegetable, "quantity": veg_quantity, "unit": "piece"})
        
        return meal_data, ingredients
        
    except Exception as e:
        logger.error(f"Error generating meal for {day}: {e}")
        return None, None


# Helper functions
def parse_ingredient_string(ingredient_str: str) -> Dict:
    """
    Parse ingredient string to extract name, quantity, and unit.
    Examples:
    - "1 lb chicken thighs" -> {name: "chicken thighs", quantity: 1.0, unit: "lb"}
    - "2 zucchini" -> {name: "zucchini", quantity: 2.0, unit: "piece"}
    - "Salt and pepper" -> {name: "Salt and pepper", quantity: 1.0, unit: "serving"}
    """
    import re
    
    # Default values
    result = {
        'name': ingredient_str.strip(),
        'quantity': 1.0,
        'unit': 'piece'
    }
    
    # Try to parse quantity and unit
    # Pattern: (number) (unit) (rest)
    pattern = r'^(\d+\.?\d*)\s*(lb|lbs|oz|cup|cups|tbsp|tsp|piece|pieces|cloves?|bunch|bunches)?\s*(.+)$'
    match = re.match(pattern, ingredient_str.strip(), re.IGNORECASE)
    
    if match:
        quantity_str, unit, name = match.groups()
        result['quantity'] = float(quantity_str)
        if unit:
            # Normalize units
            unit_lower = unit.lower()
            if unit_lower in ['lb', 'lbs']:
                result['unit'] = 'lb'
            elif unit_lower == 'oz':
                result['unit'] = 'oz'
            elif unit_lower in ['cup', 'cups']:
                result['unit'] = 'cup'
            elif unit_lower in ['piece', 'pieces']:
                result['unit'] = 'piece'
            elif unit_lower in ['clove', 'cloves']:
                result['unit'] = 'clove'
            elif unit_lower in ['bunch', 'bunches']:
                result['unit'] = 'bunch'
            else:
                result['unit'] = unit_lower
        result['name'] = name.strip()
    else:
        # Try pattern without unit: just number and name
        pattern2 = r'^(\d+\.?\d*)\s+(.+)$'
        match2 = re.match(pattern2, ingredient_str.strip())
        if match2:
            quantity_str, name = match2.groups()
            result['quantity'] = float(quantity_str)
            result['name'] = name.strip()
            result['unit'] = 'piece'
    
    return result

def is_protein(item_name: str) -> bool:
    """Check if item is a protein source."""
    name = item_name.lower()
    return any(protein in name for protein in [
        'chicken', 'beef', 'fish', 'salmon', 'bass', 'eggs', 
        'steelhead', 'cod', 'tuna', 'shrimp', 'turkey', 'pork'
    ])

def is_vegetable(item_name: str) -> bool:
    """Check if item is a vegetable."""
    name = item_name.lower()
    return any(veg in name for veg in [
        'carrot', 'lettuce', 'tomato', 'pepper', 'onion', 'potato',
        'broccoli', 'spinach', 'kale', 'corn', 'cucumber'
    ]) and not any(fruit in name for fruit in [
        'apple', 'banana', 'orange', 'peach', 'plum', 'berry'
    ])