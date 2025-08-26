# ReportLab PDF Enhancement Request

I have an existing ReportLab PDF generator for meal plans in Python. I need to enhance it to create a more professional layout with meal cards in a grid instead of sequential recipes.

## My Current Code Structure:

### 1. Class Definition and Styles:
```python
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

class PDFMealPlanner:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        # Main title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2E7D32')  # Farm green
        ))
        
        # Section heading style
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
        self.styles.add(ParagraphStyle(
            name='RecipeTitle',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=8,
            textColor=colors.HexColor('#1B5E20')
        ))
```

### 2. My Current PDF Generation Method:
```python
def generate_pdf(self, meal_plan_data: Dict[str, Any], output_path: str) -> str:
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    story = []
    
    # Title
    story.append(Paragraph("🌱 Your Farm to People Meal Plan", self.styles['CustomTitle']))
    story.append(Spacer(1, 20))
    
    # Currently adds sequential recipes with full details
    # I want to replace this with a compact card grid
    for i, meal in enumerate(meal_plan_data.get('meals', [])):
        story.append(Paragraph(f"{i+1}. {meal.get('title')}", self.styles['RecipeTitle']))
        # ... lots of detailed recipe content ...
    
    doc.build(story)
    return output_path
```

### 3. Data Structure I'm Working With:
```python
meal_plan_data = {
    "meals": [
        {
            "title": "Mediterranean Chicken Bowl",
            "total_time": 30,
            "servings": 4,
            "protein_per_serving": 35,
            "base": {
                "uses": ["Chicken Breast", "Cherry Tomatoes", "Cucumber", "Feta Cheese"]
            },
            "cooking_instructions": [...],
            "estimated_servings": 4
        },
        {
            "title": "Quick Salmon Stir-Fry", 
            "total_time": 20,
            "servings": 2,
            "protein_per_serving": 32,
            "base": {
                "uses": ["Salmon Fillet", "Zucchini", "Bell Peppers", "Garlic"]
            }
        },
        # ... 3 more meals for total of 5
    ],
    "analysis_data": {
        "individual_items": [
            {"name": "Pasture Raised Eggs", "quantity": 1, "price": "$5.99"},
            {"name": "Organic Chicken Breast", "quantity": 2, "price": "$15.99"},
            {"name": "Wild Salmon", "quantity": 1, "price": "$18.99"}
        ]
    }
}
```

### 4. Working Functions I've Started:
```python
def create_cart_overview_section(cart_data, styles):
    """Creates categorized cart overview"""
    elements = []
    elements.append(Paragraph("Current Cart Overview", styles['Heading2']))
    
    # Categorize items
    proteins = []
    vegetables = []
    fruits = []
    
    for item in cart_data.get('individual_items', []):
        name = item.get('name', '')
        lower_name = name.lower()
        
        if any(word in lower_name for word in ['chicken', 'fish', 'eggs', 'salmon']):
            proteins.append(name)
        elif any(word in lower_name for word in ['apple', 'banana', 'peach']):
            fruits.append(name)
        else:
            vegetables.append(name)
    
    # Add formatted lists
    if proteins:
        elements.append(Paragraph("<b>Proteins:</b>", styles['Normal']))
        for protein in proteins:
            elements.append(Paragraph(f"• {protein}", styles['Normal']))
    
    return elements

def create_recommendation_box(title, items, reason, styles):
    """Creates yellow background recommendation box"""
    data = [[Paragraph(f"<b>{title}</b>", styles['Heading3'])]]
    
    for item in items:
        data.append([Paragraph(f"• {item}", styles['Normal'])])
    
    data.append([Paragraph(f"<i>Reasoning: {reason}</i>", styles['Normal'])])
    
    table = Table(data, colWidths=[6*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFF9C4')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#F9A825')),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    return table
```

## What I Need:

### 1. MEAL CARD GRID FUNCTION (Most Important)
I need a function that creates a 2-column grid of meal cards to replace my current sequential recipe layout:

- Should work within my PDFMealPlanner class
- Create compact cards (not full recipes) in a 2-column layout
- Handle 5 meals (3 in first row, 2 in second row)
- Each card should display:
  - Meal number & title (e.g., "Meal 1: Mediterranean Chicken Bowl")
  - Cook time (e.g., "⏱️ 30 min")
  - Servings (e.g., "Serves 4")
  - Protein (e.g., "💪 35g protein")
  - First 3-4 ingredients from base['uses']
- Cards need borders and consistent height/width
- Should look professional and scannable

### 2. INTEGRATE ALL SECTIONS
Show me how to properly combine these sections in my story[] list:
1. Cart Overview (using my function above)
2. Yellow Recommendation Box (using my function above)
3. The new Meal Card Grid
4. Keep my existing detailed recipes as a later section if needed

### 3. STYLE IMPROVEMENTS
- How can I make the yellow box look more professional?
- Any suggestions for better spacing between sections?
- How to ensure the meal cards don't break awkwardly across pages?

## Specific Requirements:
- Must integrate with my existing PDFMealPlanner class
- Use my existing styles where possible, add new ones if needed
- Provide complete, runnable functions
- Show me how to modify my generate_pdf() method to use the new layout

Please provide Python code that I can directly integrate into my existing class. Focus on the meal card grid implementation as that's the most complex part I need help with.