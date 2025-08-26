import os
from datetime import datetime
from typing import Dict, List, Any
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER


class OnePageMealPlan:
    """Single page meal plan that actually helps"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_styles()
    
    def setup_styles(self):
        """Minimal, clean styles"""
        if 'CompactTitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CompactTitle',
                fontSize=14,
                spaceAfter=8,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#000000')
            ))
        
        if 'SectionHead' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='SectionHead',
                fontSize=10,
                spaceBefore=6,
                spaceAfter=3,
                textColor=colors.HexColor('#000000'),
                leading=12
            ))
        
        if 'CompactBody' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CompactBody',
                fontSize=8,
                spaceAfter=2,
                leading=10
            ))
        
        if 'CompactSmall' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CompactSmall',
                fontSize=7,
                leading=8,
                textColor=colors.HexColor('#555555')
            ))
    
    def generate_pdf(self, data: Dict, output_path: str) -> str:
        """Generate single-page meal plan"""
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        story = []
        
        # Title
        story.append(Paragraph(
            f"<b>Your Cart → Meal Plan</b> | {datetime.now().strftime('%b %d')}",
            self.styles['CompactTitle']
        ))
        story.append(Spacer(1, 6))
        
        # WHAT YOU HAVE - All items in boxes
        story.append(Paragraph("<b>WHAT YOU HAVE</b>", self.styles['SectionHead']))
        
        # Individual items
        individual = data.get('analysis_data', {}).get('individual_items', [])
        if individual:
            items_text = " • ".join([item['name'] for item in individual[:8]])
            story.append(Paragraph(f"<b>Individual:</b> {items_text}", self.styles['CompactBody']))
        
        # Boxes
        for box in data.get('analysis_data', {}).get('customizable_boxes', []):
            box_name = box.get('box_name', 'Box')
            selected = box.get('selected_items', [])
            items_text = ", ".join([item['name'] for item in selected[:6]])
            story.append(Paragraph(f"<b>{box_name}:</b> {items_text}", self.styles['CompactBody']))
        
        for box in data.get('analysis_data', {}).get('non_customizable_boxes', []):
            box_name = box.get('box_name', 'Box')
            selected = box.get('selected_items', [])
            items_text = ", ".join([item['name'] for item in selected[:6]])
            story.append(Paragraph(f"<b>{box_name}:</b> {items_text}", self.styles['CompactBody']))
        
        story.append(Spacer(1, 8))
        
        # SMART SWAPS based on preferences
        story.append(Paragraph("<b>RECOMMENDED SWAPS</b>", self.styles['SectionHead']))
        
        # Get user preferences
        preferences = data.get('user_preferences', {})
        restrictions = preferences.get('dietary_restrictions', [])
        goals = preferences.get('goals', [])
        
        swaps = []
        
        # Check for items that conflict with preferences
        all_items = []
        for item in individual:
            all_items.append(item['name'])
        for box in data.get('analysis_data', {}).get('customizable_boxes', []):
            for item in box.get('selected_items', []):
                all_items.append(item['name'])
        
        # Flag pork if user doesn't eat it
        if 'no-pork' in restrictions:
            pork_items = [i for i in all_items if 'pork' in i.lower()]
            if pork_items:
                swaps.append(f"⚠️ {pork_items[0]} → Chicken (you don't eat pork)")
        
        # Add onions if missing and useful
        has_onions = any('onion' in item.lower() for item in all_items)
        if not has_onions:
            swaps.append("➕ Add onions ($1.29) - essential for 5+ meals")
        
        # Quick dinner focus
        if 'quick-dinners' in goals:
            swaps.append("➕ Pre-marinated proteins - saves 15 min prep")
        
        # High protein focus
        if 'high-protein' in goals:
            protein_count = sum(1 for i in all_items if any(
                p in i.lower() for p in ['chicken', 'salmon', 'eggs', 'turkey', 'beef']
            ))
            if protein_count < 2:
                swaps.append("➕ Add salmon or chicken - hit 30g protein/meal")
        
        # Display swaps
        for swap in swaps[:4]:  # Max 4 swaps
            story.append(Paragraph(swap, self.styles['CompactBody']))
        
        story.append(Spacer(1, 8))
        
        # MEALS YOU CAN MAKE - Just names with time
        story.append(Paragraph("<b>5 DINNERS YOU CAN MAKE</b>", self.styles['SectionHead']))
        
        meals = data.get('meals', [])
        
        # Sort by time if quick dinners is a goal
        if 'quick-dinners' in goals:
            meals = sorted(meals, key=lambda x: x.get('total_time', 999))
        
        # Create a simple table with meal names and times
        meal_data = []
        for i, meal in enumerate(meals[:5], 1):
            name = meal.get('title', 'Meal')
            time = meal.get('total_time', 30)
            protein = meal.get('protein_per_serving', 0)
            
            # Add tags
            tags = []
            if time <= 20:
                tags.append("QUICK")
            if protein >= 30:
                tags.append("HIGH-PROTEIN")
            
            tag_str = f" [{', '.join(tags)}]" if tags else ""
            
            meal_data.append([
                f"{i}. {name}{tag_str}",
                f"{time} min",
                f"{protein}g"
            ])
        
        # Create table
        meal_table = Table(meal_data, colWidths=[4.5*inch, 0.8*inch, 0.7*inch])
        meal_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('TEXTCOLOR', (1, 0), (-1, -1), colors.HexColor('#666666')),
        ]))
        
        story.append(meal_table)
        story.append(Spacer(1, 8))
        
        # KEY STATS - One line
        total_servings = sum(m.get('estimated_servings', 2) for m in meals[:5])
        avg_time = sum(m.get('total_time', 30) for m in meals[:5]) // 5
        high_protein = sum(1 for m in meals[:5] if m.get('protein_per_serving', 0) >= 30)
        
        stats = f"Total: {total_servings} servings | Avg: {avg_time} min/meal | {high_protein}/5 high-protein"
        story.append(Paragraph(stats, self.styles['CompactSmall']))
        
        story.append(Spacer(1, 8))
        
        # QUICK ADD LIST - What they actually need to buy
        story.append(Paragraph("<b>SHOPPING LIST</b> (to complete all meals)", self.styles['SectionHead']))
        
        # Smart shopping list based on gaps
        shopping = []
        if not has_onions:
            shopping.append("Onions (2)")
        
        # Check for common missing items
        shopping.extend([
            "Garlic (1 head)",
            "Olive oil",
            "Soy sauce",
            "Salt & pepper"
        ])
        
        shopping_text = " • ".join(shopping[:6])
        story.append(Paragraph(shopping_text, self.styles['CompactBody']))
        
        story.append(Spacer(1, 8))
        
        # STORAGE TIPS - Ultra condensed
        story.append(Paragraph("<b>STORAGE</b>", self.styles['SectionHead']))
        storage_tips = [
            "Proteins: Use within 2 days or freeze",
            "Leafy greens: Wash, dry, container",
            "Tomatoes: Counter until ripe, then fridge",
            "Herbs: Trim stems, water glass in fridge"
        ]
        
        for tip in storage_tips:
            story.append(Paragraph(f"• {tip}", self.styles['CompactSmall']))
        
        # Build PDF
        doc.build(story)
        return output_path


# Test it
if __name__ == "__main__":
    test_data = {
        "user_preferences": {
            "dietary_restrictions": ["no-pork"],
            "goals": ["quick-dinners", "high-protein"],
            "household_size": 2
        },
        "analysis_data": {
            "individual_items": [
                {"name": "Organic Avocados"},
                {"name": "Eggs (dozen)"}
            ],
            "customizable_boxes": [
                {
                    "box_name": "Paleo Box",
                    "selected_items": [
                        {"name": "Chicken Breast"},
                        {"name": "Pork Chops"},  # Will flag this
                        {"name": "Ground Beef"},
                        {"name": "Sweet Potatoes"}
                    ]
                }
            ],
            "non_customizable_boxes": [
                {
                    "box_name": "Small Produce Box",
                    "selected_items": [
                        {"name": "Zucchini"},
                        {"name": "Cherry Tomatoes"},
                        {"name": "Bell Peppers"},
                        {"name": "Lettuce"},
                        {"name": "Carrots"}
                    ]
                }
            ]
        },
        "meals": [
            {
                "title": "15-Min Chicken Stir-Fry",
                "total_time": 15,
                "estimated_servings": 2,
                "protein_per_serving": 35
            },
            {
                "title": "Quick Egg Scramble",
                "total_time": 10,
                "estimated_servings": 2,
                "protein_per_serving": 24
            },
            {
                "title": "Sheet Pan Chicken & Veggies",
                "total_time": 35,
                "estimated_servings": 4,
                "protein_per_serving": 40
            },
            {
                "title": "Zucchini Beef Skillet",
                "total_time": 20,
                "estimated_servings": 3,
                "protein_per_serving": 32
            },
            {
                "title": "Mediterranean Bowl",
                "total_time": 25,
                "estimated_servings": 2,
                "protein_per_serving": 28
            }
        ]
    }
    
    planner = OnePageMealPlan()
    output = planner.generate_pdf(test_data, "one_page_meal_plan.pdf")
    print(f"✅ Generated: {output}")
    print("\nSingle page with:")
    print("• Everything you have in your cart")
    print("• Smart swaps based on YOUR preferences")
    print("• 5 dinner names with times")
    print("• What you need to buy")
    print("• Ultra-condensed storage tips")