#!/usr/bin/env python3
"""
Generate a final test PDF with realistic data to verify the layout.
"""

import sys
sys.path.append('server')

from pdf_meal_planner import PDFMealPlanner
from datetime import datetime

# Create realistic test data that matches actual meal planner output
test_data = {
    "analysis_data": {
        "individual_items": [
            {"name": "Locust Point Farm Skinless Chicken Breast", "quantity": 2, "price": "$15.99"},
            {"name": "Wild Caught Salmon", "quantity": 1, "price": "$18.99"},
            {"name": "Organic Free-Range Eggs", "quantity": 1, "price": "$7.99"},
            {"name": "Organic Zucchini", "quantity": 3, "price": "$4.99"},
            {"name": "Heirloom Cherry Tomatoes", "quantity": 2, "price": "$5.99"},
            {"name": "Organic Bell Peppers", "quantity": 3, "price": "$6.99"},
            {"name": "Fresh Spinach", "quantity": 1, "price": "$3.99"},
            {"name": "Organic Garlic", "quantity": 1, "price": "$2.99"},
            {"name": "Fresh Basil", "quantity": 1, "price": "$2.99"}
        ]
    },
    "total_estimated_servings": 22,
    "meals": [
        {
            "title": "High-Protein Mediterranean Bowl",
            "total_time": 25,
            "estimated_servings": 4,
            "protein_per_serving": 42,
            "base": {
                "uses": ["Chicken Breast", "Cherry Tomatoes", "Spinach", "Feta"]
            }
        },
        {
            "title": "15-Minute Salmon Power Plate",
            "total_time": 15,
            "estimated_servings": 2,
            "protein_per_serving": 38,
            "base": {
                "uses": ["Salmon", "Zucchini", "Garlic", "Lemon"]
            }
        },
        {
            "title": "Protein-Packed Veggie Frittata",
            "total_time": 20,
            "estimated_servings": 4,
            "protein_per_serving": 31,
            "base": {
                "uses": ["Eggs (8)", "Bell Peppers", "Spinach", "Cheese"]
            }
        },
        {
            "title": "Quick Chicken Stir-Fry",
            "total_time": 18,
            "estimated_servings": 3,
            "protein_per_serving": 35,
            "base": {
                "uses": ["Chicken Breast", "Bell Peppers", "Zucchini", "Soy Sauce"]
            }
        },
        {
            "title": "Baked Salmon with Roasted Veggies",
            "total_time": 28,
            "estimated_servings": 2,
            "protein_per_serving": 36,
            "base": {
                "uses": ["Salmon", "Cherry Tomatoes", "Zucchini", "Basil"]
            }
        }
    ]
}

# Generate the PDF
print("📄 Generating final PDF with enhanced layout...")
planner = PDFMealPlanner()

output_file = f"meal_plan_enhanced_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
result = planner.generate_pdf(test_data, output_file)

print(f"\n✅ Successfully generated: {output_file}")
print("\nThe PDF includes:")
print("1️⃣  Cart Overview - categorized by proteins/vegetables/fruits")
print("2️⃣  Smart Recommendations - yellow box with suggestions")
print("3️⃣  Meal Cards Grid - 2-column layout with all 5 meals")
print("4️⃣  Storage Guide - proper storage for all ingredients")
print("5️⃣  Detailed Recipes - full cooking instructions")
print(f"\n👉 Opening {output_file}...")

import os
os.system(f"open {output_file}")