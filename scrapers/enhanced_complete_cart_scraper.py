"""
Enhanced version of complete_cart_scraper.py with fallback safety nets.
Uses the original scraper but ADDS fallback protection.
NO changes to core logic - only safety nets.
"""

from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import json
import re
from auth_helper import ensure_logged_in
from selector_fallbacks import get_cart_items_robust, fallback_system

# Import all the working functions from the original scraper
from complete_cart_scraper import (
    categorize_items, 
    generate_customer_summary,
    clean_producer_name
)

load_dotenv()

def scrape_all_cart_items_enhanced(page):
    """
    Enhanced cart scraping with fallback protection.
    Uses original logic but adds safety nets.
    """
    cart_items = []
    
    print("🔍 Looking for cart items...")
    
    # Use enhanced cart item detection with fallbacks
    try:
        # Try the original working method first
        items = page.locator("article[class*='cart-order_cartOrderItem']").all()
        
        if len(items) == 0:
            print("⚠️ Primary cart selector found 0 items, trying fallbacks...")
            items = get_cart_items_robust(page)
        
        print(f"🔍 Found {len(items)} cart items")
        
        if len(items) == 0:
            return {
                "error": "no_cart_items",
                "message": "No cart items found with any selector method",
                "fallbacks_tried": True
            }
        
    except Exception as e:
        print(f"❌ Cart item detection failed: {e}")
        # Try fallback system as last resort
        items = get_cart_items_robust(page)
        
        if len(items) == 0:
            return {
                "error": "cart_detection_failed", 
                "message": f"Cart detection error: {e}",
                "fallbacks_tried": True
            }
    
    # Process each item using original logic with error recovery
    for i, item in enumerate(items, 1):
        try:
            print(f"\n--- PROCESSING ITEM {i} ---")
            item_data = process_single_item_enhanced(item, page)
            
            if item_data.get("error"):
                print(f"⚠️ Item {i} had errors but continuing...")
                # Save partial data even if there are errors
                cart_items.append(item_data)
            else:
                cart_items.append(item_data)
                
        except Exception as e:
            print(f"❌ Failed to process item {i}: {e}")
            # Save what we can about the failed item
            cart_items.append({
                "error": "item_processing_failed",
                "item_number": i,
                "error_message": str(e),
                "partial_data": "Unable to extract item data"
            })
    
    return cart_items

def process_single_item_enhanced(item, page):
    """
    Process a single cart item with enhanced error handling.
    Uses original logic but adds recovery for partial failures.
    """
    item_data = {
        "type": "unknown",
        "name": "Unknown Item",
        "price": "$0.00",
        "errors": []
    }
    
    try:
        # Try to get item name using multiple selectors
        name_selectors = [
            "h3, h4",  # Original working selectors
            "[class*='product-name']",
            "[class*='item-name']", 
            "a[class*='subproduct-name']",
            ".title, .name"
        ]
        
        item_name = None
        for selector in name_selectors:
            try:
                name_elem = item.locator(selector).first
                if name_elem.count() > 0:
                    item_name = name_elem.text_content()
                    if item_name and item_name.strip():
                        break
            except Exception:
                continue
        
        if not item_name:
            item_data["errors"].append("Could not extract item name")
            item_name = "Unknown Item"
        
        item_data["name"] = item_name.strip()
        print(f"📦 Item: {item_data['name']}")
        
        # Try to get price using multiple selectors
        price_selectors = [
            "[class*='price']",  # Original working
            ".price, .cost, .amount",
            "[data-price]",
            "span:has-text('$')"
        ]
        
        price = None
        for selector in price_selectors:
            try:
                price_elem = item.locator(selector).first
                if price_elem.count() > 0:
                    price_text = price_elem.text_content()
                    if price_text and "$" in price_text:
                        price = price_text.strip()
                        break
            except Exception:
                continue
        
        if not price:
            item_data["errors"].append("Could not extract price")
            price = "$0.00"
        
        item_data["price"] = price
        print(f"   💰 Price: {price}")
        
        # Check if item is customizable (has sub-items)
        sub_items_container = item.locator("ul[class*='cart-order-line-item-subproducts']").first
        
        if sub_items_container.count() > 0:
            # This is a customizable box
            item_data["type"] = "box"
            item_data["customizable"] = True
            
            sub_items = sub_items_container.locator("li").all()
            item_data["sub_items"] = []
            
            print(f"   📋 Sub-items: {len(sub_items)}")
            
            for sub_item in sub_items:
                try:
                    sub_item_data = extract_sub_item_data_enhanced(sub_item)
                    item_data["sub_items"].append(sub_item_data)
                except Exception as e:
                    item_data["errors"].append(f"Sub-item extraction failed: {e}")
                    # Continue processing other sub-items
        else:
            # Individual item
            item_data["type"] = "individual"
            item_data["customizable"] = False
            
            # Try to get quantity
            try:
                quantity_elem = item.locator("div[class*='quantity-selector'] span, [class*='quantity']").first
                if quantity_elem.count() > 0:
                    quantity_text = quantity_elem.text_content()
                    item_data["quantity"] = quantity_text.strip()
                else:
                    item_data["quantity"] = "1"
            except Exception:
                item_data["quantity"] = "1"
                item_data["errors"].append("Could not extract quantity")
            
            print(f"   🔢 Quantity: {item_data.get('quantity', '1')}")
    
    except Exception as e:
        item_data["errors"].append(f"Major processing error: {e}")
        print(f"❌ Error processing item: {e}")
    
    return item_data

