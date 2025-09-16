from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timedelta
import json
import re
import pytz
import sys
sys.path.append(os.path.dirname(__file__))
from auth_helper import ensure_logged_in, login_to_farm_to_people

# Add path for server modules
sys.path.append(str(Path(__file__).resolve().parent.parent / 'server'))
try:
    import supabase_client
except ImportError:
    print("⚠️ Could not import supabase_client - database save will be skipped")
    supabase_client = None

# Load .env from project root
project_root = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=project_root / '.env', override=True)

# Detect if we're running in production (Railway) or local
IS_PRODUCTION = os.getenv('RAILWAY_ENVIRONMENT', '').lower() == 'production' or os.getenv('RAILWAY_PROJECT_ID', None) is not None

# Adjust timeouts based on environment (optimized for performance)
TIMEOUT_MULTIPLIER = 1.0  # Removed production multiplier for better performance

def get_timeout(base_ms):
    """Get adjusted timeout based on environment"""
    adjusted = int(base_ms * TIMEOUT_MULTIPLIER)
    if IS_PRODUCTION and adjusted != base_ms:
        print(f"⏱️ Timeout adjusted for production: {base_ms}ms → {adjusted}ms")
    return adjusted

def parse_delivery_date(delivery_text: str) -> datetime:
    """Parse delivery date from text and return as datetime object."""
    if not delivery_text:
        return None
    
    try:
        # Common patterns in Farm to People delivery text
        import re
        
        # Pattern: "Sun, Aug 31, 10:00AM - 4:00PM"
        pattern1 = r'(\w+),\s+(\w+)\s+(\d+)'
        match = re.search(pattern1, delivery_text)
        
        if match:
            month_name = match.group(2)
            day = int(match.group(3))
            current_year = datetime.now().year
            
            # Convert month name to number
            months = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                     'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
                     'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
                     'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12}
            
            month = months.get(month_name, None)
            if month:
                return datetime(current_year, month, day)
    
    except Exception as e:
        print(f"⚠️ Error parsing delivery date '{delivery_text}': {e}")
    
    return None

def calculate_cart_lock_time(delivery_date: datetime) -> datetime:
    """Calculate when cart locks: 11:59 AM ET the day before delivery."""
    if not delivery_date:
        return None
    
    # Cart locks the day before delivery at 11:59 AM ET
    lock_date = delivery_date - timedelta(days=1)
    eastern = pytz.timezone('US/Eastern')
    
    # Set to 11:59 AM ET
    lock_datetime = eastern.localize(
        datetime(lock_date.year, lock_date.month, lock_date.day, 11, 59, 0)
    )
    
    return lock_datetime

def get_cart_status(delivery_text: str) -> dict:
    """Get cart status based on delivery date."""
    delivery_date = parse_delivery_date(delivery_text)
    if not delivery_date:
        return {"status": "unknown", "reason": "Could not parse delivery date"}
    
    lock_time = calculate_cart_lock_time(delivery_date)
    if not lock_time:
        return {"status": "unknown", "reason": "Could not calculate lock time"}
    
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    
    if now >= lock_time:
        return {
            "status": "locked",
            "reason": "Cart locked",
            "lock_time": lock_time,
            "delivery_date": delivery_date,
            "locked_ago_minutes": int((now - lock_time).total_seconds() / 60)
        }
    else:
        minutes_until_lock = int((lock_time - now).total_seconds() / 60)
        return {
            "status": "active",
            "reason": "Cart still active",
            "lock_time": lock_time,
            "delivery_date": delivery_date,
            "minutes_until_lock": minutes_until_lock,
            "should_backup_soon": minutes_until_lock <= 30  # Backup if locking within 30 mins
        }

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
            
            # Get producer info with enhanced detection
            producer = ""

            # Try multiple producer selectors
            producer_selectors = [
                "p[class*='producer'] a",       # Original selector
                "a[href*='/farms/']",           # Direct farm links
                "a[href*='/producers/']",       # Producer links
                "a[href*='/growers/']",         # Grower links
                ".producer-name",               # CSS class for producer
                ".farm-name",                   # CSS class for farm
                "[data-producer]",              # Data attribute
                "[title*='Farm']",              # Title attribute with 'Farm'
                "[title*='Producer']",          # Title attribute with 'Producer'
            ]

            for selector in producer_selectors:
                try:
                    producer_elem = article.locator(selector).first
                    if await producer_elem.count() > 0:
                        producer_text = (await producer_elem.text_content()).strip()
                        if producer_text and len(producer_text) > 2:  # Valid producer name
                            producer = producer_text
                            print(f"    🏪 Box item producer via {selector}: {producer}")
                            break
                except:
                    continue
            
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

