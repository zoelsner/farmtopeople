from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
import json
import re
from datetime import datetime

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
            page.goto("https://farmtopeople.com")
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
                page.fill("input[type='email']", email)
                page.keyboard.press("Enter")
                
                print("Waiting for password field...")
                page.wait_for_selector("input[type='password']")
                
                print("Entering password...")
                page.fill("input[placeholder='Password']", password)
                
                print("Clicking login button...")
                page.click("button[native-type='button']")
                page.wait_for_load_state("networkidle")
                
                # Save auth state for future runs when not using persistent context
                try:
                    if browser is not None:
                        context.storage_state(path=str(storage_state_path))
                        print("Login credentials saved for future runs")
                except Exception:
                    pass
            
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
                    
                    # Enhanced debugging for avocados to find the actual quantity
                    if "avocado" in item_name.lower():
                        print(f"      🔍 DEBUGGING AVOCADO QUANTITY:")
                        
                        # Try to find ANY element that might contain the quantity "5"
                        all_elements = item.locator("*").all()
                        elements_with_5 = []
                        for el in all_elements[:20]:  # Check first 20 elements
                            try:
                                text = (el.text_content() or "").strip()
                                if text == "5":
                                    elements_with_5.append(f"'{text}' in {el.tag_name()}")
                                # Also check attributes
                                value_attr = el.get_attribute("value")
                                if value_attr == "5":
                                    elements_with_5.append(f"value='{value_attr}' in {el.tag_name()}")
                            except:
                                pass
                        
                        if elements_with_5:
                            print(f"      Found '5' in: {', '.join(elements_with_5)}")
                        else:
                            print(f"      No '5' found in first 20 elements")
                        
                        # Check all select elements more carefully
                        selects = item.locator("select").all()
                        for i, sel in enumerate(selects):
                            try:
                                # Get the actual value of the select
                                sel_value = sel.get_attribute("value")
                                # Get all options
                                options = sel.locator("option").all()
                                selected_options = []
                                for opt in options:
                                    is_selected = opt.get_attribute("selected") is not None
                                    opt_value = opt.get_attribute("value")
                                    opt_text = (opt.text_content() or "").strip()
                                    if is_selected:
                                        selected_options.append(f"{opt_value}('{opt_text}')")
                                
                                print(f"      Select {i}: value='{sel_value}', selected={selected_options}")
                            except Exception as e:
                                print(f"      Select {i}: Error - {e}")
                    
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
            customizable_items = [item for item in all_cart_items if item["is_customizable"]]
            if not customizable_items:
                print("   No customizable items found")
                return
            
            box_json_saved = False
            
            for i, cart_item in enumerate(customizable_items, 1):
                try:
                    item_name = cart_item["name"]
                    print(f"\n🔧 Analyzing: {item_name}")
                    
                    # Find the actual cart element for this item
                    matching_item = None
                    for cart_element in cart_items:
                        if item_name in (cart_element.text_content() or ""):
                            matching_item = cart_element
                            break
                    
                    if not matching_item:
                        print(f"Could not find cart element for {item_name}")
                        continue
                    
                    # Try to find the customize button
                    customize_btn = matching_item.locator("button:has-text('CUSTOMIZE')").first
                    
                    if customize_btn.count() > 0:
                        print(f"   🔧 {item_name} - analyzing options...")
                        
                        selected_from_cart = []  # Initialize for this item
                        
                        # Read currently selected items from the cart sidebar under this box (robust)
                        try:
                            # Find any <ul> with <li> descendants inside this cart item
                            ul_candidates = matching_item.locator("xpath=.//ul[descendant::li]").all()
                            for ul in ul_candidates:
                                lis = ul.locator("xpath=./li").all()
                                for li in lis:
                                    # Prefer a details container if present, otherwise use li text
                                    details = li.locator("xpath=.//*[contains(@class,'details') or contains(@class,'subproduct')][self::div or self::span or self::p]").first
                                    text = (details.text_content() if details.count() > 0 else li.text_content()) or ""
                                    text = text.strip()
                                    if not text:
                                        continue
                                    # Normalize whitespace and split lines
                                    lines = [t.strip() for t in text.split("\n") if t.strip()]
                                    if not lines:
                                        continue
                                    # Heuristic: first line sometimes "1 White Peaches"; next line unit info like "2 pieces"
                                    name_line = lines[0]
                                    unit_info = lines[1] if len(lines) > 1 else ""
                                    # If the first token is a number, strip it from name
                                    m = re.match(r"^(\d+)\s+(.*)$", name_line)
                                    if m:
                                        quantity = m.group(1)
                                        sel_name = m.group(2).strip()
                                    else:
                                        quantity = "1"
                                        sel_name = name_line
                                    selected_from_cart.append({"name": sel_name, "unit_info": unit_info, "quantity": quantity})
                            if selected_from_cart:
                                print(f"Found {len(selected_from_cart)} selected items in cart sidebar under this box")
                        except Exception as e:
                            print(f"Cart sidebar parse error: {e}")

                        # Check for customize button
                        customize_btn = item.locator("button:has-text('CUSTOMIZE'), button:has-text('Customize'), a:has-text('CUSTOMIZE'), a:has-text('Customize')").first
                        if customize_btn.count() > 0:
                            print("Customize button found! Clicking it...")
                            # Ensure the item is scrolled into view within the sidebar, then try robust click
                            try:
                                item.scroll_into_view_if_needed()
                            except Exception:
                                pass
                            clicked = safe_click(page, customize_btn)
                            if not clicked:
                                # Fallback: navigate via closest anchor href if present
                                try:
                                    link = customize_btn.locator("xpath=ancestor::a[1]").first
                                    if link.count() > 0:
                                        href = link.get_attribute("href")
                                        if href:
                                            page.goto(href)
                                            clicked = True
                                except Exception:
                                    pass
                            if clicked:
                                # Do not block on networkidle; just a short settle
                                try:
                                    page.wait_for_timeout(1500)
                                except Exception:
                                    pass
                            else:
                                print("Customize click failed; waiting 7 seconds before reopening cart sidebar...")
                                try:
                                    page.wait_for_timeout(7000)  # 7 second wait as requested
                                except Exception:
                                    pass
                                open_cart_sidebar(page)

                            # Skip screenshot to speed up execution
                            # customization_screenshot_path = output_dir / f"customize_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                            # page.screenshot(path=str(customization_screenshot_path))
                            # print(f"Customization page screenshot saved to {customization_screenshot_path}")

                            print("\n----- Scanning Box Contents -----")

                            # Primary approach: classify left-side product tiles based on presence of ADD vs quantity controls
                            selected_items = []
                            alternative_items = []
                            
                            # Try to detect categories/sections (Proteins, Produce, Pantry, etc.)
                            categories = {}
                            try:
                                # Look for section headers
                                section_headers = page.locator("h2, h3, h4, .section-title, [class*='section'], [class*='category']").all()
                                current_category = "Items"  # Default category
                                
                                for header in section_headers:
                                    header_text = (header.text_content() or "").strip().lower()
                                    if any(word in header_text for word in ["protein", "meat", "seafood"]):
                                        current_category = "Proteins"
                                    elif any(word in header_text for word in ["produce", "vegetable", "fruit"]):
                                        current_category = "Produce"  
                                    elif any(word in header_text for word in ["pantry", "dairy", "eggs"]):
                                        current_category = "Pantry"
                                    
                                    if current_category not in categories:
                                        categories[current_category] = []
                            except Exception:
                                pass

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
                                "div:has(button:has-text('+'))"
                            ]
                            
                            for selector in selectors_to_try:
                                try:
                                    cards = page.locator(selector).all()
                                    if cards:
                                        product_cards = cards
                                        print(f"Found {len(product_cards)} product cards using selector: {selector}")
                                        break
                                except Exception:
                                    continue
                            
                            if not product_cards:
                                print("Warning: No product cards found with any selector")

                            def extract_name(card_el):
                                # Extract product name from the complex text patterns we're seeing
                                try:
                                    full_text = (card_el.text_content() or "").strip()
                                    
                                    # Pattern: "Read more aboutDecrease quantity1Increase quantityRead more aboutWHITE_PEACHESWeaver's Orchard..."
                                    # The SECOND "Read more about" contains the actual product name
                                    
                                    # First, try to find the second "Read more about" occurrence
                                    read_more_parts = full_text.split("Read more about")
                                    if len(read_more_parts) >= 3:  # "", "button text", "PRODUCT_NAME + farm"
                                        product_section = read_more_parts[2]  # Third part has the product name
                                        
                                        # Extract product name before farm name
                                        farm_pattern = r"([^A-Z]+?)(?:[A-Z][a-z]*(?:Farm|Orchard|Harvest|Acres|Road|Brothers|Cooperative|Point|Best|Grass-Fed))"
                                        match = re.search(farm_pattern, product_section)
                                        if match:
                                            product_name = match.group(1).strip()
                                            if product_name and len(product_name) > 2 and not product_name.startswith("Decrease"):
                                                return product_name
                                    
                                    # Pattern for ADD buttons: "AddAdd PRODUCT_NAME to your..."
                                    match = re.search(r"AddAdd ([^t]+?) to your", full_text)
                                    if match:
                                        product_name = match.group(1).strip()
                                        if product_name and len(product_name) > 2:
                                            return product_name
                                    
                                    # Fallback: look for any "Read more about PRODUCT" pattern and clean it
                                    matches = re.findall(r"Read more about([^R]+?)(?:[A-Z][a-z]*(?:Farm|Orchard|Harvest|Acres|Road|Brothers|Cooperative|Point|Best|Grass-Fed)|$)", full_text)
                                    for match in matches:
                                        product_name = match.strip()
                                        # Skip button text
                                        if any(x in product_name.lower() for x in ["decrease", "increase", "quantity", "add"]):
                                            continue
                                        # Clean up the name
                                        product_name = re.sub(r"^(Organically Grown |Organic )", "", product_name)
                                        product_name = re.sub(r"\d+.*$", "", product_name).strip()
                                        if product_name and len(product_name) > 2:
                                            return product_name
                                    
                                    # Ultra fallback: manual cleanup of common patterns
                                    if "White Peaches" in full_text:
                                        return "White Peaches"
                                    elif "Mixed Cherry Tomatoes" in full_text:
                                        return "Organically Grown Mixed Cherry Tomatoes"
                                    elif "Black Beauty Eggplant" in full_text:
                                        return "Organically Grown Black Beauty Eggplant"
                                    elif "Mixed Specialty Lettuce" in full_text:
                                        return "Organic Mixed Specialty Lettuce"
                                    elif "Green Kale" in full_text:
                                        return "Organic Green Kale"
                                    elif "Rainbow Carrots" in full_text:
                                        return "Organic Bunched Rainbow Carrots"
                                    elif "Italian Sausage" in full_text:
                                        return "Mild Italian Sausage"
                                    elif "Spanish Mackerel" in full_text:
                                        return "Spanish Mackerel"
                                    
                                except Exception:
                                    pass
                                    
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
                                # Use input[type=number] if present
                                try:
                                    inp = card_el.locator("input[type='number']").first
                                    if inp.count() > 0:
                                        return int(inp.input_value() or "0")
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
                                
                                return 0

                            seen = set()
                            items_processed = 0
                            items_selected = 0
                            items_alternative = 0
                            
                            for card in product_cards:
                                items_processed += 1
                                try:
                                    name_val = extract_name(card)
                                    if not name_val or name_val in seen:
                                        continue
                                    seen.add(name_val)

                                    # Check for ADD button first (these are definitely alternatives)
                                    has_add_btn = card.locator("button:has-text('ADD')").count() > 0
                                    
                                    # Check for quantity controls (+ and - buttons) with multiple selectors
                                    plus_selectors = ["button:has-text('+')", "button[aria-label*='+']", "[aria-label*='increase']", "[aria-label*='add']"]
                                    minus_selectors = ["button:has-text('-')", "button:has-text('−')", "button[aria-label*='-']", "[aria-label*='decrease']", "[aria-label*='remove']"]
                                    
                                    has_plus = any(card.locator(sel).count() > 0 for sel in plus_selectors)
                                    has_minus = any(card.locator(sel).count() > 0 for sel in minus_selectors)
                                    has_quantity_controls = has_plus and has_minus
                                    
                                    # Also check for input fields that might indicate selection
                                    has_number_input = card.locator("input[type='number']").count() > 0
                                    
                                    # Check for "Remove" or "Selected" indicators
                                    has_remove = card.locator("button:has-text('Remove')").count() > 0
                                    has_selected_text = "selected" in card.text_content().lower()
                                    
                                    # Simplified debug output (only when needed)
                                    # debug_info = f"Item: {name_val[:30]}... ADD:{has_add_btn} +/-:{has_quantity_controls}"
                                    # print(f"  Debug: {debug_info}")

                                    if has_add_btn:
                                        # Definitely an alternative - has ADD button
                                        alternative_items.append({
                                            "name": name_val,
                                            "unit_info": extract_unit_info(card)
                                        })
                                        items_alternative += 1
                                    elif has_quantity_controls or has_number_input or has_remove or has_selected_text:
                                        # Likely selected - has quantity controls, number input, remove button, or selected text
                                        qty = extract_quantity(card)
                                        if qty == 0:
                                            qty = 1  # Assume at least 1 if other indicators suggest it's selected
                                        selected_items.append({
                                            "name": name_val,
                                            "unit_info": extract_unit_info(card),
                                            "quantity": qty
                                        })
                                        items_selected += 1
                                    else:
                                        # No ADD button and no clear indicators - this is likely a selected item
                                        # since the page shows "X of X items selected"
                                        qty = extract_quantity(card)
                                        if qty == 0:
                                            qty = 1  # Default quantity for likely selected items
                                        selected_items.append({
                                            "name": name_val,
                                            "unit_info": extract_unit_info(card),
                                            "quantity": qty
                                        })
                                        items_selected += 1
                                        # print(f"  → Assuming selected (no ADD btn): {name_val}")
                                except Exception as e:
                                    print(f"  Error processing card: {e}")
                                    continue

                            # Box selection status text (e.g., "6 of 6 items selected")
                            count_text = "Unknown"
                            items_count_text = page.locator("text=/\\d+ of \\d+ items selected/").first
                            if items_count_text.count() > 0:
                                count_text = (items_count_text.text_content() or "").strip()
                                print(f"      ✓ Found {items_selected} selected, {items_alternative} alternatives")

                            # Additional approach: read selected items from the right sidebar on customize page
                            if not selected_items:
                                try:
                                    sidebar_img_containers = page.locator("div.mr-2:has(img)").all()
                                    for img_container in sidebar_img_containers:
                                        parent_row = img_container.locator("xpath=..").first
                                        if parent_row.count() > 0:
                                            row_text = (parent_row.text_content() or "").strip()
                                            if row_text:
                                                # Simple parse: quantity then name on separate lines
                                                lines = [t.strip() for t in row_text.split("\n") if t.strip()]
                                                if lines:
                                                    qty_match = re.match(r"^(\d+)\s+(.+)$", lines[0])
                                                    if qty_match:
                                                        quantity = qty_match.group(1)
                                                        name_val = qty_match.group(2)
                                                        unit_val = (lines[1] if len(lines) > 1 else "")
                                                        selected_items.append({"name": name_val, "unit_info": unit_val, "quantity": quantity})
                                except Exception:
                                    pass

                            # Final fallback: if we have empty selected_items but the page says items are selected,
                            # use a simple heuristic: items without ADD buttons might be the selected ones
                            if not selected_items and "selected" in count_text:
                                print("  Fallback: Using items without ADD buttons as selected items")
                                print(f"  Alternative items found: {len(alternative_items)}")
                                
                                # Get list of alternative item names to avoid duplicates
                                alt_names = {item['name'] for item in alternative_items}
                                print(f"  Alt names to skip: {list(alt_names)[:3]}...")  # Show first 3
                                
                                for card in product_cards:
                                    try:
                                        name_val = extract_name(card)
                                        print(f"    Processing: '{name_val}' | in alt_names: {name_val in alt_names}")
                                        
                                        if not name_val:
                                            print(f"      Skipping: empty name")
                                            continue
                                            
                                        if name_val in alt_names:
                                            print(f"      Skipping: already in alternatives")
                                            continue
                                        
                                        has_add_btn = card.locator("button:has-text('ADD')").count() > 0
                                        print(f"      Has ADD button: {has_add_btn}")
                                        
                                        if not has_add_btn:
                                            # This is likely a selected item
                                            selected_items.append({
                                                "name": name_val,
                                                "unit_info": extract_unit_info(card),
                                                "quantity": 1  # Default quantity
                                            })
                                            print(f"    ✓ Added to selected: {name_val}")
                                    except Exception as e:
                                        print(f"      Error: {e}")
                                        continue
                                
                                # Remove selected items from alternatives to prevent duplicates
                                selected_names = {item['name'] for item in selected_items}
                                alternative_items = [item for item in alternative_items if item['name'] not in selected_names]

                            # Print a concise summary
                            print(f"\nCurrently selected items ({len(selected_items)}):")
                            if not selected_items:
                                print("  (No selected items detected)")
                            for i_obj in selected_items:
                                ui = f" ({i_obj['unit_info']})" if i_obj.get("unit_info") else ""
                                qty = f" x{i_obj.get('quantity', 1)}" if i_obj.get('quantity', 1) > 1 else ""
                                print(f"  - {i_obj['name']}{ui}{qty}")

                            # Suggest top alternatives (first 10 unselected for now)
                            print(f"\nSuggested alternatives ({len(alternative_items)} available):")
                            if not alternative_items:
                                print("  (No alternatives found)")
                            for i_obj in alternative_items[:10]:
                                ui = f" ({i_obj['unit_info']})" if i_obj.get("unit_info") else ""
                                print(f"  - {i_obj['name']}{ui}")
                            
                            # If page parsing yielded nothing, fall back to what we saw in the cart sidebar
                            if not selected_items and selected_from_cart:
                                selected_items = selected_from_cart

                            # Save structured results
                            box_data = {
                                "timestamp": datetime.now().isoformat(),
                                "status": count_text,
                                "selected_items": selected_items,
                                "alternative_items": alternative_items,
                            }
                            box_json_path = output_dir / f"box_contents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                            with open(box_json_path, "w") as f:
                                json.dump(box_data, f, indent=2)
                            print(f"\nBox contents saved to {box_json_path}")
                            box_json_saved = True

                            # Simple estimate for meals later (we'll refine with AI):
                            meal_potential = max(0, len(selected_items) // 2)
                            print(f"\nEstimated meal potential: {meal_potential} meals")
                            print("(Heuristic: ~2 produce items per meal)")
                        else:
                            print("Customize button not found; reopening cart sidebar and continuing scan...")
                            try:
                                page.wait_for_timeout(800)
                            except Exception:
                                pass
                            open_cart_sidebar(page)
                    
                except Exception as e:
                    print(f"Error processing item {i+1}: {str(e)}")
            
            if not customizable_items:
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
                if context and browser is None:
                    # persistent context
                    context.close()
                elif browser is not None:
                    browser.close()
            except Exception:
                pass

if __name__ == "__main__":
    scan_produce_box()