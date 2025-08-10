from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
import json
import re
from datetime import datetime
import argparse
import random

load_dotenv()

def classify_item(name: str) -> str:
    """
    Categorize an item name into proper food categories.
    Returns one of: 'root_veg', 'greens', 'fruit', 'protein', 'other_veg', or 'other'.
    """
    name_lower = name.lower()

    # Fix "watermelon radish" confusion
    if "radish" in name_lower:
        return "root_veg"
    
    # Root vegetables
    root_keywords = ["potato", "carrot", "beet", "turnip", "onion", "garlic", 
                     "ginger", "parsnip", "rutabaga", "radish", "shallot", "yam", 
                     "cassava", "celeriac", "sweet potato", "yuca"]
    for root_word in root_keywords:
        if root_word in name_lower:
            return "root_veg"
    
    # Fruit keywords expanded
    fruit_keywords = [
        "apple", "pear", "peach", "plum", "banana", "mandarin", "orange", "grapefruit", 
        "melon", "mango", "pineapple", "fruit", "lemon", "lime", "berry", "berries",
        "strawberry", "blueberry", "blackberry", "raspberry", "grape", "cherry", 
        "kiwi", "persimmon", "watermelon", "cantaloupe", "honeydew", "papaya", "nectarine",
        "apricot", "avocado", "guava", "fig", "pear", "pomegranate", "tomato"
    ]
    for fruit_word in fruit_keywords:
        if fruit_word in name_lower:
            return "fruit"
    
    # Greens keywords expanded
    green_keywords = ["broccoli", "kale", "chard", "lettuce", "spinach", "rabe", "arugula", 
                     "collard", "cabbage", "brussels sprout", "bok choy", "mustard green", 
                     "romaine", "mesclun", "microgreen", "dandelion", "watercress"]
    for green_word in green_keywords:
        if green_word in name_lower:
            return "greens"
    
    # Protein items (for Paleo box)
    protein_keywords = ["meat", "beef", "chicken", "turkey", "fish", "salmon", "egg", 
                        "pork", "bacon", "sausage", "steak", "jerky", "prosciutto", 
                        "salami", "ham", "bison", "lamb", "duck"]
    for protein_word in protein_keywords:
        if protein_word in name_lower:
            return "protein"
    
    # Other vegetables expanded
    veg_keywords = ["pepper", "zucchini", "squash", "cucumber", "eggplant", "asparagus", 
                    "celery", "bean", "pea", "corn", "cauliflower", "artichoke", "fennel",
                    "leek", "mushroom", "okra", "sprout", "shishito"]
    for veg_word in veg_keywords:
        if veg_word in name_lower:
            return "other_veg"
    
    # If we can't identify the category, return "other"
    return "other"

def simplify_ingredient(full_name: str) -> tuple:
    """
    Takes a full ingredient name and returns a tuple of (full_name, simplified_name).
    Enhanced with more ingredients including those for paleo boxes.
    """
    full_name = full_name.lower()
    
    # Remove "organic" prefix which doesn't affect cooking
    cleaned_name = full_name.replace("organic ", "")
    
    # Look for the main ingredient in the name
    # First try to match complete phrases
    ingredient_mapping = {
        "sweet potato": "sweet potato",
        "russet potato": "potato",
        "yukon gold potato": "potato",
        "potato": "potato",
        "watermelon radish": "watermelon radish",
        "radish": "radish",
        "carrot": "carrot",
        "broccoli rabe": "broccoli rabe",
        "broccoli": "broccoli",
        "kale": "kale",
        "spinach": "spinach",
        "lettuce": "lettuce",
        "green bean": "green beans",
        "zucchini": "zucchini",
        "shishito pepper": "shishito pepper",
        "bell pepper": "bell pepper",
        "pepper": "pepper",
        "mandarin": "mandarin",
        "apple": "apple",
        "banana": "banana",
        "lemon": "lemon",
        "chicken": "chicken",
        "beef": "beef",
        "pork": "pork",
        "salmon": "salmon",
        "egg": "egg",
        "mushroom": "mushroom",
        "asparagus": "asparagus",
        "onion": "onion",
        "garlic": "garlic",
        "cucumber": "cucumber",
        "cauliflower": "cauliflower",
        "beet": "beet",
        "turnip": "turnip",
        "squash": "squash",
        "cabbage": "cabbage",
        "brussels sprout": "brussels sprouts",
        "ginger": "ginger",
        "tomato": "tomato"
    }
    
    # Try to find the most specific match first
    for key, value in sorted(ingredient_mapping.items(), key=lambda x: len(x[0]), reverse=True):
        if key in cleaned_name:
            return (full_name, value)
    
    # If no specific match, just use the cleaned name
    return (full_name, cleaned_name)

