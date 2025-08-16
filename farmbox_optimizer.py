from playwright.sync_api import sync_playwright, expect
import os
from dotenv import load_dotenv
from pathlib import Path
import json
import re
from datetime import datetime

# Load environment variables for login credentials
load_dotenv()

def safe_click(page, locator):
    """Reliably click a locator, even if obscured, using a direct JavaScript event."""
    try:
        print(f"  -> Attempting JS click...")
        locator.evaluate("element => element.click()")
        page.wait_for_timeout(1000) # Pause for UI to react
        return True
    except Exception as e:
        print(f"  -> JS click failed. Error: {e}")
        return False

def open_cart_sidebar(page) -> bool:
    """Re-open the cart sidebar using known triggers and wait until visible."""
    triggers = [
        "div.cart-button.ml-auto.cursor-pointer",
        "#cart-button",
        "button[aria-label='Cart']",
        "a[href='/cart']",
        "[data-testid='cart-button']",
    ]
    opened = False
    for t in triggers:
        try:
            el = page.locator(t).first
            if el.count() > 0 and safe_click(page, el):
                opened = True
                break
        except Exception:
            continue
    if opened:
        try:
            page.wait_for_selector("#cart aside, #cart aside [class*='cart_cartContent'], #cart [class*='cart_cartContent']", state="visible", timeout=8000)
            # Give the sidebar time to finish animating and populate
            page.wait_for_timeout(3000)
        except Exception:
            pass
    return opened

