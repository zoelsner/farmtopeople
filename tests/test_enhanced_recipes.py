#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced recipe generation system
"""

import json
import sys
import os

# Add the server directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from recipe_generator import RecipeGenerator

def test_recipe_generation():
    """Test the recipe generation with different skill levels"""
    
    # Sample meal from the meal planner
    test_meal = {
        "title": "Pan-Seared Wild Salmon with Roasted Brussels Sprouts and Sweet Potatoes",
        "base": {
            "uses": ["Wild Salmon", "Brussels Sprouts", "Sweet Potatoes", "Organic Lemons"],
            "steps": 3,
            "time_mode": "standard"
        },
        "level_ups": [
            {
                "name": "Herb butter finish",
                "adds_minutes": 5,
                "uses": ["Fresh Thyme", "Butter"]
            },
            {
                "name": "Crispy capers",
                "adds_minutes": 3,
                "uses": ["Capers"]
            }
        ],
        "quantity_status": "sufficient",
        "estimated_servings": 2
    }
    
    generator = RecipeGenerator()
    
    print("🧪 Testing Recipe Generation System")
    print("=" * 60)
    
    # Test different skill levels
    skill_levels = ["beginner", "intermediate", "advanced"]
    
    for skill_level in skill_levels:
        print(f"\n📚 Generating {skill_level.upper()} level recipe...")
        print("-" * 40)
        
        enhanced_recipe = generator.generate_detailed_recipe(test_meal, skill_level)
        
        # Display key parts of the recipe
        if 'mise_en_place' in enhanced_recipe:
            print("\n🔪 Mise en Place:")
            for prep in enhanced_recipe['mise_en_place'][:2]:  # Show first 2 items
                print(f"  • {prep['ingredient']}: {prep['prep']}")
                if prep.get('knife_cut'):
                    print(f"    Cut: {prep['knife_cut']}")
        
        if 'cooking_instructions' in enhanced_recipe:
            print("\n👨‍🍳 Sample Cooking Steps:")
            for instruction in enhanced_recipe['cooking_instructions'][:2]:  # Show first 2 steps
                print(f"\n  Step {instruction['step_number']}: {instruction['title']}")
                print(f"  Instructions: {instruction['instructions'][:100]}...")
                if instruction.get('temperature'):
                    print(f"  Temperature: {instruction['temperature']}")
                if instruction.get('sensory_cues'):
                    print(f"  Look for: {instruction['sensory_cues']}")
        
        if 'chef_notes' in enhanced_recipe:
            print("\n👨‍🍳 Chef Notes:")
            notes = enhanced_recipe['chef_notes']
            if notes.get('make_ahead'):
                print(f"  Make Ahead: {notes['make_ahead'][:80]}...")
            if notes.get('plating'):
                print(f"  Plating: {notes['plating'][:80]}...")
    
    # Save a complete example
    print("\n\n💾 Saving complete intermediate recipe example to 'sample_enhanced_recipe.json'...")
    intermediate_recipe = generator.generate_detailed_recipe(test_meal, "intermediate")
    
    with open('sample_enhanced_recipe.json', 'w') as f:
        json.dump(intermediate_recipe, f, indent=2)
    
    print("\n✅ Recipe generation test complete!")
    print("\nKey improvements over template-based system:")
    print("  • Specific temperatures and timing for each step")
    print("  • Professional knife cuts and mise en place")
    print("  • Sensory cues for determining doneness")
    print("  • Troubleshooting tips for common mistakes")
    print("  • Skill-level appropriate instructions")
    print("  • Make-ahead and storage guidance")

if __name__ == "__main__":
    test_recipe_generation()
