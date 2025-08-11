from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
import json
import re
from datetime import datetime
import supabase_client as db
import sys

# Load environment variables for login credentials
load_dotenv()

def safe_click(page, locator):
    """Try to click a locator reliably: scroll into view, normal click, then force click.
    Returns True if any strategy succeeded, False otherwise.
    """
    try:
        if locator.count() == 0:
            return False
        try:
            locator.scroll_into_view_if_needed()
        except Exception:
            pass
        try:
            locator.click()
            return True
        except Exception:
            pass
        try:
            locator.click(force=True)
            return True
        except Exception:
            pass
    except Exception:
        pass
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

def scan_farm_box(phone_number: str):
    """
    Main function to run the scanner for a specific user.
    """
    print(f"===== Starting Farm to People Box Scanner for {phone_number} =====")
    
    # --- Step 1: Get user credentials from Supabase ---
    user = db.get_user_by_phone(phone_number)
    if not user:
        print(f"❌ Error: No user found in Supabase with phone number {phone_number}")
        return

    email = user.get("ftp_email")
    password = user.get("ftp_password")  # The helper decodes this for us

    if not email or not password:
        print(f"❌ Error: User {phone_number} is missing FTP credentials in the database.")
        return

    print(f"✅ Found credentials for user: {email}")
    
    # Create output directories
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
            storage_state_path = Path("auth_state.json")
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
            
            # Check if login is needed by looking for the password field. If it's not there, we're likely logged in.
            if page.locator("input[type='password']").count() == 0:
                 print("Already logged in or on the account page.")
            else:
                print("Logging in...")
                
                print("Entering email...")
                page.fill("input[type='email']", email)
                page.keyboard.press("Enter")
                
                print("Waiting for password field...")
                page.wait_for_selector("input[type='password']")
                
                print("Entering password...")
                page.fill("input[placeholder='Password']", password)
                
                print("Clicking login button...")
                page.click("button:has-text('Log in')")
                page.wait_for_url("**/account**", timeout=30000)
                
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
            page.wait_for_selector("#cart aside div.cart_cartContent__gLS77", state="visible", timeout=10000)
            print("Cart sidebar is visible")
            
            # Skip cart screenshot to speed up execution
            # cart_screenshot_path = output_dir / f"cart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            # page.screenshot(path=str(cart_screenshot_path))
            # print(f"Cart screenshot saved to {cart_screenshot_path}")
            # Let the sidebar finish animating before querying (explicit request: wait 3 seconds)
            try:
                page.wait_for_timeout(3000)
            except Exception:
                pass
            
            # Step 6: Extract cart contents
            print("\n----- Cart Contents -----")
            
            # Parse ALL cart items first - individual items, boxes, etc.
            all_cart_items = []
            cart_items = page.locator("article.cart-order_cartOrderItem__CDYTs").all()
            print(f"Found {len(cart_items)} items in cart")
            
            for i, item in enumerate(cart_items, 1):
                try:
                    # Get main item info
                    item_text = (item.text_content() or "").strip()
                    lines = [line.strip() for line in item_text.split("\n") if line.strip()]
                    
                    # Extract clean item name
                    item_name = "Unknown Item"
                    
                    # Extract item name and quantity from the cart structure
                    try:
                        # Look for the main product link
                        name_link = item.locator("a.web-link_unstyled-link__uJvxp.bold, a[class*='unstyled-link']").first
                        if name_link.count() > 0:
                            item_name = (name_link.text_content() or "").strip()
                    except Exception:
                        pass
                    
                    # Extract quantity info - both order count and item details
                    order_count = 1  # Default to 1 order
                    item_details = ""
                    
                    try:
                        # Look for quantity selector (the dropdown) to get order count
                        # Try multiple selectors for the quantity dropdown
                        qty_selectors = [
                            "select",  # Any select element
                            "select[aria-label*='quantity']",
                            "select[name*='quantity']",
                            "*[role='combobox']",
                            "*[aria-label*='quantity']"
                        ]
                        
                        for selector in qty_selectors:
                            qty_selector = item.locator(selector).first
                            if qty_selector.count() > 0:
                                # Try to get the selected value
                                selected_option = qty_selector.locator("option[selected]").first
                                if selected_option.count() > 0:
                                    value = selected_option.get_attribute("value")
                                    if value and value.isdigit() and len(value) <= 2:  # Reasonable quantity
                                        order_count = int(value)
                                        break
                                # Alternative: get the value attribute of the select itself
                                select_value = qty_selector.get_attribute("value")
                                if select_value and select_value.isdigit() and len(select_value) <= 2:
                                    order_count = int(select_value)
                                    break
                        
                        # Try to find the selected quantity from the UI
                        # Look for the actual input value or selected text
                        qty_input = item.locator("input[type='number']").first
                        if qty_input.count() > 0:
                            input_value = qty_input.get_attribute("value") or qty_input.input_value()
                            if input_value and input_value.isdigit():
                                order_count = int(input_value)
                        
                        # If that didn't work, look for quantity patterns in clean lines (avoiding the dropdown mess)
                        if order_count == 1:
                            for line in lines:
                                # Skip lines with too many digits (dropdown options)
                                if len(re.findall(r'\d', line)) > 3:
                                    continue
                                # Look for simple "quantity N" patterns
                                qty_text_match = re.search(r'^quantity\s*(\d{1,2})$', line.lower().strip())
                                if qty_text_match:
                                    order_count = int(qty_text_match.group(1))
                                    break
                        
                        # Look for item details (what comes in each order)
                        for line in lines:
                            # Match patterns like "2 pieces", "1 dozen", "1 lb", etc.
                            detail_match = re.search(r'(\d+)\s*(piece|pieces|dozen|lb|lbs|oz|bunch|pint|quart|each)', line.lower())
                            if detail_match:
                                item_details = f"{detail_match.group(1)} {detail_match.group(2)}"
                                break
                        
                        # If we couldn't find item details, try to extract from item name or description
                        if not item_details:
                            # Look for size info in item name or text
                            for line in lines:
                                size_match = re.search(r'(\d+\.?\d*)\s*(lb|lbs|oz|kg|g|piece|pieces)', line.lower())
                                if size_match:
                                    item_details = f"{size_match.group(1)} {size_match.group(2)}"
                                    break
                    
                    except Exception:
                        pass
                    
                    # Format the quantity display
                    quantity_text = ""
                    if order_count > 1 and item_details:
                        quantity_text = f" (×{order_count} orders, {item_details} each)"
                    elif order_count > 1:
                        quantity_text = f" (×{order_count} orders)"
                    elif item_details:
                        quantity_text = f" ({item_details})"
                    
                    # Fallback name cleanup if needed
                    if item_name == "Unknown Item" and lines:
                        raw_name = lines[0]
                        item_name = re.sub(r"(Farm to People|Remove|Customize|\$[\d.]+|quantity\d+).*$", "", raw_name).strip()
                        if not item_name:
                            item_name = f"Item {i}"
                    
                    # Check if customizable (has CUSTOMIZE button)
                    customize_btn = item.locator("button:has-text('CUSTOMIZE'), button:has-text('Customize')").first
                    is_customizable = customize_btn.count() > 0
                    
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
                    except Exception:
                        pass
                    
                    # Determine item type
                    item_type = "box" if any(x in item_name.lower() for x in ["box", "medley"]) else "individual"
                    
                    cart_item = {
                                            "name": item_name,
                        "is_customizable": is_customizable,
                        "sub_items": sub_items,
                        "item_type": item_type
                    }
                    
                    all_cart_items.append(cart_item)
                    
                    # Store detailed quantity info in the data structure
                    cart_item["order_count"] = order_count
                    cart_item["item_details"] = item_details
                    cart_item["quantity_text"] = quantity_text
                    
                    # Clean, simplified terminal output
                    status_icon = "🔧" if is_customizable else "📦" if item_type == "box" else "🔸"
                    print(f"  {status_icon} {item_name}{quantity_text}")
                    
                    # Enhanced avocado quantity extraction using JavaScript
                    if "avocado" in item_name.lower():
                        print(f"      🔍 EXTRACTING AVOCADO QUANTITY:")
                        
                        # Try JavaScript evaluation on select elements
                        selects = item.locator("select").all()
                        found_quantity = False
                        
                        for i, sel in enumerate(selects):
                            try:
                                # Use JavaScript to get the actual selected value
                                js_value = page.evaluate("el => el.value", sel.element_handle())
                                if js_value and str(js_value).isdigit():
                                    qty = int(js_value)
                                    if qty > 1:
                                        print(f"      ✅ Found quantity {qty} via JavaScript!")
                                        quantity_text = f" ({qty} pieces)"
                                        order_count = 1
                                        item_details = f"{qty} pieces"
                                        found_quantity = True
                                        break
                                
                                # Also show what we found for debugging
                                selected_option = sel.locator("option[selected]").first
                                if selected_option.count() > 0:
                                    opt_text = (selected_option.text_content() or "").strip()
                                    print(f"      Select {i}: JS value='{js_value}', selected option='{opt_text}'")
                            except Exception as e:
                                print(f"      Error with select {i}: {e}")
                        
                        if not found_quantity:
                            print(f"      ⚠️  Using fallback quantity extraction")
                    
                    # Show order count for items with multiple orders
                    if order_count > 1:
                        print(f"      → {order_count} orders")
                    
                    if sub_items:
                        sub_summary = ', '.join([f"{s['name']} (×{s['quantity']})" for s in sub_items[:3]])
                        extra = '...' if len(sub_items) > 3 else ''
                        print(f"      ↳ {len(sub_items)} items: {sub_summary}{extra}")
                    
                except Exception as e:
                    print(f"  {i}. Error parsing item: {e}")
                    continue
            
            # Store cart items for output using the new parsed structure
            cart_contents = all_cart_items
            
            # Now process only customizable boxes for customize page analysis
            print(f"\n📋 Analyzing Customizable Items")
            
            # Capture all customizable boxes upfront before visiting any customize pages
            customizable_articles = page.locator("article:has(button:has-text('CUSTOMIZE'))").all()
            initial_customize_count = len(customizable_articles)
            print(f"   Found {initial_customize_count} customizable box(es) to process.")
            
            # Extract box names and their positions before any navigation
            boxes_to_process = []
            for i, article in enumerate(customizable_articles):
                try:
                    name_elem = article.locator("a[class*='unstyled-link']").first
                    box_name = (name_elem.text_content(timeout=3000) or f"Box #{i+1}").strip()
                    boxes_to_process.append({"name": box_name, "index": i})
                    print(f"   → Queued: {box_name}")
                except:
                    boxes_to_process.append({"name": f"Unknown Box #{i+1}", "index": i})
            
            initial_customize_count = len(boxes_to_process)
            
            if initial_customize_count == 0:
                print("   No customizable items found")
            
            box_json_saved = False
            
            for i, box_info in enumerate(boxes_to_process):
                try:
                    box_name_for_log = box_info["name"]
                    print(f"\n🔧 Analyzing box #{i + 1}: {box_name_for_log}")
                    
                    # Prepare a "clean" version of the box name for use in the CSS selector
                    # This removes characters like apostrophes that can break the selector
                    safe_box_name = box_name_for_log.replace("'", "")
                    
                    # Re-find the customizable articles to ensure we have the latest page state
                    customize_article_locator = page.locator(f"article:has(a:has-text('{safe_box_name}')):has(button:has-text('CUSTOMIZE'))").first

                    if customize_article_locator.count() == 0:
                        print(f"   ⚠️  Could not find CUSTOMIZE button specifically for '{box_name_for_log}'. Trying a more general locator...")
                        # Fallback: find the i-th customize button on the page
                        all_buttons = page.locator("button:has-text('CUSTOMIZE')").all()
                        if i < len(all_buttons):
                            customize_btn_locator = all_buttons[i]
                            customize_article_locator = customize_btn_locator.locator("xpath=ancestor::article").first
                        else:
                            print(f"   ⚠️  Fallback failed. Skipping box.")
                            continue

                    if customize_article_locator.count() == 0:
                        print(f"   ⚠️  Could not find CUSTOMIZE button for '{box_name_for_log}'. Skipping.")
                        continue

                    customize_btn_locator = customize_article_locator.locator("button:has-text('CUSTOMIZE')").first
                    
                    if safe_click(page, customize_btn_locator):
                        print(f"   🔧 {box_name_for_log} - analyzing options...")
                        
                        selected_from_cart = []  # Initialize for this item
                        
                        # Wait for customize page to load
                        page.wait_for_selector("article[class*='customize-farmbox-item']", timeout=15000)
                        page.wait_for_timeout(2000)  # Wait for animations

                        # Extract selected and alternative items using the sophisticated working logic
                        selected_items = []
                        alternative_items = []
                        
                        # Try multiple selectors to find product cards
                        product_cards = []
                        selectors_to_try = [
                            "article[aria-label*='Read more about']",
                            "article[class*='customize-farmbox']",
                            "div[class*='product-card']",
                            "div[class*='item-card']",
                            "[data-testid*='product']",
                            "article:has(button:has-text('ADD'))",
                            "article:has(button:has-text('+'))",
                            "div:has(button:has-text('ADD'))",
                            "div:has-text('+')"
                        ]
                        
                        for selector in selectors_to_try:
                            try:
                                cards = page.locator(selector).all()
                                if cards:
                                    product_cards = cards
                                    print(f"      Found {len(product_cards)} product cards using selector: {selector}")
                                    break
                            except Exception:
                                continue
                        
                        if not product_cards:
                            print("      Warning: No product cards found with any selector")

                        def clean_product_name(name):
                            """A more careful approach to cleaning product names."""
                            if not name:
                                return ""

                            # Handle very specific known text artifacts first
                            # Ex: "AddAdd Local Yellow Peaches to your..." -> "Local Yellow Peaches"
                            add_match = re.search(r"AddAdd (.+?) to your", name)
                            if add_match:
                                name = add_match.group(1)

                            # Remove farm names, which are often concatenated at the end
                            farm_names = [
                                "Weaver's Orchard", "Blue Moon Acres", "Sun Sprout Farm", 
                                "Eagle Road Farm", "Lancaster Farm Fresh Cooperative", "Row by Row Farm"
                            ]
                            for farm in farm_names:
                                # Remove the farm name if it's at the end of the string
                                if name.endswith(farm):
                                    name = name[:-len(farm)]

                            # Remove common prefixes like "Organically Grown" or "Organic"
                            name = re.sub(r"^(Organically Grown|Organic)\s+", "", name)
                            
                            # Clean up text artifacts like "Read more about" and quantity buttons
                            name = re.sub(r"Read more about|Decrease quantity\d+Increase quantity", "", name)
                            
                            # Final trim to remove any leading/trailing whitespace
                            return name.strip()

                        def extract_name(card_el):
                            """Extracts the product name from a product card element."""
                            try:
                                # First, try a precise locator for the main product title
                                title_locator = card_el.locator("h3[class*='product-name'] a, h4[class*='product-name'] a")
                                if title_locator.count() > 0:
                                    raw_name = title_locator.first.text_content()
                                    if raw_name:
                                        return clean_product_name(raw_name)

                                # Fallback to parsing the full text content of the card
                                full_text = (card_el.text_content() or "").strip()
                                
                                # Use regex to find potential names, then clean them
                                # This helps with cards that have complex text structures
                                potential_names = re.findall(r"Read more about(.+?)(?:Weaver's|Blue Moon|Sun Sprout)", full_text)
                                if potential_names:
                                    return clean_product_name(potential_names[0])
                                
                                # If all else fails, return the best-effort full text
                                return clean_product_name(full_text)
                                
                            except Exception:
                                return "Unknown Item"

                        def extract_unit_info(card_el):
                            try:
                                unit_candidates = card_el.locator("p.weight, span, small, p").all()
                                for uc in unit_candidates:
                                    ut = (uc.text_content() or "").strip()
                                    if re.search(r"(oz|lb|lbs|bunch|dozen|pieces|each|count|pint|quart)", ut, re.I):
                                        return ut
                            except Exception:
                                pass
                            return ""

                        def extract_quantity(card_el):
                            # Use JavaScript evaluation to get the actual input value
                            try:
                                inp = card_el.locator("input[type='number']").first
                                if inp.count() > 0:
                                    # Use JavaScript to get the real value
                                    js_value = page.evaluate("el => el.value", inp.element_handle())
                                    if js_value and str(js_value).isdigit():
                                        return int(js_value)
                                    
                                    # Fallback to input_value()
                                    input_val = inp.input_value() or "0"
                                    if input_val.isdigit():
                                        return int(input_val)
                            except Exception:
                                pass
                            
                            # Look for quantity controls (+ and - buttons)
                            try:
                                plus_btn = card_el.locator("button:has-text('+')").first
                                minus_btn = card_el.locator("button:has-text('-')").first
                                if plus_btn.count() > 0 and minus_btn.count() > 0:
                                    # Look for quantity text between the buttons
                                    parent = plus_btn.locator("xpath=ancestor::*[contains(@class,'quantity') or contains(@class,'stepper') or contains(@class,'controls')]").first
                                    if parent.count() == 0:
                                        parent = plus_btn.locator("xpath=ancestor::*[1]").first
                                    
                                    txt = (parent.text_content() or "").strip()
                                    # Look for standalone number between buttons
                                    numbers = re.findall(r'\b(\d+)\b', txt)
                                    for num_str in numbers:
                                        num = int(num_str)
                                        if 0 < num <= 20:  # Reasonable quantity range
                                            return num
                                    
                                    # If we find + and - buttons, assume quantity is at least 1
                                    return 1
                            except Exception:
                                pass
                            
                            # Look for explicit quantity text patterns
                            try:
                                txt = (card_el.text_content() or "").strip()
                                # Look for "Qty: N" or "Quantity: N" patterns
                                qty_match = re.search(r'(?:qty|quantity):\s*(\d+)', txt, re.I)
                                if qty_match:
                                    return int(qty_match.group(1))
                            except Exception:
                                pass
                            
                            return 1  # Default to 1 for selected items

                        # Process each product card
                        seen = set()
                        for card in product_cards:
                            try:
                                name_val = extract_name(card)
                                if not name_val or name_val in seen:
                                    continue
                                seen.add(name_val)

                                # Check for ADD button first (these are definitely alternatives)
                                has_add_btn = card.locator("button:has-text('ADD')").count() > 0
                                
                                if has_add_btn:
                                    # Definitely an alternative - has ADD button
                                    alternative_items.append({
                                        "name": name_val,
                                        "unit_info": extract_unit_info(card)
                                    })
                                else:
                                    # No ADD button - likely a selected item
                                    qty = extract_quantity(card)
                                    selected_items.append({
                                        "name": name_val,
                                        "unit_info": extract_unit_info(card),
                                        "quantity": qty
                                    })
                            except Exception as e:
                                print(f"      Error processing card: {e}")
                                continue

                        # Final fallback logic if we got no selected items
                        if not selected_items and alternative_items:
                            print("      Fallback: Using items without ADD buttons as selected items")
                            for card in product_cards:
                                try:
                                    name_val = extract_name(card)
                                    if not name_val:
                                        continue
                                    
                                    # Skip items that are already in alternatives
                                    alt_names = {item['name'] for item in alternative_items}
                                    if name_val in alt_names:
                                        continue
                                    
                                    has_add_btn = card.locator("button:has-text('ADD')").count() > 0
                                    if not has_add_btn:
                                        # This is likely a selected item
                                        selected_items.append({
                                            "name": name_val,
                                            "unit_info": extract_unit_info(card),
                                            "quantity": 1
                                        })
                                except Exception:
                                    continue
                        
                        # Enhanced terminal output for selected items
                        print(f"\n   📋 SELECTED ITEMS ({len(selected_items)}):")
                        if not selected_items:
                            print("      (No items currently selected)")
                        else:
                            for item in selected_items:
                                unit_display = f" ({item['unit_info']})" if item.get('unit_info') else ""
                                qty_display = f" x{item.get('quantity', 1)}" if item.get('quantity', 1) != 1 else ""
                                print(f"      ✓ {item['name']}{unit_display}{qty_display}")
                        
                        print(f"\n   🔄 ALTERNATIVE OPTIONS ({len(alternative_items)}):")
                        if not alternative_items:
                            print("      (No alternatives available)")
                        else:
                            for item in alternative_items[:8]:  # Show first 8
                                unit_display = f" ({item['unit_info']})" if item.get('unit_info') else ""
                                print(f"      → {item['name']}{unit_display}")
                            if len(alternative_items) > 8:
                                print(f"      ... and {len(alternative_items) - 8} more alternatives")
                        
                        # Save box contents
                        name_slug = re.sub(r'[^a-zA-Z0-9]+', '_', box_name_for_log).lower()
                        box_data = {
                            "timestamp": datetime.now().isoformat(),
                            "box_name": box_name_for_log,
                            "selected_items": selected_items,
                            "alternative_items": alternative_items
                        }
                        box_filename = output_dir / f"box_contents_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name_slug}.json"
                        with open(box_filename, 'w') as f:
                            json.dump(box_data, f, indent=2)
                        print(f"   -> Box contents saved to {box_filename}")
                        
                        # Don't navigate back! Instead, look for more CUSTOMIZE buttons on this page (sidebar)
                        print(f"   -> Looking for additional boxes to customize on this page...")
                        
                        # Check for more CUSTOMIZE buttons in the sidebar (like "The Cook's Box - Paleo")
                        sidebar_customize_buttons = page.locator("button:has-text('CUSTOMIZE')").all()
                        print(f"   -> Found {len(sidebar_customize_buttons)} total CUSTOMIZE buttons on this page.")
                        
                        # If there are more boxes to process, we'll continue the loop
                        # The next iteration will find and click the next CUSTOMIZE button
                    else:
                        print(f"   Could not click customize for {box_name_for_log}. Re-opening cart and trying next.")
                        open_cart_sidebar(page)
                        continue
                
                except Exception as e:
                    print(f"   An error occurred processing box {i+1}: {e}")
                    try:
                        open_cart_sidebar(page)  # Try to recover
                    except Exception:
                        pass
                    continue
            
            if not initial_customize_count:
                print("No customizable items found in cart")
            
            # Save cart contents to a file
            cart_data = {
                "timestamp": datetime.now().isoformat(),
                "items": cart_contents
            }
            
            cart_json_path = output_dir / f"cart_contents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(cart_json_path, 'w') as f:
                json.dump(cart_data, f, indent=2)
            
            print(f"\nCart contents saved to {cart_json_path}")
            
            # Keep browser open for manual inspection
            print("\nScan complete. Browser will remain open for manual inspection.")
            print("Press Enter to close the browser...")
            input()
        
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            error_screenshot_path = output_dir / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            page.screenshot(path=str(error_screenshot_path))
            print(f"Error screenshot saved to {error_screenshot_path}")
        
        finally:
            try:
                if context and persist_session:
                    # For persistent context, we only close the context
                    print("Closing persistent context.")
                    context.close()
                elif browser:
                    # For non-persistent, we close the entire browser
                    print("Closing browser.")
                    browser.close()
            except Exception as e:
                print(f"Error during browser/context close: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python farmbox_optimizer.py <phone_number>")
        # For easy testing, you can use a default number from your .env file
        test_phone_number = os.getenv("YOUR_PHONE_NUMBER")
        if not test_phone_number:
            print("No phone number provided and YOUR_PHONE_NUMBER not set in .env. Exiting.")
            sys.exit(1)
        
        print(f"\n📞 No phone number provided. Using test number from .env: {test_phone_number}")
        scan_farm_box(phone_number=test_phone_number)
    else:
        phone_number_arg = sys.argv[1]
        scan_farm_box(phone_number=phone_number_arg)
