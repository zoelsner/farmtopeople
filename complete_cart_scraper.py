from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import json
import re

load_dotenv()

def generate_weekly_customer_summary(cart_data):
    """Generate a beautiful customer-friendly weekly summary including individual items."""
    
    summary_lines = []
    
    # Header with date
    today = datetime.now().strftime("%A, %B %d, %Y")
    summary_lines.append(f"🌱 **Your Farm to People Cart Update - {today}** 🌱")
    summary_lines.append("")
    
    # Separate boxes and individual items
    boxes = [item for item in cart_data if item['type'] == 'box']
    individual_items = [item for item in cart_data if item['type'] == 'individual']
    
    # Process boxes
    for box in boxes:
        box_name = box['name']
        selected_items = box.get('selected_items', [])
        alternatives = box.get('available_alternatives', [])
        
        # Box header with emoji
        if "Produce" in box_name:
            emoji = "🥬"
        elif "Cook" in box_name or "Paleo" in box_name:
            emoji = "🍳"
        elif "Fruit" in box_name:
            emoji = "🍓"
        else:
            emoji = "📦"
            
        summary_lines.append(f"{emoji} **{box_name}**")
        if alternatives:
            summary_lines.append(f"✅ **{len(selected_items)} items selected** | 🔄 **{len(alternatives)} alternatives available**")
        else:
            summary_lines.append(f"✅ **{len(selected_items)} items included**")
        summary_lines.append("")
        
        # Categorize selected items
        categories = categorize_items(selected_items)
        
        # Show selected items by category
        summary_lines.append("**What's in this box:**")
        
        for category, items in categories.items():
            if items:
                category_emoji = get_category_emoji(category)
                summary_lines.append(f"• {category_emoji} **{category}:** {format_items_list(items)}")
        
        summary_lines.append("")
        
        # Show swap options if available
        if alternatives:
            summary_lines.append("**Available swaps (click CUSTOMIZE to change):**")
            alt_categories = categorize_items(alternatives)
            for category, items in alt_categories.items():
                if items:
                    category_emoji = get_category_emoji(category)
                    summary_lines.append(f"• {category_emoji} {format_items_list(items)}")
            summary_lines.append("")
        
        summary_lines.append("---")
        summary_lines.append("")
    
    # Process individual items
    if individual_items:
        summary_lines.append("🛒 **Individual Items Added**")
        summary_lines.append("")
        
        # Categorize individual items
        all_individual_products = []
        for item in individual_items:
            all_individual_products.append({
                'name': item['name'],
                'quantity': item['quantity'],
                'unit': item.get('unit', ''),
                'price': item.get('price', '')
            })
        
        individual_categories = categorize_items(all_individual_products)
        
        for category, items in individual_categories.items():
            if items:
                category_emoji = get_category_emoji(category)
                summary_lines.append(f"• {category_emoji} **{category}:** {format_individual_items_list(items)}")
        
        summary_lines.append("")
        summary_lines.append("---")
        summary_lines.append("")
    
    # Footer
    summary_lines.append("💡 **Ready for meal inspiration?** Reply 'MEALS' for personalized recipe suggestions!")
    summary_lines.append("🔄 **Want to make changes?** Visit farmtopeople.com or reply 'SWAP'")
    summary_lines.append("")
    summary_lines.append("Happy cooking! 👨‍🍳👩‍🍳")
    
    return "\n".join(summary_lines)

def categorize_items(items):
    """Categorize items by type."""
    categories = {
        "Fresh Fruits": [],
        "Leafy Greens": [],
        "Root Vegetables": [],
        "Garden Vegetables": [],
        "Premium Proteins": [],
        "Herbs & Aromatics": []
    }
    
    for item in items:
        name = item['name'].lower()
        
        # Fruits
        if any(fruit in name for fruit in ['cantaloupe', 'peach', 'tomato', 'cherry tomato', 'fruit', 'apple', 'pear', 'berry']):
            categories["Fresh Fruits"].append(item)
        # Leafy greens
        elif any(green in name for green in ['lettuce', 'kale', 'green beans', 'spinach', 'arugula']):
            categories["Leafy Greens"].append(item)
        # Root vegetables
        elif any(root in name for root in ['potato', 'carrot', 'onion', 'beet', 'turnip']):
            categories["Root Vegetables"].append(item)
        # Proteins
        elif any(protein in name for protein in ['tuna', 'pork', 'chicken', 'belly', 'fish', 'meat', 'beef', 'lamb']):
            categories["Premium Proteins"].append(item)
        # Herbs & Aromatics
        elif any(herb in name for herb in ['pepper', 'jalapeno', 'herb', 'basil', 'cilantro']):
            categories["Herbs & Aromatics"].append(item)
        # Everything else
        else:
            categories["Garden Vegetables"].append(item)
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}