async def main(credentials=None, return_data=False, phone_number=None, force_save=False):
    """
    Main scraper function.

    Args:
        credentials: Dict with 'email' and 'password' keys (optional)
        return_data: If True, return the scraped data instead of just saving to file

    Returns:
        If return_data=True: Dict with scraped cart data
        Otherwise: None (saves to file)
    """
    print(f"🚀 Starting comprehensive scraper for phone: {phone_number}")

    # CRITICAL: Extract credentials at the very beginning to prevent scope issues
    email = None
    password = None
    if credentials:
        email = credentials.get('email')
        password = credentials.get('password')
    else:
        email = os.getenv("EMAIL") or os.getenv("FTP_EMAIL")
        password = os.getenv("PASSWORD") or os.getenv("FTP_PWD")

    print(f"🔐 Using email: {email}")
    print(f"⏱️ Force save: {force_save}")
    print(f"📊 Return data: {return_data}")

    import time
    start_time = time.time()

    output_dir = Path("../farm_box_data")
    output_dir.mkdir(exist_ok=True)

    async with async_playwright() as p:
        print("🌐 Starting browser session...")
        browser = await p.chromium.launch(headless=True)  # Must be headless in cloud environment
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})

        page = await context.new_page()

        # Session caching disabled for debugging - always do fresh login
        # TODO: Re-enable session caching after fixing core issues
        session_used = False

        # Navigate and potentially login (always fresh for now)
        if not session_used:
            # Navigate to home where header/cart lives
            await page.goto("https://farmtopeople.com/home")
            await page.wait_for_load_state("domcontentloaded")

            # Smart wait: Look for either login elements or cart elements (indicates page is ready)
            try:
                await page.wait_for_selector("input[placeholder='Enter email address'], .cart-button", timeout=5000)
                print("✅ Page ready - found login or cart elements")
            except:
                # Fallback to shorter timeout if selectors not found
                await page.wait_for_timeout(get_timeout(1500))  # Reduced from 2500ms
                print("⚠️ Using fallback timeout for page settle")

            # Check if we're on a login page or if login elements are visible
            current_url = page.url
            login_form_visible = await page.locator("input[placeholder='Enter email address']").count() > 0

            # Also check if we see a "Log in" link/button which indicates we're not logged in
            login_link_visible = await page.locator("a:has-text('Log in'), button:has-text('Log in')").count() > 0

            if "login" in current_url or login_form_visible or login_link_visible:
                print(f"🔐 Login page detected. Performing login... (elapsed: {time.time() - start_time:.1f}s)")
            
            # Credentials already extracted at the top of the function
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
                        await page.wait_for_timeout(get_timeout(2500))  # Wait after login click (increased for reliability)
                        
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
                                await page.wait_for_timeout(get_timeout(4000))  # Wait for zipcode modal (increased for reliability)

                                # Add additional wait for login to fully settle
                                await page.wait_for_load_state("networkidle", timeout=10000)
                                
                                # Verify we're logged in
                                if "login" not in page.url:
                                    print("✅ Login successful!")

                                    # Save session cookies for future use
                                    if phone_number and email:
                                        try:
                                            cookies = await context.cookies()
                                            # Reuse the sys.path setup from above if not already imported
                                            try:
                                                from services.cache_service import CacheService
                                            except ImportError:
                                                import sys
                                                import os as os_module  # Avoid scope conflicts
                                                server_path = os_module.path.join(os_module.path.dirname(__file__), '../server')
                                                if server_path not in sys.path:
                                                    sys.path.append(server_path)
                                                from services.cache_service import CacheService

                                            CacheService.set_browser_session(phone_number, email, cookies, ttl=3600)  # 1 hour
                                            print(f"💾 Saved browser session for {phone_number}")
                                        except Exception as session_error:
                                            print(f"⚠️ Failed to save session: {session_error}")

                                else:
                                    print("⚠️ Still on login page, may have failed")
                            
            except Exception as e:
                print(f"❌ Login error: {e}")
        else:
            # Not on login page, use the auth helper to verify session
            print("🔐 Checking session status...")
            ensure_logged_in(page)  
        
        # The scraper can now proceed assuming it's logged in.
        print(f"🛒 Opening cart... (elapsed: {time.time() - start_time:.1f}s)")
        
        # Prefer a cart button that isn’t inside any dialog
        cart_btn = page.locator("body > div:not([role='dialog']) >> div.cart-button.ml-auto.cursor-pointer").first
        
        if await cart_btn.is_visible():
            print("✅ Cart button is visible and not in a modal. Clicking it.")
            await cart_btn.click()

            # Smart wait: Look for cart articles to appear (indicates cart has loaded)
            try:
                await page.wait_for_selector("article[class*='cart-order_cartOrderItem']", timeout=5000)
                print("✅ Cart loaded - found cart articles")
            except:
                # Fallback timeout if cart articles not found
                await page.wait_for_timeout(get_timeout(2000))  # Reduced from 3000ms
                print("⚠️ Using fallback timeout for cart load")
        else:
            print("❌ Cart button not found or not visible. Trying direct navigation.")
            await page.goto("https://farmtopeople.com/cart")

            # Smart wait: Look for cart articles after direct navigation
            try:
                await page.wait_for_selector("article[class*='cart-order_cartOrderItem']", timeout=5000)
                print("✅ Cart page loaded - found cart articles")
            except:
                # Fallback timeout if cart articles not found
                await page.wait_for_timeout(get_timeout(2000))  # Reduced from 3000ms
                print("⚠️ Using fallback timeout for cart page load")

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
                
                # Try to get unit info and producer/farm name with enhanced detection
                unit_info = ""
                producer = ""

                # First, try specific producer selectors
                producer_selectors = [
                    "a[href*='/farms/']",           # Direct farm links
                    "a[href*='/producers/']",       # Producer links
                    "a[href*='/growers/']",         # Grower links
                    "p[class*='producer'] a",       # Producer class with link
                    "p[class*='farm'] a",           # Farm class with link
                    ".producer-name",               # CSS class for producer
                    ".farm-name",                   # CSS class for farm
                    "[data-producer]",              # Data attribute
                    "[title*='Farm']",              # Title attribute with 'Farm'
                    "[title*='Producer']",          # Title attribute with 'Producer'
                ]

                for selector in producer_selectors:
                    try:
                        producer_elem = article.locator(selector).first
                        if await producer_elem.count() > 0:
                            producer_text = (await producer_elem.text_content()).strip()
                            if producer_text and len(producer_text) > 2:  # Valid producer name
                                producer = producer_text
                                print(f"    🏪 Found producer via {selector}: {producer}")
                                break
                    except:
                        continue

                # If no producer found via specific selectors, try text-based detection
                if not producer:
                    unit_elements = await article.locator("p, span, div, a").all()
                    for unit_elem in unit_elements:
                        unit_text = (await unit_elem.text_content()).strip()
                        if unit_text and not unit_text.startswith("$") and len(unit_text) < 100:
                            # Check if this is a farm/producer name (expanded patterns)
                            farm_indicators = [
                                'Farm', 'Farms', 'Acres', 'Ranch', 'Creamery', 'Dairy', 'Orchard', 'Grove',
                                'Co.', 'Company', 'Bros', 'Brothers', 'Sons', 'Valley', 'Hills', 'Gardens',
                                'Organics', 'Organic', 'Family', 'Heritage', 'Fresh', 'Natural', 'Estate',
                                'Harvest', 'Growers', 'Market', 'Meadow', 'Ridge', 'Creek', 'Mountain',
                                'Cooperative', 'Coop', 'Collective', 'Union', 'Association', 'Group',
                                'Local', 'Community', 'Artisan', 'Pasture', 'Grass', 'Free Range',
                                'Sustainable', 'Homestead', 'Woods', 'Fields', 'Barn', 'Mill'
                            ]

                            # Look for "from [Farm Name]" pattern
                            if unit_text.lower().startswith('from '):
                                producer = unit_text[5:]  # Remove "from " prefix
                                print(f"    🏪 Found producer via 'from' pattern: {producer}")
                                break
                            # Look for farm indicators
                            elif any(word in unit_text for word in farm_indicators):
                                producer = unit_text
                                print(f"    🏪 Found producer via farm indicators: {producer}")
                                break
                            # Look for patterns like "by [Farm Name]"
                            elif unit_text.lower().startswith('by '):
                                producer = unit_text[3:]  # Remove "by " prefix
                                print(f"    🏪 Found producer via 'by' pattern: {producer}")
                                break

                # Get unit info from remaining elements (if no producer found in them)
                if not unit_info:
                    unit_elements = await article.locator("p").all()
                    for unit_elem in unit_elements:
                        unit_text = (await unit_elem.text_content()).strip()
                        if (unit_text and not unit_text.startswith("$") and
                            unit_text != producer and  # Don't use producer text as unit
                            "people" not in unit_text.lower() and
                            len(unit_text) < 50):
                            unit_info = unit_text
                            break
                
                individual_item = {
                    "name": item_name,
                    "producer": producer,  # Now includes farm name if found
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
        print(f"🔍 Checking for non-customizable boxes... (elapsed: {time.time() - start_time:.1f}s)")
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
                    
                    # Try to find price for non-customizable box
                    box_price = ""
                    price_elem = article.locator("p[class*='font-medium'], span[class*='price'], p:has-text('$'), span:has-text('$')").first
                    if await price_elem.count() > 0:
                        price_text = (await price_elem.text_content()).strip()
                        # Extract just the price part
                        import re
                        price_match = re.search(r'\$[\d,]+\.?\d*', price_text)
                        if price_match:
                            box_price = price_match.group()
                            print(f"💰 Found box price: {box_price}")
                    
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
                        "price": box_price,
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
        print(f"🎯 Processing customizable boxes... (elapsed: {time.time() - start_time:.1f}s)")
        customize_btns = await page.locator("button:has-text('CUSTOMIZE'), button:has-text('Customize')").all()

        print(f"🔍 Found {len(customize_btns)} customizable boxes to process")
        all_box_data = []
        
        for i, customize_btn in enumerate(customize_btns):
            try:
                print(f"📦 Processing customizable box {i+1}/{len(customize_btns)}... (elapsed: {time.time() - start_time:.1f}s)")
                # Get box name and price from the parent article
                article = customize_btn.locator("xpath=ancestor::article").first
                box_name = "Unknown Box"
                box_price = ""
                if await article.count() > 0:
                    name_link = article.locator("a[href*='/product/']").first
                    if await name_link.count() > 0:
                        box_name = (await name_link.text_content()).strip()
                    
                    # Try to find price - look for elements with $ symbol
                    price_elem = article.locator("p[class*='font-medium'], span[class*='price'], p:has-text('$'), span:has-text('$')").first
                    if await price_elem.count() > 0:
                        price_text = (await price_elem.text_content()).strip()
                        # Extract just the price part (handle cases like "$45.99" or "Total: $45.99")
                        import re
                        price_match = re.search(r'\$[\d,]+\.?\d*', price_text)
                        if price_match:
                            box_price = price_match.group()
                            print(f"💰 Found box price: {box_price}")
                
                print(f"\n=== PROCESSING BOX {i+1}: {box_name} ===")
                
                # Improved clicking with retries and better error handling
                box_data = None
                max_retries = 3
                
                for attempt in range(max_retries):
                    try:
                        print(f"Clicking CUSTOMIZE... (attempt {attempt + 1}/{max_retries})")
                        
                        # Ensure button is in viewport and ready
                        await customize_btn.scroll_into_view_if_needed()
                        await page.wait_for_timeout(get_timeout(1500))  # Wait for page stability (increased for reliability)
                        
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
                                await customize_btn.click(force=True)
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
                        await page.wait_for_timeout(get_timeout(2500))  # Wait for modal (increased for reliability)
                        
                        # Check if modal actually opened
                        modal_present = await page.locator("aside[aria-label*='Customize']").count() > 0
                        if modal_present:
                            print("✅ Customize modal opened successfully")

                            # Wait for modal content to fully load (Farm to People loads dynamically)
                            await page.wait_for_timeout(3000)

                            # DEBUG: Uncomment below for diagnostic logging when debugging stale data:
                            # modal = page.locator("aside[aria-label*='Customize']").first
                            # articles = await modal.locator("article[aria-label]").all()
                            # print(f"🔍 Found {len(articles)} items in modal")
                            # for i, article in enumerate(articles[:3]):
                            #     name = await article.get_attribute("aria-label")
                            #     print(f"  Item {i+1}: {name}")
                            # nectarine_count = await modal.locator("article[aria-label*='Nectarine']").count()
                            # peach_count = await modal.locator("article[aria-label*='Peach']").count()
                            # print(f"📊 Modal check - Nectarines: {nectarine_count}, Peaches: {peach_count}")

                            box_data = await scrape_customize_modal(page)
                            break  # Success, exit retry loop
                        else:
                            print("⚠️ Modal didn't open, retrying...")
                            await page.wait_for_timeout(get_timeout(2000))  # Wait before retry (increased for reliability)
                            
                    except Exception as e:
                        print(f"❌ Attempt {attempt + 1} failed: {e}")
                        if attempt < max_retries - 1:
                            print(f"🔄 Retrying in 3 seconds...")
                            await page.wait_for_timeout(get_timeout(3500))  # Wait after failed attempt (increased for reliability)
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
                if box_price:
                    box_data["price"] = box_price
                
                all_box_data.append(box_data)
                
                print(f"\n📊 RESULTS for {box_name}:")
                print(f"  • {box_data['selected_count']} selected items")
                print(f"  • {box_data['alternatives_count']} available alternatives")
                print(f"  • {box_data['total_items']} total items")
                
                # Close the modal (look for Close button)
                close_btn = page.locator("button:has-text('Close')").first
                if await close_btn.count() > 0:
                    await close_btn.click()
                    await page.wait_for_timeout(get_timeout(500))  # Wait for modal close
                else:
                    # Try ESC key
                    await page.keyboard.press("Escape")
                    await page.wait_for_timeout(get_timeout(500))  # Wait for ESC close
                
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
                if not text or len(text) > 500:
                    continue

                # Look for month names to find delivery date
                if any(month in text for month in ['January', 'February', 'March', 'April', 'May', 'June',
                                                   'July', 'August', 'September', 'October', 'November', 'December',
                                                   'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):

                    # Extract just the delivery date part using regex
                    import re

                    # Try multiple patterns to extract delivery date
                    patterns = [
                        r'Shopping for:\s*([A-Za-z]+,\s*[A-Za-z]+\s*\d+,\s*\d+:\d+[AP]M\s*-\s*\d+:\d+[AP]M)',  # "Shopping for: Wed, Sep 17, 10:00AM - 3:00PM"
                        r'([A-Za-z]+,\s*[A-Za-z]+\s*\d+,\s*\d+:\d+[AP]M\s*-\s*\d+:\d+[AP]M)',  # "Wed, Sep 17, 10:00AM - 3:00PM"
                        r'([A-Za-z]+\s*\d+,\s*\d+:\d+[AP]M\s*-\s*\d+:\d+[AP]M)',  # "Sep 17, 10:00AM - 3:00PM"
                        r'([A-Za-z]+,\s*[A-Za-z]+\s*\d+)',  # "Wed, Sep 17"
                        r'([A-Za-z]+\s*\d+)',  # "Sep 17"
                    ]

                    extracted_date = None
                    for pattern in patterns:
                        match = re.search(pattern, text)
                        if match:
                            extracted_date = match.group(1).strip()
                            print(f"  📅 Extracted delivery date: '{extracted_date}' from: '{text[:100]}...'")
                            break

                    # Use extracted date if found, otherwise use original text (but truncated)
                    if extracted_date:
                        delivery_info['delivery_text'] = extracted_date
                        print(f"  ✅ Using extracted date for comparison: '{extracted_date}'")
                        found_date = True
                        break
                    else:
                        # Fallback: use original text but warn about potential parsing issues
                        delivery_info['delivery_text'] = text
                        print(f"  ⚠️ Could not extract clean date, using full text: {text[:100]}...")
                        found_date = True
                        break

                # Also check for "Deliver" keyword with dates and apply same extraction
                elif 'deliver' in text.lower() and any(char.isdigit() for char in text):
                    print(f"  📅 Found delivery mention: {text[:100]}...")

                    # Apply same regex extraction for delivery mentions
                    import re
                    patterns = [
                        r'Shopping for:\s*([A-Za-z]+,\s*[A-Za-z]+\s*\d+,\s*\d+:\d+[AP]M\s*-\s*\d+:\d+[AP]M)',  # "Shopping for: Wed, Sep 17, 10:00AM - 3:00PM"
                        r'([A-Za-z]+,\s*[A-Za-z]+\s*\d+,\s*\d+:\d+[AP]M\s*-\s*\d+:\d+[AP]M)',  # "Wed, Sep 17, 10:00AM - 3:00PM"
                        r'([A-Za-z]+\s*\d+,\s*\d+:\d+[AP]M\s*-\s*\d+:\d+[AP]M)',  # "Sep 17, 10:00AM - 3:00PM"
                        r'([A-Za-z]+,\s*[A-Za-z]+\s*\d+)',  # "Wed, Sep 17"
                        r'([A-Za-z]+\s*\d+)',  # "Sep 17"
                    ]

                    extracted_date = None
                    for pattern in patterns:
                        match = re.search(pattern, text)
                        if match:
                            extracted_date = match.group(1).strip()
                            print(f"  📅 Extracted delivery date from 'deliver' mention: '{extracted_date}' from: '{text[:100]}...'")
                            break

                    # Use extracted date if found, otherwise use original text
                    if extracted_date:
                        delivery_info['delivery_text'] = extracted_date
                        print(f"  ✅ Using extracted date for comparison: '{extracted_date}'")
                    else:
                        delivery_info['delivery_text'] = text
                        print(f"  ⚠️ Could not extract clean date from deliver mention, using full text: {text[:100]}...")

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
            "customizable_boxes": all_box_data,
            "scraped_timestamp": datetime.now().isoformat()  # Add timestamp
        }
        
        # Add delivery info if found
        if delivery_info:
            complete_results["delivery_info"] = delivery_info
        
        # Save results to file (always, for debugging)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"customize_results_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(complete_results, f, indent=2)
        
        # Save to database if phone number provided and supabase client available
        if phone_number and supabase_client:
            try:
                # Extract delivery date from delivery_info
                delivery_date_text = None
                if delivery_info and 'delivery_text' in delivery_info:
                    delivery_date_text = delivery_info['delivery_text']
                
                # Get cart status based on delivery date
                cart_status = get_cart_status(delivery_date_text) if delivery_date_text else {"status": "unknown"}
                print(f"🕒 Cart status: {cart_status['status']} - {cart_status.get('reason', 'No reason')}")
                
                if cart_status['status'] == 'active' and cart_status.get('minutes_until_lock'):
                    print(f"⏰ Cart locks in {cart_status['minutes_until_lock']} minutes")
                elif cart_status['status'] == 'locked' and cart_status.get('locked_ago_minutes'):
                    print(f"🔒 Cart locked {cart_status['locked_ago_minutes']} minutes ago")
                
                # Decision logic for saving cart data
                should_save = False
                save_reason = ""

                existing_cart = supabase_client.get_latest_cart_data(phone_number)

                # Force save overrides all other logic (when user explicitly clicks "Refresh Cart")
                if force_save:
                    should_save = True
                    save_reason = "Force save requested - user explicitly refreshed cart"
                elif cart_status['status'] == 'active':
                    if cart_status.get('should_backup_soon'):
                        # Cart is about to lock - definitely save
                        should_save = True
                        save_reason = f"Cart locks in {cart_status['minutes_until_lock']} minutes - backup needed"
                    elif not existing_cart:
                        # No existing cart data - save this one
                        should_save = True
                        save_reason = "No existing cart data - saving first capture"
                    else:
                        # Cart is active but not about to lock, and we have existing data
                        # Check if this looks like the same week's cart by comparing dates properly
                        try:
                            stored_delivery = existing_cart.get('delivery_date', '')

                            # Parse both dates to compare them properly
                            current_parsed_date = parse_delivery_date(delivery_date_text)
                            stored_parsed_date = None

                            if stored_delivery:
                                try:
                                    # Handle different stored date formats
                                    if 'T' in stored_delivery:  # ISO format from database
                                        # Use datetime from top-level import to avoid scope issues
                                        stored_parsed_date = datetime.fromisoformat(stored_delivery.replace('Z', '+00:00'))
                                        print(f"✅ Parsed stored delivery date: {stored_parsed_date}")
                                    else:  # Text format
                                        stored_parsed_date = parse_delivery_date(stored_delivery)
                                        print(f"✅ Parsed stored delivery date via parse_delivery_date: {stored_parsed_date}")
                                except Exception as date_error:
                                    print(f"⚠️ Could not parse stored delivery date: {stored_delivery} - Error: {date_error}")
                                    stored_parsed_date = None

                            # Compare dates (ignore time, just compare the date part)
                            dates_match = False
                            current_is_newer = False

                            if current_parsed_date and stored_parsed_date:
                                dates_match = current_parsed_date.date() == stored_parsed_date.date()
                                current_is_newer = current_parsed_date.date() > stored_parsed_date.date()

                            if dates_match:
                                should_save = True
                                save_reason = "Same delivery date - updating cart data"
                            elif current_is_newer:
                                should_save = True
                                save_reason = f"Newer delivery date detected - updating to latest cart"
                            else:
                                should_save = False
                                save_reason = f"Different delivery date (stored: '{stored_delivery}' vs current: '{delivery_date_text}') - preserving existing data"

                        except Exception as date_comparison_error:
                            # If ANY part of date comparison fails, default to saving fresh data
                            print(f"🚨 Date comparison completely failed: {date_comparison_error}")
                            print("🔄 Defaulting to saving fresh cart data since comparison failed")
                            should_save = True
                            save_reason = "Date comparison failed - saving fresh cart data"
                
                elif cart_status['status'] == 'locked':
                    # Cart is locked - don't overwrite, this is likely next week's cart
                    should_save = False
                    save_reason = "Cart is locked - this might be next week's cart, preserving existing data"
                
                else:
                    # Unknown status - be conservative
                    if not existing_cart:
                        should_save = True
                        save_reason = "Unknown cart status but no existing data - saving"
                    else:
                        should_save = False
                        save_reason = "Unknown cart status with existing data - preserving existing data"
                
                print(f"💭 Save decision: {save_reason}")
                
                if should_save:
                    success = supabase_client.save_latest_cart_data(phone_number, complete_results, delivery_date_text)
                    if success:
                        print(f"💾 Cart data saved to database for {phone_number}")

                        # CRITICAL: Cache fresh data to Redis immediately
                        try:
                            import sys
                            import os
                            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
                            from server.services.cache_service import CacheService

                            # Cache for 2 hours (7200 seconds)
                            CacheService.set_cart(phone_number, complete_results, ttl=7200)
                            print(f"🔥 Cart data cached to Redis for {phone_number} (2hr TTL)")
                        except Exception as cache_error:
                            print(f"⚠️ Redis cache failed (non-critical): {cache_error}")
                    else:
                        print(f"⚠️ Failed to save cart data to database")
                else:
                    print(f"🔒 Skipping database save: {save_reason}")
                    
            except Exception as e:
                print(f"⚠️ Database save error: {e}")
        
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
