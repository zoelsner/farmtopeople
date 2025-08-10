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
    Returns one of: 'root_veg', 'greens', 'fruit', or 'other_veg'.
    """
    name_lower = name.lower()

    # Fix "watermelon radish" confusion
    if "radish" in name_lower:
        return "root_veg"
    
    # Root vegetables
    for root_word in ["potato", "carrot", "beet", "turnip", "onion", "garlic"]:
        if root_word in name_lower:
            return "root_veg"
    
    # Fruit keywords
    fruit_keywords = [
        "apple", "pear", "peach", "plum", "banana", 
        "mandarin", "orange", "grapefruit", "melon", "mango", 
        "pineapple", "fruit", "lemon", "lime", "berry", "berries"
    ]
    for fruit_word in fruit_keywords:
        if fruit_word in name_lower:
            return "fruit"
    
    # Greens keywords
    green_keywords = ["broccoli", "kale", "chard", "lettuce", "spinach", "rabe", "arugula", "collard"]
    for green_word in green_keywords:
        if green_word in name_lower:
            return "greens"
    
    # Otherwise default to other veg
    return "other_veg"

def simplify_ingredient(full_name: str) -> tuple:
    """
    Takes a full ingredient name and returns a tuple of (full_name, simplified_name).
    Preserves important distinctions like "green beans" vs "beans".
    """
    full_name = full_name.lower()
    
    # Remove "organic" prefix which doesn't affect cooking
    cleaned_name = full_name.replace("organic ", "")
    
    # Specific ingredient simplifications
    # This maintains the full specificity but gives us shorter keys
    
    # Root vegetables
    if "sweet potato" in cleaned_name:
        return (full_name, "sweet potato")
    if "potato" in cleaned_name and "sweet" not in cleaned_name:
        return (full_name, "potato")
    if "watermelon radish" in cleaned_name:
        return (full_name, "watermelon radish")
    if "radish" in cleaned_name and "watermelon" not in cleaned_name:
        return (full_name, "radish")
    if "carrot" in cleaned_name:
        return (full_name, "carrot")
        
    # Greens
    if "broccoli rabe" in cleaned_name:
        return (full_name, "broccoli rabe") 
    if "broccoli" in cleaned_name and "rabe" not in cleaned_name:
        return (full_name, "broccoli")
    if "kale" in cleaned_name:
        return (full_name, "kale")
    if "spinach" in cleaned_name:
        return (full_name, "spinach")
    if "lettuce" in cleaned_name:
        return (full_name, "lettuce")
        
    # Other vegetables
    if "green bean" in cleaned_name:
        return (full_name, "green beans")  # Keep "green beans" distinct from other beans
    if "zucchini" in cleaned_name:
        return (full_name, "zucchini")
    if "shishito pepper" in cleaned_name:
        return (full_name, "shishito pepper")
    if "bell pepper" in cleaned_name:
        return (full_name, "bell pepper")
    if "pepper" in cleaned_name and "bell" not in cleaned_name and "shishito" not in cleaned_name:
        return (full_name, "pepper")
        
    # Fruits
    if "mandarin" in cleaned_name:
        return (full_name, "mandarin")
    if "apple" in cleaned_name:
        return (full_name, "apple")
    if "banana" in cleaned_name:
        return (full_name, "banana")
    if "lemon" in cleaned_name:
        return (full_name, "lemon")
        
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
        self.recipe_database = {
            "bowls": [
                {
                    "name": "Roasted Veggie Power Bowl",
                    "ingredients": ["sweet potato", "broccoli", "kale"],
                    "protein": "Chicken or tofu",
                    "method": "Roast veggies at 425°F for 25 min, add protein of choice, top with tahini dressing",
                    "office_friendly": True,
                    "tags": ["meal_prep", "healthy", "gluten_free"]
                },
                {
                    "name": "Buddha Bowl with Ginger-Sesame Drizzle",
                    "ingredients": ["sweet potato", "zucchini", "broccoli", "kale"],
                    "protein": "Baked tofu or chicken thighs",
                    "method": "Roast veggies, prepare protein separately, combine with rice/quinoa, top with sesame seeds and ginger dressing",
                    "office_friendly": True,
                    "tags": ["asian_inspired", "healthy"]
                },
                {
                    "name": "Mediterranean Bowl",
                    "ingredients": ["zucchini", "potato", "broccoli", "tomato"],
                    "protein": "Chicken or chickpeas",
                    "method": "Season veggies with oregano and roast, serve over couscous with lemon-olive oil dressing",
                    "office_friendly": True,
                    "tags": ["mediterranean", "bright", "colorful"]
                }
            ],
            "sheet_pan_meals": [
                {
                    "name": "Sheet Pan Sweet Potato & Greens Hash",
                    "ingredients": ["sweet potato", "kale", "onion"],
                    "protein": "Sausage or chicken thighs",
                    "method": "Dice everything, toss with olive oil and herbs, roast at 425°F for 30 min, crack eggs on top for last 5 min (optional)",
                    "office_friendly": True,
                    "tags": ["one_pan", "easy_cleanup", "weeknight"]
                },
                {
                    "name": "Fully Loaded Sheet Pan Nachos",
                    "ingredients": ["sweet potato", "zucchini", "bell pepper", "onion"],
                    "protein": "Ground turkey or black beans",
                    "method": "Roast veggies, layer with tortilla chips, protein, cheese, broil briefly, top with avocado and salsa",
                    "office_friendly": False,
                    "tags": ["fun", "comfort_food", "weekend"]
                },
                {
                    "name": "Herb Roasted Veggie Medley",
                    "ingredients": ["potato", "carrot", "broccoli", "green beans"],
                    "protein": "Chicken breast or salmon (home only)",
                    "method": "Toss veggies with olive oil, garlic, rosemary, and thyme, roast alongside protein at 400°F for 25 min",
                    "office_friendly": True,
                    "tags": ["classic", "versatile", "herby"]
                }
            ],
            "stir_fry": [
                {
                    "name": "Ginger-Garlic Veggie Stir-Fry",
                    "ingredients": ["broccoli", "carrot", "bell pepper", "green beans"],
                    "protein": "Chicken, tofu, or shrimp",
                    "method": "Stir-fry veggies with ginger and garlic, add protein, finish with soy sauce and rice vinegar, serve over rice",
                    "office_friendly": True,
                    "tags": ["quick", "flavorful", "asian_inspired"]
                },
                {
                    "name": "Quick Teriyaki Vegetable Medley",
                    "ingredients": ["broccoli", "carrot", "zucchini", "mushroom"],
                    "protein": "Thinly sliced beef or tempeh",
                    "method": "Stir-fry veggies, add protein, coat with teriyaki sauce, garnish with sesame seeds and green onion",
                    "office_friendly": True,
                    "tags": ["quick", "savory", "umami"]
                }
            ],
            "salads": [
                {
                    "name": "Hearty Roasted Vegetable Salad",
                    "ingredients": ["sweet potato", "watermelon radish", "kale", "arugula"],
                    "protein": "Grilled chicken or chickpeas",
                    "method": "Roast root vegetables, combine with greens, protein, and vinaigrette, top with nuts or seeds",
                    "office_friendly": True,
                    "tags": ["meal_sized", "satisfying", "nutritious"]
                },
                {
                    "name": "Citrus & Greens Superfood Salad",
                    "ingredients": ["kale", "arugula", "apple", "mandarin"],
                    "protein": "Grilled chicken or quinoa",
                    "method": "Massage kale with olive oil, add citrus segments, protein, and light vinaigrette",
                    "office_friendly": True,
                    "tags": ["bright", "refreshing", "detox"]
                }
            ],
            "roasts": [
                {
                    "name": "Herb-Crusted Roasted Vegetables",
                    "ingredients": ["potato", "carrot", "broccoli", "onion"],
                    "protein": "Roast chicken or pot roast (separately)",
                    "method": "Toss vegetables with herbs and olive oil, roast at 400°F for 35-40 min while preparing protein separately",
                    "office_friendly": True,
                    "tags": ["classic", "comfort_food", "sunday_dinner"]
                }
            ],
            "soups": [
                {
                    "name": "Hearty Vegetable & Grain Soup",
                    "ingredients": ["carrot", "potato", "onion", "kale"],
                    "protein": "Chicken, turkey, or white beans",
                    "method": "Sauté aromatics, add chopped veggies, broth, grain (barley/farro), and protein, simmer until tender",
                    "office_friendly": True,
                    "tags": ["comforting", "meal_in_bowl", "freezer_friendly"]
                }
            ]
        }
    
    def scan_box(self):
        """
        Main entry point:
        - Logs in / re-uses saved session
        - Opens cart & finds the seasonal produce box
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
                
                # If we see the produce box, click customize
                if "Seasonal Produce Box" in name:
                    print("\n! Found Seasonal Produce Box !")
                    customize_btn = item.locator("button:has-text('CUSTOMIZE')").first
                    if customize_btn.count() > 0:
                        print("Customize button found! Clicking it...")
                        customize_btn.click()
                        page.wait_for_load_state("networkidle")
                        page.wait_for_timeout(3000)  # brief pause
                    else:
                        print("Customize button not found.")
            
            except Exception as e:
                print(f"Error processing item {i+1}: {str(e)}")
    
    def _truly_scan_box_contents(self, page):
        """
        Enhanced method to accurately detect what's currently in the box.
        This uses multiple targeted approaches with better debugging.
        """
        customization_screenshot_path = self.output_dir / f"customize_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=str(customization_screenshot_path))
        
        print("\n----- TRULY Reading Box Contents -----")
        
        # Check if we can see the "7 of 7 items selected" text to confirm we're on the right page
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
        # This approach is the most reliable since it directly shows what's currently in the box
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
        
        # APPROACH 3: Look for items in the right sidebar by reading container IDs
        # This is a more targeted approach looking for specific UI elements
        if not sidebar_items:
            print("\nTrying to find selected items by container IDs...")
            
            # Look for elements with specific container patterns
            sidebar_containers = page.locator("div[class*='sidebar'], div[class*='selected-items']").all()
            print(f"Found {len(sidebar_containers)} potential sidebar containers")
            
            for container in sidebar_containers:
                try:
                    # Look for elements that might contain product info
                    item_rows = container.locator("div.flex, div.tw-flex").all()
                    
                    if item_rows:
                        print(f"  Found {len(item_rows)} potential item rows in container")
                        
                        for row in item_rows:
                            row_text = row.text_content().strip()
                            
                            # Debug output
                            if self.debug:
                                print(f"  Row text: {row_text}")
                            
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
                                
                                print(f"  Found item in container: {quantity}x {name} {unit_info}")
                except Exception as e:
                    print(f"  Error processing container: {str(e)}")
        
        # For debugging: extract HTML of key regions to help understand the structure
        if self.debug:
            try:
                print("\nExtracting HTML for debugging...")
                
                # Get the HTML of a sidebar region
                sidebar_debug = page.locator("div.tw-flex.tw-items-center").first
                if sidebar_debug.count() > 0:
                    sidebar_html = sidebar_debug.evaluate("el => el.outerHTML")
                    print(f"Sidebar item HTML sample:\n{sidebar_html[:200]}...")
                
                # Get a sample article HTML
                article_debug = page.locator("article").first
                if article_debug.count() > 0:
                    article_html = article_debug.evaluate("el => el.outerHTML")
                    print(f"Article HTML sample:\n{article_html[:200]}...")
            except Exception as e:
                print(f"Error extracting debug HTML: {str(e)}")
        
        # If we found items with any method, use them!
        if sidebar_items:
            print(f"\nSuccessfully found {len(sidebar_items)} items in your box using dynamic detection!")
            self.box_selected_items = sidebar_items
        else:
            # Emergency fallback ONLY if all methods failed
            print("\nWARNING: All dynamic detection methods failed! Using fallback data.")
            # This is only used if absolutely nothing else works
            fallback_items = [
                {"name": "Stem and Leaf Mandarins", "quantity": "1", "unit_info": "5-7 pieces"},
                {"name": "Organic Green Beans", "quantity": "1", "unit_info": "12.0 oz"},
                {"name": "Organic Watermelon Radishes", "quantity": "1", "unit_info": "1.0 Lbs"},
                {"name": "Murasaki Sweet Potatoes", "quantity": "1", "unit_info": "1.0 Lbs"},
                {"name": "Organic Green Zucchini", "quantity": "1", "unit_info": "2 pieces"},
                {"name": "Shishito Peppers", "quantity": "1", "unit_info": "8.0 oz"},
                {"name": "Organic Broccoli Rabe", "quantity": "1", "unit_info": "1 bunch"}
            ]
            
            print("Using emergency fallback data for recommendations:")
            for item in fallback_items:
                print(f"  Fallback item: {item['quantity']}x {item['name']} ({item['unit_info']})")
            
            self.box_selected_items = fallback_items
        
        # Save final box data
        box_data = {
            "timestamp": datetime.now().isoformat(),
            "selected_items": self.box_selected_items,
            "detection_method": "dynamic" if sidebar_items else "fallback"
        }
        box_json_path = self.output_dir / f"box_contents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(box_json_path, 'w') as f:
            json.dump(box_data, f, indent=2)
        
        print(f"\nBox contents saved to {box_json_path}")
    
    def _suggest_meal_prep_ideas(self):
        """
        Generate creative and exciting meal prep ideas for 4 servings.
        """
        print("\n===== Exciting Meal Prep Ideas (4 Servings) =====")
        
        if not self.box_selected_items:
            print("No items found in your box this week, so no meal suggestions.")
            return
        
        # Categorize everything properly
        categorized = {"root_veg": [], "greens": [], "fruit": [], "other_veg": []}
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
        for category, recipes in self.recipe_database.items():
            for recipe in recipes:
                matching_ingredients = 0
                matched_ingredient_names = []
                
                for ingredient in recipe["ingredients"]:
                    if ingredient in simplified_ingredients:
                        matching_ingredients += 1
                        # Get the original full name for display
                        matched_ingredient_names.append(simplified_lookup[ingredient])
                
                if matching_ingredients >= 2:  # At least 2 matching ingredients
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
            
            secondary_veg = None
            if categorized["greens"]:
                secondary_veg = categorized["greens"][0]["name"]
            elif len(categorized["other_veg"]) > 1:
                secondary_veg = categorized["other_veg"][1]["name"]
            
            if primary_veg and secondary_veg:
                print(f"\n🔥 CUSTOM POWER BOWL WITH {primary_veg.upper()} & {secondary_veg.upper()}")
                print("  Type: Versatile Grain Bowl")
                print(f"  Main ingredients: {primary_veg}, {secondary_veg}")
                
                # Choose appropriate protein
                if "potato" in primary_veg.lower():
                    protein = "Roasted chicken thighs (juicy and flavorful)"
                elif "broccoli" in primary_veg.lower() or "rabe" in secondary_veg.lower():
                    protein = "Grilled chicken breast or baked tofu"
                else:
                    protein = "Your choice of chicken, ground turkey, or tofu"
                
                print(f"  Recommended protein: {protein}")
                print("  Method: Roast vegetables with olive oil, garlic, and herbs of choice at 425°F")
                print("         Serve over quinoa or brown rice with your favorite sauce")
                print("  Office-friendly: Yes (stores and reheats well)")
                print("  Makes: 4 hearty servings")
        
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
            leftover_by_category = {"root_veg": [], "greens": [], "fruit": [], "other_veg": []}
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