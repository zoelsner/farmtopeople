import os
import json
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

# Load environment variables
load_dotenv()

class BoxContentOrganizer:
    def __init__(self):
        self.email = os.getenv("EMAIL")
        self.password = os.getenv("PASSWORD")
        self.contact_email = os.getenv("CONTACT_EMAIL", self.email or "")
        self.zip_code = os.getenv("ZIP_CODE", "")
        
        # Paths
        self.data_dir = Path("farm_box_data")
        self.data_dir.mkdir(exist_ok=True)
        self.auth_state_path = Path("auth_state.json")
        
        # Results
        self.box_price = 0
        self.protein_items = []
        self.protein_limit = 2
        self.produce_items = []
        self.produce_limit = 7
        self.other_items = []  # Items that don't fit either category
        self.cart_items = []
    
    def run(self):
        """Main method to run the detection process."""
        print("\n===== Farm Box Content Organizer =====\n")
        
        with sync_playwright() as p:
            # Launch browser in non-headless mode so you can see what's happening
            browser = p.chromium.launch(headless=False)
            
            context_options = {}
            if self.auth_state_path.exists():
                print(f"Found saved session at {self.auth_state_path}")
                context_options["storage_state"] = str(self.auth_state_path)
            
            context = browser.new_context(**context_options)
            page = context.new_page()
            
            try:
                # Login
                self._login(page, context)
                
                # Open cart & find box
                self._open_cart_and_find_box(page)
                
                # Detect and organize box contents
                self._detect_box_contents(page)
                
                # Save a screenshot for verification
                screenshot_path = self.data_dir / f"box_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
                print(f"\nScreenshot saved to {screenshot_path}")
                
                # Save results
                self._save_results()
                
                # Print results
                self._print_results()
                
                # Wait for user to close
                print("\nPress Enter to close the browser...")
                input()
                
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                error_path = self.data_dir / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                page.screenshot(path=str(error_path), full_page=True)
                print(f"Error screenshot saved to {error_path}")
            
            finally:
                browser.close()
    
    def _find_login_form(self, page):
        """Return the locator of the actual login form (not the newsletter form)."""
        candidates = [
            # A form that contains a LOG IN button
            page.locator("form:has(button:has-text('LOG IN'))").first,
            page.locator("form:has(button:has-text('Log in'))").first,
            # Forms that post to a login endpoint
            page.locator("form[action*='login']").first,
        ]
        for form in candidates:
            try:
                if form.count() > 0:
                    return form
            except Exception:
                continue
        return page.locator("form").first

    def _handle_zip_gate(self, page):
        """Handle the zipcode/email gate modal if it appears."""
        try:
            # The right drawer often has a heading like "Enter Your Zip Code"
            gate_visible = page.locator("text=/Enter Your Zip Code/i").first
            if gate_visible.count() == 0:
                # Sometimes only the Zip/Email labels are visible
                if page.locator("label:text('Zip code'), text=/Zip code/i").count() == 0:
                    return
            print("Zip gate detected. Attempting to continue...")

            # Fill zip if provided
            if self.zip_code:
                # Try common input selectors
                filled = False
                for selector in [
                    "input[name='zip']",
                    "input[placeholder*='zip' i]",
                    "input[type='text']"
                ]:
                    inp = page.locator(selector).first
                    if inp.count() > 0:
                        try:
                            inp.fill(self.zip_code)
                            filled = True
                            break
                        except Exception:
                            pass
                if not filled:
                    print("Could not find zip input to fill; trying to proceed anyway.")
            else:
                print("ZIP_CODE not provided; you may need to enter it manually.")

            # Fill contact email if requested
            if self.contact_email:
                email_filled = False
                for selector in [
                    "input[type='email']",
                    "input[name='email']",
                    "input[placeholder*='email' i]"
                ]:
                    einp = page.locator(selector).first
                    if einp.count() > 0:
                        try:
                            einp.fill(self.contact_email)
                            email_filled = True
                            break
                        except Exception:
                            pass

            # Uncheck marketing if present
            try:
                marketing_checkbox = page.get_by_role("checkbox").first
                if marketing_checkbox and marketing_checkbox.is_checked():
                    marketing_checkbox.uncheck()
            except Exception:
                pass

            # Click Continue/Save/Submit button
            for name in ["Continue", "CONTINUE", "Save", "Submit"]:
                btn = page.get_by_role("button", name=name).first
                if btn.count() > 0:
                    try:
                        btn.scroll_into_view_if_needed()
                    except Exception:
                        pass
                    try:
                        btn.click()
                    except Exception:
                        try:
                            btn.click(force=True)
                        except Exception:
                            pass
                    page.wait_for_load_state("networkidle")
                    page.wait_for_timeout(1000)
                    break

            # If close button exists (X), click it
            close_btn = page.locator("button:has-text('×'), button[aria-label='Close'], button[aria-label='Dismiss']").first
            if close_btn.count() > 0:
                try:
                    close_btn.click()
                except Exception:
                    pass
        except Exception as e:
            print(f"Zip gate handling encountered an error: {e}")
    
    def _login(self, page, context):
        """Ensure we are logged in. If a saved session exists, use it and verify."""
        # If we have storage state, go to homepage first and see if we're already logged in
        start_url = "https://www.farmtopeople.com/"
        print("Opening site to verify login state...")
        page.goto(start_url)
        page.wait_for_load_state("networkidle")
        # Handle zipcode/email gate if present
        self._handle_zip_gate(page)
        
        print("Checking login status...")
        is_logged_in = False

        # Prefer role/text-based indicators
        try:
            if page.get_by_role("link", name=re.compile("Account|Hi ", re.I)).count() > 0:
                is_logged_in = True
        except Exception:
            pass

        if not is_logged_in:
            # Fallback checks
            login_indicators = [
                "text=Shopping for:",
                "text=Hi ",
                "div.account-button",
                "a[href='/account']"
            ]
            for indicator in login_indicators:
                try:
                    if page.locator(indicator).count() > 0:
                        is_logged_in = True
                        break
                except Exception:
                    pass
        
        if is_logged_in:
            print("Already logged in!")
            return
        else:
            print("Not logged in. Navigating to login page...")
            page.goto("https://www.farmtopeople.com/login")
            page.wait_for_load_state("networkidle")
            # Some sites force zip gate on /login as well
            self._handle_zip_gate(page)

            print("Entering email...")
            # Use robust email selector
            email_filled = False
            login_form = self._find_login_form(page)
            for selector in [
                "input[type='email']",
                "input[name='email']",
                "input[placeholder='Email']",
                "#email",
                "input[aria-label='Email address']",
                "input[placeholder*='email' i]",
            ]:
                try:
                    login_form.locator(selector).first.fill(self.email)
                    email_filled = True
                    break
                except Exception:
                    continue
            if not email_filled:
                raise RuntimeError("Could not find email input on login page.")

            # Click the LOG IN button (case-insensitive) within the login form
            def attempt_click_login():
                candidates = [
                    login_form.get_by_role("button", name=re.compile(r"^log in$", re.I)).first,
                    login_form.locator("button:has-text('LOG IN')").first,
                    login_form.locator("button:has-text('Log in')").first,
                    login_form.locator("button.button.cta").first,
                ]
                for btn in candidates:
                    try:
                        if btn.count() == 0:
                            continue
                        try:
                            btn.scroll_into_view_if_needed()
                        except Exception:
                            pass
                        try:
                            btn.click()
                            return True
                        except Exception:
                            try:
                                btn.click(force=True)
                                return True
                            except Exception:
                                continue
                    except Exception:
                        continue
                # Keyboard fallback
                try:
                    login_form.press("Enter")
                    return True
                except Exception:
                    return False

            # Try clicking up to 3 times if nothing changes
            prev_url = page.url
            for _ in range(3):
                if attempt_click_login():
                    try:
                        page.wait_for_load_state("networkidle")
                    except Exception:
                        pass
                    # Break if URL changed or confirmation visible
                    if page.url != prev_url or page.locator("text=/Check your email/i").count() > 0:
                        break
                    page.wait_for_timeout(1500)

            # Wait for either password step, an authenticated UI, or a confirmation message
            print("Waiting for next step after email submit...")
            try:
                page.wait_for_selector(
                    "input[type='password'], input[placeholder='Password'], text=/Check your email/i, a[href*='/account'], text=/Hi /i",
                    timeout=15000,
                )
            except Exception:
                pass

            # If password exists and we see a password field, complete it
            try:
                if self.password and login_form.locator("input[type='password'], input[placeholder='Password'], input[name='password']").first.count() > 0:
                    print("Entering password...")
                    login_form.locator("input[type='password'], input[placeholder='Password'], input[name='password']").first.fill(self.password)
                    # Click a submit button or press Enter
                    submit_clicked = False
                    for sel in [
                        "button[type='submit']",
                        "button[native-type='button']",
                        "button:has-text('Log in')",
                        "button:has-text('Sign in')",
                        "button:has-text('Submit')",
                    ]:
                        btn = login_form.locator(sel).first
                        if btn.count() > 0:
                            try:
                                btn.scroll_into_view_if_needed()
                            except Exception:
                                pass
                            try:
                                btn.click()
                            except Exception:
                                btn.click(force=True)
                            submit_clicked = True
                            break
                    if not submit_clicked:
                        login_form.press("Enter")
                    page.wait_for_load_state("networkidle")
            except Exception:
                pass

            # Save storage state regardless if we're fully logged in (best-effort)
            try:
                context.storage_state(path=str(self.auth_state_path))
                print("Login/session state saved for future runs.")
            except Exception:
                pass
            return
    
    def _open_cart_and_find_box(self, page):
        """Open the cart (page or sidebar) and find a box to customize."""
        print("Opening cart page...")
        try:
            page.goto("https://www.farmtopeople.com/cart")
            page.wait_for_load_state("networkidle")
        except Exception:
            pass
        
        # First, try parsing the full cart page
        print("Parsing cart page for items...")
        cart_items = []
        try:
            cart_items_loc = page.locator(
                "xpath=//article[contains(@class,'cart') or contains(@class,'CartItem') or contains(@class,'orderItem') or contains(@class,'cartOrderItem')]"
            )
            cart_items = cart_items_loc.all()
        except Exception:
            cart_items = []
        
        # If the cart page is empty, try opening the sidebar as a fallback
        if len(cart_items) == 0:
            print("Opening cart sidebar...")
            opened = False
            # Try multiple ways to open the cart
            for trigger in [
                "div.cart-button.ml-auto.cursor-pointer",
                "#cart-button",
                "button[aria-label='Cart']",
                "a[href='/cart']",
                "[data-testid='cart-button']"
            ]:
                try:
                    el = page.locator(trigger).first
                    if el.count() > 0:
                        el.click()
                        opened = True
                        break
                except Exception:
                    continue
            if not opened:
                # As a fallback, try pressing Escape to close any modal, then retry the main selector
                try:
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(250)
                    page.locator("div.cart-button.ml-auto.cursor-pointer").first.click()
                    opened = True
                except Exception:
                    pass
            
            print("Waiting for cart sidebar...")
            try:
                page.wait_for_selector("#cart aside, #cart [class*='cart_cartContent']", state="visible", timeout=10000)
            except Exception:
                print("Cart sidebar may not have opened. Continuing anyway.")
            
            print("\n----- Cart Contents -----")
            # Use a more resilient selector for cart line items (CSS modules safe via contains)
            cart_items_loc = page.locator("xpath=//article[contains(@class,'cart-order') or contains(@class,'CartItem') or contains(@class,'cartOrderItem')] ")
            cart_items = cart_items_loc.all()
        else:
            print("\n----- Cart Contents (Cart Page) -----")
        
        print(f"Found {len(cart_items)} items in cart")
        
        # Flag to track if we've found a box
        box_found = False
        
        for i, item in enumerate(cart_items):
            try:
                # Try multiple ways to get the item name
                name = ""
                name_locators = [
                    "a[class*='web-link_unstyled-link']",
                    "a",
                    "div[class*='name']",
                    "h3, h4, h5"
                ]
                for nl in name_locators:
                    nl_el = item.locator(nl).first
                    if nl_el.count() > 0:
                        txt = (nl_el.text_content() or "").strip()
                        if txt:
                            name = txt
                            break
                if not name:
                    print(f"Item {i+1}: Could not find name element")
                    continue
                
                # Quantity
                quantity = "1"
                qty_elem = item.locator("p.mt-2, [data-qty], [class*='quantity']").first
                if qty_elem.count() > 0:
                    qtxt = (qty_elem.text_content() or "").strip()
                    if qtxt:
                        quantity = qtxt
                
                # Try to get price
                price = ""
                price_elem = item.locator("xpath=.//*[contains(text(),'$')]").first
                if price_elem.count() > 0:
                    price_text = (price_elem.text_content() or "").strip()
                    price_match = re.search(r'\$(\d+\.\d+|\d+)', price_text)
                    if price_match:
                        price = price_match.group(0)
                
                print(f"Item {i+1}: {name} - {quantity} {price}")
                
                # Save cart item
                cart_item = {
                    "name": name,
                    "quantity": quantity
                }
                if price:
                    cart_item["price"] = price
                
                self.cart_items.append(cart_item)
                
                # Look for any box type with a customize button
                box_keywords = ["box", "bundle", "basket"]
                is_box = any(keyword.lower() in name.lower() for keyword in box_keywords)
                
                if is_box and not box_found:
                    print(f"\n! Found a box: {name} !")
                    
                    # Get box price if present
                    if price:
                        try:
                            self.box_price = float(price.replace('$', ''))
                            print(f"Box price: {price}")
                        except:
                            pass
                    
                    customize_btn = item.locator(
                        "button:has-text('CUSTOMIZE'), a:has-text('CUSTOMIZE'), button:has-text('Customize'), a:has-text('Customize')"
                    ).first
                    if customize_btn.count() > 0:
                        print("Customize button found! Clicking it...")
                        customize_btn.click()
                        page.wait_for_load_state("networkidle")
                        page.wait_for_timeout(3000)  # brief pause
                        box_found = True
                    else:
                        print("Customize button not found for this box.")
            
            except Exception as e:
                print(f"Error processing item {i+1}: {str(e)}")
        
        if not box_found:
            print("No customizable box found in cart. Add a farm box to your cart, then re-run.")
    
    def _detect_box_contents(self, page):
        """Detect and organize the contents of the box into protein and produce sections."""
        print("\n----- Detecting and Organizing Box Contents -----")
        
        # First, check if we have the category headers on the page
        protein_header = page.locator("h2:text('Proteins'), div:text('Proteins')").first
        protein_section_exists = protein_header.count() > 0
        
        if protein_section_exists:
            # Check if we have a protein limit
            protein_limit_text = page.locator("text=/Mix and match up to \\d+ item\\(s\\) from Proteins/").first
            if protein_limit_text.count() > 0:
                limit_match = re.search(r'up to (\d+)', protein_limit_text.text_content())
                if limit_match:
                    self.protein_limit = int(limit_match.group(1))
                    print(f"Protein selection limit: {self.protein_limit}")
        
        produce_header = page.locator("h2:text('Produce'), div:text('Produce')").first
        produce_section_exists = produce_header.count() > 0
        
        if produce_section_exists:
            # Check if we have a produce limit
            produce_limit_text = page.locator("text=/Mix and match up to \\d+ item\\(s\\) from Produce/").first
            if produce_limit_text.count() > 0:
                limit_match = re.search(r'up to (\d+)', produce_limit_text.text_content())
                if limit_match:
                    self.produce_limit = int(limit_match.group(1))
                    print(f"Produce selection limit: {self.produce_limit}")
        
        # Method 1: Look for items with robust selectors
        all_items = []
        
        item_selectors = [
            # Original class-based selectors
            "div[class*='customize-farmbox_customize-farmbox-item-name']",
            "div[class*='customize-farmbox-item-name']",
            # Buttons that often include the product name via "Read more about <name>"
            "button:has-text('Read more about')",
            "button[aria-label^='Read more about']",
            # Any element that has a child button with that text
            ":has(button:has-text('Read more about'))"
        ]
        
        for selector in item_selectors:
            try:
                item_elements = page.locator(selector).all()
            except Exception:
                item_elements = []
            print(f"Found {len(item_elements)} elements with selector '{selector}'")
            
            for elem in item_elements:
                try:
                    # Get the item text (may be in a button as shown in the screenshot)
                    item_text = (elem.text_content() or "").strip()
                    
                    # Handle aria-label versions
                    try:
                        aria = elem.get_attribute("aria-label") or ""
                        if aria:
                            item_text = aria.strip()
                    except Exception:
                        pass
                    
                    # The screenshot shows the text might be in a button
                    if "Read more about" in item_text:
                        item_text = item_text.replace("Read more about", "").strip()
                    
                    if not item_text:
                        button = elem.locator("button").first
                        if button.count() > 0:
                            button_text = (button.text_content() or "").strip()
                            # Remove "Read more about" text if present
                            item_text = button_text.replace("Read more about", "").strip()
                    
                    if item_text and item_text not in ["Read more about"]:
                        # Now look for quantity and unit info near this element
                        
                        # Default values
                        quantity = "1"
                        unit_info = ""
                        
                        # Look for nearby elements with quantity/unit info
                        parent = elem.locator("xpath=ancestor::div[contains(@class, 'flex') or contains(@class, 'grid')][position()<=3]").first
                        if parent.count() > 0:
                            # Look for unit info text
                            unit_texts = parent.locator("div, span, p").all()
                            for unit_elem in unit_texts:
                                unit_text = (unit_elem.text_content() or "").strip()
                                # Match patterns like "8.0 oz", "1.0 Lbs", "1 dozen", "2 pieces", etc.
                                unit_match = re.search(r'(\d+\.?\d*)\s*(oz|lb|lbs|dozen|head|bunch|pieces?)', unit_text, re.IGNORECASE)
                                if unit_match and unit_text != item_text:
                                    unit_info = unit_text
                                    break
                        
                        # Special handling: check if this is a protein item
                        is_protein = False
                        protein_keywords = ["chicken", "beef", "fish", "redfish", "salmon", "pork", "meat", "egg", "seafood", 
                                           "turkey", "sausage", "thigh", "monkfish", "ground", "italian sausage", "sweet italian", 
                                           "boneless", "skinless", "white ground", "chicken breast", "chicken thighs",]
                        if any(keyword in item_text.lower() for keyword in protein_keywords):
                            is_protein = True
                        
                        # Add to our list of items to process
                        all_items.append({
                            "name": item_text,
                            "quantity": quantity,
                            "unit_info": unit_info,
                            "is_protein": is_protein
                        })
                except Exception as e:
                    print(f"  Error processing element: {str(e)}")
        
        # Deduplicate items based on name
        unique_items = {}
        for item in all_items:
            name = item["name"]
            if name not in unique_items:
                unique_items[name] = item
        
        # Sort items into protein and produce categories
        for name, item in unique_items.items():
            if item["is_protein"]:
                self.protein_items.append(item)
            else:
                # Check if it might be produce
                produce_keywords = ["organic", "fruit", "vegetable", "kale", "cabbage", "carrot", "onion", 
                                   "cucumber", "apple", "orange", "radish", "beet", "mushroom", "pepper",
                                   "leaf", "lettuce", "parsnip", "squash", "zucchini", "broccoli", "cauliflower",
                                   "spinach", "celery", "potato", "sweet potato", "tomato", "berry", "grape",
                                   "pear", "peach", "plum", "cherry", "melon", "cabbage", "leafy green"]
                if any(keyword in name.lower() for keyword in produce_keywords):
                    self.produce_items.append(item)
                else:
                    # If we can't categorize it, put it in other
                    self.other_items.append(item)
        
        print(f"\nOrganized {len(unique_items)} unique items:")
        print(f"  - Proteins: {len(self.protein_items)} (limit: {self.protein_limit})")
        print(f"  - Produce: {len(self.produce_items)} (limit: {self.produce_limit})")
        print(f"  - Other items: {len(self.other_items)}")
    
    def _save_results(self):
        """Save the organized box contents to a file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "box_price": self.box_price,
            "protein_items": self.protein_items,
            "protein_limit": self.protein_limit,
            "produce_items": self.produce_items,
            "produce_limit": self.produce_limit,
            "other_items": self.other_items,
            "cart_items": self.cart_items
        }
        
        output_file = self.data_dir / f"organized_box_contents_{timestamp}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\nSaved organized results to {output_file}")
    
    def _print_results(self):
        """Print the organized box contents nicely."""
        print("\n===== Organized Box Contents =====")
        print(f"Box Price: ${self.box_price}" if self.box_price > 0 else "Box Price: Unknown")
        
        print(f"\nPROTEINS (Choose {self.protein_limit}):")
        print(f"Found {len(self.protein_items)} protein options")
        for i, item in enumerate(self.protein_items):
            name = item.get("name", "Unknown Item")
            unit_info = f" ({item.get('unit_info')})" if item.get("unit_info") else ""
            print(f"  {i+1}. {name}{unit_info}")
        
        print(f"\nPRODUCE (Choose {self.produce_limit}):")
        print(f"Found {len(self.produce_items)} produce options")
        for i, item in enumerate(self.produce_items):
            name = item.get("name", "Unknown Item")
            unit_info = f" ({item.get('unit_info')})" if item.get("unit_info") else ""
            print(f"  {i+1}. {name}{unit_info}")
        
        if self.other_items:
            print("\nOTHER ITEMS (Uncategorized):")
            for i, item in enumerate(self.other_items):
                name = item.get("name", "Unknown Item")
                unit_info = f" ({item.get('unit_info')})" if item.get("unit_info") else ""
                print(f"  {i+1}. {name}{unit_info}")


if __name__ == "__main__":
    organizer = BoxContentOrganizer()
    organizer.run()