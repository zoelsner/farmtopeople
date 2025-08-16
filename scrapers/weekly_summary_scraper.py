from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import json
import re

load_dotenv()

def generate_weekly_customer_summary(box_data):
    """Generate a beautiful customer-friendly weekly summary."""
    
    summary_lines = []
    
    # Header with date
    today = datetime.now().strftime("%A, %B %d, %Y")
    summary_lines.append(f"🌱 **Your Farm to People Box Update - {today}** 🌱")
    summary_lines.append("")
    
    for box in box_data:
        box_name = box['box_name']
        selected_items = box['selected_items']
        alternatives = box['available_alternatives']
        
        # Box header with emoji
        if "Produce" in box_name:
            emoji = "🥬"
        elif "Cook" in box_name or "Paleo" in box_name:
            emoji = "🍳"
        else:
            emoji = "📦"
            
        summary_lines.append(f"{emoji} **{box_name}**")
        summary_lines.append(f"✅ **{len(selected_items)} items selected** | 🔄 **{len(alternatives)} alternatives available**")
        summary_lines.append("")
        
        # Categorize selected items
        categories = categorize_items(selected_items)
        
        # Show selected items by category
        summary_lines.append("**What's in your box this week:**")
        
        for category, items in categories.items():
            if items:
                category_emoji = get_category_emoji(category)
                summary_lines.append(f"• {category_emoji} **{category}:** {format_items_list(items)}")
        
        summary_lines.append("")
        
        # Show top producers
        producers = get_top_producers(selected_items)
        if producers:
            summary_lines.append("**Featured farms this week:**")
            for producer, count in producers[:3]:  # Top 3 producers
                summary_lines.append(f"• 🏪 **{clean_producer_name(producer)}** ({count} item{'s' if count > 1 else ''})")
            summary_lines.append("")
        
        # Show swap options
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
        if any(fruit in name for fruit in ['cantaloupe', 'peach', 'tomato', 'cherry tomato']):
            categories["Fresh Fruits"].append(item)
        # Leafy greens
        elif any(green in name for green in ['lettuce', 'kale', 'green beans']):
            categories["Leafy Greens"].append(item)
        # Root vegetables
        elif any(root in name for root in ['potato', 'carrot', 'onion']):
            categories["Root Vegetables"].append(item)
        # Proteins
        elif any(protein in name for protein in ['tuna', 'pork', 'chicken', 'belly']):
            categories["Premium Proteins"].append(item)
        # Herbs & Aromatics
        elif any(herb in name for herb in ['pepper', 'jalapeno']):
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
        return f"{clean_item_name(item['name'])} ({item['unit']})"
    elif len(items) == 2:
        return f"{clean_item_name(items[0]['name'])} & {clean_item_name(items[1]['name'])}"
    else:
        names = [clean_item_name(item['name']) for item in items[:2]]
        return f"{', '.join(names)} + {len(items) - 2} more"

def clean_item_name(name):
    """Clean up item names for customer display."""
    # Remove "Organic" prefix for cleaner look
    name = re.sub(r'^Organic\s+', '', name)
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def clean_producer_name(producer):
    """Clean up producer names."""
    # Remove duplicated text (e.g., "Sunny HarvestSunny Harvest" -> "Sunny Harvest")
    # Handle cases where text is repeated back-to-back
    words = producer.split()
    
    # Try to find if first half equals second half
    for split_point in range(1, len(words)):
        first_part = ' '.join(words[:split_point])
        remaining = ' '.join(words[split_point:])
        if remaining.startswith(first_part):
            return first_part
    
    # Remove "..." at end
    producer = re.sub(r'\.\.\..*$', '', producer)
    return producer.strip()

def get_top_producers(items):
    """Get top producers by item count."""
    producer_counts = {}
    for item in items:
        producer = clean_producer_name(item['producer'])
        producer_counts[producer] = producer_counts.get(producer, 0) + 1
    
    return sorted(producer_counts.items(), key=lambda x: x[1], reverse=True)

