from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import json
import re

load_dotenv()

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
        
        print("Opening Farm to People...")
        page.goto("https://farmtopeople.com/home")
        page.wait_for_timeout(3000)
        
        # Click cart button
        print("Opening cart...")
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
                
                print(f"Clicking CUSTOMIZE...")
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
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"customize_results_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(all_box_data, f, indent=2)
        
        print(f"\n🎉 COMPLETE! Results saved to: {output_file}")
        print(f"\n📈 SUMMARY:")
        for box_data in all_box_data:
            print(f"  {box_data['box_name']}:")
            print(f"    ✅ {box_data['selected_count']} selected")
            print(f"    🔄 {box_data['alternatives_count']} alternatives")
        
        context.close()

if __name__ == "__main__":
    main()
