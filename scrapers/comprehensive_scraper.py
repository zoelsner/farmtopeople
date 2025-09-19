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
                
                # Try to detect category from section header
                category = "produce"  # default
                try:
                    # Look for section header above this item
                    parent = await item.locator("..").first
                    section_header = await parent.locator("xpath=preceding::h3[1]").first
                    if await section_header.count() > 0:
                        header_text = (await section_header.text_content()).strip().lower()
                        if "protein" in header_text:
                            category = "protein"
                        elif "grocery" in header_text or "pantry" in header_text:
                            category = "grocery"
                        elif "produce" in header_text:
                            category = "produce"
                except:
                    pass

                selected_items.append({
                    "name": item_name,
                    "producer": producer,
                    "unit": unit_info,
                    "quantity": quantity,
                    "selected": True,
                    "category": category
                })
                print(f"  ✅ Selected: {item_name} (qty: {quantity}) - {unit_info}")
                
            elif await add_button.count() > 0:
                # This is an available alternative
                # Try to detect category from section header
                category = "produce"  # default
                try:
                    parent = await item.locator("..").first
                    section_header = await parent.locator("xpath=preceding::h3[1]").first
                    if await section_header.count() > 0:
                        header_text = (await section_header.text_content()).strip().lower()
                        if "protein" in header_text:
                            category = "protein"
                        elif "grocery" in header_text or "pantry" in header_text:
                            category = "grocery"
                except:
                    pass

                available_alternatives.append({
                    "name": item_name,
                    "producer": producer,
                    "unit": unit_info,
                    "quantity": 0,
                    "selected": False,
                    "category": category
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


def detect_and_store_swaps(phone_number, new_cart_data, delivery_date):
    """
    Detect swaps by comparing new cart with previous cart data.
    Only detects clear 1:1 swaps (one item removed, one item added in same box).

    Args:
        phone_number: User's phone number
        new_cart_data: New cart data from scraper
        delivery_date: Delivery date string

    Returns:
        List of detected swap dictionaries
    """
    if not supabase_client:
        print("⚠️ Supabase not available - skipping swap detection")
        return []

    try:
        # Get previous cart data
        previous_cart = supabase_client.get_latest_cart_data(phone_number)
        if not previous_cart or not previous_cart.get('cart_data'):
            print("📦 No previous cart data found - skipping swap detection")
            return []

        old_cart_data = previous_cart['cart_data']
        detected_swaps = []

        # Check each box type for swaps
        for box_type in ['customizable_boxes', 'non_customizable_boxes']:
            old_boxes = old_cart_data.get(box_type, [])
            new_boxes = new_cart_data.get(box_type, [])

            # Match boxes by name
            for new_box in new_boxes:
                box_name = new_box.get('box_name', '')
                if not box_name:
                    continue

                # Find corresponding old box
                old_box = None
                for ob in old_boxes:
                    if ob.get('box_name') == box_name:
                        old_box = ob
                        break

                if not old_box:
                    continue  # New box, no comparison possible

                # Compare selected items
                old_items = set()
                new_items = set()

                for item in old_box.get('selected_items', []):
                    old_items.add(item.get('name', ''))

                for item in new_box.get('selected_items', []):
                    new_items.add(item.get('name', ''))

                # Find differences
                removed_items = old_items - new_items
                added_items = new_items - old_items

                # Clear 1:1 swaps only (keeps it simple)
                if len(removed_items) == 1 and len(added_items) == 1:
                    from_item = list(removed_items)[0]
                    to_item = list(added_items)[0]

                    if from_item and to_item:  # Make sure neither is empty
                        swap_data = {
                            'phone': phone_number,
                            'delivery_date': delivery_date[:10] if isinstance(delivery_date, str) else str(delivery_date),  # Ensure YYYY-MM-DD format
                            'box_name': box_name,
                            'from_item': from_item,
                            'to_item': to_item
                        }

                        # Save to database
                        if supabase_client.save_swap_history(swap_data):
                            detected_swaps.append(swap_data)

        return detected_swaps

    except Exception as e:
        print(f"❌ Error in swap detection: {e}")
        return []


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
    import time
    from datetime import datetime as dt

    def log_progress(message, elapsed=None):
        """Helper function to log with timestamp and elapsed time."""
        timestamp = dt.now().strftime("%H:%M:%S.%f")[:-3]
        if elapsed is not None:
            print(f"[{timestamp}] {message} (elapsed: {elapsed:.1f}s)")
        else:
            print(f"[{timestamp}] {message}")

    start_time = time.time()
    log_progress(f"🚀 Starting comprehensive scraper for phone: {phone_number}")

    # CRITICAL: Extract credentials at the very beginning to prevent scope issues
    email = None
    password = None
    if credentials:
        email = credentials.get('email')
        password = credentials.get('password')
        log_progress("📋 Using provided credentials")
    else:
        email = os.getenv("EMAIL") or os.getenv("FTP_EMAIL")
        password = os.getenv("PASSWORD") or os.getenv("FTP_PWD")
        log_progress("📋 Using environment credentials")

    log_progress(f"🔐 Email: {email}")
    log_progress(f"⚙️ Force save: {force_save}, Return data: {return_data}")

    output_dir = Path("../farm_box_data")
    output_dir.mkdir(exist_ok=True)

    async with async_playwright() as p:
        log_progress("🌐 Initializing Playwright...", time.time() - start_time)
        browser = await p.chromium.launch(headless=True)  # Must be headless in cloud environment
        log_progress("🌐 Browser launched", time.time() - start_time)
        context = await browser.new_context(viewport={"width": 1920, "height": 1080})
        log_progress("🌐 Browser context created", time.time() - start_time)

        page = await context.new_page()
        log_progress("📄 New page created", time.time() - start_time)

        # Session caching disabled for debugging - always do fresh login
        # TODO: Re-enable session caching after fixing core issues
        session_used = False

        # Navigate and potentially login (always fresh for now)
        if not session_used:
            # Navigate to home where header/cart lives
            log_progress("🔗 Navigating to farmtopeople.com/home...", time.time() - start_time)
            await page.goto("https://farmtopeople.com/home")
            log_progress("✅ Page loaded", time.time() - start_time)
            await page.wait_for_load_state("domcontentloaded")
            log_progress("✅ DOM content loaded", time.time() - start_time)

            # Smart wait: Look for either login elements or cart elements (indicates page is ready)
            try:
                log_progress("⏳ Waiting for login or cart elements...", time.time() - start_time)
                await page.wait_for_selector("input[placeholder='Enter email address'], .cart-button", timeout=5000)
                log_progress("✅ Page ready - found login or cart elements", time.time() - start_time)
            except:
                # Fallback to shorter timeout if selectors not found
                await page.wait_for_timeout(get_timeout(1500))  # Reduced from 2500ms
                log_progress("⚠️ Using fallback timeout for page settle", time.time() - start_time)

            # Check if we're on a login page or if login elements are visible
            current_url = page.url
            log_progress(f"📍 Current URL: {current_url}", time.time() - start_time)

            login_form_visible = await page.locator("input[placeholder='Enter email address']").count() > 0
            log_progress(f"🔍 Login form visible: {login_form_visible}", time.time() - start_time)

            # Also check if we see a "Log in" link/button which indicates we're not logged in
            login_link_visible = await page.locator("a:has-text('Log in'), button:has-text('Log in')").count() > 0
            log_progress(f"🔍 Login link visible: {login_link_visible}", time.time() - start_time)

            if "login" in current_url or login_form_visible or login_link_visible:
                log_progress("🔐 Login required - starting authentication flow", time.time() - start_time)
            
            # Credentials already extracted at the top of the function
            if not email or not password:
                log_progress("❌ No credentials found in environment (EMAIL/PASSWORD)")
                log_progress(f"   Looking in .env at: {project_root / '.env'}")
                await context.close()
                return

            try:
                # Fill email
                log_progress("📝 Looking for email input field...", time.time() - start_time)
                email_input = page.locator("input[placeholder='Enter email address']").first
                if await email_input.count() > 0:
                    await email_input.fill(email)
                    log_progress(f"✅ Email entered: {email}", time.time() - start_time)
                    
                    # Click LOG IN to proceed to password
                    log_progress("🔍 Looking for LOG IN button...", time.time() - start_time)
                    login_btn = page.locator("button:has-text('LOG IN')").first
                    if await login_btn.count() > 0:
                        log_progress("👆 Clicking LOG IN to proceed to password...", time.time() - start_time)
                        await login_btn.click()
                        await page.wait_for_timeout(get_timeout(2500))  # Wait after login click (increased for reliability)
                        log_progress("⏳ Waiting for password field to appear...", time.time() - start_time)

                        # Now fill password
                        password_input = page.locator("input[type='password']").first
                        if await password_input.count() > 0:
                            await password_input.fill(password)
                            log_progress("✅ Password entered", time.time() - start_time)
                            
                            # Click LOG IN again
                            final_login_btn = page.locator("button:has-text('LOG IN')").first
                            if await final_login_btn.count() > 0:
                                log_progress("👆 Clicking final LOG IN button...", time.time() - start_time)
                                await final_login_btn.click()
                                log_progress("⏳ Waiting for login to complete...", time.time() - start_time)
                                await page.wait_for_timeout(get_timeout(4000))  # Wait for zipcode modal (increased for reliability)

                                # Add additional wait for login to fully settle
                                log_progress("⏳ Waiting for network idle...", time.time() - start_time)
                                await page.wait_for_load_state("networkidle", timeout=10000)

                                # Verify we're logged in
                                new_url = page.url
                                if "login" not in new_url:
                                    log_progress(f"✅ Login successful! Now at: {new_url}", time.time() - start_time)

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
                                    log_progress("⚠️ Still on login page, may have failed", time.time() - start_time)
                            
            except Exception as e:
                log_progress(f"❌ Login error: {e}", time.time() - start_time)
        else:
            # Not on login page, use the auth helper to verify session
            log_progress("🔐 Checking session status...", time.time() - start_time)
            ensure_logged_in(page)  
        
        # The scraper can now proceed assuming it's logged in.
        log_progress("🛒 Starting cart scraping phase...", time.time() - start_time)
        
        # Prefer a cart button that isn't inside any dialog
        log_progress("🔍 Looking for cart button...", time.time() - start_time)
        cart_btn = page.locator("body > div:not([role='dialog']) >> div.cart-button.ml-auto.cursor-pointer").first

        if await cart_btn.is_visible():
            log_progress("✅ Cart button found and visible", time.time() - start_time)
            log_progress("👆 Clicking cart button...", time.time() - start_time)
            await cart_btn.click()

            # Smart wait: Look for cart articles to appear (indicates cart has loaded)
            try:
                log_progress("⏳ Waiting for cart modal to load...", time.time() - start_time)
                await page.wait_for_selector("article[class*='cart-order_cartOrderItem']", timeout=5000)
                log_progress("✅ Cart modal loaded - found cart articles", time.time() - start_time)
            except:
                # Fallback timeout if cart articles not found
                await page.wait_for_timeout(get_timeout(2000))  # Reduced from 3000ms
                log_progress("⚠️ Using fallback timeout for cart load", time.time() - start_time)
        else:
            log_progress("❌ Cart button not found - trying direct navigation", time.time() - start_time)
            await page.goto("https://farmtopeople.com/cart")
            log_progress("📍 Navigated to /cart", time.time() - start_time)

            # Smart wait: Look for cart articles after direct navigation
            try:
                log_progress("⏳ Waiting for cart page to load...", time.time() - start_time)
                await page.wait_for_selector("article[class*='cart-order_cartOrderItem']", timeout=5000)
                log_progress("✅ Cart page loaded - found cart articles", time.time() - start_time)
            except:
                # Fallback timeout if cart articles not found
                await page.wait_for_timeout(get_timeout(2000))  # Reduced from 3000ms
                log_progress("⚠️ Using fallback timeout for cart page load", time.time() - start_time)

        # First, get individual cart items (non-customizable items like eggs, avocados, etc.)
        log_progress("📦 Phase 1: Scraping individual cart items...", time.time() - start_time)
        articles = await page.locator("article[class*='cart-order_cartOrderItem']").all()
        log_progress(f"🔍 Found {len(articles)} cart articles to process", time.time() - start_time)
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
        log_progress("📦 Phase 2: Scraping non-customizable boxes...", time.time() - start_time)
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
                    log_progress(f"📦 Found non-customizable box: {box_name}", time.time() - start_time)
                    
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
                            log_progress(f"💰 Found box price: {box_price}", time.time() - start_time)
                    
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
                log_progress(f"  ⚠️ Error processing non-customizable box: {e}", time.time() - start_time)
                continue

        log_progress(f"✅ Found {len(non_customizable_boxes)} non-customizable boxes", time.time() - start_time)

        # Get all CUSTOMIZE buttons
        log_progress("📦 Phase 3: Processing customizable boxes...", time.time() - start_time)
        customize_btns = await page.locator("button:has-text('CUSTOMIZE'), button:has-text('Customize')").all()

        log_progress(f"🔍 Found {len(customize_btns)} customizable boxes to process", time.time() - start_time)
        all_box_data = []
        
        for i, customize_btn in enumerate(customize_btns):
            try:
                log_progress(f"📦 Processing customizable box {i+1}/{len(customize_btns)}...", time.time() - start_time)
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
                            log_progress(f"💰 Found box price: {box_price}", time.time() - start_time)
                
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
                            log_progress("✅ Customize modal opened successfully", time.time() - start_time)

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
                            log_progress("⚠️ Modal didn't open, retrying...", time.time() - start_time)
                            await page.wait_for_timeout(get_timeout(2000))  # Wait before retry (increased for reliability)
                            
                    except Exception as e:
                        log_progress(f"❌ Attempt {attempt + 1} failed: {e}", time.time() - start_time)
                        if attempt < max_retries - 1:
                            log_progress(f"🔄 Retrying in 3 seconds...", time.time() - start_time)
                            await page.wait_for_timeout(get_timeout(3500))  # Wait after failed attempt (increased for reliability)
                        else:
                            log_progress(f"❌ All {max_retries} attempts failed for {box_name}", time.time() - start_time)
                
                # If we still don't have box_data, create empty structure
                if box_data is None:
                    log_progress(f"⚠️ Could not get data for {box_name}, creating empty structure", time.time() - start_time)
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
                
                log_progress(f"📊 Box results: {box_name} - {box_data['selected_count']} selected, {box_data['alternatives_count']} alternatives", time.time() - start_time)
                
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
                log_progress(f"❌ Error processing box {i+1}: {e}", time.time() - start_time)
                continue
        
        # Extract delivery date (just the raw date, handle logic downstream)
        delivery_info = {}
        try:
            log_progress("📅 Phase 4: Extracting delivery date...", time.time() - start_time)
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
                            log_progress(f"  📅 Extracted delivery date: '{extracted_date}' from: '{text[:100]}...'", time.time() - start_time)
                            break

                    # Use extracted date if found, otherwise use original text (but truncated)
                    if extracted_date:
                        delivery_info['delivery_text'] = extracted_date
                        log_progress(f"  ✅ Using extracted date: '{extracted_date}'", time.time() - start_time)
                        found_date = True
                        break
                    else:
                        # Fallback: use original text but warn about potential parsing issues
                        delivery_info['delivery_text'] = text
                        log_progress(f"  ⚠️ Could not extract clean date, using full text: {text[:100]}...", time.time() - start_time)
                        found_date = True
                        break

                # Also check for "Deliver" keyword with dates and apply same extraction
                elif 'deliver' in text.lower() and any(char.isdigit() for char in text):
                    log_progress(f"  📅 Found delivery mention: {text[:100]}...", time.time() - start_time)

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
                            log_progress(f"  📅 Extracted delivery date from 'deliver' mention: '{extracted_date}' from: '{text[:100]}...'", time.time() - start_time)
                            break

                    # Use extracted date if found, otherwise use original text
                    if extracted_date:
                        delivery_info['delivery_text'] = extracted_date
                        log_progress(f"  ✅ Using extracted date: '{extracted_date}'", time.time() - start_time)
                    else:
                        delivery_info['delivery_text'] = text
                        log_progress(f"  ⚠️ Could not extract clean date from deliver mention, using full text: {text[:100]}...", time.time() - start_time)

                    found_date = True
                    break
                    
            if not found_date:
                log_progress("  ⚠️ No delivery date found on cart page", time.time() - start_time)
                # Try looking at page title or other specific locations
                try:
                    title = page.title()
                    if any(month in title for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                                         'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']):
                        delivery_info['delivery_text'] = title
                        log_progress(f"  📅 Found in page title: {title}", time.time() - start_time)
                except:
                    pass
                    
        except Exception as e:
            log_progress(f"⚠️ Could not extract delivery date: {e}", time.time() - start_time)
        
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
                log_progress(f"🕒 Cart status: {cart_status['status']} - {cart_status.get('reason', 'No reason')}", time.time() - start_time)

                if cart_status['status'] == 'active' and cart_status.get('minutes_until_lock'):
                    log_progress(f"⏰ Cart locks in {cart_status['minutes_until_lock']} minutes", time.time() - start_time)
                elif cart_status['status'] == 'locked' and cart_status.get('locked_ago_minutes'):
                    log_progress(f"🔒 Cart locked {cart_status['locked_ago_minutes']} minutes ago", time.time() - start_time)
                
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
                                        log_progress(f"✅ Parsed stored delivery date: {stored_parsed_date}", time.time() - start_time)
                                except Exception as date_error:
                                    log_progress(f"⚠️ Could not parse stored delivery date: {stored_delivery} - Error: {date_error}", time.time() - start_time)
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
                            log_progress(f"🚨 Date comparison failed: {date_comparison_error}", time.time() - start_time)
                            log_progress("🔄 Defaulting to saving fresh cart data", time.time() - start_time)
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
                
                log_progress(f"💭 Save decision: {save_reason}", time.time() - start_time)

                if should_save:
                    # DETECT SWAPS: Compare new cart with previous before saving
                    try:
                        detected_swaps = detect_and_store_swaps(phone_number, complete_results, delivery_date_text)
                        if detected_swaps:
                            log_progress(f"🔄 Detected {len(detected_swaps)} cart swaps", time.time() - start_time)
                            for swap in detected_swaps:
                                log_progress(f"   • {swap['from_item']} → {swap['to_item']} ({swap['box_name']})", time.time() - start_time)
                        else:
                            log_progress("🔄 No cart swaps detected", time.time() - start_time)
                    except Exception as swap_error:
                        log_progress(f"⚠️ Swap detection failed (non-critical): {swap_error}", time.time() - start_time)

                    success = supabase_client.save_latest_cart_data(phone_number, complete_results, delivery_date_text)
                    if success:
                        log_progress(f"💾 Cart data saved to database for {phone_number}", time.time() - start_time)

                        # CRITICAL: Cache fresh data to Redis immediately
                        try:
                            import sys
                            import os as os_module
                            sys.path.append(os_module.path.join(os_module.path.dirname(__file__), '..'))
                            sys.path.append(os_module.path.join(os_module.path.dirname(__file__), '..', 'server'))
                            from services.cache_service import CacheService

                            # Cache for 2 hours (7200 seconds)
                            CacheService.set_cart(phone_number, complete_results, ttl=7200)
                            log_progress(f"🔥 Cart data cached to Redis for {phone_number} (2hr TTL)", time.time() - start_time)
                        except Exception as cache_error:
                            log_progress(f"⚠️ Redis cache failed (non-critical): {cache_error}", time.time() - start_time)
                    else:
                        log_progress("⚠️ Failed to save cart data to database", time.time() - start_time)
                else:
                    log_progress(f"🔒 Skipping database save: {save_reason}", time.time() - start_time)
                    
            except Exception as e:
                log_progress(f"⚠️ Database save error: {e}", time.time() - start_time)

        log_progress(f"\n🎉 COMPLETE! Results saved to: {output_file}", time.time() - start_time)

        # Return data if requested
        if return_data:
            log_progress("📤 Returning cart data to caller...", time.time() - start_time)
            await context.close()
            await browser.close()
            return complete_results
        log_progress("\n🎆 SCRAPING COMPLETE - Final Summary:", time.time() - start_time)
        if individual_items:
            log_progress(f"  🛒 Individual Items: {len(individual_items)} items", time.time() - start_time)
        for box_data in non_customizable_boxes:
            log_progress(f"  📦 {box_data['box_name']} (non-customizable): {box_data['selected_count']} items", time.time() - start_time)
        for box_data in all_box_data:
            log_progress(f"  📦 {box_data['box_name']} (customizable): {box_data['selected_count']} selected, {box_data['alternatives_count']} alternatives", time.time() - start_time)
        log_progress(f"\n✅ Total scraping time: {time.time() - start_time:.1f}s\n", time.time() - start_time)
        
        await context.close()
        await browser.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