def extract_sub_item_data_enhanced(sub_item):
    """
    Extract sub-item data with enhanced error handling.
    """
    sub_item_data = {
        "name": "Unknown Sub-item",
        "quantity": "1",
        "unit": "",
        "errors": []
    }
    
    try:
        # Sub-item name
        name_selectors = [
            "a[class*='subproduct-name']",  # Original working
            ".subproduct-name",
            ".item-name", 
            "a, span, div"
        ]
        
        for selector in name_selectors:
            try:
                name_elem = sub_item.locator(selector).first
                if name_elem.count() > 0:
                    name_text = name_elem.text_content()
                    if name_text and name_text.strip():
                        sub_item_data["name"] = clean_producer_name(name_text.strip())
                        break
            except Exception:
                continue
        
        # Sub-item quantity and unit
        quantity_selectors = [
            "span[class*='quantity']",  # Original working
            ".quantity",
            "[data-quantity]"
        ]
        
        for selector in quantity_selectors:
            try:
                qty_elem = sub_item.locator(selector).first
                if qty_elem.count() > 0:
                    qty_text = qty_elem.text_content()
                    if qty_text:
                        # Parse quantity and unit
                        match = re.search(r'(\d+(?:\.\d+)?)\s*x?\s*(.+)', qty_text.strip())
                        if match:
                            sub_item_data["quantity"] = match.group(1)
                            sub_item_data["unit"] = match.group(2).strip()
                        else:
                            sub_item_data["quantity"] = qty_text.strip()
                        break
            except Exception:
                continue
        
    except Exception as e:
        sub_item_data["errors"].append(f"Sub-item extraction error: {e}")
    
    return sub_item_data

