"""
Preference data models for Farm to People onboarding.

Contains meal definitions and preference structures used across
the onboarding flow and meal planning algorithms.

DATA STRUCTURES:
- FARM_BOX_MEALS: Core meal/cooking style options with signals
- PROTEIN_TYPES: Available protein preferences  
- COOKING_STYLES: Cooking method categories
- DIETARY_RESTRICTIONS: Supported dietary needs
- GOALS: Outcome preferences for ML ranking

SIGNAL TAXONOMY:
- Reveals: Direct preferences from specific meal selections
  Examples: chicken, roast, comfort, family, 30_45m
  
- Signals: Indirect preferences from cooking style selections
  Examples: time_fast, one_pan, batch_cook, stovetop_fast

The distinction helps the ML model understand both WHAT users 
like (reveals) and HOW they like to cook (signals).
"""

# Farm box meal data for high-signal preference discovery
# This data structure is shared between JavaScript frontend and Python backend
FARM_BOX_MEALS = {
    'screen1': [
        {
            'id': 'lemon-herb-roast-chicken',
            'name': 'Lemon Herb Roast Chicken',
            'reveals': ['chicken', 'roast', 'comfort', 'family', '30_45m', 'dinner']
        },
        {
            'id': '15-minute-chicken-stir-fry',
            'name': '15-Minute Chicken Stir-Fry',
            'reveals': ['chicken', 'quick', 'stir_fry', 'asian', 'veg_forward', 'weeknight']
        },
        {
            'id': 'grilled-salmon-greens',
            'name': 'Grilled Salmon with Greens',
            'reveals': ['seafood', 'healthy', 'grill_pan', 'quick', 'low_carb']
        },
        {
            'id': 'mediterranean-chickpea-bowl',
            'name': 'Mediterranean Chickpea Bowl',
            'reveals': ['vegetarian', 'mediterranean', 'grain_bowl', 'fresh', 'fiber']
        },
        {
            'id': 'turkey-meatballs-farro',
            'name': 'Turkey Meatballs with Farro',
            'reveals': ['turkey', 'balanced', 'meal_prep_friendly', 'oven', 'high_protein']
        },
        {
            'id': 'beef-tacos-skillet',
            'name': 'Beef Tacos (Skillet)',
            'reveals': ['beef', 'tex_mex', 'handhelds', 'skillet', 'weeknight']
        },
        {
            'id': 'veggie-pesto-pasta',
            'name': 'Veggie Pesto Pasta',
            'reveals': ['vegetarian', 'pasta', 'comfort', 'italian', '20_30m']
        },
        {
            'id': 'seasonal-vegetable-soup',
            'name': 'Seasonal Vegetable Soup',
            'reveals': ['veg_forward', 'soup_stew', 'batch_cook', 'freezer_friendly']
        }
    ],
    'screen2': [
        {
            'id': '15-20-minute-meals',
            'name': '15–20 Minute Meals',
            'signals': ['time_fast']
        },
        {
            'id': 'one-pan-sheet-pan',
            'name': 'One-Pan or Sheet-Pan',
            'signals': ['one_pan', 'easy_cleanup', 'oven']
        },
        {
            'id': 'meal-prep-week',
            'name': 'Meal Prep for the Week',
            'signals': ['batch_cook', 'portions_4plus']
        },
        {
            'id': 'stir-fry-skillet',
            'name': 'Stir-Fry or Skillet',
            'signals': ['stovetop_fast', 'asian_lean']
        },
        {
            'id': 'salads-grain-bowls',
            'name': 'Salads and Grain Bowls',
            'signals': ['bowls', 'fresh']
        },
        {
            'id': 'soups-stews',
            'name': 'Soups and Stews',
            'signals': ['cozy', 'make_ahead', 'freezer']
        },
        {
            'id': 'tacos-wraps',
            'name': 'Tacos and Wraps',
            'signals': ['handhelds', 'family_friendly']
        },
        {
            'id': 'grill-roast',
            'name': 'Grill or Roast',
            'signals': ['dry_heat', 'dinner_focus']
        }
    ]
}

# Preference categories for analysis
PROTEIN_TYPES = [
    'chicken', 'beef', 'pork', 'fish', 'eggs', 
    'dairy', 'plant', 'flexible', 'bone_broth'
]

COOKING_STYLES = [
    'roasted', 'grilled', 'stir_fry', 'pan_fry', 'simmered',
    'stewed', 'slow_cook', 'sheet_pan', 'raw', 'assembly',
    'blended', 'juiced', 'fermented', 'baked', 'pasta'
]

DIFFICULTY_LEVELS = ['easy', 'moderate', 'advanced']

MEAL_CATEGORIES = [
    'comfort', 'healthy', 'quick', 'breakfast', 'convenience',
    'gourmet', 'dessert', 'preservation', 'nourishing', 'seasonal', 'drinks'
]

DIETARY_RESTRICTIONS = [
    'high-protein', 'vegetarian', 'vegan', 'pescatarian',
    'gluten-free', 'dairy-free', 'low-carb', 'paleo', 
    'mediterranean', 'keto', 'none'
]

GOALS = [
    'quick-dinners',     # Hard prefer recipes ≤20 min, penalize >35
    'whole-food',        # Upweight veg_forward, whole grains, downweight processed
    'new-recipes',       # Set discovery mix to 20-30% stretch
    'reduce-waste',      # Prioritize use-your-box matches, leftovers-friendly
    'family-friendly'    # Favor mild spice, familiar formats, avoid bones/shells
]