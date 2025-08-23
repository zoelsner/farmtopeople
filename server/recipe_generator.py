"""
Professional Recipe Generation System for Farm to People
Transforms basic meal plans into restaurant-quality detailed recipes
"""

import json
from typing import Dict, List, Any, Optional
import openai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RecipeGenerator:
    """Generates detailed, professional-quality recipes from meal plan data"""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.client = openai.OpenAI(api_key=api_key)
        else:
            self.client = None
            print("⚠️ WARNING: OPENAI_API_KEY not found")
    
    def generate_detailed_recipe(self, meal: Dict[str, Any], user_skill_level: str = "intermediate") -> Dict[str, Any]:
        """
        Generate a detailed, professional recipe from basic meal information
        
        Args:
            meal: Basic meal data with title, ingredients, and basic info
            user_skill_level: "beginner", "intermediate", or "advanced"
            
        Returns:
            Enhanced meal data with professional recipe details
        """
        if not self.client:
            return self._add_fallback_recipe_details(meal)
        
        try:
            # Extract meal information
            title = meal.get('title', 'Untitled Recipe')
            base_ingredients = meal.get('base', {}).get('uses', [])
            level_ups = meal.get('level_ups', [])
            time_mode = meal.get('base', {}).get('time_mode', 'standard')
            
            # Create the recipe generation prompt
            system_prompt = self._get_recipe_generation_prompt(user_skill_level)
            user_prompt = self._format_meal_for_recipe_generation(meal)
            
            # Call OpenAI for detailed recipe
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            recipe_data = json.loads(response.choices[0].message.content)
            
            # Merge the detailed recipe with original meal data
            enhanced_meal = meal.copy()
            enhanced_meal.update(recipe_data)
            
            return enhanced_meal
            
        except Exception as e:
            print(f"Error generating detailed recipe: {e}")
            return self._add_fallback_recipe_details(meal)
    
    def _get_recipe_generation_prompt(self, skill_level: str) -> str:
        """Get the system prompt for recipe generation based on skill level"""
        
        base_prompt = """You are a professional chef and recipe developer creating detailed, restaurant-quality recipes for home cooks.

Your recipes must be:
1. PRECISE: Exact temperatures, timing, and measurements
2. PROFESSIONAL: Use proper culinary terminology with explanations
3. SENSORY: Include visual, aromatic, and textural cues for each step
4. PRACTICAL: Account for home kitchen limitations
5. EDUCATIONAL: Teach techniques while guiding through the recipe

CRITICAL RECIPE COMPONENTS TO INCLUDE:

1. **Mise en Place** (mandatory):
   - Specific knife cuts (julienne, brunoise, chiffonade, etc.) with measurements
   - Exact prep for each ingredient
   - Organization tips for efficient cooking

2. **Equipment & Temperature**:
   - Essential and optional equipment
   - Exact temperatures for each cooking stage
   - Pan sizes and heat distribution tips

3. **Detailed Instructions**:
   - WHY each step matters (the science/technique)
   - SENSORY CUES for doneness (not just times)
   - TROUBLESHOOTING for common mistakes
   - TECHNIQUE TIPS for best results

4. **Professional Techniques**:
   - Proper searing methods (oil temperature, pat dry, don't move)
   - Emulsification techniques for sauces
   - Seasoning layers and when to add each
   - Resting times and carryover cooking

5. **Timing & Workflow**:
   - Active vs passive time
   - Multi-tasking opportunities
   - Make-ahead elements
   - Service temperature and holding tips
"""

        skill_adjustments = {
            "beginner": """
SKILL LEVEL: BEGINNER
- Define ALL culinary terms in parentheses
- Break complex techniques into micro-steps
- Include more safety reminders
- Suggest pre-prepped alternatives when appropriate
- Extra detail on visual cues
- Include "Why This Works" explanations
""",
            "intermediate": """
SKILL LEVEL: INTERMEDIATE  
- Balance technique explanation with flow
- Introduce some advanced techniques with guidance
- Assume basic knife skills but explain specialty cuts
- Include chef tips and variations
""",
            "advanced": """
SKILL LEVEL: ADVANCED
- Use professional terminology freely
- Focus on technique refinement
- Include restaurant-style plating notes
- Suggest equipment upgrades for better results
- Include advanced flavor development techniques
"""
        }
        
        output_format = """

Your response must be a JSON object with this structure:
{
  "mise_en_place": [
    {
      "ingredient": "ingredient name",
      "prep": "specific prep instructions",
      "knife_cut": "if applicable",
      "notes": "storage or timing tips"
    }
  ],
  "equipment_needed": {
    "essential": ["list of must-have equipment"],
    "helpful": ["nice-to-have items"],
    "temperatures": {"equipment": "exact temperature"}
  },
  "cooking_instructions": [
    {
      "step_number": 1,
      "title": "Brief title (e.g., 'Sear the Protein')",
      "instructions": "Detailed instructions",
      "time": "X-Y minutes",
      "temperature": "exact heat level/temp",
      "sensory_cues": "what to look/smell/hear for",
      "why": "technique explanation",
      "troubleshooting": "common mistakes and fixes"
    }
  ],
  "chef_notes": {
    "make_ahead": "what can be prepped in advance",
    "storage": "how to store leftovers",
    "variations": "suggested modifications",
    "wine_pairing": "if applicable",
    "plating": "presentation tips"
  },
  "nutrition_highlights": ["key nutritional benefits"],
  "technique_glossary": {
    "term": "definition"
  }
}"""
        
        return base_prompt + skill_adjustments.get(skill_level, skill_adjustments["intermediate"]) + output_format
    
    def _format_meal_for_recipe_generation(self, meal: Dict[str, Any]) -> str:
        """Format meal data for the recipe generation prompt"""
        
        meal_description = f"""
Please create a detailed, professional recipe for:

DISH: {meal.get('title', 'Untitled Recipe')}

MAIN INGREDIENTS:
{json.dumps(meal.get('base', {}).get('uses', []), indent=2)}

TIME MODE: {meal.get('base', {}).get('time_mode', 'standard')} (quick=15min, standard=30min, all_in=45-60min)

OPTIONAL LEVEL-UPS:
{json.dumps(meal.get('level_ups', []), indent=2)}

SERVINGS: {meal.get('estimated_servings', 2)}

Create a recipe that:
1. Uses restaurant-quality techniques adapted for home cooking
2. Maximizes flavor development within the time constraints
3. Includes specific temperatures, timing, and sensory cues
4. Teaches proper technique while being practical
"""
        
        return meal_description
    
    def _add_fallback_recipe_details(self, meal: Dict[str, Any]) -> Dict[str, Any]:
        """Add basic recipe details as fallback when AI is unavailable"""
        
        enhanced = meal.copy()
        
        # Add basic structure that PDF generator expects
        enhanced['mise_en_place'] = [
            {
                "ingredient": ing,
                "prep": "Prepare as needed",
                "notes": "Have ready before cooking"
            }
            for ing in meal.get('base', {}).get('uses', [])
        ]
        
        enhanced['equipment_needed'] = {
            "essential": ["Large skillet or pot", "Cutting board", "Sharp knife"],
            "helpful": ["Thermometer", "Timer"],
            "temperatures": {}
        }
        
        enhanced['cooking_instructions'] = [
            {
                "step_number": i + 1,
                "title": f"Step {i + 1}",
                "instructions": step,
                "time": "See instructions",
                "temperature": "Medium heat",
                "sensory_cues": "Cook until done",
                "why": "This step is important for the recipe",
                "troubleshooting": "Adjust as needed"
            }
            for i, step in enumerate([
                "Prepare all ingredients as directed",
                "Heat pan and add oil",
                "Cook protein if applicable", 
                "Add vegetables and seasonings",
                "Combine all ingredients and serve"
            ])
        ]
        
        enhanced['chef_notes'] = {
            "make_ahead": "Prep ingredients in advance",
            "storage": "Store leftovers in airtight container",
            "variations": "Adjust seasonings to taste"
        }
        
        return enhanced