def main_enhanced():
    """
    Enhanced main function with comprehensive error recovery.
    """
    print("🌱 Enhanced Farm to People Cart Scraper")
    print("=" * 50)
    
    output_dir = Path("farm_box_data")
    output_dir.mkdir(exist_ok=True)
    
    # Initialize error tracking
    errors_encountered = []
    partial_success = False
    
    with sync_playwright() as p:
        user_data_dir = Path("browser_data")
        user_data_dir.mkdir(exist_ok=True)
        
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        try:
            print("🌱 Opening Farm to People...")
            
            # Enhanced authentication with better error reporting
            if not ensure_logged_in(page):
                error_msg = "Authentication failed after retries"
                print(f"❌ {error_msg}")
                errors_encountered.append(error_msg)
                context.close()
                return {"success": False, "errors": errors_encountered}
            
            print("✅ Successfully logged in, proceeding with cart scraping...")
            page.wait_for_timeout(2000)
            
            # Enhanced cart access
            print("📦 Opening cart...")
            try:
                cart_btn = page.locator("div.cart-button").first
                if cart_btn.count() == 0:
                    # Try fallback cart button detection
                    cart_btn = fallback_system.find_cart_button(page)
                
                if cart_btn and cart_btn.count() > 0:
                    cart_btn.click()
                    page.wait_for_timeout(3000)
                else:
                    raise Exception("Cart button not found with any selector")
                    
            except Exception as e:
                error_msg = f"Cart access failed: {e}"
                errors_encountered.append(error_msg)
                print(f"❌ {error_msg}")
                context.close()
                return {"success": False, "errors": errors_encountered}
            
            # Enhanced cart scraping
            cart_data = scrape_all_cart_items_enhanced(page)
            
            if isinstance(cart_data, dict) and cart_data.get("error"):
                errors_encountered.append(cart_data["message"])
                context.close()
                return {"success": False, "errors": errors_encountered}
            
            # Check for partial failures
            item_errors = []
            successful_items = []
            
            for item in cart_data:
                if item.get("error"):
                    item_errors.append(f"Item processing: {item.get('error_message', 'Unknown error')}")
                elif item.get("errors"):
                    item_errors.extend(item["errors"])
                    successful_items.append(item)  # Item has some data despite errors
                else:
                    successful_items.append(item)
            
            if item_errors:
                errors_encountered.extend(item_errors)
                partial_success = True
            
            # Generate outputs even with partial data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Enhanced JSON output with error tracking
            json_output = {
                "timestamp": timestamp,
                "cart_items": successful_items,
                "errors": errors_encountered,
                "partial_success": partial_success,
                "total_items_attempted": len(cart_data),
                "successful_items": len(successful_items)
            }
            
            json_file = output_dir / f"enhanced_cart_{timestamp}.json"
            with open(json_file, 'w') as f:
                json.dump(json_output, f, indent=2)
            
            # Generate customer summary if we have any data
            if successful_items:
                customer_summary = generate_customer_summary(successful_items)
                
                if errors_encountered:
                    customer_summary += "\n\n---\n"
                    customer_summary += "⚠️ **Note:** Some items may be missing due to technical issues. "
                    customer_summary += "Please check your cart directly on farmtopeople.com to verify all items."
                
                md_file = output_dir / f"enhanced_summary_{timestamp}.md"
                with open(md_file, 'w') as f:
                    f.write(customer_summary)
                
                print(f"\n🎉 COMPLETE! Files saved:")
                print(f"📊 Raw data: {json_file}")
                print(f"📝 Customer summary: {md_file}")
                
                if partial_success:
                    print(f"⚠️ Partial success: {len(successful_items)} items processed, {len(item_errors)} errors")
                else:
                    print(f"✅ Full success: {len(successful_items)} items processed")
            
            else:
                print("❌ No items could be processed successfully")
                return {"success": False, "errors": errors_encountered}
            
        except Exception as e:
            critical_error = f"Critical error: {e}"
            errors_encountered.append(critical_error)
            print(f"🚨 {critical_error}")
            return {"success": False, "errors": errors_encountered}
        
        finally:
            context.close()
    
    return {
        "success": len(successful_items) > 0,
        "items_processed": len(successful_items) if 'successful_items' in locals() else 0,
        "errors": errors_encountered,
        "partial_success": partial_success
    }

if __name__ == "__main__":
    result = main_enhanced()
    
    if result["success"]:
        if result.get("partial_success"):
            print("\n🟡 Scraping completed with some issues")
        else:
            print("\n🟢 Scraping completed successfully")
    else:
        print("\n🔴 Scraping failed")
        print("Errors encountered:")
        for error in result["errors"]:
            print(f"  • {error}")
