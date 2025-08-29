"""
Async version of the comprehensive scraper using Playwright's async API.
This is the robust solution for running within FastAPI's async context.
"""

from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import json
import re
import sys
sys.path.append(os.path.dirname(__file__))

# Load .env from project root
project_root = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=project_root / '.env', override=True)


async def scrape_customize_modal(page):
    """Scrape both selected and available items from the customize modal."""
    
    # Wait for the customize modal to be fully loaded
    await page.wait_for_selector("aside[aria-label*='Customize']", timeout=10000)
    
    # Find the customize modal container
    modal = page.locator("aside[aria-label*='Customize']").first
    
    # Get all articles (individual items)
    articles = await modal.locator("article[aria-label]").all()
    
    selected_items = []
    available_alternatives = []
    
    print(f"Found {len(articles)} total items in customize modal")
    
    for article in articles:
        try:
            # Get item name from aria-label
            item_name = await article.get_attribute("aria-label")
            
            # Get producer info
            producer_elem = article.locator("p[class*='producer'] a").first
            producer = ""
            if await producer_elem.count() > 0:
                producer = (await producer_elem.text_content()).strip()
            
            # Get unit/details info
            details_elem = article.locator("div[class*='item-details'] p").first
            unit_info = ""
            if await details_elem.count() > 0:
                unit_info = (await details_elem.text_content()).strip()
            
            # Check if item is selected (has quantity selector) or available (has Add button)
            quantity_selector = article.locator("div[class*='quantity-selector']").first
            add_button = article.locator("button:has-text('Add')").first
            
            if await quantity_selector.count() > 0:
                # This is a selected item - get the quantity
                quantity_span = quantity_selector.locator("span[class*='quantity']").first
                quantity = 1
                if await quantity_span.count() > 0:
                    try:
                        quantity = int((await quantity_span.text_content()).strip())
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
                
            elif await add_button.count() > 0:
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


async def login_to_farm_to_people_async(page, email, password):
    """Async version of login function."""
    print(f"🔐 Logging in as {email}...")
    
    # Look for email input field
    email_input = page.locator("input[placeholder*='email' i], input[type='email']").first
    if await email_input.count() > 0:
        await email_input.fill(email)
        print("✅ Filled email")
    
    # Look for password input field
    password_input = page.locator("input[type='password']").first
    if await password_input.count() > 0:
        await password_input.fill(password)
        print("✅ Filled password")
    
    # Click login button
    login_button = page.locator("button[type='submit'], button:has-text('Log in')").first
    if await login_button.count() > 0:
        await login_button.click()
        print("✅ Clicked login button")
    
    # Wait for navigation
    await page.wait_for_timeout(3000)
    
    # Check if login was successful
    if "home" in page.url or "cart" in page.url:
        print("✅ Login successful!")
        return True
    else:
        print(f"⚠️ Login may have failed. Current URL: {page.url}")
        return False