def enhance_meal_plan_with_recipes(meal_plan: Dict[str, Any], user_skill_level: str = "intermediate") -> Dict[str, Any]:
    """
    Enhance an entire meal plan with detailed recipes
    
    Args:
        meal_plan: The basic meal plan from meal_planner.py
        user_skill_level: The user's cooking skill level
        
    Returns:
        Meal plan with professional recipe details added
    """
    generator = RecipeGenerator()
    enhanced_plan = meal_plan.copy()
    
    # Enhance each meal with detailed recipe
    enhanced_meals = []
    for meal in meal_plan.get('meals', []):
        enhanced_meal = generator.generate_detailed_recipe(meal, user_skill_level)
        enhanced_meals.append(enhanced_meal)
    
    enhanced_plan['meals'] = enhanced_meals
    enhanced_plan['recipe_quality'] = 'professional'
    
    return enhanced_plan


if __name__ == "__main__":
    # Test the recipe generator
    test_meal = {
        "title": "Pan-Seared Salmon with Roasted Vegetables",
        "base": {
            "uses": ["Wild Salmon", "Brussels Sprouts", "Sweet Potatoes", "Lemon"],
            "steps": 3,
            "time_mode": "standard"
        },
        "level_ups": [
            {"name": "Herb butter finish", "adds_minutes": 5, "uses": ["butter", "fresh herbs"]}
        ],
        "estimated_servings": 2
    }
    
    generator = RecipeGenerator()
    enhanced_recipe = generator.generate_detailed_recipe(test_meal, "intermediate")
    
    print(json.dumps(enhanced_recipe, indent=2))
