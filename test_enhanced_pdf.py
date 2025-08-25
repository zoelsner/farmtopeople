#!/usr/bin/env python3
"""
Test the enhanced PDF generation with meal cards and recommendations.
"""

import json
from pathlib import Path
import sys

# Add server directory to path
sys.path.append('server')

from pdf_meal_planner import PDFMealPlanner

# Load real scraped data if available
data_file = Path("farm_box_data/customize_results_20250822_221218.json")
if data_file.exists():
    with open(data_file, 'r') as f:
        cart_data = json.load(f)
else:
    # Fallback test data
    cart_data = {
        "individual_items": [
            {"name": "Organic Chicken Breast", "quantity": 2, "price": "$15.99"},
            {"name": "Wild Salmon Fillet", "quantity": 1, "price": "$18.99"},
            {"name": "Pasture Raised Eggs", "quantity": 1, "price": "$5.99"},
            {"name": "Organic Zucchini", "quantity": 3, "price": "$4.99"},
            {"name": "Cherry Tomatoes", "quantity": 2, "price": "$3.99"},
            {"name": "Organic Apples", "quantity": 5, "price": "$6.99"}
        ]
    }

# Create comprehensive test meal plan data
test_data = {
    "analysis_data": cart_data,
    "total_estimated_servings": 18,
    "meals": [
        {
            "title": "Mediterranean Chicken Bowl",
            "total_time": 30,
            "estimated_servings": 4,
            "protein_per_serving": 35,
            "base": {
                "uses": ["Chicken Breast", "Cherry Tomatoes", "Cucumber", "Feta Cheese", "Olives"]
            },
            "level_ups": [
                {
                    "name": "Add Quinoa Base",
                    "adds_minutes": 15,
                    "uses": ["Quinoa", "Vegetable Broth"]
                }
            ]
        },
        {
            "title": "Quick Salmon Stir-Fry",
            "total_time": 20,
            "estimated_servings": 2,
            "protein_per_serving": 32,
            "base": {
                "uses": ["Salmon Fillet", "Zucchini", "Bell Peppers", "Garlic", "Ginger"]
            }
        },
        {
            "title": "Veggie-Packed Frittata",
            "total_time": 25,
            "estimated_servings": 3,
            "protein_per_serving": 18,
            "base": {
                "uses": ["Eggs", "Spinach", "Mushrooms", "Cheese", "Onion"]
            }
        },
        {
            "title": "Turkey Lettuce Wraps",
            "total_time": 15,
            "estimated_servings": 2,
            "protein_per_serving": 28,
            "base": {
                "uses": ["Ground Turkey", "Butter Lettuce", "Carrots", "Water Chestnuts"]
            }
        },
        {
            "title": "Sheet Pan Chicken & Veggies",
            "total_time": 35,
            "estimated_servings": 4,
            "protein_per_serving": 40,
            "base": {
                "uses": ["Chicken Thighs", "Brussels Sprouts", "Sweet Potatoes", "Red Onion"]
            },
            "level_ups": [
                {
                    "name": "Herb Butter Finish",
                    "adds_minutes": 5,
                    "uses": ["Butter", "Fresh Herbs"]
                }
            ]
        },
        {
            "title": "Asian-Inspired Noodle Bowl",
            "total_time": 25,
            "estimated_servings": 3,
            "protein_per_serving": 22,
            "base": {
                "uses": ["Rice Noodles", "Tofu", "Bok Choy", "Soy Sauce", "Sesame Oil"]
            }
        }
    ]
}

# Generate PDF
print("🎨 Creating enhanced PDF meal planner...")
planner = PDFMealPlanner()

output_path = "enhanced_meal_plan_test.pdf"
result = planner.generate_pdf(test_data, output_path)

print(f"✅ Generated: {output_path}")
print("\n📋 Features included:")
print("• Cart Overview with categorized items")
print("• Smart Recommendations box (yellow callout)")
print("• 2-column meal card grid (6 meals)")
print("• Ingredient Storage Guide")
print("• Detailed recipe instructions")
print("\n👀 Open the PDF to review the enhanced layout!")