async def main(credentials=None, return_data=False):
    """
    Main async scraper function.
    
    Args:
        credentials: Dict with 'email' and 'password' keys (optional)
        return_data: If True, return the scraped data instead of just saving to file
        
    Returns:
        If return_data=True: Dict with scraped cart data
        Otherwise: None (saves to file)
    """
    output_dir = Path("../farm_box_data")
    output_dir.mkdir(exist_ok=True)
    
    async with async_playwright() as p:
        # Always use fresh browser session for multi-user support
        print("🌐 Starting fresh browser session...")
        browser = await p.chromium.launch(headless=True)  # Must be headless in cloud environment
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        
        page = await context.new_page()

        # Navigate to home where header/cart lives
        await page.goto("https://farmtopeople.com/home")
        await page.wait_for_load_state("domcontentloaded")
        await page.wait_for_timeout(2000)  # Give page time to settle

        # Check if we're on a login page or if login elements are visible
        current_url = page.url
        login_form_visible = await page.locator("input[placeholder='Enter email address']").count() > 0
        
        # Also check if we see a "Log in" link/button which indicates we're not logged in
        login_link_visible = await page.locator("a:has-text('Log in'), button:has-text('Log in')").count() > 0
        
        if "login" in current_url or login_form_visible or login_link_visible:
            print("🔐 Login page detected. Performing login...")
            
            # Get credentials - use passed credentials first, then env vars
            if credentials:
                email = credentials.get('email')
                password = credentials.get('password')
            else:
                email = os.getenv("EMAIL") or os.getenv("FTP_EMAIL")
                password = os.getenv("PASSWORD") or os.getenv("FTP_PWD")
            
            if not email or not password:
                print("❌ No credentials found in environment (EMAIL/PASSWORD)")
                print("   Looking in .env at:", project_root / '.env')
                await context.close()
                await browser.close()
                return None
            
            # Perform login
            success = await login_to_farm_to_people_async(page, email, password)
            if not success:
                print("❌ Login failed")
                await context.close()
                await browser.close()
                return None

        # Navigate to cart page
        print("🛒 Navigating to cart...")
        await page.goto("https://farmtopeople.com/cart")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)

        # Initialize results
        results = {
            "individual_items": [],
            "non_customizable_boxes": [],
            "customizable_boxes": [],
            "delivery_date": None,
            "scraped_at": datetime.now().isoformat()
        }

        # Extract delivery date
        print("\n📅 Looking for delivery date...")
        delivery_selectors = [
            "h2:has-text('Delivery')",
            "span:has-text('Delivery')",
            "div:has-text('Estimated delivery')",
            "*:has-text('Deliver on')",
            "*:has-text('Delivery scheduled')"
        ]
        
        for selector in delivery_selectors:
            elements = await page.locator(selector).all()
            for element in elements:
                text = await element.text_content()
                if text:
                    # Look for date patterns
                    date_match = re.search(r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}', text)
                    if date_match:
                        results["delivery_date"] = date_match.group(0)
                        print(f"✅ Found delivery date: {results['delivery_date']}")
                        break
            if results["delivery_date"]:
                break

        # Get all cart items
        print("\n🔍 Scanning cart items...")
        cart_items = await page.locator("li[data-testid*='cart-item'], article[aria-label]").all()
        
        print(f"Found {len(cart_items)} items in cart")

        for idx, item in enumerate(cart_items):
            try:
                # Get item name
                name_elem = item.locator("h3, h4, [class*='item-name']").first
                if await name_elem.count() == 0:
                    # Try getting from aria-label
                    aria_label = await item.get_attribute("aria-label")
                    if aria_label:
                        item_name = aria_label
                    else:
                        continue
                else:
                    item_name = (await name_elem.text_content()).strip()
                
                print(f"\n📦 Processing: {item_name}")
                
                # Check if it's a customizable box
                customize_button = item.locator("button:has-text('Customize'), a:has-text('Customize')").first
                
                if await customize_button.count() > 0:
                    # This is a customizable box
                    print(f"  🎯 Customizable box detected: {item_name}")
                    
                    # Click customize button
                    await customize_button.click()
                    await page.wait_for_timeout(2000)
                    
                    # Scrape the customize modal
                    modal_data = await scrape_customize_modal(page)
                    
                    # Structure customizable box data
                    box_data = {
                        "box_name": item_name,
                        "customizable": True,
                        "selected_items": modal_data["selected_items"],
                        "available_alternatives": modal_data["available_alternatives"],
                        "selected_count": modal_data["selected_count"],
                        "alternatives_count": modal_data["alternatives_count"]
                    }
                    
                    results["customizable_boxes"].append(box_data)
                    
                    # Close modal
                    close_button = page.locator("button[aria-label*='Close'], button:has-text('Done')").first
                    if await close_button.count() > 0:
                        await close_button.click()
                        await page.wait_for_timeout(1000)
                    
                else:
                    # Check if it's a non-customizable box (has nested items)
                    nested_items = item.locator("ul li, div[class*='box-item']").all()
                    
                    if len(await nested_items) > 0:
                        # Non-customizable box with items
                        print(f"  📦 Non-customizable box: {item_name}")
                        
                        box_items = []
                        for nested in await nested_items:
                            nested_text = (await nested.text_content()).strip()
                            if nested_text:
                                box_items.append({"name": nested_text, "quantity": 1})
                        
                        box_data = {
                            "box_name": item_name,
                            "customizable": False,
                            "selected_items": box_items,
                            "selected_count": len(box_items)
                        }
                        
                        results["non_customizable_boxes"].append(box_data)
                    
                    else:
                        # Individual item
                        print(f"  🥕 Individual item: {item_name}")
                        
                        # Get quantity
                        quantity = 1
                        quantity_elem = item.locator("input[type='number'], span[class*='quantity']").first
                        if await quantity_elem.count() > 0:
                            if await quantity_elem.get_attribute("value"):
                                quantity = int(await quantity_elem.get_attribute("value"))
                            else:
                                qty_text = await quantity_elem.text_content()
                                if qty_text and qty_text.isdigit():
                                    quantity = int(qty_text)
                        
                        # Get price
                        price = ""
                        price_elem = item.locator("span[class*='price'], p[class*='price']").first
                        if await price_elem.count() > 0:
                            price = (await price_elem.text_content()).strip()
                        
                        # Get unit info
                        unit = ""
                        unit_elem = item.locator("p[class*='unit'], span[class*='unit']").first
                        if await unit_elem.count() > 0:
                            unit = (await unit_elem.text_content()).strip()
                        
                        item_data = {
                            "name": item_name,
                            "quantity": quantity,
                            "unit": unit if unit else "1 piece",
                            "price": price,
                            "type": "individual"
                        }
                        
                        results["individual_items"].append(item_data)
                        
            except Exception as e:
                print(f"  ❌ Error processing item {idx}: {e}")
                continue

        # Save results
        if not return_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"customize_results_{timestamp}.json"
            
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"\n✅ Results saved to: {output_file}")

        # Print summary
        print("\n" + "="*50)
        print("📊 SCRAPING SUMMARY:")
        print(f"  • Individual items: {len(results['individual_items'])}")
        print(f"  • Non-customizable boxes: {len(results['non_customizable_boxes'])}")
        print(f"  • Customizable boxes: {len(results['customizable_boxes'])}")
        if results["delivery_date"]:
            print(f"  • Delivery date: {results['delivery_date']}")
        print("="*50)

        # Cleanup
        await context.close()
        await browser.close()
        
        return results if return_data else None


# For backwards compatibility - wrap async function for sync usage
def main_sync(credentials=None, return_data=False):
    """Synchronous wrapper for the async main function."""
    import asyncio
    return asyncio.run(main(credentials, return_data))


if __name__ == "__main__":
    # Run async version directly
    import asyncio
    asyncio.run(main())