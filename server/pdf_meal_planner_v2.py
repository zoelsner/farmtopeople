import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
    KeepInFrame, ListFlowable, ListItem, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
import meal_planner


class PDFMealPlannerV2:
    """Professional PDF meal planner following ChatGPT's design feedback"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Create professional styles with proper hierarchy"""
        
        # H1 - Main title (16-18pt)
        if 'H1' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='H1',
                parent=self.styles['Heading1'],
                fontSize=18,
                spaceAfter=12,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#2E7D32')  # Farm green
            ))
        
        # H2 - Section headings (13pt)
        if 'H2' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='H2',
                parent=self.styles['Heading2'],
                fontSize=13,
                spaceBefore=10,
                spaceAfter=6,
                textColor=colors.HexColor('#1B5E20'),
                leading=16
            ))
        
        # Body - Regular text (10-11pt)
        if 'Body' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='Body',
                parent=self.styles['Normal'],
                fontSize=10,
                spaceAfter=4,
                alignment=TA_LEFT,
                leading=12
            ))
        
        # Small - Meta text (8pt)
        if 'Small' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='Small',
                parent=self.styles['Normal'],
                fontSize=8,
                leading=10,
                textColor=colors.HexColor('#455A64')
            ))
        
        # KPI - Key metrics style
        if 'KPI' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='KPI',
                parent=self.styles['Normal'],
                fontSize=11,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#1B5E20'),
                spaceBefore=6,
                spaceAfter=10
            ))
        
        # Card styles
        if 'CardTitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CardTitle',
                fontSize=11,
                leading=13,
                textColor=colors.HexColor('#1B5E20'),
                spaceAfter=2
            ))
        
        if 'CardMeta' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CardMeta',
                fontSize=9,
                leading=11,
                textColor=colors.HexColor('#37474F')
            ))
        
        # Callout style for yellow boxes
        if 'CalloutTitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CalloutTitle',
                fontSize=11,
                textColor=colors.HexColor('#5D4037'),
                spaceAfter=4
            ))
    
    def calculate_kpis(self, meal_plan_data: Dict) -> Dict[str, Any]:
        """Calculate key performance indicators for the meal plan"""
        meals = meal_plan_data.get('meals', [])
        
        # Count meals by criteria
        quick_meals = sum(1 for m in meals if m.get('total_time', 999) <= 30)
        high_protein_meals = sum(1 for m in meals if m.get('protein_per_serving', 0) >= 30)
        
        # Calculate cart utilization
        cart_items = set()
        for item in meal_plan_data.get('analysis_data', {}).get('individual_items', []):
            cart_items.add(item.get('name', '').lower())
        
        used_items = set()
        for meal in meals:
            for ingredient in meal.get('base', {}).get('uses', []):
                used_items.add(ingredient.lower())
        
        cart_utilization = int((len(used_items) / max(len(cart_items), 1)) * 100)
        
        return {
            'total_servings': meal_plan_data.get('total_estimated_servings', 0),
            'meal_count': len(meals),
            'quick_meals': quick_meals,
            'high_protein_meals': high_protein_meals,
            'cart_utilization': cart_utilization
        }
    
    def build_kpi_strip(self, kpis: Dict) -> Paragraph:
        """Build the KPI strip for instant value"""
        kpi_text = (
            f"<b>{kpis['total_servings']} servings</b> • "
            f"<b>{kpis['meal_count']} meals</b> • "
            f"<b>{kpis['quick_meals']} dinners ≤30 min</b> • "
            f"<b>{kpis['high_protein_meals']} meals ≥30g protein</b> • "
            f"<b>{kpis['cart_utilization']}% cart utilization</b>"
        )
        return Paragraph(kpi_text, self.styles['KPI'])
    
    def analyze_cart_gaps(self, meal_plan_data: Dict) -> Tuple[float, List[str]]:
        """Analyze cart readiness and identify gaps"""
        # Simple scoring based on categories present
        cart_items = meal_plan_data.get('analysis_data', {}).get('individual_items', [])
        
        has_protein = any('chicken' in item.get('name', '').lower() or 
                         'salmon' in item.get('name', '').lower() or
                         'eggs' in item.get('name', '').lower() 
                         for item in cart_items)
        
        has_aromatics = any('onion' in item.get('name', '').lower() or 
                           'garlic' in item.get('name', '').lower() 
                           for item in cart_items)
        
        has_greens = any('spinach' in item.get('name', '').lower() or 
                        'lettuce' in item.get('name', '').lower() or
                        'kale' in item.get('name', '').lower() 
                        for item in cart_items)
        
        score = sum([has_protein * 2, has_aromatics * 1.5, has_greens * 1.5])
        
        gaps = []
        if not has_aromatics:
            gaps.append("alliums (onion/garlic)")
        if not has_greens:
            gaps.append("leafy greens")
        if score < 3:
            gaps.append("second lean protein")
        
        return min(score, 5.0), gaps[:3]  # Return top 3 gaps
    
    def build_priority_recommendations(self, meal_plan_data: Dict) -> List:
        """Build yellow callout boxes with actionable recommendations"""
        elements = []
        
        # Analyze what's needed
        meals = meal_plan_data.get('meals', [])
        low_protein_count = sum(1 for m in meals if m.get('protein_per_serving', 0) < 30)
        
        cart_items = meal_plan_data.get('analysis_data', {}).get('individual_items', [])
        has_onions = any('onion' in item.get('name', '').lower() for item in cart_items)
        
        recommendations = []
        
        if not has_onions:
            recommendations.append({
                'title': 'Add onions',
                'why': 'Unlocks 3 salsas and 2 stews',
                'cost': 'Est. $1.29'
            })
        
        if low_protein_count > 2:
            recommendations.append({
                'title': 'Add second protein',
                'why': f'Lifts {low_protein_count} meals above 30g protein',
                'cost': 'Est. $6-$10'
            })
        
        # Create yellow boxes for each recommendation
        for rec in recommendations[:2]:  # Max 2 recommendations
            data = [
                [Paragraph(f"<b>{rec['title']}</b>", self.styles['CalloutTitle'])],
                [Paragraph(rec['why'], self.styles['Small'])],
                [Paragraph(rec['cost'], self.styles['Small'])]
            ]
            
            box = Table(data, colWidths=[3*inch])
            box.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFF9C4')),
                ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#F9A825')),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(box)
        
        # Arrange recommendations side by side if we have 2
        if len(elements) == 2:
            combined = Table([[elements[0], elements[1]]], 
                           colWidths=[3.1*inch, 3.1*inch])
            combined.setStyle(TableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            return [combined]
        
        return elements
    
    def build_meal_card_v2(self, meal: Dict, index: int, card_w: float, card_h: float):
        """Build an improved meal card with tags"""
        
        title = meal.get('title', 'Untitled')
        time_min = meal.get('total_time', meal.get('cook_time', ''))
        servings = meal.get('servings', meal.get('estimated_servings', ''))
        protein = meal.get('protein_per_serving', 0)
        
        # Get top 3-4 ingredients only
        uses = []
        if 'base' in meal and 'uses' in meal.get('base', {}):
            uses = meal['base']['uses'][:3]
        
        # Determine tags
        tags = []
        if time_min and time_min <= 20:
            tags.append("quick")
        elif time_min and time_min <= 30:
            tags.append("30-min")
        if 'sheet' in title.lower():
            tags.append("sheet-pan")
        if protein >= 30:
            tags.append("high-protein")
        
        # Build card content
        header = Paragraph(f"<b>{index}. {title}</b>", self.styles['CardTitle'])
        
        # Meta line with better formatting
        meta_text = f"{time_min} min • Serves {servings} • {protein}g protein"
        meta = Paragraph(meta_text, self.styles['CardMeta'])
        
        # Ingredients (shorter)
        ing_text = " • ".join(uses) if uses else "See recipe"
        ingredients = Paragraph(ing_text, self.styles['Small'])
        
        # Tags
        tag_text = " • ".join(tags) if tags else ""
        tag_para = Paragraph(f"<i>{tag_text}</i>", self.styles['Small'])
        
        # Assemble
        inner = [header, meta, Spacer(1, 2), ingredients]
        if tag_text:
            inner.append(Spacer(1, 2))
            inner.append(tag_para)
        
        # Keep together
        kif = KeepInFrame(card_w - 12, card_h - 12, inner, 
                         hAlign='LEFT', vAlign='TOP', mode='shrink')
        
        # Card with subtle border
        card = Table([[kif]], colWidths=[card_w], rowHeights=[card_h])
        card.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#E0E0E0')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        return card
    
    def build_meal_grid_v2(self, meals: List[Dict], doc):
        """Build improved 2-column meal grid sorted by time"""
        flow = []
        
        if not meals:
            return flow
        
        # Sort meals by time (quickest first)
        sorted_meals = sorted(meals, key=lambda x: x.get('total_time', 999))
        
        total_w = doc.width
        card_w = (total_w - 10) / 2.0
        card_h = 1.8 * inch  # Slightly smaller for cleaner look
        
        # Build cards
        cards = []
        for i, meal in enumerate(sorted_meals[:6], 1):
            cards.append(self.build_meal_card_v2(meal, i, card_w, card_h))
        
        # Create rows
        rows = []
        it = iter(cards)
        for left in it:
            right = next(it, None)
            if right:
                rows.append([left, right])
            else:
                rows.append([left, Spacer(card_w, card_h)])
        
        # Grid table
        grid = Table(rows, 
                    colWidths=[card_w, card_w], 
                    rowHeights=[card_h]*len(rows),
                    hAlign='LEFT',
                    spaceBefore=6, 
                    spaceAfter=10)
        
        grid.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        # Keep together
        flow.append(KeepTogether([grid]))
        
        return flow
    
    def build_shopping_gaps(self, gaps: List[str]) -> List:
        """Build concise shopping gaps section"""
        elements = []
        
        if gaps:
            elements.append(Paragraph("<b>Shopping Gaps</b>", self.styles['H2']))
            
            gap_items = []
            for gap in gaps:
                if gap == "alliums (onion/garlic)":
                    gap_items.append("• Onions/garlic - essential aromatics ($2-3)")
                elif gap == "leafy greens":
                    gap_items.append("• Spinach/kale - adds nutrition ($3-4)")
                elif gap == "second lean protein":
                    gap_items.append("• Extra protein - more meal variety ($8-12)")
                else:
                    gap_items.append(f"• {gap}")
            
            for item in gap_items:
                elements.append(Paragraph(item, self.styles['Body']))
            
            elements.append(Spacer(1, 10))
        
        return elements
    
    def build_recipe_v2(self, meal: Dict, index: int) -> List:
        """Build a precise, actionable recipe section"""
        elements = []
        
        # Title with tags
        title = meal.get('title', 'Untitled Recipe')
        time_min = meal.get('total_time', 30)
        servings = meal.get('estimated_servings', 2)
        protein = meal.get('protein_per_serving', 0)
        
        # Determine tags
        tags = []
        if time_min <= 20:
            tags.append("quick")
        if 'sheet' in title.lower():
            tags.append("sheet-pan")
        if protein >= 30:
            tags.append("meal-prep")
        
        tag_text = f" [{', '.join(tags)}]" if tags else ""
        
        elements.append(Paragraph(f"<b>{index}. {title}</b>{tag_text}", self.styles['H2']))
        
        # Quick stats line
        stats = f"{time_min} min • Serves {servings} • {protein}g protein per serving"
        elements.append(Paragraph(stats, self.styles['Small']))
        elements.append(Spacer(1, 6))
        
        # Ingredients split into "From your box" and "Pantry"
        base_uses = meal.get('base', {}).get('uses', [])
        
        if base_uses:
            # Assume first 3-4 are from box, rest are pantry (simplified)
            box_items = base_uses[:3]
            pantry_items = base_uses[3:] if len(base_uses) > 3 else []
            
            elements.append(Paragraph("<b>From your box:</b>", self.styles['Body']))
            for item in box_items:
                elements.append(Paragraph(f"• {item}", self.styles['Body']))
            
            if pantry_items:
                elements.append(Spacer(1, 4))
                elements.append(Paragraph("<b>Pantry:</b>", self.styles['Body']))
                for item in pantry_items:
                    elements.append(Paragraph(f"• {item}", self.styles['Body']))
        
        elements.append(Spacer(1, 6))
        
        # Precise cooking steps
        elements.append(Paragraph("<b>Steps:</b>", self.styles['Body']))
        
        # Generate better steps based on meal type
        if 'stir' in title.lower() or 'fry' in title.lower():
            steps = [
                "Heat 2 Tbsp oil in large skillet over <b>medium-high heat</b>",
                f"Season protein with salt and pepper. Cook <b>4-5 min</b> per side to <b>165°F</b>",
                "Remove protein, add vegetables with 1 Tbsp oil",
                f"Stir-fry <b>3-4 min</b> until crisp-tender",
                "Return protein, add sauce, toss <b>1 min</b>",
                "Rest <b>2 min</b> before serving"
            ]
        elif 'sheet' in title.lower() or 'bake' in title.lower():
            steps = [
                "Preheat oven to <b>425°F</b>",
                "Line sheet pan with parchment",
                "Toss vegetables with 2 Tbsp oil, salt, pepper",
                f"Arrange on pan, bake <b>15 min</b>",
                f"Add protein, bake <b>15-20 min</b> to <b>165°F internal</b>",
                "Rest <b>5 min</b> before serving"
            ]
        else:
            steps = [
                f"Prep all ingredients (mise en place)",
                f"Heat pan to <b>medium-high</b>",
                f"Cook protein to <b>165°F internal</b>",
                f"Add vegetables, cook until tender",
                f"Season and serve immediately"
            ]
        
        for i, step in enumerate(steps, 1):
            elements.append(Paragraph(f"{i}. {step}", self.styles['Body']))
        
        # Pro tip
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(
            "<b>Pro tip:</b> <i>Prep all ingredients before starting. "
            "This recipe reheats well for meal prep.</i>", 
            self.styles['Small']
        ))
        
        elements.append(Spacer(1, 14))
        
        return elements
    
    def build_condensed_storage_guide(self, meal_plan_data: Dict) -> List:
        """Build a condensed 3-column storage table"""
        elements = []
        
        elements.append(Paragraph("Appendix A: Storage Guide", self.styles['H2']))
        elements.append(Spacer(1, 6))
        
        # Get unique ingredients
        all_ingredients = set()
        for meal in meal_plan_data.get('meals', []):
            all_ingredients.update(meal.get('base', {}).get('uses', []))
        
        # Build condensed table
        storage_data = [['Item', 'How to Store', 'Shelf Life']]
        
        # Only include items we know about
        storage_map = {
            'Chicken': ('Refrigerate at 40°F', '1-2 days'),
            'Salmon': ('Coldest part of fridge', '1-2 days'),
            'Eggs': ('In carton, refrigerated', '3-5 weeks'),
            'Spinach': ('Crisper drawer', '5-7 days'),
            'Tomatoes': ('Room temp if ripe', '3-5 days'),
            'Zucchini': ('Refrigerate in bag', '4-5 days'),
        }
        
        for ingredient in sorted(all_ingredients):
            # Try to match known items
            for key, (storage, life) in storage_map.items():
                if key.lower() in ingredient.lower():
                    storage_data.append([ingredient[:20], storage, life])
                    break
        
        if len(storage_data) > 1:
            table = Table(storage_data, colWidths=[2*inch, 2.5*inch, 1.5*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F5F5F5')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            elements.append(table)
        
        return elements
    
    def generate_pdf(self, meal_plan_data: Dict[str, Any], output_path: str) -> str:
        """Generate professional PDF following information architecture"""
        
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=36,
            bottomMargin=36
        )
        
        story = []
        
        # 1. Title + KPI Strip
        story.append(Paragraph("🌱 Your Farm to People Meal Plan", self.styles['H1']))
        
        kpis = self.calculate_kpis(meal_plan_data)
        story.append(self.build_kpi_strip(kpis))
        story.append(Spacer(1, 10))
        
        # 2. Priority Recommendations (yellow callouts)
        recommendations = self.build_priority_recommendations(meal_plan_data)
        if recommendations:
            story.extend(recommendations)
            story.append(Spacer(1, 14))
        
        # 3. Strategic Meal Plan (2-column cards)
        story.append(Paragraph("Strategic Meal Plan", self.styles['H2']))
        story.append(Paragraph(
            "<i>Sorted by cooking time - start with the quickest</i>", 
            self.styles['Small']
        ))
        story.append(Spacer(1, 6))
        story.extend(self.build_meal_grid_v2(meal_plan_data.get('meals', []), doc))
        
        # 4. Shopping Gaps
        cart_score, gaps = self.analyze_cart_gaps(meal_plan_data)
        if gaps:
            story.extend(self.build_shopping_gaps(gaps))
        
        # 5. Cart Readiness Score (collapsed overview)
        story.append(Paragraph("Cart Overview", self.styles['H2']))
        score_text = f"Cart readiness: {cart_score:.1f}/5.0"
        story.append(Paragraph(score_text, self.styles['Body']))
        
        if gaps:
            gap_text = f"You are light on: {', '.join(gaps)}"
            story.append(Paragraph(gap_text, self.styles['Small']))
        story.append(Spacer(1, 14))
        
        # Page break before recipes
        story.append(PageBreak())
        
        # 6. Recipes (precise and actionable)
        story.append(Paragraph("Detailed Recipes", self.styles['H1']))
        story.append(Spacer(1, 10))
        
        sorted_meals = sorted(
            meal_plan_data.get('meals', []), 
            key=lambda x: x.get('total_time', 999)
        )
        
        for i, meal in enumerate(sorted_meals, 1):
            recipe_elements = self.build_recipe_v2(meal, i)
            story.extend(recipe_elements)
        
        # 7. Appendix A: Storage Guide
        story.append(PageBreak())
        storage_elements = self.build_condensed_storage_guide(meal_plan_data)
        story.extend(storage_elements)
        
        # Build the PDF
        doc.build(story)
        
        return output_path


# Test it
if __name__ == "__main__":
    # Test data with better structure
    test_data = {
        "analysis_data": {
            "individual_items": [
                {"name": "Organic Chicken Breast", "quantity": 2},
                {"name": "Wild Salmon", "quantity": 1},
                {"name": "Eggs", "quantity": 12},
                {"name": "Zucchini", "quantity": 3},
                {"name": "Cherry Tomatoes", "quantity": 2},
                {"name": "Spinach", "quantity": 1}
            ]
        },
        "total_estimated_servings": 22,
        "meals": [
            {
                "title": "Mediterranean Chicken Bowl",
                "total_time": 25,
                "estimated_servings": 4,
                "protein_per_serving": 42,
                "base": {
                    "uses": ["Chicken Breast", "Tomatoes", "Spinach", "Olive Oil", "Lemon"]
                }
            },
            {
                "title": "Quick Salmon Stir-Fry",
                "total_time": 15,
                "estimated_servings": 2,
                "protein_per_serving": 38,
                "base": {
                    "uses": ["Salmon", "Zucchini", "Soy Sauce", "Ginger", "Garlic"]
                }
            },
            {
                "title": "Protein-Packed Frittata",
                "total_time": 20,
                "estimated_servings": 4,
                "protein_per_serving": 31,
                "base": {
                    "uses": ["Eggs", "Spinach", "Cheese", "Milk"]
                }
            },
            {
                "title": "Sheet Pan Chicken",
                "total_time": 35,
                "estimated_servings": 4,
                "protein_per_serving": 40,
                "base": {
                    "uses": ["Chicken Thighs", "Zucchini", "Tomatoes", "Olive Oil"]
                }
            },
            {
                "title": "Egg Scramble Deluxe",
                "total_time": 10,
                "estimated_servings": 2,
                "protein_per_serving": 24,
                "base": {
                    "uses": ["Eggs", "Spinach", "Tomatoes", "Butter"]
                }
            }
        ]
    }
    
    planner = PDFMealPlannerV2()
    output = planner.generate_pdf(test_data, "meal_plan_professional.pdf")
    print(f"✅ Generated: {output}")
    print("\nImprovements based on feedback:")
    print("• KPI strip with instant value metrics")
    print("• Priority recommendations with cost/impact")
    print("• Meals sorted by cooking time")
    print("• Precise cooking steps with temps/times")
    print("• Condensed storage guide")
    print("• Professional typography and spacing")