#!/usr/bin/env python3
"""
Integration script to combine the meal_plan_pdf_layout.md code 
with your existing PDFMealPlanner class.

This shows how to integrate the new layout while keeping your existing functionality.
"""

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepInFrame, PageBreak, ListFlowable, ListItem
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from typing import Dict, List, Any

class EnhancedPDFMealPlanner:
    """
    Enhanced version that integrates the card layout with your existing code.
    """
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Add all the styles including the new card styles"""
        
        # Your existing styles
        if 'CustomTitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CustomTitle',
                parent=self.styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#2E7D32')
            ))
        
        # New card-specific styles from the layout doc
        self.styles.add(ParagraphStyle(
            name='CardTitle',
            parent=self.styles['Heading3'],
            fontSize=12, leading=14,
            textColor=colors.HexColor('#1B5E20'),
            spaceAfter=4
        ))
        
        self.styles.add(ParagraphStyle(
            name='CardMeta',
            parent=self.styles['Normal'],
            fontSize=9, leading=11,
            textColor=colors.HexColor('#455A64')
        ))
        
        self.styles.add(ParagraphStyle(
            name='CardLabel',
            parent=self.styles['Normal'],
            fontSize=9, leading=11,
            textColor=colors.HexColor('#2E7D32')
        ))
        
        self.styles.add(ParagraphStyle(
            name='Small',
            parent=self.styles['Normal'],
            fontSize=8, leading=10,
            textColor=colors.HexColor('#37474F')
        ))
        
        self.styles.add(ParagraphStyle(
            name='CalloutTitle',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#684e00')
        ))
    
    def build_meal_card(self, meal: Dict, index: int, card_w: float, card_h: float):
        """Build a single meal card - adapted to use your data structure"""
        
        # Extract data flexibly from your meal structure
        title = meal.get('title', 'Untitled')
        
        # Handle different time formats
        time_min = meal.get('total_time', meal.get('cook_time', ''))
        
        # Get servings
        servings = meal.get('servings', meal.get('estimated_servings', ''))
        
        # Get protein - check multiple possible fields
        protein = meal.get('protein_per_serving', 
                          meal.get('protein', 
                          meal.get('nutrition', {}).get('protein', '')))
        
        # Get ingredients from your structure
        uses = []
        if 'base' in meal and 'uses' in meal.get('base', {}):
            uses = meal['base']['uses'][:4]  # Limit to 4
        elif 'ingredients' in meal:
            # Handle if ingredients is a list of strings
            ingredients = meal['ingredients']
            if isinstance(ingredients, list) and len(ingredients) > 0:
                if isinstance(ingredients[0], str):
                    uses = ingredients[:4]
                elif isinstance(ingredients[0], dict):
                    uses = [ing.get('name', str(ing)) for ing in ingredients[:4]]
        
        # Build the card content
        header = Paragraph(f"<b>Meal {index}:</b> {title}", self.styles['CardTitle'])
        
        # Format metadata line
        meta_parts = []
        if time_min:
            meta_parts.append(f"⏱ {time_min} min")
        if servings:
            meta_parts.append(f"Serves {servings}")
        if protein:
            meta_parts.append(f"💪 {protein}g protein")
        
        meta_text = " • ".join(meta_parts) if meta_parts else "Details coming..."
        meta = Paragraph(meta_text, self.styles['CardMeta'])
        
        # Ingredients section
        label = Paragraph("Ingredients", self.styles['CardLabel'])
        ing_lines = [Paragraph(f"• {i}", self.styles['Small']) for i in uses]
        
        if not ing_lines:
            ing_lines = [Paragraph("• See detailed recipe below", self.styles['Small'])]
        
        # Assemble card content
        inner = [header, meta, Spacer(1, 4), label, Spacer(1, 2)] + ing_lines
        
        # Keep content together
        kif = KeepInFrame(card_w - 16, card_h - 16, inner, 
                         hAlign='LEFT', vAlign='TOP', mode='shrink')
        
        # Create card with border
        card = Table([[kif]], colWidths=[card_w], rowHeights=[card_h])
        card.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#C8E6C9')),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        return card
    
    def build_meal_cards_grid(self, meals: List[Dict], doc, gutter: float = 12, card_h: float = 2.1*inch):
        """Build the 2-column grid of meal cards"""
        flow = []
        
        if not meals:
            return flow
        
        total_w = doc.width
        card_w = (total_w - gutter) / 2.0
        
        # Build all cards
        cards = []
        for i, meal in enumerate(meals[:6]):  # Cap at 6 for 3 rows
            cards.append(self.build_meal_card(meal, i+1, card_w, card_h))
        
        # Arrange in rows of 2
        rows = []
        it = iter(cards)
        for left in it:
            right = next(it, None)
            if right:
                rows.append([left, right])
            else:
                # Last card alone - add spacer for alignment
                rows.append([left, Spacer(card_w, card_h)])
        
        # Create the grid table
        grid = Table(rows, 
                    colWidths=[card_w, card_w], 
                    rowHeights=[card_h]*len(rows),
                    hAlign='LEFT',
                    spaceBefore=6, 
                    spaceAfter=6)
        
        grid.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))
        
        # Keep the entire grid together
        kif = KeepInFrame(doc.width, doc.height, [grid], 
                         mode='shrink', hAlign='LEFT')
        flow.append(kif)
        
        return flow
    
    def build_recommendation_box(self, title: str, bullets: List[str], reason: str):
        """Build a yellow callout box for recommendations"""
        
        title_p = Paragraph(title, self.styles['CalloutTitle'])
        
        # Create bullet list
        bullet_items = [ListItem(Paragraph(b, self.styles['Normal']), leftIndent=6) 
                       for b in bullets]
        bullet_list = ListFlowable(bullet_items, bulletType='bullet', 
                                   start='•', leftIndent=10, 
                                   spaceBefore=2, spaceAfter=2)
        
        reason_p = Paragraph(f"<i>{reason}</i>", self.styles['Small'])
        
        # Assemble the box
        inner = [[title_p], [bullet_list], [reason_p]]
        box = Table(inner, colWidths=[6.2*inch])
        box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFF9C4')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#F9A825')),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        return box
    
    def generate_smart_recommendations(self, meal_plan_data: Dict) -> Dict:
        """Generate dynamic recommendations based on the data"""
        
        # Analyze what's in the cart vs what's needed
        recommendations = {
            'title': 'Recommended Additions',
            'bullets': [],
            'reason': ''
        }
        
        # Check for protein gaps
        meals = meal_plan_data.get('meals', [])
        low_protein_count = sum(1 for m in meals 
                               if m.get('protein_per_serving', 0) < 30)
        
        if low_protein_count > 2:
            recommendations['bullets'].append(
                f"Add more protein sources - {low_protein_count} meals are under 30g protein"
            )
        
        # Check cart items
        cart_items = meal_plan_data.get('analysis_data', {}).get('individual_items', [])
        has_onions = any('onion' in item.get('name', '').lower() for item in cart_items)
        
        if not has_onions:
            recommendations['bullets'].append(
                "Consider adding onions - versatile aromatic for multiple dishes"
            )
        
        # Add a reason
        if recommendations['bullets']:
            recommendations['reason'] = "These additions will help you create more complete, balanced meals"
        else:
            recommendations['bullets'] = ["Your cart is well-balanced!"]
            recommendations['reason'] = "You have good coverage for the week"
        
        return recommendations
    
    def generate_pdf(self, meal_plan_data: Dict[str, Any], output_path: str) -> str:
        """Generate the enhanced PDF with card layout"""
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )
        
        story = []
        
        # Title
        story.append(Paragraph("🌱 Your Farm to People Meal Plan", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Cart Overview (if data available)
        if 'analysis_data' in meal_plan_data:
            story.extend(self.build_cart_overview(meal_plan_data['analysis_data']))
            story.append(Spacer(1, 10))
        
        # Smart Recommendations
        recs = self.generate_smart_recommendations(meal_plan_data)
        story.append(self.build_recommendation_box(
            recs['title'],
            recs['bullets'],
            recs['reason']
        ))
        story.append(Spacer(1, 14))
        
        # Meal Cards Grid
        story.append(Paragraph("Your Meal Plan", self.styles['SectionHeading']))
        story.extend(self.build_meal_cards_grid(
            meal_plan_data.get('meals', []), 
            doc,
            gutter=14,
            card_h=2.2*inch
        ))
        
        # Optional: Keep your detailed recipes after the cards
        if meal_plan_data.get('include_detailed_recipes', False):
            story.append(PageBreak())
            # Add your existing detailed recipe code here
            pass
        
        doc.build(story)
        return output_path
    
    def build_cart_overview(self, cart_data: Dict) -> List:
        """Build cart overview section"""
        out = []
        out.append(Paragraph("Current Cart Overview", self.styles['SectionHeading']))
        
        # Categorize items
        proteins, vegetables, fruits = [], [], []
        
        for item in cart_data.get('individual_items', []):
            name = item.get('name', '')
            lower_name = name.lower()
            
            # Smart categorization
            if any(word in lower_name for word in ['chicken', 'fish', 'salmon', 'eggs', 'beef', 'turkey', 'pork']):
                proteins.append(name)
            elif any(word in lower_name for word in ['apple', 'banana', 'peach', 'pear', 'plum', 'berries', 'melon']):
                fruits.append(name)
            else:
                vegetables.append(name)
        
        # Add sections
        if proteins:
            out.append(Paragraph("<b>Proteins:</b>", self.styles['Normal']))
            for p in proteins:
                out.append(Paragraph(f"• {p}", self.styles['Normal']))
            out.append(Spacer(1, 6))
        
        if vegetables:
            out.append(Paragraph("<b>Vegetables:</b>", self.styles['Normal']))
            for v in vegetables:
                out.append(Paragraph(f"• {v}", self.styles['Normal']))
            out.append(Spacer(1, 6))
        
        if fruits:
            out.append(Paragraph("<b>Fruits:</b>", self.styles['Normal']))
            for f in fruits:
                out.append(Paragraph(f"• {f}", self.styles['Normal']))
            out.append(Spacer(1, 6))
        
        return out


# Test it
if __name__ == "__main__":
    # Load sample data
    import json
    from pathlib import Path
    
    # Try to load real data
    data_file = Path("farm_box_data/customize_results_20250822_221218.json")
    if data_file.exists():
        with open(data_file, 'r') as f:
            cart_data = json.load(f)
    else:
        cart_data = {"individual_items": []}
    
    # Create test meal plan data
    test_data = {
        "analysis_data": cart_data,
        "meals": [
            {
                "title": "Mediterranean Chicken Bowl",
                "total_time": 30,
                "servings": 4,
                "protein_per_serving": 35,
                "base": {
                    "uses": ["Chicken Breast", "Cherry Tomatoes", "Cucumber", "Feta"]
                }
            },
            {
                "title": "Quick Salmon Stir-Fry",
                "total_time": 20,
                "servings": 2,
                "protein_per_serving": 32,
                "base": {
                    "uses": ["Salmon", "Zucchini", "Bell Peppers", "Garlic"]
                }
            },
            {
                "title": "Veggie Frittata",
                "total_time": 25,
                "servings": 3,
                "protein_per_serving": 18,
                "base": {
                    "uses": ["Eggs", "Spinach", "Mushrooms", "Cheese"]
                }
            },
            {
                "title": "Turkey Lettuce Wraps",
                "total_time": 15,
                "servings": 2,
                "protein_per_serving": 28,
                "base": {
                    "uses": ["Ground Turkey", "Lettuce", "Carrots", "Ginger"]
                }
            },
            {
                "title": "Sheet Pan Chicken",
                "total_time": 35,
                "servings": 4,
                "protein_per_serving": 40,
                "base": {
                    "uses": ["Chicken Thighs", "Brussels Sprouts", "Sweet Potatoes"]
                }
            }
        ]
    }
    
    # Generate PDF
    planner = EnhancedPDFMealPlanner()
    output = planner.generate_pdf(test_data, "enhanced_meal_plan.pdf")
    print(f"✅ Generated: {output}")
    print("\nFeatures:")
    print("• 2-column meal card grid")
    print("• Yellow recommendation boxes")
    print("• Cart overview section")
    print("• Dynamic content based on data")
    print("• No hardcoding - all from meal_plan_data")