class FarmToTablePlanner:
    def __init__(self, output_dir=None, prefer_summer=False, debug=False):
        self.email = os.getenv("EMAIL")
        self.password = os.getenv("PASSWORD")
        self.storage_state_path = Path("auth_state.json")
        self.output_dir = Path(output_dir) if output_dir else Path("farm_box_data")
        self.output_dir.mkdir(exist_ok=True)

        self.prefer_summer = prefer_summer
        self.debug = debug
        
        self.cart_contents = []
        self.box_selected_items = []
        
        # Recipe database - exciting meal prep ideas
        # Extended with more recipes for a wider variety of ingredients including paleo options
        self.recipe_database = {
            "bowls": [
                {
                    "name": "Roasted Veggie Power Bowl",
                    "ingredients": ["sweet potato", "broccoli", "kale"],
                    "protein": "Chicken or tofu",
                    "method": "Roast veggies at 425°F for 25 min, add protein of choice, top with tahini dressing",
                    "office_friendly": True,
                    "tags": ["meal_prep", "healthy", "gluten_free"],
                    "diet_type": ["regular", "paleo"]
                },
                {
                    "name": "Buddha Bowl with Ginger-Sesame Drizzle",
                    "ingredients": ["sweet potato", "zucchini", "broccoli", "kale"],
                    "protein": "Baked tofu or chicken thighs",
                    "method": "Roast veggies, prepare protein separately, combine with rice/quinoa, top with sesame seeds and ginger dressing",
                    "office_friendly": True,
                    "tags": ["asian_inspired", "healthy"],
                    "diet_type": ["regular"]
                },
                {
                    "name": "Mediterranean Bowl",
                    "ingredients": ["zucchini", "potato", "broccoli", "tomato"],
                    "protein": "Chicken or chickpeas",
                    "method": "Season veggies with oregano and roast, serve over couscous with lemon-olive oil dressing",
                    "office_friendly": True,
                    "tags": ["mediterranean", "bright", "colorful"],
                    "diet_type": ["regular"]
                },
                {
                    "name": "Paleo Protein Bowl",
                    "ingredients": ["sweet potato", "kale", "broccoli"],
                    "protein": "Grilled chicken or steak",
                    "method": "Roast veggies with olive oil and herbs, top with grilled protein and avocado",
                    "office_friendly": True,
                    "tags": ["paleo", "high_protein", "low_carb"],
                    "diet_type": ["paleo"]
                }
            ],
            "sheet_pan_meals": [
                {
                    "name": "Sheet Pan Sweet Potato & Greens Hash",
                    "ingredients": ["sweet potato", "kale", "onion"],
                    "protein": "Sausage or chicken thighs",
                    "method": "Dice everything, toss with olive oil and herbs, roast at 425°F for 30 min, crack eggs on top for last 5 min (optional)",
                    "office_friendly": True,
                    "tags": ["one_pan", "easy_cleanup", "weeknight"],
                    "diet_type": ["regular", "paleo"]
                },
                {
                    "name": "Roasted Root Vegetable Medley",
                    "ingredients": ["carrot", "beet", "turnip", "onion"],
                    "protein": "Roast chicken or pork tenderloin",
                    "method": "Dice vegetables, toss with olive oil, rosemary and thyme, roast at 400°F for 35-40 min alongside protein",
                    "office_friendly": True,
                    "tags": ["seasonal", "comfort_food", "root_vegetables"],
                    "diet_type": ["regular", "paleo"]
                },
                {
                    "name": "Paleo Sheet Pan Dinner",
                    "ingredients": ["sweet potato", "broccoli", "carrot"],
                    "protein": "Chicken thighs or salmon",
                    "method": "Season protein, arrange on sheet pan with vegetables, roast at 400°F for 25 min",
                    "office_friendly": True,
                    "tags": ["paleo", "easy", "complete_meal"],
                    "diet_type": ["paleo"]
                }
            ],
            "stir_fry": [
                {
                    "name": "Ginger-Garlic Veggie Stir-Fry",
                    "ingredients": ["broccoli", "carrot", "bell pepper", "green beans"],
                    "protein": "Chicken, tofu, or shrimp",
                    "method": "Stir-fry veggies with ginger and garlic, add protein, finish with soy sauce and rice vinegar, serve over rice",
                    "office_friendly": True,
                    "tags": ["quick", "flavorful", "asian_inspired"],
                    "diet_type": ["regular"]
                },
                {
                    "name": "Paleo Vegetable and Protein Stir-Fry",
                    "ingredients": ["broccoli", "carrot", "onion", "mushroom"],
                    "protein": "Sliced beef or chicken",
                    "method": "Stir-fry protein first, remove from pan, stir-fry vegetables, combine with coconut aminos",
                    "office_friendly": True,
                    "tags": ["paleo", "quick", "easy"],
                    "diet_type": ["paleo"]
                }
            ],
            "salads": [
                {
                    "name": "Hearty Roasted Vegetable Salad",
                    "ingredients": ["sweet potato", "watermelon radish", "kale", "arugula"],
                    "protein": "Grilled chicken or chickpeas",
                    "method": "Roast root vegetables, combine with greens, protein, and vinaigrette, top with nuts or seeds",
                    "office_friendly": True,
                    "tags": ["meal_sized", "satisfying", "nutritious"],
                    "diet_type": ["regular", "paleo"]
                },
                {
                    "name": "Citrus & Greens Superfood Salad",
                    "ingredients": ["kale", "arugula", "apple", "mandarin"],
                    "protein": "Grilled chicken or quinoa",
                    "method": "Massage kale with olive oil, add citrus segments, protein, and light vinaigrette",
                    "office_friendly": True,
                    "tags": ["bright", "refreshing", "detox"],
                    "diet_type": ["regular", "paleo"]
                },
                {
                    "name": "Paleo Chef's Salad",
                    "ingredients": ["lettuce", "tomato", "cucumber", "radish"],
                    "protein": "Hard-boiled eggs, chicken, and bacon",
                    "method": "Arrange vegetables in a large bowl, top with protein, drizzle with olive oil and lemon juice",
                    "office_friendly": True,
                    "tags": ["paleo", "protein_rich", "filling"],
                    "diet_type": ["paleo"]
                }
            ],
            "roasts": [
                {
                    "name": "Herb-Crusted Roasted Vegetables",
                    "ingredients": ["potato", "carrot", "broccoli", "onion"],
                    "protein": "Roast chicken or pot roast (separately)",
                    "method": "Toss vegetables with herbs and olive oil, roast at 400°F for 35-40 min while preparing protein separately",
                    "office_friendly": True,
                    "tags": ["classic", "comfort_food", "sunday_dinner"],
                    "diet_type": ["regular"]
                },
                {
                    "name": "Paleo Sunday Roast",
                    "ingredients": ["sweet potato", "carrot", "onion", "brussels sprouts"],
                    "protein": "Beef roast or whole chicken",
                    "method": "Season protein, arrange vegetables around it, roast until protein is cooked through and vegetables are tender",
                    "office_friendly": True,
                    "tags": ["paleo", "family_meal", "weekend"],
                    "diet_type": ["paleo"]
                }
            ],
            "soups": [
                {
                    "name": "Hearty Vegetable & Grain Soup",
                    "ingredients": ["carrot", "potato", "onion", "kale"],
                    "protein": "Chicken, turkey, or white beans",
                    "method": "Sauté aromatics, add chopped veggies, broth, grain (barley/farro), and protein, simmer until tender",
                    "office_friendly": True,
                    "tags": ["comforting", "meal_in_bowl", "freezer_friendly"],
                    "diet_type": ["regular"]
                },
                {
                    "name": "Paleo Vegetable Soup",
                    "ingredients": ["carrot", "onion", "zucchini", "kale"],
                    "protein": "Chicken or beef",
                    "method": "Sauté aromatics, add protein and brown lightly, add vegetables and broth, simmer until tender",
                    "office_friendly": True,
                    "tags": ["paleo", "warming", "nutrient_dense"],
                    "diet_type": ["paleo"]
                }
            ]
        }
    
    def scan_box(self):
        """
        Main entry point:
        - Logs in / re-uses saved session
        - Opens cart & finds any type of produce or paleo box
        - Extracts selected items
        - Provides creative meal prep ideas for 4 servings
        """
        print("\n===== Farm to People Dynamic Meal Planner =====\n")
        if self.prefer_summer:
            print("Note: Focusing on heat-friendly and no-cook options for summer.\n")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            
            context_options = {}
            if self.storage_state_path.exists():
                print(f"Found saved session at {self.storage_state_path}")
                context_options["storage_state"] = str(self.storage_state_path)
            
            context = browser.new_context(**context_options)
            page = context.new_page()
            
            try:
                self._login(page, context)
                self._open_cart(page)
                self._truly_scan_box_contents(page)
                
                # Generate meal ideas
                self._suggest_meal_prep_ideas()
                
                # Keep browser open for final manual adjustments
                print("\nPress Enter when you're done making changes to close the browser...")
                input()
            
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                error_screenshot_path = self.output_dir / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                page.screenshot(path=str(error_screenshot_path))
                print(f"Error screenshot saved to {error_screenshot_path}")
            
            finally:
                browser.close()
    
    def _login(self, page, context):
        print("Navigating to Farm to People...")
        page.goto("https://www.farmtopeople.com")
        page.wait_for_load_state("networkidle")
        
        print("Checking login status...")
        is_logged_in = False
        login_indicators = [
            "text=Shopping for:",
            "text=Hi ",
            "div.account-button",
            "a[href='/account']"
        ]
        
        for indicator in login_indicators:
            if page.locator(indicator).count() > 0:
                print("Already logged in!")
                is_logged_in = True
                break
        
        if not is_logged_in:
            print("Not logged in. Proceeding to login page...")
            page.goto("https://www.farmtopeople.com/login")
            page.wait_for_load_state("networkidle")
            
            print("Entering email...")
            page.fill("input[type='email']", self.email)
            page.keyboard.press("Enter")
            
            print("Waiting for password field...")
            page.wait_for_selector("input[type='password']")
            
            print("Entering password...")
            page.fill("input[placeholder='Password']", self.password)
            
            print("Clicking login button...")
            page.click("button[native-type='button']")
            page.wait_for_load_state("networkidle")
            
            context.storage_state(path=str(self.storage_state_path))
            print("Login credentials saved for future runs.")
    
    def _open_cart(self, page):
        print("Clicking the cart button...")
        page.click("div.cart-button.ml-auto.cursor-pointer")
        
        print("Waiting for cart sidebar to appear...")
        page.wait_for_selector("#cart aside div.cart_cartContent__gLS77",
                               state="visible",
                               timeout=10000)
        print("Cart sidebar is visible.")
        
        cart_screenshot_path = self.output_dir / f"cart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=str(cart_screenshot_path))
        
        print("\n----- Cart Contents -----")
        cart_items = page.locator("article.cart-order_cartOrderItem__CDYTs").all()
        print(f"Found {len(cart_items)} items in cart.")
        
        # Flag to track if we've found a box
        box_found = False
        
        for i, item in enumerate(cart_items):
            try:
                name_elem = item.locator("a.web-link_unstyled-link__uJvxp.bold").first
                if name_elem.count() == 0:
                    print(f"Item {i+1}: Could not find name element")
                    continue
                
                name = name_elem.text_content().strip()
                qty_elem = item.locator("p.mt-2").first
                quantity = qty_elem.text_content().strip() if qty_elem.count() > 0 else "N/A"
                
                print(f"Item {i+1}: {name} - {quantity}")
                self.cart_contents.append({"name": name, "quantity": quantity})
                
                # Look for any box type with a customize button - now checks for any type of box
                # This matches Seasonal Produce Box, Paleo Box, Small Produce Box, etc.
                box_keywords = ["box", "bundle", "basket"]
                is_box = any(keyword.lower() in name.lower() for keyword in box_keywords)
                
                if is_box and not box_found:
                    print(f"\n! Found a box: {name} !")
                    customize_btn = item.locator("button:has-text('CUSTOMIZE')").first
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
    
    def _truly_scan_box_contents(self, page):
        """
        Enhanced method to accurately detect what's currently in the box.
        This uses multiple targeted approaches with better debugging.
        """
        customization_screenshot_path = self.output_dir / f"customize_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=str(customization_screenshot_path))
        
        print("\n----- Reading Box Contents -----")
        
        # Check if we can see the "X of Y items selected" text to confirm we're on the right page
        items_count_text = page.locator("text=/\\d+ of \\d+ items selected/").first
        if items_count_text.count() > 0:
            selected_count_text = items_count_text.text_content().strip()
            print(f"Found box status: {selected_count_text}")
            
            # Extract the numbers from the text
            match = re.search(r'(\d+) of (\d+)', selected_count_text)
            if match:
                selected_count = int(match.group(1))
                total_allowed = int(match.group(2))
                print(f"Box has {selected_count} of {total_allowed} items selected")
        
        # APPROACH 1: Look at the sidebar items list on the right of the customization page
        sidebar_items = []
        
        # The right sidebar shows selected items with images
        print("\nAttempting to read selected items from right sidebar...")
        
        # Look for divs containing images and item descriptions in the right column
        sidebar_img_containers = page.locator("div.mr-2:has(img)").all()
        
        if sidebar_img_containers:
            print(f"Found {len(sidebar_img_containers)} items with images in sidebar")
            
            for img_container in sidebar_img_containers:
                # Look for the item name and quantity text next to the image
                try:
                    # Try to get the full item row to extract text
                    parent_row = img_container.locator("xpath=..").first
                    if parent_row.count() > 0:
                        row_text = parent_row.text_content().strip()
                        
                        # Debug output
                        if self.debug:
                            print(f"Row text: {row_text}")
                        
                        # Look for patterns like "1 Stem and Leaf Mandarins"
                        match = re.search(r'(\d+)\s+(.+?)(?:\s+(\d+\.?\d*\s*\w+|\d+-\d+\s*\w+))?$', row_text)
                        if match:
                            quantity = match.group(1)
                            name = match.group(2).strip()
                            unit_info = match.group(3) if match.group(3) else ""
                            
                            sidebar_items.append({
                                "name": name,
                                "quantity": quantity,
                                "unit_info": unit_info
                            })
                            
                            print(f"  Found sidebar item: {quantity}x {name} {unit_info}")
                        else:
                            # If regex fails, try to find the item name another way
                            item_text_div = parent_row.locator("div.text-sm, div.text-base").first
                            if item_text_div.count() > 0:
                                text = item_text_div.text_content().strip()
                                if text:
                                    # Simple parsing: assume first digit is quantity, rest is name
                                    parts = text.split(' ', 1)
                                    if len(parts) > 1 and parts[0].isdigit():
                                        quantity = parts[0]
                                        name = parts[1]
                                        
                                        sidebar_items.append({
                                            "name": name,
                                            "quantity": quantity,
                                            "unit_info": ""
                                        })
                                        
                                        print(f"  Found sidebar item (alt method): {quantity}x {name}")
                except Exception as e:
                    print(f"  Error processing sidebar item: {str(e)}")
        else:
            print("No items with images found in sidebar")
        
        # APPROACH 2: Look for selected items in the main content area
        # These are items with minus/plus buttons instead of "ADD" buttons
        if not sidebar_items:
            print("\nTrying to find selected items from main content area...")
            
            # Find elements that have minus buttons (these are selected items)
            all_minus_buttons = page.locator("button:has-text('-')").all()
            print(f"Found {len(all_minus_buttons)} minus buttons on the page")
            
            for minus_btn in all_minus_buttons:
                try:
                    # Find the parent article that contains product info
                    article = minus_btn.locator("xpath=ancestor::article").first
                    
                    if article.count() > 0:
                        # Get the product name
                        name_elem = article.locator("h3").first
                        if name_elem.count() > 0:
                            name = name_elem.text_content().strip()
                            
                            # Get quantity
                            qty_input = article.locator("input[type='number']").first
                            quantity = "1"  # Default
                            if qty_input.count() > 0:
                                try:
                                    quantity = qty_input.input_value()
                                    # Skip if quantity is 0
                                    if quantity == "0":
                                        continue
                                except:
                                    pass
                            
                            # Get unit info
                            unit_elem = article.locator("p.weight").first
                            unit_info = ""
                            if unit_elem.count() > 0:
                                unit_info = unit_elem.text_content().strip()
                            
                            # Only add if we have a valid name and quantity > 0
                            if name and quantity and quantity != "0":
                                sidebar_items.append({
                                    "name": name,
                                    "quantity": quantity,
                                    "unit_info": unit_info
                                })
                                print(f"  Found selected item in main content: {quantity}x {name} ({unit_info})")
                except Exception as e:
                    print(f"  Error processing minus button: {str(e)}")
        
        # APPROACH 3: Try other selector patterns that might contain selected items
        if not sidebar_items:
            print("\nTrying alternative selectors for items...")
            
            # This is a generic approach that tries to find any element with item information
            selectors = [
                "div.product-card", 
                "article.product-item",
                "div.item-card",
                "li.selected-item"
            ]
            
            for selector in selectors:
                try:
                    item_elements = page.locator(selector).all()
                    print(f"Found {len(item_elements)} potential items with selector: {selector}")
                    
                    for item_elem in item_elements:
                        # Try to get name from any heading element
                        name_elem = item_elem.locator("h3, h4, h5, .title, .name").first
                        
                        if name_elem.count() > 0:
                            name = name_elem.text_content().strip()
                            
                            # Try to find quantity
                            qty_elem = item_elem.locator("input[type='number'], .quantity, .qty").first
                            quantity = "1"  # Default
                            
                            if qty_elem.count() > 0:
                                try:
                                    quantity = qty_elem.input_value() or qty_elem.text_content().strip()
                                    # Skip if quantity is 0
                                    if quantity == "0":
                                        continue
                                except:
                                    pass
                            
                            # Try to find unit info
                            unit_elem = item_elem.locator(".weight, .unit, .size").first
                            unit_info = ""
                            if unit_elem.count() > 0:
                                unit_info = unit_elem.text_content().strip()
                            
                            # Only add if we have a valid name
                            if name:
                                sidebar_items.append({
                                    "name": name,
                                    "quantity": quantity,
                                    "unit_info": unit_info
                                })
                                print(f"  Found item with alt selector: {quantity}x {name} ({unit_info})")
                except Exception as e:
                    print(f"  Error with alt selector {selector}: {str(e)}")
        
        # Save the detected items - no fallback
        if sidebar_items:
            print(f"\nSuccessfully found {len(sidebar_items)} items in your box!")
            self.box_selected_items = sidebar_items
        else:
            print("\nWARNING: No items were detected in your box.")
            self.box_selected_items = []
        
        # Save final box data
        box_data = {
            "timestamp": datetime.now().isoformat(),
            "selected_items": self.box_selected_items,
            "detection_method": "dynamic"
        }
        box_json_path = self.output_dir / f"box_contents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(box_json_path, 'w') as f:
            json.dump(box_data, f, indent=2)
        
        print(f"\nBox contents saved to {box_json_path}")
    
    def _suggest_meal_prep_ideas(self):
        """
        Generate creative and exciting meal prep ideas for 4 servings.
        Enhanced to work with paleo and small produce boxes.
        """
        print("\n===== Exciting Meal Prep Ideas (4 Servings) =====")
        
        if not self.box_selected_items:
            print("No items found in your box this week, so no meal suggestions.")
            return
        
        # Detect if this might be a paleo box by checking for protein items
        has_protein_items = any(classify_item(item["name"]) == "protein" for item in self.box_selected_items)
        is_likely_paleo = has_protein_items
        
        if is_likely_paleo:
            print("\nDetected protein items - looks like you might have a Paleo box!")
        
        # Categorize everything properly
        categorized = {"root_veg": [], "greens": [], "fruit": [], "other_veg": [], "protein": [], "other": []}
        for item in self.box_selected_items:
            cat = classify_item(item["name"])
            categorized[cat].append(item)
        
        # Print categorized items for verification
        print("\nYour box items by category:")
        for category, items in categorized.items():
            if items:
                print(f"  {category.replace('_', ' ').title()}: {', '.join(item['name'] for item in items)}")
        
        # Find matching recipes based on box contents
        matched_recipes = []
        simplified_ingredients = []
        simplified_lookup = {}  # Maps simplified names back to full names
        
        # Create a simplified list of ingredients for matching, keeping full names
        for category in categorized.values():
            for item in category:
                full_name = item["name"]
                full_name_lower = full_name.lower()
                
                # Get appropriate simplified name for matching while preserving distinctions
                full, simplified = simplify_ingredient(full_name)
                
                # Only add if we haven't seen this simplified name yet
                if simplified not in simplified_lookup:
                    simplified_ingredients.append(simplified)
                    simplified_lookup[simplified] = full
        
        print(f"\nKey ingredients identified:")
        for simp in simplified_ingredients:
            full = simplified_lookup[simp]
            print(f"  • {full} (matching as '{simp}')")
        
        # Find recipes that use these ingredients
        diet_type_filter = ["paleo"] if is_likely_paleo else ["regular", "paleo"]
        
        for category, recipes in self.recipe_database.items():
            for recipe in recipes:
                # Skip recipes that don't match the box type
                if not any(dt in diet_type_filter for dt in recipe.get("diet_type", ["regular"])):
                    continue
                
                matching_ingredients = 0
                matched_ingredient_names = []
                
                for ingredient in recipe["ingredients"]:
                    if ingredient in simplified_ingredients:
                        matching_ingredients += 1
                        # Get the original full name for display
                        matched_ingredient_names.append(simplified_lookup[ingredient])
                
                # For small boxes, we need to be more flexible with matches
                min_matches = 1 if len(self.box_selected_items) <= 3 else 2
                
                if matching_ingredients >= min_matches:
                    matched_recipes.append({
                        "recipe": recipe,
                        "matches": matching_ingredients,
                        "category": category,
                        "matched_ingredients": matched_ingredient_names
                    })
        
        # Sort by number of matching ingredients, descending
        matched_recipes.sort(key=lambda x: x["matches"], reverse=True)
        
        # If we found matching recipes, share them
        if matched_recipes:
            print(f"\nFound {len(matched_recipes)} recipe ideas that work with your box!")
            
            # Select the 2 best matches to showcase
            for i, match in enumerate(matched_recipes[:2]):
                recipe = match["recipe"]
                print(f"\n🔥 EXCITING MEAL IDEA #{i+1}: {recipe['name'].upper()}")
                print(f"  Type: {match['category'].replace('_', ' ').title()}")
                print(f"  Matching ingredients: {', '.join(match['matched_ingredients'])}")
                print(f"  Recommended protein: {recipe['protein']}")
                print(f"  Method: {recipe['method']}")
                print(f"  Office-friendly: {'Yes' if recipe['office_friendly'] else 'Better for home'}")
                print(f"  Makes: 4 servings")
        else:
            # If no matches, create a custom suggestion
            print("\nCreating a custom meal plan for your unique ingredients:")
            
            # Find our primary ingredients
            primary_veg = None
            if categorized["root_veg"]:
                # Prioritize sweet potatoes
                sweet_potatoes = [item for item in categorized["root_veg"] 
                                 if "sweet potato" in item["name"].lower()]
                if sweet_potatoes:
                    primary_veg = sweet_potatoes[0]["name"]
                else:
                    primary_veg = categorized["root_veg"][0]["name"]
            elif categorized["other_veg"]:
                primary_veg = categorized["other_veg"][0]["name"]
            elif categorized["greens"]:
                primary_veg = categorized["greens"][0]["name"]
            
            secondary_veg = None
            if categorized["greens"] and primary_veg not in [item["name"] for item in categorized["greens"]]:
                secondary_veg = categorized["greens"][0]["name"]
            elif categorized["other_veg"] and primary_veg not in [item["name"] for item in categorized["other_veg"]]:
                secondary_veg = categorized["other_veg"][0]["name"]
            elif categorized["root_veg"] and primary_veg not in [item["name"] for item in categorized["root_veg"]]:
                secondary_veg = categorized["root_veg"][0]["name"]
            
            # For paleo boxes, incorporate protein
            primary_protein = None
            if categorized["protein"]:
                primary_protein = categorized["protein"][0]["name"]
            
            if primary_veg and (secondary_veg or primary_protein):
                title_components = []
                if primary_veg:
                    title_components.append(primary_veg.upper())
                if secondary_veg:
                    title_components.append(secondary_veg.upper())
                if primary_protein:
                    title_components.append(primary_protein.upper())
                
                title = " & ".join(title_components)
                print(f"\n🔥 CUSTOM {'PALEO ' if is_likely_paleo else ''}POWER MEAL WITH {title}")
                
                meal_type = "Sheet Pan Dinner" if primary_veg and primary_protein else "Grain Bowl"
                print(f"  Type: {meal_type}")
                
                main_ingredients = []
                if primary_veg:
                    main_ingredients.append(primary_veg)
                if secondary_veg:
                    main_ingredients.append(secondary_veg)
                if primary_protein:
                    main_ingredients.append(primary_protein)
                
                print(f"  Main ingredients: {', '.join(main_ingredients)}")
                
                # Choose appropriate protein suggestion if we don't already have one
                if not primary_protein:
                    if is_likely_paleo:
                        protein = "Grilled chicken or grass-fed beef"
                    else:
                        if "potato" in (primary_veg or "").lower():
                            protein = "Roasted chicken thighs (juicy and flavorful)"
                        elif any(green in (primary_veg or "").lower() or green in (secondary_veg or "").lower() 
                                for green in ["broccoli", "kale", "spinach"]):
                            protein = "Grilled chicken breast or baked tofu"
                        else:
                            protein = "Your choice of chicken, ground turkey, or tofu"
                    
                    print(f"  Recommended protein: {protein}")
                else:
                    print(f"  Protein: {primary_protein} (already in your box!)")
                
                if is_likely_paleo:
                    method = (f"Season {primary_protein if primary_protein else 'protein'} with herbs and spices, "
                              f"arrange on sheet pan with chopped vegetables, roast at 400°F for 25-30 minutes")
                else:
                    method = ("Roast vegetables with olive oil, garlic, and herbs of choice at 425°F. "
                              "Serve over quinoa or brown rice with your favorite sauce")
                
                print(f"  Method: {method}")
                print("  Office-friendly: Yes (stores and reheats well)")
                print("  Makes: 4 hearty servings")
            else:
                print("Not enough ingredients found to create a custom recipe.")
        
        # Additional ideas for using leftover items
        used_items = set()
        if matched_recipes:
            for match in matched_recipes[:2]:
                for matched_ingredient in match["matched_ingredients"]:
                    used_items.add(matched_ingredient)
        
        leftover_items = [item for item in self.box_selected_items if item["name"] not in used_items]
        
        if leftover_items:
            print("\n🥗 IDEAS FOR OTHER ITEMS IN YOUR BOX:")
            
            # Group by category
            leftover_by_category = {"root_veg": [], "greens": [], "fruit": [], "other_veg": [], "protein": [], "other": []}
            for item in leftover_items:
                cat = classify_item(item["name"])
                leftover_by_category[cat].append(item["name"])
            
            # Suggest uses based on category
            if leftover_by_category["fruit"]:
                print("  Fruit Items:")
                for fruit in leftover_by_category["fruit"]:
                    if "apple" in fruit.lower():
                        print(f"   • {fruit}: Perfect for snacking, or slice and top with nut butter")
                    elif "mandarin" in fruit.lower() or "orange" in fruit.lower():
                        print(f"   • {fruit}: Great for on-the-go snacks or add segments to salads")
                    else:
                        print(f"   • {fruit}: Enjoy as a healthy snack")
            
            if leftover_by_category["greens"]:
                print("  Greens:")
                for green in leftover_by_category["greens"]:
                    print(f"   • {green}: Quick sauté with garlic for a simple side, or add to smoothies")
            
            if leftover_by_category["root_veg"]:
                print("  Root Vegetables:")
                for root in leftover_by_category["root_veg"]:
                    print(f"   • {root}: Roast with olive oil and herbs for a hearty side dish")
            
            if leftover_by_category["other_veg"]:
                print("  Other Vegetables:")
                for veg in leftover_by_category["other_veg"]:
                    if "zucchini" in veg.lower():
                        print(f"   • {veg}: Grill with a touch of olive oil and lemon juice")
                    elif "pepper" in veg.lower():
                        print(f"   • {veg}: Blister in a hot pan for a fun snack or appetizer")
                    elif "green bean" in veg.lower():
                        print(f"   • {veg}: Blanch quickly and toss with lemon and almonds")
                    else:
                        print(f"   • {veg}: Steam or roast for a quick side dish")
            
            if leftover_by_category["protein"]:
                print("  Protein Items:")
                for protein in leftover_by_category["protein"]:
                    if "chicken" in protein.lower():
                        print(f"   • {protein}: Grill or roast with herbs for a simple protein option")
                    elif "beef" in protein.lower() or "steak" in protein.lower():
                        print(f"   • {protein}: Pan-sear to your preferred doneness with just salt and pepper")
                    elif "egg" in protein.lower():
                        print(f"   • {protein}: Perfect for breakfast or add a protein boost to salads")
                    else:
                        print(f"   • {protein}: Cook according to package directions for a paleo-friendly meal")
        
        print("\nHappy cooking! Enjoy your farm-fresh meal prep!")

def main():
    parser = argparse.ArgumentParser(description="Farm to People Dynamic Meal Planner")
    parser.add_argument("--summer", action="store_true", help="If set, focus on summer-friendly recipes")
    parser.add_argument("--output", type=str, default="farm_box_data", help="Output directory")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode with extra information")
    args = parser.parse_args()
    
    prefer_summer = args.summer
    debug_mode = args.debug
    planner = FarmToTablePlanner(output_dir=args.output, prefer_summer=prefer_summer, debug=debug_mode)
    planner.scan_box()

if __name__ == "__main__":
    main()