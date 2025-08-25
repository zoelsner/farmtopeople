# Meal Plan PDF Layout with ReportLab
A practical guide and drop-in code to render a professional meal plan PDF using ReportLab. Includes a 2-column grid of meal cards, yellow recommendation callouts, and continuous sections on a single flow. Copy this file to your repo and adapt the helper functions to your data model.

---

## What you get
- Meal cards that keep content together and never split across pages
- A 2-column grid that keeps rows intact
- Yellow recommendation boxes for priority swaps
- Section helpers for Cart Overview and a Strategic Meal Plan
- Clean spacing, padding, and pagination control

---

## Requirements
```bash
pip install reportlab
```
You will also need a class or module that exposes a `styles` collection. This file shows how to add missing styles and how to compose a full `generate_pdf` function.

---

## Imports
```python
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepInFrame, PageBreak, ListFlowable, ListItem
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
```

---

## Style setup
Add these to your existing style initialisation. The code below creates a base style sheet if you do not already have one and adds a few styles referenced later.

```python
def setup_custom_styles():
    styles = getSampleStyleSheet()

    # Base section headings if you do not already have them
    if 'CustomTitle' not in styles:
        styles.add(ParagraphStyle(
            name='CustomTitle', parent=styles['Heading1'],
            fontSize=16, leading=20, spaceAfter=6
        ))
    if 'SectionHeading' not in styles:
        styles.add(ParagraphStyle(
            name='SectionHeading', parent=styles['Heading2'],
            fontSize=13, leading=16, spaceBefore=6, spaceAfter=4
        ))
    if 'RecipeTitle' not in styles:
        styles.add(ParagraphStyle(
            name='RecipeTitle', parent=styles['Heading3'],
            fontSize=12, leading=14, spaceBefore=8, spaceAfter=4
        ))

    # Card styles
    styles.add(ParagraphStyle(
        name='CardTitle',
        parent=styles['Heading3'],
        fontSize=12, leading=14,
        textColor=colors.HexColor('#1B5E20'),
        spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name='CardMeta',
        parent=styles['Normal'],
        fontSize=9, leading=11,
        textColor=colors.HexColor('#455A64')
    ))
    styles.add(ParagraphStyle(
        name='CardLabel',
        parent=styles['Normal'],
        fontSize=9, leading=11,
        textColor=colors.HexColor('#2E7D32')
    ))
    styles.add(ParagraphStyle(
        name='Small',
        parent=styles['Normal'],
        fontSize=8, leading=10,
        textColor=colors.HexColor('#37474F')
    ))
    styles.add(ParagraphStyle(
        name='CalloutTitle',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#684e00')
    ))
    return styles
```

---

## Meal card component
The card uses an inner `KeepInFrame` so a long ingredient line will shrink slightly instead of overflowing. An outer `Table` provides consistent border, padding, and fixed height.

```python
def build_meal_card(styles, meal, index, card_w, card_h):
    title = meal.get('title', 'Untitled')
    time_min = meal.get('total_time', '')
    servings = meal.get('servings', '')
    protein = meal.get('protein_per_serving', '')
    # Adjust to your data model. This example grabs up to 4 ingredients to keep density even.
    uses = (meal.get('base', {}) or {}).get('uses', [])[:4]

    header = Paragraph(f"<b>Meal {index}:</b> {title}", styles['CardTitle'])
    meta = Paragraph(
        f"⏱ {time_min} min &nbsp;&nbsp;•&nbsp;&nbsp; Serves {servings} &nbsp;&nbsp;•&nbsp;&nbsp; 💪 {protein}g protein",
        styles['CardMeta']
    )
    label = Paragraph("Ingredients", styles['CardLabel'])
    ing_lines = [Paragraph(f"• {i}", styles['Small']) for i in uses] or [Paragraph("• —", styles['Small'])]

    inner = [header, meta, Spacer(1, 4), label, Spacer(1, 2)] + ing_lines

    kif = KeepInFrame(card_w - 16, card_h - 16, inner, hAlign='LEFT', vAlign='TOP', mode='shrink')

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
```

---

## 2-column grid builder
Creates rows of two cards. Wrap the whole grid in `KeepInFrame` so it moves as a unit to the next page when needed.

```python
def build_meal_cards_grid(styles, meals, doc, gutter=12, card_h=2.1*inch):
    flow = []
    if not meals:
        return flow

    total_w = doc.width
    card_w = (total_w - gutter) / 2.0

    cards = [build_meal_card(styles, m, i+1, card_w, card_h) for i, m in enumerate(meals)]

    rows = []
    it = iter(cards)
    for left in it:
        right = next(it, None)
        rows.append([left, right if right else Spacer(card_w, card_h)])

    grid = Table(rows, colWidths=[card_w, card_w], rowHeights=[card_h]*len(rows), hAlign='LEFT', spaceBefore=6, spaceAfter=6)
    grid.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 0, colors.white),
    ]))

    kif = KeepInFrame(doc.width, doc.height, [grid], mode='shrink', hAlign='LEFT')
    flow.append(kif)
    return flow
```

---

## Yellow recommendation callout
A padded table that contains a title, a bullet list, and a short reasoning paragraph. Uses your color values.