def get_category_emoji(category):
    """Get emoji for category."""
    emojis = {
        "Fresh Fruits": "🍅",
        "Leafy Greens": "🥬", 
        "Root Vegetables": "🥔",
        "Garden Vegetables": "🥒",
        "Premium Proteins": "🥩",
        "Herbs & Aromatics": "🌶️"
    }
    return emojis.get(category, "🌱")

def format_items_list(items):
    """Format items into a readable list."""
    if len(items) == 1:
        item = items[0]
        return f"{clean_item_name(item['name'])} ({item.get('unit', '')})"
    elif len(items) == 2:
        return f"{clean_item_name(items[0]['name'])} & {clean_item_name(items[1]['name'])}"
    else:
        names = [clean_item_name(item['name']) for item in items[:2]]
        return f"{', '.join(names)} + {len(items) - 2} more"

def format_individual_items_list(items):
    """Format individual items with quantities and prices."""
    formatted_items = []
    for item in items:
        name = clean_item_name(item['name'])
        qty = item.get('quantity', 1)
        unit = item.get('unit', '')
        price = item.get('price', '')
        
        item_str = f"{qty}x {name}"
        if unit:
            item_str += f" ({unit})"
        if price:
            item_str += f" - {price}"
        
        formatted_items.append(item_str)
    
    # For readability, put each item on its own line if more than 2 items
    if len(formatted_items) > 2:
        return "\n  • ".join([""] + formatted_items)
    else:
        return ", ".join(formatted_items)

def clean_item_name(name):
    """Clean up item names for customer display."""
    # Remove "Organic" prefix for cleaner look
    name = re.sub(r'^Organic\s+', '', name)
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def scrape_cart_item(article):
    """Scrape a single cart item (box or individual)."""
    try:
        # Get the item name
        name_link = article.locator("a[class*='unstyled-link'][href*='/product/']").first
        if name_link.count() == 0:
            return None
            
        item_name = name_link.text_content().strip()
        
        # Get price
        price_elem = article.locator("p[class*='font-medium']").first
        price = ""
        if price_elem.count() > 0:
            price = price_elem.text_content().strip()
        
        # Check if this is a box (has sub-products) or individual item
        sub_list = article.locator("+ ul[class*='cart-order-line-item-subproducts']").first
        has_sublist = sub_list.count() > 0
        
        # Check for CUSTOMIZE button
        customize_btn = article.locator("button:has-text('CUSTOMIZE'), button:has-text('Customize')").first
        has_customize = customize_btn.count() > 0
        
        if has_sublist:
            # This is a box - get sub-items
            selected_items = []
            sub_items = sub_list.locator("li[class*='cart-order-line-item-subproduct']").all()
            
            for sub_item in sub_items:
                # Get the item name
                name_elem = sub_item.locator("a[class*='subproduct-name']").first
                if name_elem.count() > 0:
                    sub_item_name = name_elem.text_content().strip()
                    
                    # Extract quantity from the name (e.g. "1 Sugar Cube Cantaloupe")
                    quantity = 1
                    clean_name = sub_item_name
                    
                    match = re.match(r'^(\d+)\s+(.+)$', sub_item_name)
                    if match:
                        quantity = int(match.group(1))
                        clean_name = match.group(2)
                    
                    # Get the unit/size info
                    unit_elem = sub_item.locator("p").first
                    unit_info = ""
                    if unit_elem.count() > 0:
                        unit_info = unit_elem.text_content().strip()
                    
                    selected_items.append({
                        "name": clean_name,
                        "quantity": quantity,
                        "unit": unit_info,
                        "selected": True
                    })
            
            return {
                "name": item_name,
                "type": "box",
                "price": price,
                "customizable": has_customize,
                "selected_items": selected_items,
                "available_alternatives": []  # Will be filled by customize scraper if needed
            }
        
        else:
            # This is an individual item - check for quantity selector
            quantity_selector = article.locator("div[class*='quantity-selector']").first
            quantity = 1
            
            if quantity_selector.count() > 0:
                quantity_span = quantity_selector.locator("span[class*='quantity']").first
                if quantity_span.count() > 0:
                    try:
                        quantity = int(quantity_span.text_content().strip())
                    except:
                        quantity = 1
            
            # Try to get unit info from article text
            unit_info = ""
            unit_elements = article.locator("p").all()
            for unit_elem in unit_elements:
                unit_text = unit_elem.text_content().strip()
                # Skip price and farm name elements
                if (unit_text and 
                    not unit_text.startswith("$") and 
                    "farm" not in unit_text.lower() and
                    "people" not in unit_text.lower() and
                    len(unit_text) < 50):  # Avoid long descriptions
                    unit_info = unit_text
                    break
            
            return {
                "name": item_name,
                "type": "individual",
                "quantity": quantity,
                "unit": unit_info,
                "price": price
            }
            
    except Exception as e:
        print(f"❌ Error scraping cart item: {e}")
        return None