def scan_produce_box():
    """
    Script to access the Farm to People box and scan its contents without trying to modify it.
    """
    
    # Get credentials from environment variables
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")
    storage_state_path = Path("auth_state.json")
    
    # Create output directory for results
    output_dir = Path("farm_box_data")
    output_dir.mkdir(exist_ok=True)
    
    print("\n===== Farm to People Box Scanner =====\n")
    
    with sync_playwright() as p:
        # Prefer persistent context so you don't have to log in each run
        persist_session = os.getenv("PERSIST_SESSION", "1") not in ("0", "false", "False")
        browser = None
        context = None
        if persist_session:
            user_data_dir = str((Path("browser_data").resolve()))
            context = p.chromium.launch_persistent_context(user_data_dir=user_data_dir, headless=False)
            page = context.new_page()
            print("Using persistent browser context (cookies and localStorage will be reused).")
        else:
            browser = p.chromium.launch(headless=False)
            # Create browser context using stored session if available
            context_options = {}
            if storage_state_path.exists():
                print(f"Found saved session at {storage_state_path}")
                context_options["storage_state"] = str(storage_state_path)
            context = browser.new_context(**context_options)
            page = context.new_page()
        
        try:
            # Step 1: Navigate to the website
            print("Navigating to Farm to People...")
            page.goto("https://farmtopeople.com/login")
            page.wait_for_load_state("networkidle")
            
            # Step 2: Check if already logged in
            print("Checking login status...")
            is_logged_in = False
            login_indicators = [
                "text=Shopping for:",
                "text=Hi Zachary",
                "div.account-button",
                "a[href='/account']"
            ]
            
            for indicator in login_indicators:
                if page.locator(indicator).count() > 0:
                    print("Already logged in!")
                    is_logged_in = True
                    break
            
            # Step 3: Log in if needed
            if not is_logged_in:
                print("Not logged in. Proceeding to login...")
                page.goto("https://farmtopeople.com/login")
                page.wait_for_load_state("networkidle")
                
                print("Entering email...")
                page.locator("input[type='email']").first.fill(email)

                # Click the "continue" button, which is more reliable than pressing Enter.
                print("Submitting email to reveal password field...")
                page.locator("button[type='submit']").first.click()
                
                # Now, wait for the password field to become visible.
                print("Waiting for password field...")
                password_input = page.locator("input[type='password']").first
                password_input.wait_for(timeout=15000)
                
                print("Entering password...")
                password_input.fill(password)
                
                # Click the final login button to submit credentials.
                print("Clicking final login button...")
                page.locator("button[type='submit']").first.click()

                # Wait for the page to process the login.
                print("Waiting for login to complete...")
                page.wait_for_load_state("networkidle", timeout=30000)

                # Explicitly check for a login indicator to confirm success.
                print("Verifying login success...")
                page.wait_for_selector("a[href='/account']", timeout=15000)
                print("Login successful.")

                # Save auth state for future runs when not using persistent context
                if not persist_session:
                    try:
                        context.storage_state(path=str(storage_state_path))
                        print("Login credentials saved for future runs")
                    except Exception as e:
                        print(f"Could not save auth state: {e}")
            
            # Step 4: Navigate to the Farm to People Cart
            print("Clicking the cart button...")
            page.click("div.cart-button.ml-auto.cursor-pointer")
            
            # Step 5: Wait for the cart sidebar to appear
            print("Waiting for cart sidebar...")
            cart_sidebar_locator = page.locator("#cart aside div.cart_cartContent__gLS77")
            cart_sidebar_locator.wait_for(state="visible", timeout=10000)
            print("Cart sidebar is visible")
            
            # --- NEW: Add a pause to let the cart fully render before interacting ---
            print("  -> Pausing for 2 seconds to let cart settle...")
            page.wait_for_timeout(2000)

            # Let the sidebar finish animating before querying
            page.wait_for_timeout(3000)
            
            # Step 6: Extract cart contents
            print("\n----- Cart Contents -----")
            
            all_cart_items = []
            cart_items = page.locator("article.cart-order_cartOrderItem__CDYTs").all()
            print(f"Found {len(cart_items)} items in cart")
            
            # Extract delivery date from cart sidebar (e.g., "Sun Aug 11")
            delivery_date = "Unknown"
            day_of_week = "Unknown"
            try:
                date_elems = page.locator(r"text=/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w* \d{1,2}/i").all()
                for elem in date_elems:
                    candidate = elem.text_content().strip()
                    # Extract date-like substring
                    date_match = re.search(r"([A-Z][a-z]{2,3} \d{1,2})", candidate)
                    if date_match:
                        date_str = date_match.group(1)
                        # Add current year for accurate day calculation
                        current_year = datetime.now().year
                        date_str_with_year = f"{date_str} {current_year}"
                        # Try to parse
                        try:
                            date_obj = datetime.strptime(date_str_with_year, "%b %d %Y")
                            delivery_date = date_obj.strftime("%b %d")
                            day_of_week = date_obj.strftime("%A")
                            break
                        except:
                            pass
            except:
                pass
            
            # Calculate total order amount
            total_amount = 0.0
            
            for i, item in enumerate(cart_items, 1):
                try:
                    # Get main item info
                    item_text = (item.text_content() or "").strip()
                    lines = [line.strip() for line in item_text.split("\n") if line.strip()]
                    
                    # Extract clean item name
                    item_name = "Unknown Item"
                    try:
                        name_link = item.locator("a[class*='unstyled-link']").first
                        if name_link.count() > 0:
                            item_name = (name_link.text_content() or "").strip()
                    except Exception:
                        pass
                    
                    # Determine item type
                    item_type = "box" if "box" in item_name.lower() or "medley" in item_name.lower() else "individual"
                    
                    # Extract quantity and unit information
                    order_count = 1
                    quantity_text = ""
                    try:
                        # Use JS to get selected quantity from dropdown
                        select = item.locator("select").first
                        if select.count() > 0:
                            order_count = page.evaluate("el => parseInt(el.value) || 1", select.element_handle())
                        
                        # Look for quantity text like "1 dozen", "1 piece", "1 bunch"
                        quantity_patterns = [
                            r"(\d+)\s+(dozen|piece|pieces?|bunch|bunches?|oz|pound|pounds?|lb|lbs?)",
                            r"(\d+)\s+(pack|packs?|bag|bags?|container|containers?)",
                            r"(\d+)\s+(each|item|items?)"
                        ]
                        
                        item_text = (item.text_content() or "").strip()
                        for pattern in quantity_patterns:
                            qty_match = re.search(pattern, item_text, re.IGNORECASE)
                            if qty_match:
                                base_qty = int(qty_match.group(1))
                                unit = qty_match.group(2).lower()
                                # Calculate total quantity
                                total_qty = base_qty * order_count
                                # Format quantity text
                                if total_qty == 1:
                                    quantity_text = f"1 {unit}"
                                else:
                                    # Handle plural forms
                                    if unit == "piece":
                                        quantity_text = f"{total_qty} pieces"
                                    elif unit == "dozen":
                                        quantity_text = f"{total_qty} dozen"
                                    elif unit == "bunch":
                                        quantity_text = f"{total_qty} bunches"
                                    else:
                                        quantity_text = f"{total_qty} {unit}"
                                break
                        
                        # Fallback if no pattern matched
                        if not quantity_text:
                            quantity_text = f"Qty: {order_count}"
                            
                    except Exception:
                        quantity_text = f"Qty: {order_count}"
                    
                    # Extract price and add to total
                    price = "Unknown"
                    try:
                        price_elem = item.locator(r"text=/\$[\d.]+/").first
                        if price_elem.count() > 0:
                            price_text = price_elem.text_content().strip()
                            price = price_text
                            # Extract numeric value for total calculation
                            price_match = re.search(r'\$([\d.]+)', price_text)
                            if price_match:
                                item_price = float(price_match.group(1))
                                total_amount += item_price * order_count
                    except:
                        pass
                    
                    # Extract sub-items from boxes
                    sub_items = []
                    
                    try:
                        if "box" in item_name.lower() or "medley" in item_name.lower():
                            # Look for expanded content or lists within this cart item
                            # Try multiple strategies to find sub-items
                            
                            # Strategy 1: Look for direct list items
                            sub_lists = item.locator("ul li, ol li").all()
                            for sub_li in sub_lists:
                                sub_text = (sub_li.text_content() or "").strip()
                                if sub_text and len(sub_text) > 3:
                                    # Parse quantity patterns like "1 White Peaches"
                                    qty_match = re.match(r"(\d+)\s*(.+)", sub_text)
                                    if qty_match:
                                        quantity = int(qty_match.group(1))
                                        sub_name = qty_match.group(2).strip()
                                    else:
                                        quantity = 1
                                        sub_name = sub_text
                                    
                                    # Clean up the name
                                    sub_name = re.sub(r"(Remove|\$[\d.]+).*$", "", sub_name).strip()
                                    
                                    if sub_name and len(sub_name) > 2:
                                        sub_items.append({
                                            "name": sub_name,
                                            "quantity": quantity
                                        })
                            
                            # Strategy 2: Look for items after "Hide items in" text
                            if not sub_items:
                                # Parse from the full text looking for patterns
                                full_text = (item.text_content() or "").strip()
                                
                                # Look for lines that start with numbers (quantity indicators)
                                for line in lines:
                                    if re.match(r'^\d+\s+[A-Z]', line):  # "1 White Peaches", "2 Red Plums"
                                        qty_match = re.match(r'(\d+)\s*(.+)', line)
                                        if qty_match:
                                            quantity = int(qty_match.group(1))
                                            sub_name = qty_match.group(2).strip()
                                            
                                            # Clean it up
                                            sub_name = re.sub(r"(pieces?|piece)$", "", sub_name).strip()
                                            
                                            if len(sub_name) > 2:
                                                sub_items.append({
                                                    "name": sub_name,
                                                    "quantity": quantity
                                                })
                            
                            # New: Strategy 3 - If customization is locked, use the listed items as current contents
                            if not is_customizable and not sub_items:
                                # Look for any text that looks like "1 Local Yellow Peaches" etc.
                                potential_sub_items = item.locator("p, span, div").all()
                                for el in potential_sub_items:
                                    txt = (el.text_content() or "").strip()
                                    qty_match = re.match(r'^(\d+)\s+(.+)', txt)
                                    if qty_match:
                                        quantity = int(qty_match.group(1))
                                        sub_name = qty_match.group(2).strip()
                                        sub_name = re.sub(r"(Remove|\$[\d.]+).*$", "", sub_name).strip()
                                        if len(sub_name) > 2:
                                            sub_items.append({
                                                "name": sub_name,
                                                "quantity": quantity
                                            })
                    except Exception:
                        pass
                    
                    cart_item = {
                        "name": item_name,
                        "type": item_type,
                        "quantity": order_count,
                        "price": price,
                        "delivery_date": delivery_date,
                        "day_of_week": day_of_week,
                        "sub_items": sub_items
                    }
                    all_cart_items.append(cart_item)
                    
                    cart_item["price"] = price
                    cart_item["delivery_date"] = delivery_date
                    cart_item["day_of_week"] = day_of_week
                    
                    # Simplified console output with quantity
                    print(f"  {i}. {item_name} - {price} ({quantity_text})")
                
                except Exception as e:
                    print(f"  {i}. Error parsing item: {e}")
                    continue
            
            # Extract actual cart summary values from the page
            subtotal = "Unknown"
            delivery_fee = "Unknown"
            credits = "Unknown"
            final_total = "Unknown"
            
            try:
                # Look for cart summary section first
                cart_summary = page.locator("#cart aside, #cart [class*='cart_cartContent']").first
                
                # Look for subtotal with different patterns
                subtotal_patterns = ["Subtotal", "subtotal", "SUB TOTAL"]
                for pattern in subtotal_patterns:
                    subtotal_elem = cart_summary.locator(f"text=/{pattern}/").first
                    if subtotal_elem.count() > 0:
                        # Get the parent element that contains both label and value
                        parent = subtotal_elem.locator("..").first
                        if parent.count() > 0:
                            parent_text = parent.text_content().strip()
                            subtotal_match = re.search(r'\$([\d.]+)', parent_text)
                            if subtotal_match:
                                subtotal = f"${subtotal_match.group(1)}"
                                break
                
                # Look for delivery fee
                delivery_patterns = ["Delivery Fee", "delivery fee", "DELIVERY"]
                for pattern in delivery_patterns:
                    delivery_elem = cart_summary.locator(f"text=/{pattern}/").first
                    if delivery_elem.count() > 0:
                        parent = delivery_elem.locator("..").first
                        if parent.count() > 0:
                            parent_text = parent.text_content().strip()
                            delivery_match = re.search(r'\$([\d.]+)', parent_text)
                            if delivery_match:
                                delivery_fee = f"${delivery_match.group(1)}"
                                break
                
                # Look for credits
                credit_patterns = ["Credit Applied", "credit applied", "CREDIT"]
                for pattern in credit_patterns:
                    credit_elem = cart_summary.locator(f"text=/{pattern}/").first
                    if credit_elem.count() > 0:
                        parent = credit_elem.locator("..").first
                        if parent.count() > 0:
                            parent_text = parent.text_content().strip()
                            credit_match = re.search(r'\$([\d.]+)', parent_text)
                            if credit_match:
                                credits = f"${credit_match.group(1)}"
                                break
                
                # Look for final total
                total_patterns = ["Total", "TOTAL", "total"]
                for pattern in total_patterns:
                    total_elem = cart_summary.locator(f"text=/{pattern}/").first
                    if total_elem.count() > 0:
                        parent = total_elem.locator("..").first
                        if parent.count() > 0:
                            parent_text = parent.text_content().strip()
                            total_match = re.search(r'\$([\d.]+)', parent_text)
                            if total_match:
                                final_total = f"${total_match.group(1)}"
                                break
                        
            except Exception as e:
                print(f"Error extracting cart summary: {e}")
            
            # Display order summary
            print(f"\n----- Order Summary -----")
            print(f"Delivery Date: {delivery_date} ({day_of_week})")
            print(f"Subtotal: {subtotal}")
            print(f"Delivery Fee: {delivery_fee}")
            if credits != "Unknown" and credits != "$0.00":
                print(f"Credits Applied: {credits}")
            print(f"Final Total: {final_total}")
            print(f"Items in Cart: {len(cart_items)}")
            
            # Debug: Show entire cart sidebar structure
            print(f"\n----- DEBUG: Cart Sidebar Structure -----")
            try:
                cart_sidebar_html = cart_sidebar.inner_html()
                print(f"Cart sidebar HTML length: {len(cart_sidebar_html)} characters")
                print("First 2000 characters of cart sidebar HTML:")
                print(cart_sidebar_html[:2000])
                print("\n--- End of cart sidebar HTML snippet ---\n")
            except Exception as e:
                print(f"Error getting cart sidebar HTML: {e}")
            
            # Function to scrape items from the customization overlay
            def scrape_customization_overlay(page):
                """Scrapes selected items from the customization overlay."""
                selected_items = []
                
                print("  -> Waiting for customization overlay to load...")
                try:
                    page.wait_for_selector("[role='dialog'], [class*='modal']", state="visible", timeout=5000)
                    page.wait_for_timeout(1500)
                except:
                    print("  -> Timeout waiting for customization overlay")
                    return selected_items
                
                overlay = page.locator("[role='dialog'], [class*='modal']").first
                if overlay.count() == 0:
                    print("  -> Could not find overlay")
                    return selected_items
                
                # First, let's understand what we're dealing with
                print("\n  -> Analyzing overlay structure...")
                
                # Try to find item containers
                item_selectors = [
                    "[class*='item']",
                    "article",
                    "[class*='product']",
                    "li"
                ]
                
                items = []
                used_selector = None
                for selector in item_selectors:
                    test_items = overlay.locator(selector).all()
                    if len(test_items) > 5:  # Likely found the right container
                        items = test_items
                        used_selector = selector
                        print(f"  -> Found {len(items)} items using selector: {selector}")
                        break
                
                if len(items) == 0:
                    # Fallback to text parsing
                    print("  -> No item containers found, parsing text directly")
                    overlay_text = overlay.text_content()
                    print(f"\n  -> Overlay text (first 500 chars):\n{overlay_text[:500]}\n")
                    
                    lines = overlay_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if re.match(r'^\d+\s+[A-Za-z]', line) and len(line) > 5:
                            parts = line.split(None, 1)
                            if len(parts) == 2:
                                try:
                                    qty = int(parts[0])
                                    name = parts[1]
                                    if not any(skip in name.lower() for skip in ['checkout', 'total', 'skip', 'edit']):
                                        selected_items.append({
                                            "name": name,
                                            "quantity": qty,
                                            "selected": True
                                        })
                                        print(f"    - [✓] Found: {qty}x {name}")
                                except:
                                    pass
                else:
                    # Process each item container
                    print(f"  -> Processing {len(items)} item containers...")
                    
                    for idx, item in enumerate(items):
                        try:
                            item_text = item.text_content()
                            
                            # Skip items that are too short or are UI elements
                            if len(item_text) < 10 or any(skip in item_text.lower() for skip in ['remove', 'checkout', 'required', 'skip or edit']):
                                continue
                            
                            print(f"\n  -> Item {idx + 1} raw text: {item_text[:100]}...")
                            
                            # The text seems to be concatenated. Let's try to extract patterns
                            # Looking for: FarmNameProductNameQty: 1unit
                            
                            # Try to find Qty: pattern
                            qty_match = re.search(r'Qty:\s*(\d+)', item_text)
                            if qty_match:
                                quantity = int(qty_match.group(1))
                                
                                # Now extract the product name
                                # It seems to come after the farm name (which appears twice)
                                # Split by 'Qty:' to get the part before
                                before_qty = item_text.split('Qty:')[0]
                                
                                # Look for repeated text (farm name)
                                words = before_qty.split()
                                product_name = None
                                
                                # Simple approach: look for capital letters that might start product name
                                # after the repeated farm name
                                parts = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z]?[a-z]+)*', before_qty)
                                if len(parts) >= 3:
                                    # Assume last substantial part is product name
                                    product_name = parts[-1]
                                
                                # Alternative: if we see repeated text, take what comes after
                                for i in range(len(words) - 1):
                                    for j in range(i + 1, len(words)):
                                        if words[i] == words[j]:
                                            # Found repeat, take everything after
                                            product_name = ' '.join(words[j+1:])
                                            break
                                    if product_name:
                                        break
                                
                                if not product_name:
                                    # Fallback: just take the text before Qty, cleaned up
                                    product_name = before_qty.strip()
                                
                                if product_name:
                                    selected_items.append({
                                        "name": product_name,
                                        "quantity": quantity,
                                        "selected": True
                                    })
                                    print(f"    - [✓] Extracted: {quantity}x {product_name}")
                            else:
                                # No Qty found, try line by line parsing
                                lines = item_text.split('\n')
                                for line in lines:
                                    match = re.match(r'^(\d+)\s+(.+)$', line.strip())
                                    if match:
                                        selected_items.append({
                                            "name": match.group(2),
                                            "quantity": int(match.group(1)),
                                            "selected": True
                                        })
                                        print(f"    - [✓] Found: {match.group(1)}x {match.group(2)}")
                                        break
                            
                        except Exception as e:
                            print(f"    - Error processing item {idx + 1}: {e}")
                
                print(f"\n  -> Total items found: {len(selected_items)}")
                return selected_items

            # After extracting basic cart info, for each customizable box, try to access customization
            for i, cart_item in enumerate(all_cart_items):
                try:
                    if cart_item["type"] == "box":
                        print(f"\nProcessing box: {cart_item['name']}")
                        
                        # Ensure cart sidebar is open
                        open_cart_sidebar(page)
                        page.wait_for_timeout(1000)
                        
                        # Find the cart sidebar and its scrollable content
                        cart_sidebar = page.locator("#cart aside, #cart [class*='cart_cartContent']").first
                        if cart_sidebar.count() == 0:
                            print("  -> Could not find cart sidebar")
                            continue
                            
                        # Find the specific cart item
                        escaped_name = cart_item['name'].replace("'", "\\'")
                        cart_item_locator = cart_sidebar.locator(f"article:has-text('{escaped_name}')").first
                        
                        if cart_item_locator.count() == 0:
                            print(f"  -> Could not find '{cart_item['name']}' in cart sidebar")
                            # Debug: show all articles in the cart
                            all_articles = cart_sidebar.locator("article").all()
                            print(f"  -> Found {len(all_articles)} article elements in cart sidebar")
                            for idx, article in enumerate(all_articles):  # Show all
                                article_text = article.text_content().strip()
                                print(f"\n     Article {idx+1} full text:\n{article_text}")
                                print(f"\n     Article {idx+1} HTML (first 500 chars):")
                                print(article.inner_html()[:500])
                            
                            # Try other container types
                            print("\n  -> Looking for other container types...")
                            containers = cart_sidebar.locator("div[class*='item'], li[class*='item'], section[class*='item']").all()
                            print(f"  -> Found {len(containers)} other item containers")
                            continue
                        
                        # Scroll within the cart sidebar to make the item visible
                        print(f"  -> Scrolling to '{cart_item['name']}' in cart sidebar...")
                        
                        # Find the scrollable container within the cart
                        scrollable_container = cart_sidebar.locator("[class*='scrollable'], [class*='overflow'], [style*='overflow']").first
                        if scrollable_container.count() == 0:
                            scrollable_container = cart_sidebar
                        
                        # Scroll the item into view within the container
                        try:
                            page.evaluate("""
                                (args) => {
                                    const [element, container] = args;
                                    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                    // Also try scrolling the container
                                    if (container && container.scrollTop !== undefined) {
                                        const rect = element.getBoundingClientRect();
                                        const containerRect = container.getBoundingClientRect();
                                        if (rect.top < containerRect.top || rect.bottom > containerRect.bottom) {
                                            container.scrollTop += rect.top - containerRect.top - 50;
                                        }
                                    }
                                }
                            """, [cart_item_locator.element_handle(), scrollable_container.element_handle()])
                        except:
                            # Fallback to simple scroll
                            cart_item_locator.scroll_into_view_if_needed()
                        
                        page.wait_for_timeout(1000)
                        
                        # Find the CUSTOMIZE button - be specific but flexible
                        # First try to find buttons with exact text
                        customize_btn = cart_item_locator.locator("button").filter(has_text=re.compile(r"CUSTOMIZE", re.IGNORECASE)).first
                        
                        if customize_btn.count() == 0:
                            # Try with more specific selectors
                            customize_btn = cart_item_locator.locator("button:has-text('CUSTOMIZE'), button:has-text('Customize')").first
                        
                        if customize_btn.count() == 0:
                            # Debug: let's see what's in this cart item
                            print(f"  -> DEBUG: Cart item HTML structure:")
                            try:
                                # Get the inner HTML to understand structure
                                cart_item_html = cart_item_locator.inner_html()
                                # Show first 1000 chars to understand structure
                                print(f"  -> Cart item HTML (first 1000 chars):")
                                print(cart_item_html[:1000])
                                
                                # Look for all buttons
                                all_buttons = cart_item_locator.locator("button").all()
                                print(f"  -> Found {len(all_buttons)} buttons in this cart item")
                                for idx, btn in enumerate(all_buttons):
                                    btn_text = btn.text_content().strip()
                                    btn_class = btn.get_attribute("class") or ""
                                    print(f"     Button {idx+1}: text='{btn_text}', class='{btn_class}'")
                                
                                # Look for any element with CUSTOMIZE text
                                customize_elements = cart_item_locator.locator("*:has-text('CUSTOMIZE')").all()
                                print(f"  -> Found {len(customize_elements)} elements containing 'CUSTOMIZE'")
                                for idx, elem in enumerate(customize_elements[:3]):
                                    tag_name = elem.evaluate("el => el.tagName")
                                    elem_text = elem.text_content().strip()
                                    elem_class = elem.get_attribute("class") or ""
                                    print(f"     Element {idx+1}: <{tag_name}> text='{elem_text}', class='{elem_class}'")
                            except Exception as e:
                                print(f"  -> Error getting debug info: {e}")
                        
                        if customize_btn.count() > 0:
                            print("  -> Found CUSTOMIZE button, preparing to click...")
                            
                            # Check button position before clicking
                            btn_box = customize_btn.bounding_box()
                            if btn_box:
                                print(f"  -> Button location: x={btn_box['x']}, y={btn_box['y']}, width={btn_box['width']}, height={btn_box['height']}")
                                
                                # If button is outside viewport, we need to scroll the cart sidebar
                                if btn_box['x'] > 1500 or btn_box['x'] < 0:
                                    print("  -> Button is outside viewport, scrolling cart sidebar...")
                                    
                                    # Try scrolling the cart sidebar horizontally and vertically
                                    try:
                                        # First, scroll the cart item into view
                                        cart_item_locator.scroll_into_view_if_needed()
                                        page.wait_for_timeout(1000)
                                        
                                        # Try scrolling the entire cart sidebar
                                        cart_sidebar.scroll_into_view_if_needed()
                                        page.wait_for_timeout(1000)
                                        
                                        # Force scroll to the button using JavaScript
                                        page.evaluate("""
                                            (button) => {
                                                button.scrollIntoView({ behavior: 'instant', block: 'center', inline: 'center' });
                                                // Also scroll any parent containers
                                                let parent = button.parentElement;
                                                while (parent) {
                                                    if (parent.scrollLeft !== undefined || parent.scrollTop !== undefined) {
                                                        const rect = button.getBoundingClientRect();
                                                        const parentRect = parent.getBoundingClientRect();
                                                        if (rect.left < parentRect.left || rect.right > parentRect.right) {
                                                            parent.scrollLeft += rect.left - parentRect.left - 100;
                                                        }
                                                    }
                                                    parent = parent.parentElement;
                                                }
                                            }
                                        """, customize_btn.element_handle())
                                        page.wait_for_timeout(1000)
                                        
                                        # Check new position
                                        new_btn_box = customize_btn.bounding_box()
                                        if new_btn_box:
                                            print(f"  -> Button new location: x={new_btn_box['x']}, y={new_btn_box['y']}")
                                    except Exception as scroll_error:
                                        print(f"  -> Scrolling error: {scroll_error}")
                            
                            # Click using the most reliable method
                            print("  -> Clicking CUSTOMIZE button...")
                            success = False
                            
                            # Try multiple click approaches
                            try:
                                # First try regular click
                                customize_btn.click(timeout=5000)
                                print("  -> Regular click successful")
                                success = True
                            except Exception as e:
                                print(f"  -> Regular click failed: {e}")
                                
                                try:
                                    # Try force click
                                    customize_btn.click(force=True, timeout=5000)
                                    print("  -> Force click successful")
                                    success = True
                                except Exception as e2:
                                    print(f"  -> Force click failed: {e2}")
                                    
                                    try:
                                        # Try JavaScript click
                                        page.evaluate("(el) => el.click()", customize_btn.element_handle())
                                        print("  -> JavaScript click successful")
                                        success = True
                                    except Exception as e3:
                                        print(f"  -> JavaScript click failed: {e3}")
                            
                            if success:
                                print("  -> Click successful, waiting for overlay...")
                                page.wait_for_timeout(2000)
                                
                                # The customize button opens an overlay
                                print("  -> Waiting for customization overlay to appear...")
                                
                                # Give extra time for the first box as it seems to load differently
                                if i == 0:
                                    print("  -> First box - waiting extra time for content to load...")
                                    page.wait_for_timeout(3000)
                                
                                # Take a screenshot for debugging
                                debug_screenshot = output_dir / f"customize_overlay_{cart_item['name'].replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                                page.screenshot(path=str(debug_screenshot))
                                print(f"  -> Debug screenshot saved: {debug_screenshot}")
                                
                                # Check if we need to wait for content to load
                                overlay = page.locator("[role='dialog'], [class*='modal']").first
                                if overlay.count() > 0:
                                    overlay_text = overlay.text_content()
                                    
                                    # If we just see "in your box" or similar loading text, wait more
                                    if "in your box" in overlay_text.lower() and len(overlay_text) < 100:
                                        print("  -> Overlay showing loading state, waiting for content...")
                                        page.wait_for_timeout(2000)
                                        
                                        # Take another screenshot
                                        debug_screenshot2 = output_dir / f"customize_overlay_after_wait_{cart_item['name'].replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                                        page.screenshot(path=str(debug_screenshot2))
                                        print(f"  -> After-wait screenshot saved: {debug_screenshot2}")
                                
                                # Scrape the selected items from the overlay
                                selected_items = scrape_customization_overlay(page)
                                cart_item["selected_items"] = selected_items
                                print(f"  -> Found {len(selected_items)} selected items")
                            else:
                                print("  -> All click methods failed, skipping this box")
                                cart_item["selected_items"] = []
                            
                            # Close the overlay - try various methods
                            print("  -> Closing customization overlay...")
                            close_selectors = [
                                "button[aria-label*='close' i]",
                                "button:has-text('Close')",
                                "button:has-text('Done')",
                                "button:has-text('Save')",
                                "button:has-text('X')",
                                "[class*='close-button']",
                                "[class*='modal-close']",
                                "[class*='dismiss']",
                                "button[class*='close']"
                            ]
                            
                            closed = False
                            for close_sel in close_selectors:
                                close_btn = page.locator(close_sel).first
                                if close_btn.count() > 0 and close_btn.is_visible():
                                    try:
                                        close_btn.click()
                                        print(f"  -> Closed overlay using: {close_sel}")
                                        closed = True
                                        break
                                    except:
                                        continue
                            
                            if not closed:
                                print("  -> Could not find close button, trying ESC key")
                                page.keyboard.press("Escape")
                            
                            page.wait_for_timeout(1000)
                        else:
                            print("  -> No CUSTOMIZE button found for this item")
                            cart_item["selected_items"] = []

                except Exception as e:
                    print(f"  -> ERROR processing box '{cart_item.get('name', 'Unknown')}': {e}")
                    cart_item["selected_items"] = []
                    error_screenshot = output_dir / f"error_processing_box_{i+1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    try:
                        page.screenshot(path=str(error_screenshot))
                        print(f"  -> Error screenshot saved to {error_screenshot}")
                    except Exception as ss_error:
                        print(f"  -> Could not take error screenshot: {ss_error}")
                    continue # Safely continue to the next item in the cart
            
            # Save detailed box contents to file
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            for cart_item in all_cart_items:
                if cart_item["type"] == "box" and "selected_items" in cart_item:
                    # Sanitize box name for filename
                    box_name_slug = re.sub(r"[^a-z0-9_]+", "", cart_item['name'].lower().replace(" ", "_"))
                    box_filename = output_dir / f"box_contents_{timestamp_str}_{box_name_slug}.json"
                    
                    # Prepare data for JSON output
                    output_data = {
                        "timestamp": datetime.now().isoformat(),
                        "box_name": cart_item['name'],
                        "selected_items": cart_item.get("selected_items", []),
                        "alternative_items": cart_item.get("alternative_items", [])
                    }
                    
                    with open(box_filename, 'w') as f:
                        json.dump(output_data, f, indent=2)
                    print(f"  -> Saved box contents to {box_filename}")

            print("\nScan complete.")
            # print("Press Enter to close the browser...")
            # input()
        
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            error_screenshot = output_dir / f"error_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            try:
                page.screenshot(path=str(error_screenshot))
                print(f"  -> Error screenshot saved to {error_screenshot}")
            except Exception as ss_error:
                print(f"  -> Could not take error screenshot: {ss_error}")
            finally:
                if browser:
                    browser.close()
                if context:
                    context.close()

if __name__ == "__main__":
    scan_produce_box()