```python
def build_recommendation_box(styles, title, bullets, reason):
    title_p = Paragraph(title, styles['CalloutTitle'])

    bullet_items = [ListItem(Paragraph(b, styles['Normal']), leftIndent=6) for b in bullets]
    bullet_list = ListFlowable(bullet_items, bulletType='bullet', start='•', leftIndent=10, spaceBefore=2, spaceAfter=2)

    reason_p = Paragraph(f"<i>{reason}</i>", styles['Small'])

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
```

---

## Cart overview helper
Simple categorised bullet lists. Replace the naive categoriser with your own if needed.

```python
def build_cart_overview(styles, cart_data):
    out = []
    out.append(Paragraph("Current Cart Overview", styles['SectionHeading']))

    prots, vegs, fruits = [], [], []
    for item in (cart_data or {}).get('individual_items', []):
        name = item.get('name', '')
        ln = name.lower()
        if any(k in ln for k in ['chicken','fish','salmon','eggs','beef','turkey']):
            prots.append(name)
        elif any(k in ln for k in ['apple','banana','peach','pear','plum']):
            fruits.append(name)
        else:
            vegs.append(name)

    def bullets(title, items):
        if not items: return []
        parts = [Paragraph(f"<b>{title}</b>", styles['Normal'])]
        parts += [Paragraph(f"• {i}", styles['Normal']) for i in items]
        parts.append(Spacer(1, 6))
        return parts

    out += bullets("Proteins:", prots)
    out += bullets("Vegetables:", vegs)
    out += bullets("Fruits:", fruits)
    return out
```

---

## Compose the document
Continuous sections on the same flow. The grid is kept together. Optional detailed recipes go after a page break.

```python
def generate_pdf(meal_plan_data, output_path="meal_plan.pdf"):
    styles = setup_custom_styles()

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
    )
    story = []

    # Title
    story.append(Paragraph("🌱 Your Farm to People Meal Plan", styles['CustomTitle']))
    story.append(Spacer(1, 6))

    # 1) Cart overview
    story += build_cart_overview(styles, meal_plan_data.get('analysis_data', {}))
    story.append(Spacer(1, 10))

    # 2) Yellow recommendation box
    story.append(build_recommendation_box(
        styles,
        "Priority Swaps",
        bullets=[
            "Swap yellow peaches for red onions to unlock salsa and slaws",
            "Swap lunchbox peppers for fresnos if you want heat"
        ],
        reason="These swaps expand side options and reduce waste by reusing overlapping produce"
    ))
    story.append(Spacer(1, 14))

    # 3) Strategic meal plan grid
    story.append(Paragraph("Strategic Meal Plan", styles['SectionHeading']))
    story += build_meal_cards_grid(styles, meal_plan_data.get('meals', []), doc, gutter=14, card_h=2.2*inch)
    story.append(Spacer(1, 6))

    # Optional: detailed recipes after the grid
    if meal_plan_data.get('meals'):
        story.append(PageBreak())
        story.append(Paragraph("Detailed Recipes", styles['SectionHeading']))
        for i, meal in enumerate(meal_plan_data['meals'], 1):
            story.append(Paragraph(f"{i}. {meal.get('title','Untitled')}", styles['RecipeTitle']))
            # Add your long-form recipe content here...
            story.append(Spacer(1, 8))

    doc.build(story)
    return output_path
```

---

## Best practices and tips
- Use a spacing rhythm based on 6 or 8 points and stick to multiples for consistent vertical rhythm.
- Keep card height between 2.1 and 2.3 inches for a 2-column layout on letter size.
- Wrap grids inside `KeepInFrame` to avoid orphan rows. If it does not fit, it will move as a unit.
- Do not overfill cards. Cap ingredient bullets to 3 or 4 for even density. Place full recipes in the detailed section.
- Optimise any images you embed. Target around 120 KB per square tile at 640x640.
- If you need page headers or footers, switch to `BaseDocTemplate` with `PageTemplate` and named frames. The card and callout components will still work unchanged.

---

## Minimal example to run
```python
if __name__ == "__main__":
    demo_data = {
        "analysis_data": {
            "individual_items": [
                {"name": "Locust Point Farm Skinless Chicken Breast"},
                {"name": "Organic Red Leaf Lettuce"},
                {"name": "Organic Peaches"},
            ]
        },
        "meals": [
            {"title":"Lemon Herb Roast Chicken","total_time":40,"servings":4,"protein_per_serving":42,"base":{"uses":["Chicken thighs","Potatoes","Lemon","Rosemary"]}},
            {"title":"15-Minute Chicken Stir-Fry","total_time":15,"servings":2,"protein_per_serving":35,"base":{"uses":["Chicken breast","Snap peas","Ginger","Garlic"]}},
            {"title":"Grilled Salmon with Greens","total_time":20,"servings":2,"protein_per_serving":38,"base":{"uses":["Salmon","Asparagus","Lemon","Olive oil"]}},
            {"title":"Mediterranean Chickpea Bowl","total_time":25,"servings":2,"protein_per_serving":19,"base":{"uses":["Chickpeas","Cucumber","Tomato","Feta"]}},
            {"title":"Veggie Pesto Pasta","total_time":25,"servings":3,"protein_per_serving":16,"base":{"uses":["Pasta","Basil pesto","Parmesan","Cherry tomatoes"]}},
        ]
    }
    styles = setup_custom_styles()
    generate_pdf(demo_data, "demo_meal_plan.pdf")
    print("Generated demo_meal_plan.pdf")
```