def scrape_customize_modal(page):
    """Scrape both selected and available items from the customize modal."""
    
    # Wait for the customize modal to be fully loaded
    page.wait_for_selector("aside[aria-label*='Customize']", timeout=10000)
    
    # Find the customize modal container
    modal = page.locator("aside[aria-label*='Customize']").first
    
    # Get all articles (individual items)
    articles = modal.locator("article[aria-label]").all()
    
    selected_items = []
    available_alternatives = []
    
    print(f"Found {len(articles)} total items in customize modal")
    
    for article in articles:
        try:
            # Get item name from aria-label
            item_name = article.get_attribute("aria-label")
            
            # Get producer info
            producer_elem = article.locator("p[class*='producer'] a").first
            producer = ""
            if producer_elem.count() > 0:
                producer = producer_elem.text_content().strip()
            
            # Get unit/details info
            details_elem = article.locator("div[class*='item-details'] p").first
            unit_info = ""
            if details_elem.count() > 0:
                unit_info = details_elem.text_content().strip()
            
            # Check if item is selected (has quantity selector) or available (has Add button)
            quantity_selector = article.locator("div[class*='quantity-selector']").first
            add_button = article.locator("button:has-text('Add')").first
            
            if quantity_selector.count() > 0:
                # This is a selected item - get the quantity
                quantity_span = quantity_selector.locator("span[class*='quantity']").first
                quantity = 1
                if quantity_span.count() > 0:
                    try:
                        quantity = int(quantity_span.text_content().strip())
                    except:
                        quantity = 1
                
                selected_items.append({
                    "name": item_name,
                    "producer": producer,
                    "unit": unit_info,
                    "quantity": quantity,
                    "selected": True
                })
                print(f"  ✅ Selected: {item_name} (qty: {quantity}) - {unit_info}")
                
            elif add_button.count() > 0:
                # This is an available alternative
                available_alternatives.append({
                    "name": item_name,
                    "producer": producer,
                    "unit": unit_info,
                    "quantity": 0,
                    "selected": False
                })
                print(f"  🔄 Available: {item_name} - {unit_info}")
                
        except Exception as e:
            print(f"  ❌ Error processing article: {e}")
            continue
    
    return {
        "selected_items": selected_items,
        "available_alternatives": available_alternatives,
        "total_items": len(articles),
        "selected_count": len(selected_items),
        "alternatives_count": len(available_alternatives)
    }

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
        
        # Get all CUSTOMIZE buttons
        customize_btns = page.locator("button:has-text('CUSTOMIZE'), button:has-text('Customize')").all()
        
        all_box_data = []
        
        for i, customize_btn in enumerate(customize_btns):
            try:
                # Get box name from the parent article
                article = customize_btn.locator("xpath=ancestor::article").first
                box_name = "Unknown Box"
                if article.count() > 0:
                    name_link = article.locator("a[href*='/product/']").first
                    if name_link.count() > 0:
                        box_name = name_link.text_content().strip()
                
                print(f"\n=== PROCESSING BOX {i+1}: {box_name} ===")
                
                # Scroll button into view and click
                customize_btn.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                
                print(f"🔄 Clicking CUSTOMIZE...")
                try:
                    customize_btn.click()
                    page.wait_for_timeout(3000)
                except Exception as e:
                    print(f"Regular click failed, trying JS: {e}")
                    customize_btn.evaluate("element => element.click()")
                    page.wait_for_timeout(3000)
                
                # Scrape the customize modal
                box_data = scrape_customize_modal(page)
                box_data["box_name"] = box_name
                box_data["box_index"] = i + 1
                
                all_box_data.append(box_data)
                
                print(f"\n📊 RESULTS for {box_name}:")
                print(f"  • {box_data['selected_count']} selected items")
                print(f"  • {box_data['alternatives_count']} available alternatives")
                print(f"  • {box_data['total_items']} total items")
                
                # Close the modal (look for Close button)
                close_btn = page.locator("button:has-text('Close')").first
                if close_btn.count() > 0:
                    close_btn.click()
                    page.wait_for_timeout(1000)
                else:
                    # Try ESC key
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(1000)
                
            except Exception as e:
                print(f"❌ Error processing box {i+1}: {e}")
                continue
        
        # Generate customer summary
        print("\n🎨 Generating customer weekly summary...")
        customer_summary = generate_weekly_customer_summary(all_box_data)
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save raw data
        data_file = output_dir / f"weekly_data_{timestamp}.json"
        with open(data_file, 'w') as f:
            json.dump(all_box_data, f, indent=2)
        
        # Save customer summary
        summary_file = output_dir / f"weekly_customer_summary_{timestamp}.md"
        with open(summary_file, 'w') as f:
            f.write(customer_summary)
        
        print(f"\n🎉 COMPLETE! Files saved:")
        print(f"📊 Raw data: {data_file}")
        print(f"📝 Customer summary: {summary_file}")
        
        print(f"\n" + "="*60)
        print("📧 CUSTOMER WEEKLY SUMMARY:")
        print("="*60)
        print(customer_summary)
        print("="*60)
        
        context.close()

if __name__ == "__main__":
    main()
