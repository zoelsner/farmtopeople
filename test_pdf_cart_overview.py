#!/usr/bin/env python3
"""
Test adding a cart overview section to the PDF.
This shows how to add the missing cart summary at the top.
"""

from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter

def create_cart_overview_section(cart_data, styles):
    """Create the cart overview section for the PDF"""
    elements = []
    
    # Section title
    elements.append(Paragraph("Current Cart Overview", styles['Heading2']))
    elements.append(Spacer(1, 10))
    
    # Categorize items
    proteins = []
    vegetables = []
    fruits = []
    
    # Parse the cart data
    for item in cart_data.get('individual_items', []):
        name = item.get('name', '')
        lower_name = name.lower()
        
        if any(word in lower_name for word in ['chicken', 'fish', 'eggs', 'salmon', 'beef', 'turkey']):
            proteins.append(name)
        elif any(word in lower_name for word in ['apple', 'banana', 'peach', 'plum', 'berr']):
            fruits.append(name)
        else:
            vegetables.append(name)
    
    # Create formatted sections
    if proteins:
        elements.append(Paragraph("<b>Proteins:</b>", styles['Normal']))
        for protein in proteins:
            elements.append(Paragraph(f"• {protein}", styles['Normal']))
        elements.append(Spacer(1, 8))
    
    if vegetables:
        elements.append(Paragraph("<b>Vegetables:</b>", styles['Normal']))
        for veg in vegetables:
            elements.append(Paragraph(f"• {veg}", styles['Normal']))
        elements.append(Spacer(1, 8))
    
    if fruits:
        elements.append(Paragraph("<b>Fruits:</b>", styles['Normal']))
        for fruit in fruits:
            elements.append(Paragraph(f"• {fruit}", styles['Normal']))
        elements.append(Spacer(1, 8))
    
    return elements

def create_recommendation_box(title, items, reason, styles):
    """Create a colored recommendation box"""
    
    # Create custom style for yellow box
    box_style = ParagraphStyle(
        'YellowBox',
        parent=styles['Normal'],
        backColor=colors.HexColor('#FFF9C4'),  # Light yellow
        borderColor=colors.HexColor('#F9A825'),  # Darker yellow border
        borderWidth=1,
        borderPadding=10,
        spaceAfter=10
    )
    
    elements = []
    
    # Use a table for better control over the yellow box
    data = [[Paragraph(f"<b>{title}</b>", styles['Heading3'])]]
    
    # Add items
    for item in items:
        data.append([Paragraph(f"• {item}", styles['Normal'])])
    
    # Add reasoning
    data.append([Paragraph(f"<i>Reasoning: {reason}</i>", styles['Normal'])])
    
    # Create table with yellow background
    table = Table(data, colWidths=[6*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFF9C4')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#F9A825')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 10))
    
    return elements

# Test it
if __name__ == "__main__":
    # Sample cart data
    cart_data = {
        'individual_items': [
            {'name': 'Pasture Raised Eggs'},
            {'name': 'Organic Chicken Breast'},
            {'name': 'Wild Salmon Fillet'},
            {'name': 'Organic Zucchini'},
            {'name': 'Cherry Tomatoes'},
            {'name': 'Organic Apples'},
            {'name': 'Bananas'}
        ]
    }
    
    # Create PDF
    doc = SimpleDocTemplate("test_cart_overview.pdf", pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Add cart overview
    story.extend(create_cart_overview_section(cart_data, styles))
    
    # Add recommendation box
    story.extend(create_recommendation_box(
        "Priority Swap #1",
        ["The Cook's Box - Paleo", "Swap Local Yellow Peaches → Red Onions"],
        "Red onions are essential aromatics for multiple meals",
        styles
    ))
    
    # Build PDF
    doc.build(story)
    print("✅ Test PDF created: test_cart_overview.pdf")