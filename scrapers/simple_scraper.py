from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import json
import re

load_dotenv()

def simple_box_scraper():
    output_dir = Path("farm_box_data")
    output_dir.mkdir(exist_ok=True)
    
    with sync_playwright() as p:
        # Use persistent context to maintain login
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
        
        # Get all cart items
        cart_items = []
        articles = page.locator("article[class*='cart-order_cartOrderItem']").all()
        
        print(f"Found {len(articles)} cart items")
        
        for i, article in enumerate(articles):
            try:
                # Get the box name
                name_link = article.locator("a[class*='unstyled-link'][href*='/product/']").first
                if name_link.count() == 0:
                    continue
                    
                box_name = name_link.text_content().strip()
                print(f"\nProcessing: {box_name}")
                
                # Check if this item has sub-products
                sub_list = article.locator("+ ul[class*='cart-order-line-item-subproducts']").first
                
                selected_items = []
                if sub_list.count() > 0:
                    print(f"  Found sub-items list")
                    
                    # Get all sub-items
                    sub_items = sub_list.locator("li[class*='cart-order-line-item-subproduct']").all()
                    print(f"  Found {len(sub_items)} sub-items")
                    
                    for sub_item in sub_items:
                        # Get the item name
                        name_elem = sub_item.locator("a[class*='subproduct-name']").first
                        if name_elem.count() > 0:
                            item_name = name_elem.text_content().strip()
                            
                            # Extract quantity from the name (e.g. "1 Sugar Cube Cantaloupe")
                            quantity = 1
                            clean_name = item_name
                            
                            match = re.match(r'^(\d+)\s+(.+)$', item_name)
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
                            
                            print(f"    - {quantity}x {clean_name} ({unit_info})")
                
                cart_items.append({
                    "name": box_name,
                    "type": "box",
                    "selected_items": selected_items
                })
                
            except Exception as e:
                print(f"Error processing item {i+1}: {e}")
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"simple_scrape_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(cart_items, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
        print(f"Total boxes processed: {len(cart_items)}")
        
        for item in cart_items:
            print(f"  {item['name']}: {len(item['selected_items'])} items")
        
        context.close()

if __name__ == "__main__":
    simple_box_scraper()
