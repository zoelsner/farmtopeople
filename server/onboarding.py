"""
Preference onboarding module for Farm to People.

Implements research-backed tile-based meal preference collection
with <2 minute completion time and 70/30 familiar/adventurous ratio.

KEY COMPONENTS:
- analyze_meal_preferences(): Extracts 20-30 signals from meal selections
- save_preferences(): Stores user preferences in Supabase with session tracking

PREFERENCE ANALYSIS:
- Proteins: chicken, beef, turkey, seafood, vegetarian
- Cooking methods: roast, stir_fry, grill_pan, skillet, oven, stovetop_fast
- Cuisines: asian, mediterranean, tex_mex, italian
- Meal types: grain_bowl, handhelds, pasta, soup_stew, bowls
- Time preferences: quick, 30_45m, 20_30m, time_fast, weeknight

GOAL WEIGHTING (for ML ranking):
- quick-dinners: Hard prefer ≤20 min, penalize >35
- whole-food: Upweight veg_forward, whole grains, downweight processed
- new-recipes: Set discovery mix to 20-30% stretch
- reduce-waste: Prioritize use-your-box matches, leftovers-friendly
- family-friendly: Favor mild spice, familiar formats, avoid bones/shells
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any

# Import database client
import supabase_client as db


def analyze_meal_preferences(selected_meal_ids: List[str]) -> Dict[str, Any]:
    """
    Analyze selected meals to derive high-signal cooking preferences for AI personalization.
    
    Uses the "reveals" and "signals" structure to extract 20-30 specific insights
    that inform the 70/20/10 recommendation strategy (safe/stretch/discovery).
    
    SIGNAL EXTRACTION:
    - Combines reveals (direct preferences) and signals (indirect preferences)
    - Categorizes into proteins, cooking methods, cuisines, meal types, time
    - Calculates preference diversity score for personalization depth
    
    Args:
        selected_meal_ids: List of meal IDs from FARM_BOX_MEALS
    
    Returns:
        Dict with specific preference signals for AI meal planning:
        - proteins: List of preferred protein types
        - cooking_methods: List of preferred cooking techniques
        - cuisines: List of preferred cuisine styles
        - meal_types: List of preferred meal formats
        - time_preferences: List of time-related preferences
        - top_signals: Top 10 most frequent signals
        - analysis: Metadata including diversity score and primary focus
    """
    from models.preferences import FARM_BOX_MEALS
    
    # Combine all meals for analysis
    all_meals = FARM_BOX_MEALS.get('screen1', []) + FARM_BOX_MEALS.get('screen2', [])
    meal_lookup = {meal['id']: meal for meal in all_meals}
    
    # Collect all signals from selected meals
    all_reveals = []
    all_signals = []
    proteins = set()
    cooking_methods = set()
    cuisines = set()
    meal_types = set()
    time_preferences = set()
    
    # Analyze each selected meal
    for meal_id in selected_meal_ids:
        meal = meal_lookup.get(meal_id)
        if not meal:
            continue
        
        # Extract reveals (from concrete meal selections)
        reveals = meal.get('reveals', [])
        all_reveals.extend(reveals)
        
        # Extract signals (from cooking style selections) 
        signals = meal.get('signals', [])
        all_signals.extend(signals)
        
        # Categorize signals for analysis
        for signal in reveals + signals:
            # Protein preferences
            if signal in ['chicken', 'beef', 'turkey', 'seafood', 'vegetarian']:
                proteins.add(signal)
            # Cooking methods
            elif signal in ['roast', 'stir_fry', 'grill_pan', 'skillet', 'oven', 'stovetop_fast']:
                cooking_methods.add(signal)
            # Cuisine styles
            elif signal in ['asian', 'mediterranean', 'tex_mex', 'italian']:
                cuisines.add(signal)
            # Meal structure
            elif signal in ['grain_bowl', 'handhelds', 'pasta', 'soup_stew', 'bowls']:
                meal_types.add(signal)
            # Time preferences
            elif signal in ['quick', '30_45m', '20_30m', 'time_fast', 'weeknight']:
                time_preferences.add(signal)
    
    # Determine primary preferences based on frequency
    all_tags = all_reveals + all_signals
    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    # Get top preferences by frequency
    sorted_preferences = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    top_preferences = [pref[0] for pref in sorted_preferences[:10]]  # Top 10 signals
    
    return {
        'proteins': list(proteins),
        'cooking_methods': list(cooking_methods),
        'cuisines': list(cuisines),
        'meal_types': list(meal_types),
        'time_preferences': list(time_preferences),
        'top_signals': top_preferences,
        'all_reveals': all_reveals,
        'all_signals': all_signals,
        'analysis': {
            'total_selections': len(selected_meal_ids),
            'unique_signals_captured': len(set(all_reveals + all_signals)),
            'signal_distribution': tag_counts,
            'primary_cooking_focus': sorted_preferences[0][0] if sorted_preferences else 'balanced',
            'preference_diversity_score': len(set(all_reveals + all_signals)) / max(len(selected_meal_ids), 1)
        }
    }


async def save_preferences(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save user preferences from onboarding flow to Supabase.
    
    Now includes FTP credentials and optional phone number for complete
    account setup during onboarding.
    
    Args:
        data: JSON payload containing:
            - householdSize: Number of people (1-6+)
            - mealTiming: List of meals needed (breakfast/lunch/dinner/snacks)
            - selectedMeals: List of meal IDs from preference selection
            - dietaryRestrictions: List of dietary needs
            - goals: List of outcome preferences (max 2)
            - ftpEmail: Farm to People account email
            - ftpPassword: Farm to People account password
            - phoneNumber: Optional phone for SMS features
    
    Returns:
        Result dictionary with:
            - status: 'success' or 'error'
            - message: User-friendly status message
            - session_id: UUID for linking to future authentication
            - preferences: Complete analyzed preference profile
    """
    try:
        # Extract preference data
        household_size = data.get('householdSize')
        meal_timing = data.get('mealTiming', [])  # New: breakfast/lunch/dinner/snacks
        selected_meals = data.get('selectedMeals', [])
        dietary_restrictions = data.get('dietaryRestrictions', [])
        goals = data.get('goals', [])
        
        # Extract FTP account data
        ftp_email = data.get('ftpEmail')
        ftp_password = data.get('ftpPassword')
        phone_number = data.get('phoneNumber')
        
        # Derive insights from meal selections for AI personalization
        preferences = analyze_meal_preferences(selected_meals)
        
        # Structure complete preference profile
        user_preferences = {
            'household_size': household_size,
            'meal_timing': meal_timing,  # Which meals they need help with
            'selected_meal_ids': selected_meals,
            'dietary_restrictions': dietary_restrictions,
            'goals': goals,
            # Derived insights from meal analysis
            'preferred_proteins': preferences['proteins'],
            'cooking_methods': preferences['cooking_methods'],
            'cuisines': preferences['cuisines'],
            'meal_types': preferences['meal_types'],
            'time_preferences': preferences['time_preferences'],
            'top_signals': preferences['top_signals'],
            'all_reveals': preferences['all_reveals'],
            'all_signals': preferences['all_signals'],
            'onboarding_completed_at': datetime.utcnow().isoformat()
        }
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # If FTP credentials provided, use them; otherwise create temp account
        if ftp_email and ftp_password:
            # Full account setup with FTP credentials
            db.upsert_user_credentials(
                phone_number=phone_number,  # Optional, may be None
                ftp_email=ftp_email,
                ftp_password=ftp_password,
                preferences=user_preferences
            )
            account_type = "complete"
        else:
            # Temporary account for preferences only (backward compatibility)
            temp_email = f"onboarding_{session_id[:8]}@temp.farmtopeople.com"
            db.upsert_user_credentials(
                phone_number=phone_number,  # Optional, may be None
                ftp_email=temp_email,
                ftp_password="",  # No password for temp accounts
                preferences=user_preferences
            )
            account_type = "temporary"
        
        print(f"✅ Saved onboarding preferences for session {session_id}")
        print(f"   Account type: {account_type}")
        print(f"   Email: {ftp_email if ftp_email else 'Not provided'}")
        print(f"   Phone: {phone_number if phone_number else 'Not provided'}")
        print(f"   Household: {household_size}")
        print(f"   Meals: {len(selected_meals)} selections")
        print(f"   Restrictions: {dietary_restrictions}")
        print(f"   Goals: {goals}")
        
        # Different success messages based on account type
        if account_type == "complete":
            message = "Account created! You can now text 'plan' to get personalized meal plans."
        else:
            message = "Preferences saved! Complete setup to unlock meal planning."
        
        return {
            "status": "success", 
            "message": message,
            "session_id": session_id,
            "account_type": account_type,
            "preferences": user_preferences
        }
        
    except Exception as e:
        print(f"❌ Error saving onboarding preferences: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error", 
            "message": "Failed to save preferences. Please try again."
        }