def main():
    output_dir = Path("farm_box_data")
    output_dir.mkdir(exist_ok=True)
    
    with sync_playwright() as p:
        user_data_dir = Path("browser_data")
        user_data_dir.mkdir(exist_ok=True)
        
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        print("🌱 Opening Farm to People...")
        page.goto("https://farmtopeople.com/home")
        page.wait_for_timeout(3000)
        
        # Click cart button
        print("📦 Opening cart...")
        cart_btn = page.locator("div.cart-button.ml-auto.cursor-pointer").first
        if cart_btn.count() > 0:
            cart_btn.click()
            page.wait_for_timeout(2000)
        
        # Get all cart items
        cart_data = []
        articles = page.locator("article[class*='cart-order_cartOrderItem']").all()
        
        print(f"🔍 Found {len(articles)} cart items")
        
        for i, article in enumerate(articles):
            print(f"\n--- PROCESSING ITEM {i+1} ---")
            
            item_data = scrape_cart_item(article)
            if item_data:
                cart_data.append(item_data)
                
                if item_data['type'] == 'box':
                    print(f"📦 Box: {item_data['name']}")
                    print(f"   💰 Price: {item_data['price']}")
                    print(f"   ⚙️  Customizable: {item_data['customizable']}")
                    print(f"   📋 Sub-items: {len(item_data['selected_items'])}")
                    for item in item_data['selected_items']:
                        print(f"      - {item['quantity']}x {item['name']} ({item['unit']})")
                
                elif item_data['type'] == 'individual':
                    print(f"🛒 Individual: {item_data['name']}")
                    print(f"   💰 Price: {item_data['price']}")
                    print(f"   🔢 Quantity: {item_data['quantity']}")
                    print(f"   📏 Unit: {item_data['unit']}")
        
        # Generate customer summary
        print(f"\n🎨 Generating customer summary...")
        customer_summary = generate_weekly_customer_summary(cart_data)
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save raw data
        data_file = output_dir / f"complete_cart_{timestamp}.json"
        with open(data_file, 'w') as f:
            json.dump(cart_data, f, indent=2)
        
        # Save customer summary
        summary_file = output_dir / f"complete_summary_{timestamp}.md"
        with open(summary_file, 'w') as f:
            f.write(customer_summary)
        
        print(f"\n🎉 COMPLETE! Files saved:")
        print(f"📊 Raw data: {data_file}")
        print(f"📝 Customer summary: {summary_file}")
        
        print(f"\n" + "="*60)
        print("📧 COMPLETE CART SUMMARY:")
        print("="*60)
        print(customer_summary)
        print("="*60)
        
        # Summary stats
        boxes = [item for item in cart_data if item['type'] == 'box']
        individuals = [item for item in cart_data if item['type'] == 'individual']
        
        print(f"\n📈 CART ANALYSIS:")
        print(f"   📦 Boxes: {len(boxes)}")
        print(f"   🛒 Individual items: {len(individuals)}")
        print(f"   📋 Total sub-items in boxes: {sum(len(box['selected_items']) for box in boxes)}")
        
        context.close()

if __name__ == "__main__":
    main()
