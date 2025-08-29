from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import json
import re
import sys
sys.path.append(os.path.dirname(__file__))
from auth_helper import ensure_logged_in, login_to_farm_to_people

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

async def main(credentials=None, return_data=False):
    """
    Main scraper function.
    
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
                return
                
            try:
                # Fill email
                email_input = page.locator("input[placeholder='Enter email address']").first
                if await email_input.count() > 0:
                    await email_input.fill(email)
                    print(f"✅ Email entered: {email}")
                    
                    # Click LOG IN to proceed to password
                    login_btn = page.locator("button:has-text('LOG IN')").first
                    if await login_btn.count() > 0:
                        await login_btn.click()
                        await page.wait_for_timeout(2000)
                        
                        # Now fill password
                        password_input = page.locator("input[type='password']").first
                        if await password_input.count() > 0:
                            await password_input.fill(password)
                            print("✅ Password entered")
                            
                            # Click LOG IN again
                            final_login_btn = page.locator("button:has-text('LOG IN')").first
                            if await final_login_btn.count() > 0:
                                await final_login_btn.click()
                                print("✅ Login submitted, waiting for navigation...")
                                await page.wait_for_timeout(5000)
                                
                                # Verify we're logged in
                                if "login" not in page.url:
                                    print("✅ Login successful!")
                                else:
                                    print("⚠️ Still on login page, may have failed")
                            
            except Exception as e:
                print(f"❌ Login error: {e}")
        else:
            # Not on login page, use the auth helper to verify session
            print("🔐 Checking session status...")
            ensure_logged_in(page)  
        
        # The scraper can now proceed assuming it's logged in.
        print("Opening cart...")
        
        # Prefer a cart button that isn’t inside any dialog
        cart_btn = page.locator("body > div:not([role='dialog']) >> div.cart-button.ml-auto.cursor-pointer").first
        
        if await cart_btn.is_visible():
            print("✅ Cart button is visible and not in a modal. Clicking it.")
            await cart_btn.click()
            await page.wait_for_timeout(3000) # Wait for cart to open
        else:
            print("❌ Cart button not found or not visible. Trying direct navigation.")
            await page.goto("https://farmtopeople.com/cart")
            await page.wait_for_timeout(3000)

        # First, get individual cart items (non-customizable items like eggs, avocados, etc.)
        print("🔍 Checking for individual cart items...")
        articles = await page.locator("article[class*='cart-order_cartOrderItem']").all()
        individual_items = []
        
        for article in articles:
            try:
                # Check if this article has a CUSTOMIZE button (skip those, we'll handle them separately)
                customize_btn = article.locator("button:has-text('CUSTOMIZE'), button:has-text('Customize')").first
                if await customize_btn.count() > 0:
                    continue  # This is a customizable box, skip it for now
                
                # Check if it has sub-products list (non-customizable box)
                sub_list = article.locator("+ ul[class*='cart-order-line-item-subproducts']").first
                if await sub_list.count() > 0:
                    continue  # This is a box (non-customizable), skip individual item processing
                
                # This appears to be an individual item
                name_link = article.locator("a[class*='unstyled-link'][href*='/product/']").first
                if await name_link.count() == 0:
                    continue
                    
                item_name = (await name_link.text_content()).strip()
                
                # Get price
                price_elem = article.locator("p[class*='font-medium']").first
                price = ""
                if await price_elem.count() > 0:
                    price = (await price_elem.text_content()).strip()
                
                # Get quantity from select dropdown
                quantity = 1
                quantity_select = article.locator("select[id='quantity'], select[class*='cartOrderItemQuantity']").first
                
                if await quantity_select.count() > 0:
                    try:
                        # Get the selected option value
                        selected_value = await quantity_select.input_value()
                        quantity = int(selected_value)
                    except:
                        # Fallback: try to get the selected option text
                        try:
                            selected_option = quantity_select.locator("option[selected]").first
                            if await selected_option.count() > 0:
                                quantity = int((await selected_option.text_content()).strip())
                        except:
                            quantity = 1
                
                # Try to get unit info
                unit_info = ""
                unit_elements = await article.locator("p").all()
                for unit_elem in unit_elements:
                    unit_text = (await unit_elem.text_content()).strip()
                    # Skip price and farm name elements
                    if (unit_text and 
                        not unit_text.startswith("$") and 
                        "farm" not in unit_text.lower() and
                        "people" not in unit_text.lower() and
                        len(unit_text) < 50):  # Avoid long descriptions
                        unit_info = unit_text
                        break
                
                individual_item = {
                    "name": item_name,
                    "producer": "",  # Individual items don't have producer info in this context
                    "unit": unit_info,
                    "quantity": quantity,
                    "selected": True,
                    "price": price,
                    "type": "individual"
                }
                
                individual_items.append(individual_item)
                print(f"  ✅ Individual: {item_name} (qty: {quantity}) - {price}")
                
            except Exception as e:
                print(f"  ⚠️ Error processing individual item: {e}")
                continue
        
        print(f"🛒 Found {len(individual_items)} individual cart items")
        
        # Check for non-customizable boxes (like Seasonal Fruit Medley)
        print("🔍 Checking for non-customizable boxes...")
        non_customizable_boxes = []
        
        for article in articles:
            try:
                # Skip if it has a CUSTOMIZE button (we'll handle those separately)
                customize_btn = article.locator("button:has-text('CUSTOMIZE'), button:has-text('Customize')").first
                if await customize_btn.count() > 0:
                    continue
                
                # Check if it has sub-products list (this is a non-customizable box)
                sub_list = article.locator("+ ul[class*='cart-order-line-item-subproducts']").first
                if await sub_list.count() > 0:
                    # Get box name
                    name_link = article.locator("a[class*='unstyled-link'][href*='/product/']").first
                    if await name_link.count() == 0:
                        continue
                    
                    box_name = (await name_link.text_content()).strip()
                    print(f"📦 Found non-customizable box: {box_name}")
                    
                    # Get sub-items from the list
                    selected_items = []
                    sub_items = await sub_list.locator("li[class*='cart-order-line-item-subproduct']").all()
                    
                    for sub_item in sub_items:
                        name_elem = sub_item.locator("a[class*='subproduct-name']").first
                        if await name_elem.count() > 0:
                            sub_item_name = (await name_elem.text_content()).strip()
                            
                            # Extract quantity from the name (e.g. "1 Sugar Cube Cantaloupe")
                            quantity = 1
                            clean_name = sub_item_name
                            
                            match = re.match(r'^(\d+)\s+(.+)$', sub_item_name)
                            if match:
                                quantity = int(match.group(1))
                                clean_name = match.group(2)
                            
                            # Get unit info
                            unit_elem = sub_item.locator("p").first
                            unit_info = ""
                            if await unit_elem.count() > 0:
                                unit_info = (await unit_elem.text_content()).strip()
                            
                            selected_items.append({
                                "name": clean_name,
                                "producer": "",  # Non-customizable boxes don't show producer info
                                "unit": unit_info,
                                "quantity": quantity,
                                "selected": True
                            })
                            print(f"  ✅ Item: {clean_name} (qty: {quantity}) - {unit_info}")
                    
                    non_customizable_box = {
                        "box_name": box_name,
                        "selected_items": selected_items,
                        "available_alternatives": [],  # Non-customizable = no alternatives
                        "total_items": len(selected_items),
                        "selected_count": len(selected_items),
                        "alternatives_count": 0,
                        "box_index": len(non_customizable_boxes) + 1,
                        "customizable": False
                    }
                    
                    non_customizable_boxes.append(non_customizable_box)
                    
            except Exception as e:
                print(f"  ⚠️ Error processing non-customizable box: {e}")
                continue
        
        print(f"📦 Found {len(non_customizable_boxes)} non-customizable boxes")

        # Get all CUSTOMIZE buttons
        customize_btns = await page.locator("button:has-text('CUSTOMIZE'), button:has-text('Customize')").all()
        
        all_box_data = []
        
        for i, customize_btn in enumerate(customize_btns):
            try:
                # Get box name from the parent article
                article = customize_btn.locator("xpath=ancestor::article").first
                box_name = "Unknown Box"
                if await article.count() > 0:
                    name_link = article.locator("a[href*='/product/']").first
                    if await name_link.count() > 0:
                        box_name = (await name_link.text_content()).strip()
                
                print(f"\n=== PROCESSING BOX {i+1}: {box_name} ===")
                
                # Improved clicking with retries and better error handling
                box_data = None
                max_retries = 3
                
                for attempt in range(max_retries):
                    try:
                        print(f"Clicking CUSTOMIZE... (attempt {attempt + 1}/{max_retries})")
                        
                        # Ensure button is in viewport and ready
                        await customize_btn.scroll_into_view_if_needed()
                        await page.wait_for_timeout(1000)  # Longer wait for page stability
                        
                        # Wait for button to be visible and enabled
                        await customize_btn.wait_for(state="visible", timeout=5000)
                        
                        # Try different clicking methods in order
                        click_success = False
                        
                        # Method 1: Regular click
                        try:
                            await customize_btn.click()
                            click_success = True
                            print("✅ Regular click succeeded")
                        except Exception as e:
                            print(f"⚠️ Regular click failed: {e}")
                        
                        # Method 2: Force click if regular click failed
                        if not click_success:
                            try:
                                customize_btn.click(force=True)
                                click_success = True
                                print("✅ Force click succeeded")
                            except Exception as e:
                                print(f"⚠️ Force click failed: {e}")
                        
                        # Method 3: JavaScript click if both failed
                        if not click_success:
                            try:
                                await customize_btn.evaluate("element => element.click()")
                                click_success = True
                                print("✅ JavaScript click succeeded")
                            except Exception as e:
                                print(f"⚠️ JavaScript click failed: {e}")
                        
                        if not click_success:
                            raise Exception("All click methods failed")
                        
                        # Wait for modal to appear and verify it loaded
                        await page.wait_for_timeout(3000)
                        
                        # Check if modal actually opened
                        modal_present = await page.locator("aside[aria-label*='Customize']").count() > 0
                        if modal_present:
                            print("✅ Customize modal opened successfully")
                            box_data = await scrape_customize_modal(page)
                            break  # Success, exit retry loop
                        else:
                            print("⚠️ Modal didn't open, retrying...")
                            await page.wait_for_timeout(2000)  # Wait before retry
                            
                    except Exception as e:
                        print(f"❌ Attempt {attempt + 1} failed: {e}")
                        if attempt < max_retries - 1:
                            print(f"🔄 Retrying in 3 seconds...")
                            await page.wait_for_timeout(3000)
                        else:
                            print(f"❌ All {max_retries} attempts failed for {box_name}")
                
                # If we still don't have box_data, create empty structure
                if box_data is None:
                    print(f"⚠️ Could not get data for {box_name}, creating empty structure")
                    box_data = {
                        "selected_items": [],
                        "available_alternatives": [],
                        "total_items": 0,
                        "selected_count": 0,
                        "alternatives_count": 0
                    }
                box_data["box_name"] = box_name
                box_data["box_index"] = i + 1
                
                all_box_data.append(box_data)
                
                print(f"\n📊 RESULTS for {box_name}:")
                print(f"  • {box_data['selected_count']} selected items")
                print(f"  • {box_data['alternatives_count']} available alternatives")
                print(f"  • {box_data['total_items']} total items")
                
                # Close the modal (look for Close button)
                close_btn = page.locator("button:has-text('Close')").first
                if await close_btn.count() > 0:
                    await close_btn.click()
                    await page.wait_for_timeout(1000)
                else:
                    # Try ESC key
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(1000)
                
            except Exception as e:
                print(f"❌ Error processing box {i+1}: {e}")
                continue
        
        # Extract delivery date (just the raw date, handle logic downstream)
        delivery_info = {}
        try:
            print("🔍 Searching for delivery date...")
            # Broader search for delivery date on cart page
            elements_locator = page.locator("h1, h2, h3, h4, p, span, div")
            elements = await elements_locator.all()
            elements = elements[:50]  # Limit to first 50 elements
            
            found_date = False
            for elem in elements:
                text_content = await elem.text_content()
                text = text_content.strip() if text_content else ""
                # Skip empty or very long texts
                if not text or len(text) > 200:
                    continue
                    
                # Look for month names to find delivery date
                if any(month in text for month in ['January', 'February', 'March', 'April', 'May', 'June', 
                                                   'July', 'August', 'September', 'October', 'November', 'December',
                                                   'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                    delivery_info['delivery_text'] = text
                    print(f"  📅 Found delivery info: {text}")
                    found_date = True
                    break  # Take first match
                    
                # Also check for "Deliver" keyword with dates
                elif 'deliver' in text.lower() and any(char.isdigit() for char in text):
                    delivery_info['delivery_text'] = text
                    print(f"  📅 Found delivery mention: {text}")
                    found_date = True
                    break
                    
            if not found_date:
                print("  ⚠️ No delivery date found on cart page")
                # Try looking at page title or other specific locations
                try:
                    title = page.title()
                    if any(month in title for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                                         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                        delivery_info['delivery_text'] = title
                        print(f"  📅 Found in page title: {title}")
                except:
                    pass
                    
        except Exception as e:
            print(f"⚠️ Could not extract delivery date: {e}")
        
        # Combine all data for output
        complete_results = {
            "individual_items": individual_items,
            "non_customizable_boxes": non_customizable_boxes,
            "customizable_boxes": all_box_data
        }
        
        # Add delivery info if found
        if delivery_info:
            complete_results["delivery_info"] = delivery_info
        
        # Save results to file (always, for debugging)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"customize_results_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(complete_results, f, indent=2)
        
        print(f"\n🎉 COMPLETE! Results saved to: {output_file}")
        
        # Return data if requested
        if return_data:
            print("📤 Returning cart data to caller...")
            await context.close()
            await browser.close()
            return complete_results
        print(f"\n📈 SUMMARY:")
        if individual_items:
            print(f"  Individual Items:")
            print(f"    🛒 {len(individual_items)} items")
        for box_data in non_customizable_boxes:
            print(f"  {box_data['box_name']} (non-customizable):")
            print(f"    ✅ {box_data['selected_count']} items")
        for box_data in all_box_data:
            print(f"  {box_data['box_name']} (customizable):")
            print(f"    ✅ {box_data['selected_count']} selected")
            print(f"    🔄 {box_data['alternatives_count']} alternatives")
        
        await context.close()
        await browser.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
