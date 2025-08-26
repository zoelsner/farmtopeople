import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
    KeepInFrame, ListFlowable, ListItem
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import meal_planner


class PDFMealPlanner:
    """Generate beautiful PDF meal plans with storage tips and detailed recipes"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Create custom styles for the PDF"""
        # Main title style
        if 'CustomTitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CustomTitle',
                parent=self.styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#2E7D32')  # Farm green
            ))
        
        # Section heading style
        if 'SectionHeading' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='SectionHeading',
                parent=self.styles['Heading2'],
                fontSize=16,
                spaceBefore=20,
                spaceAfter=12,
                textColor=colors.HexColor('#388E3C'),
                borderWidth=1,
                borderColor=colors.HexColor('#C8E6C9'),
                borderPadding=8,
                backColor=colors.HexColor('#F1F8E9')
            ))
        
        # Recipe title style
        if 'RecipeTitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='RecipeTitle',
                parent=self.styles['Heading3'],
                fontSize=14,
                spaceBefore=15,
                spaceAfter=8,
                textColor=colors.HexColor('#1B5E20'),
                leftIndent=10
            ))
        
        # Body text with better spacing
        if 'CustomBodyText' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CustomBodyText',
                parent=self.styles['Normal'],
                fontSize=11,
                spaceAfter=6,
                alignment=TA_JUSTIFY,
                leftIndent=10,
                rightIndent=10
            ))
        
        # Ingredients list style
        if 'IngredientsList' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='IngredientsList',
                parent=self.styles['Normal'],
                fontSize=10,
                spaceAfter=4,
                leftIndent=20,
                bulletIndent=10
            ))
        
        # Card-specific styles for meal grid
        if 'CardTitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CardTitle',
                parent=self.styles['Heading3'],
                fontSize=12, leading=14,
                textColor=colors.HexColor('#1B5E20'),
                spaceAfter=4
            ))
        
        if 'CardMeta' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CardMeta',
                parent=self.styles['Normal'],
                fontSize=9, leading=11,
                textColor=colors.HexColor('#455A64')
            ))
        
        if 'CardLabel' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CardLabel',
                parent=self.styles['Normal'],
                fontSize=9, leading=11,
                textColor=colors.HexColor('#2E7D32')
            ))
        
        if 'Small' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='Small',
                parent=self.styles['Normal'],
                fontSize=8, leading=10,
                textColor=colors.HexColor('#37474F')
            ))
        
        if 'CalloutTitle' not in self.styles:
            self.styles.add(ParagraphStyle(
                name='CalloutTitle',
                parent=self.styles['Heading3'],
                fontSize=12,
                textColor=colors.HexColor('#684e00')
            ))

    def get_storage_tips(self, ingredient: str) -> str:
        """Get storage tips for ingredients"""
        storage_guide = {
            # Proteins
            "chicken": "Refrigerate at 40°F or below. Use within 1-2 days or freeze for up to 9 months.",
            "fish": "Store in coldest part of refrigerator. Use within 1-2 days or freeze immediately.",
            "salmon": "Store in coldest part of refrigerator. Use within 1-2 days or freeze immediately.",
            "eggs": "Refrigerate in original carton. Good for 3-5 weeks past purchase date.",
            
            # Vegetables - Refrigerated
            "avocado": "Ripen at room temperature, then refrigerate. Use within 3-5 days when ripe.",
            "tomato": "Store ripe tomatoes at room temperature. Cherry tomatoes can be refrigerated.",
            "lettuce": "Wrap in paper towels, store in crisper drawer. Lasts 7-10 days.",
            "cucumber": "Refrigerate in crisper drawer. Use within 1 week.",
            "zucchini": "Refrigerate in plastic bag. Use within 4-5 days.",
            "eggplant": "Store at room temperature if using within 2 days, otherwise refrigerate.",
            "peppers": "Refrigerate in crisper drawer. Bell peppers last 1-2 weeks.",
            "asparagus": "Store upright in water like flowers, cover tops with plastic bag. Use within 3-4 days.",
            
            # Fruits
            "banana": "Store at room temperature. Separate from other fruits to slow ripening.",
            "peaches": "Ripen at room temperature, then refrigerate. Use within 3-5 days when ripe.",
            "plums": "Ripen at room temperature, refrigerate when soft. Last 3-5 days ripe.",
            "lemon": "Store at room temperature for 1 week or refrigerate for up to 1 month.",
            "lemons": "Store at room temperature for 1 week or refrigerate for up to 1 month.",
            
            # Dairy & Pantry
            "butter": "Refrigerate in original wrapper. Can freeze for 6-9 months.",
            
            # Herbs & Aromatics  
            "basil": "Store like fresh flowers in water at room temperature. Avoid refrigeration.",
            "garlic": "Store in cool, dry place with good air circulation. Lasts 3-5 months.",
            "ginger": "Refrigerate in paper bag. Freeze for longer storage.",
        }
        
        # Find matching storage tip
        ingredient_lower = ingredient.lower()
        for key, tip in storage_guide.items():
            if key in ingredient_lower:
                return tip
        
        # Default tips based on ingredient type
        if any(word in ingredient_lower for word in ['organic', 'fresh', 'herb']):
            return "Store in refrigerator crisper drawer. Use within 5-7 days for best quality."
        elif 'meat' in ingredient_lower or 'fish' in ingredient_lower:
            return "Keep refrigerated at 40°F or below. Use within 1-2 days or freeze immediately."
        else:
            return "Store according to package directions. Keep in cool, dry place."

    def expand_recipe_details(self, meal: Dict[str, Any]) -> Dict[str, Any]:
        """Expand basic meal info into detailed recipe"""
        # Check if this meal already has AI-generated recipe details
        if 'mise_en_place' in meal and 'cooking_instructions' in meal:
            # Already has detailed recipe from AI
            return meal
            
        # Otherwise use the old template approach as fallback
        expanded = meal.copy()
        
        # Add detailed cooking steps based on meal title and ingredients
        base_uses = meal.get('base', {}).get('uses', [])
        title = meal.get('title', '')
        
        # Generate detailed steps based on ingredients and cooking method
        if 'grilled' in title.lower():
            steps = [
                "Preheat grill or grill pan to medium-high heat",
                f"Season {base_uses[0] if base_uses else 'protein'} with salt, pepper, and olive oil",
                "Grill protein for 4-6 minutes per side until cooked through",
                "Prepare vegetables while protein cooks",
                "Let protein rest 5 minutes before serving",
                "Combine all ingredients and serve immediately"
            ]
        elif 'stir-fry' in title.lower():
            steps = [
                "Heat 2 tablespoons oil in large skillet or wok over high heat",
                "Cut all vegetables into uniform pieces",
                f"Add {base_uses[0] if base_uses else 'protein'} to hot pan, cook until nearly done",
                "Add vegetables in order of cooking time (longest first)",
                "Stir frequently, cook until vegetables are crisp-tender",
                "Season with salt, pepper, and your favorite sauce"
            ]
        elif 'bake' in title.lower():
            steps = [
                "Preheat oven to 400°F (200°C)",
                "Prepare all ingredients and arrange in baking dish",
                "Drizzle with olive oil and season generously",
                "Bake for 25-30 minutes until vegetables are tender",
                "Check doneness and adjust seasoning",
                "Let rest 5 minutes before serving"
            ]
        else:
            # Default cooking steps
            steps = [
                "Prepare all ingredients (wash, chop, measure)",
                f"Cook {base_uses[0] if base_uses else 'main ingredient'} according to preference",
                "Combine with remaining ingredients",
                "Season with salt, pepper, and herbs",
                "Serve immediately while hot"
            ]
        
        expanded['detailed_steps'] = steps
        
        # Add cooking tips
        tips = []
        if any('fish' in ingredient.lower() for ingredient in base_uses):
            tips.append("Don't overcook fish - it should flake easily with a fork")
        if any('chicken' in ingredient.lower() for ingredient in base_uses):
            tips.append("Use meat thermometer - chicken is done at 165°F internal temperature")
        if any('avocado' in ingredient.lower() for ingredient in base_uses):
            tips.append("Add avocado at the end to prevent browning")
        
        expanded['cooking_tips'] = tips
        
        # Add estimated nutritional benefits
        nutrition_notes = []
        if any('fish' in ingredient.lower() for ingredient in base_uses):
            nutrition_notes.append("Rich in omega-3 fatty acids and lean protein")
        if any('avocado' in ingredient.lower() for ingredient in base_uses):
            nutrition_notes.append("High in healthy monounsaturated fats and fiber")
        if any('tomato' in ingredient.lower() for ingredient in base_uses):
            nutrition_notes.append("Excellent source of lycopene and vitamin C")
        
        expanded['nutrition_notes'] = nutrition_notes
        
        return expanded
    
    def build_meal_card(self, meal: Dict, index: int, card_w: float, card_h: float):
        """Build a single meal card for the grid layout"""
        
        # Extract data flexibly from meal structure
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
        
        # Check for variety
        if len(meals) < 5:
            recommendations['bullets'].append(
                "Consider adding more meals for better weekly variety"
            )
        
        # Add a reason
        if recommendations['bullets']:
            recommendations['reason'] = "These additions will help you create more complete, balanced meals"
        else:
            recommendations['bullets'] = ["Your cart is well-balanced!"]
            recommendations['reason'] = "You have good coverage for the week"
        
        return recommendations
    
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

    def generate_pdf(self, meal_plan_data: Dict[str, Any], output_path: str) -> str:
        """Generate the complete PDF meal plan with enhanced layout"""
        
        # Create the PDF document with slightly adjusted margins for better card layout
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=54,
            leftMargin=54,
            topMargin=54,
            bottomMargin=54
        )
        
        # Container for all content
        story = []
        
        # Title page
        story.append(Paragraph("🌱 Your Farm to People Meal Plan", self.styles['CustomTitle']))
        story.append(Spacer(1, 20))
        
        # Date and summary
        date_str = datetime.now().strftime("%B %d, %Y")
        story.append(Paragraph(f"Generated on {date_str}", self.styles['Normal']))
        story.append(Spacer(1, 10))
        
        total_servings = meal_plan_data.get('total_estimated_servings', 0)
        story.append(Paragraph(f"Total estimated servings: {total_servings}", self.styles['Normal']))
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
        
        # Meal Cards Grid - New visual summary
        story.append(Paragraph("Your Meal Plan Overview", self.styles['SectionHeading']))
        story.append(Spacer(1, 10))
        story.extend(self.build_meal_cards_grid(
            meal_plan_data.get('meals', []), 
            doc,
            gutter=14,
            card_h=2.2*inch
        ))
        story.append(PageBreak())
        
        # Ingredients Storage Guide Section
        story.append(Paragraph("📦 Ingredient Storage Guide", self.styles['SectionHeading']))
        story.append(Spacer(1, 10))
        
        # Get all unique ingredients
        all_ingredients = set()
        for meal in meal_plan_data.get('meals', []):
            all_ingredients.update(meal.get('base', {}).get('uses', []))
            for level_up in meal.get('level_ups', []):
                all_ingredients.update(level_up.get('uses', []))
        
        # Add ingredients from cart analysis if available
        if 'analysis_data' in meal_plan_data:
            analysis = meal_plan_data['analysis_data']
            for item in analysis.get('individual_items', []):
                all_ingredients.add(item.get('name', ''))
        
        # Create storage tips table
        storage_data = [['Ingredient', 'Storage Tips']]
        for ingredient in sorted(all_ingredients):
            if ingredient:  # Skip empty ingredients
                storage_tip = self.get_storage_tips(ingredient)
                storage_data.append([ingredient, storage_tip])
        
        if len(storage_data) > 1:  # Only create table if we have data
            storage_table = Table(storage_data, colWidths=[2.5*inch, 4*inch])
            storage_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E8F5E8')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#C8E6C9'))
            ]))
            story.append(storage_table)
            story.append(PageBreak())
        
        # Recipes Section
        story.append(Paragraph("🍳 Your Meal Recipes", self.styles['SectionHeading']))
        story.append(Spacer(1, 15))
        
        for i, meal in enumerate(meal_plan_data.get('meals', [])):
            expanded_meal = self.expand_recipe_details(meal)
            
            # Recipe title
            story.append(Paragraph(f"{i+1}. {expanded_meal.get('title', 'Untitled Recipe')}", 
                                 self.styles['RecipeTitle']))
            story.append(Spacer(1, 8))
            
            # Servings and time
            servings = expanded_meal.get('estimated_servings', 2)
            story.append(Paragraph(f"<b>Serves:</b> {servings} people", self.styles['CustomBodyText']))
            story.append(Spacer(1, 5))
            
            # Ingredients section
            story.append(Paragraph("<b>Ingredients:</b>", self.styles['CustomBodyText']))
            base_uses = expanded_meal.get('base', {}).get('uses', [])
            for ingredient in base_uses:
                story.append(Paragraph(f"• {ingredient}", self.styles['IngredientsList']))
            
            # Level-ups (optional ingredients)
            level_ups = expanded_meal.get('level_ups', [])
            if level_ups:
                story.append(Spacer(1, 8))
                story.append(Paragraph("<b>Optional Level-ups:</b>", self.styles['CustomBodyText']))
                for level_up in level_ups:
                    level_up_text = f"• {level_up.get('name', '')} (+{level_up.get('adds_minutes', 0)} min)"
                    if level_up.get('uses'):
                        level_up_text += f" - uses: {', '.join(level_up.get('uses', []))}"
                    story.append(Paragraph(level_up_text, self.styles['IngredientsList']))
            
            story.append(Spacer(1, 10))
            
            # Cooking instructions - check for AI-generated vs template
            if 'cooking_instructions' in expanded_meal:
                # Use AI-generated professional instructions
                story.append(Paragraph("<b>Instructions:</b>", self.styles['CustomBodyText']))
                
                for instruction in expanded_meal.get('cooking_instructions', []):
                    # Step title and main instruction
                    step_text = f"<b>{instruction['step_number']}. {instruction['title']}</b><br/>"
                    step_text += f"{instruction['instructions']}<br/>"
                    
                    # Add timing and temperature
                    if instruction.get('time'):
                        step_text += f"<i>Time: {instruction['time']}</i><br/>"
                    if instruction.get('temperature'):
                        step_text += f"<i>Temperature: {instruction['temperature']}</i><br/>"
                    
                    # Add sensory cues
                    if instruction.get('sensory_cues'):
                        step_text += f"<i>Look for: {instruction['sensory_cues']}</i><br/>"
                    
                    story.append(Paragraph(step_text, self.styles['CustomBodyText']))
                    
                    # Add why this matters (in smaller text)
                    if instruction.get('why'):
                        story.append(Paragraph(f"💡 <i>{instruction['why']}</i>", 
                                             self.styles['IngredientsList']))
                    
                    # Add troubleshooting tips
                    if instruction.get('troubleshooting'):
                        story.append(Paragraph(f"⚠️ <i>{instruction['troubleshooting']}</i>", 
                                             self.styles['IngredientsList']))
                    
                    story.append(Spacer(1, 8))
                    
                # Add mise en place section if available
                if 'mise_en_place' in expanded_meal:
                    story.append(Spacer(1, 10))
                    story.append(Paragraph("<b>Mise en Place (Prep):</b>", self.styles['CustomBodyText']))
                    for prep in expanded_meal['mise_en_place']:
                        prep_text = f"• <b>{prep['ingredient']}</b>: {prep['prep']}"
                        if prep.get('knife_cut'):
                            prep_text += f" ({prep['knife_cut']})"
                        if prep.get('notes'):
                            prep_text += f" - <i>{prep['notes']}</i>"
                        story.append(Paragraph(prep_text, self.styles['IngredientsList']))
                        
            else:
                # Fallback to template-based instructions
                story.append(Paragraph("<b>Instructions:</b>", self.styles['CustomBodyText']))
                for j, step in enumerate(expanded_meal.get('detailed_steps', []), 1):
                    story.append(Paragraph(f"{j}. {step}", self.styles['CustomBodyText']))
            
            # Chef notes and tips (AI-generated)
            if 'chef_notes' in expanded_meal:
                chef_notes = expanded_meal['chef_notes']
                
                # Make ahead tips
                if chef_notes.get('make_ahead'):
                    story.append(Spacer(1, 8))
                    story.append(Paragraph("<b>⏰ Make Ahead:</b>", self.styles['CustomBodyText']))
                    story.append(Paragraph(chef_notes['make_ahead'], self.styles['IngredientsList']))
                
                # Variations
                if chef_notes.get('variations'):
                    story.append(Spacer(1, 8))
                    story.append(Paragraph("<b>🔄 Variations:</b>", self.styles['CustomBodyText']))
                    story.append(Paragraph(chef_notes['variations'], self.styles['IngredientsList']))
                    
                # Plating tips
                if chef_notes.get('plating'):
                    story.append(Spacer(1, 8))
                    story.append(Paragraph("<b>🍽️ Plating:</b>", self.styles['CustomBodyText']))
                    story.append(Paragraph(chef_notes['plating'], self.styles['IngredientsList']))
                    
            else:
                # Fallback to template tips
                cooking_tips = expanded_meal.get('cooking_tips', [])
                if cooking_tips:
                    story.append(Spacer(1, 8))
                    story.append(Paragraph("<b>💡 Cooking Tips:</b>", self.styles['CustomBodyText']))
                    for tip in cooking_tips:
                        story.append(Paragraph(f"• {tip}", self.styles['IngredientsList']))
            
            # Nutrition notes
            nutrition_notes = expanded_meal.get('nutrition_notes', [])
            if nutrition_notes:
                story.append(Spacer(1, 8))
                story.append(Paragraph("<b>🥗 Nutrition Highlights:</b>", self.styles['CustomBodyText']))
                for note in nutrition_notes:
                    story.append(Paragraph(f"• {note}", self.styles['IngredientsList']))
            
            # Swaps section
            swaps = expanded_meal.get('swaps', [])
            if swaps:
                story.append(Spacer(1, 8))
                story.append(Paragraph("<b>🔄 Smart Swaps:</b>", self.styles['CustomBodyText']))
                for swap in swaps:
                    swap_text = f"• If {swap.get('if_oos', '')} is unavailable, use {swap.get('use', '')}"
                    story.append(Paragraph(swap_text, self.styles['IngredientsList']))
            
            # Add spacing between recipes
            story.append(Spacer(1, 20))
        
        # Shopping additions section
        farm_additions = meal_plan_data.get('farm_to_people_additions', [])
        if farm_additions:
            story.append(PageBreak())
            story.append(Paragraph("🛒 Recommended Additions to Your Cart", self.styles['SectionHeading']))
            story.append(Spacer(1, 10))
            
            total_cost = 0
            for addition in farm_additions:
                item_name = addition.get('item', '')
                quantity = addition.get('quantity', '')
                price = addition.get('price', 'Price TBD')
                usage = addition.get('usage', '')
                
                story.append(Paragraph(f"<b>{item_name}</b> ({quantity})", self.styles['CustomBodyText']))
                story.append(Paragraph(f"Price: {price}", self.styles['Normal']))
                story.append(Paragraph(f"Usage: {usage}", self.styles['Normal']))
                story.append(Spacer(1, 8))
                
                # Try to extract price for total
                if price.startswith('$'):
                    try:
                        price_val = float(price.replace('$', '').replace(',', ''))
                        total_cost += price_val
                    except:
                        pass
            
            if total_cost > 0:
                story.append(Paragraph(f"<b>Estimated additional cost: ${total_cost:.2f}</b>", 
                                     self.styles['CustomBodyText']))
        
        # Pantry staples
        pantry_staples = meal_plan_data.get('pantry_staples', [])
        if pantry_staples:
            story.append(Spacer(1, 15))
            story.append(Paragraph("🥄 Pantry Staples Needed", self.styles['SectionHeading']))
            story.append(Spacer(1, 8))
            for staple in pantry_staples:
                story.append(Paragraph(f"• {staple}", self.styles['IngredientsList']))
        
        # Build the PDF
        doc.build(story)
        return output_path

    def generate_meal_plan_pdf(self, output_filename: Optional[str] = None) -> str:
        """Generate PDF from the latest meal plan data"""
        
        # Get the latest meal plan data
        try:
            # Use instance variables if set, otherwise defaults
            generate_detailed = getattr(self, '_generate_detailed_recipes', True)
            skill_level = getattr(self, '_user_skill_level', 'intermediate')
            
            meal_plan_data = self.get_latest_meal_plan_data(
                generate_detailed_recipes=generate_detailed,
                user_skill_level=skill_level
            )
            if not meal_plan_data:
                raise ValueError("No meal plan data available")
        except Exception as e:
            print(f"Error getting meal plan data: {e}")
            return None
        
        # Generate output filename if not provided
        if not output_filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"meal_plan_{timestamp}.pdf"
        
        # Ensure output directory exists
        output_dir = "../pdfs"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)
        
        # Generate the PDF
        try:
            pdf_path = self.generate_pdf(meal_plan_data, output_path)
            print(f"✅ PDF generated successfully: {pdf_path}")
            return pdf_path
        except Exception as e:
            print(f"❌ Error generating PDF: {e}")
            return None

    def get_latest_meal_plan_data(self, generate_detailed_recipes: bool = True, 
                                  user_skill_level: str = "intermediate") -> Dict[str, Any]:
        """Get the latest meal plan data by running the meal planner
        
        Args:
            generate_detailed_recipes: If True, enhance with professional recipe details
            user_skill_level: Cooking skill level ("beginner", "intermediate", "advanced")
        """
        try:
            # Run the meal planner to get fresh data with detailed recipes
            meal_plan_result = meal_planner.run_main_planner(
                generate_detailed_recipes=generate_detailed_recipes,
                user_skill_level=user_skill_level
            )
            return meal_plan_result
        except Exception as e:
            print(f"Error running meal planner: {e}")
            return {}


def generate_pdf_meal_plan(output_filename: Optional[str] = None, 
                          generate_detailed_recipes: bool = True,
                          user_skill_level: str = "intermediate") -> str:
    """Convenience function to generate a PDF meal plan
    
    Args:
        output_filename: Optional custom filename for the PDF
        generate_detailed_recipes: If True, include professional recipe details
        user_skill_level: Cooking skill level ("beginner", "intermediate", "advanced")
    """
    planner = PDFMealPlanner()
    # Update the planner to use the new parameters
    planner._generate_detailed_recipes = generate_detailed_recipes
    planner._user_skill_level = user_skill_level
    return planner.generate_meal_plan_pdf(output_filename)


if __name__ == "__main__":
    # Test the PDF generation
    pdf_path = generate_pdf_meal_plan()
    if pdf_path:
        print(f"🎉 PDF meal plan generated: {pdf_path}")
    else:
        print("❌ Failed to generate PDF meal plan")