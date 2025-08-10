from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
import pandas as pd
import logging
from pathlib import Path
import time
from datetime import datetime, timedelta
import re

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FarmBoxOptimizer:
    def __init__(self):
        load_dotenv()
        self.email = os.getenv("EMAIL")
        self.password = os.getenv("PASSWORD")
        self.storage_state_path = Path("auth_state.json")
        
        # Load product data from CSV
        self.products_df = pd.read_csv("farmtopeople_products.csv")
        
        # For meal planning
        self.office_meals = 0
        self.home_meals = 0
        self.meal_plan = {}
        
        # Protein info for meal planning
        self.protein_info = {
            "chicken_breast": {
                "name": "Chicken Breast",
                "protein_per_serving": 26,  # grams per 3oz serving
                "reheats_well": True,
                "cold_friendly": False
            },
            "ground_turkey": {
                "name": "Ground Turkey (93% lean)",
                "protein_per_serving": 22,
                "reheats_well": True,
                "cold_friendly": False
            },
            "salmon": {
                "name": "Salmon Fillet",
                "protein_per_serving": 22,
                "reheats_well": False,  # Not ideal for reheating
                "cold_friendly": True   # Can be eaten cold
            },
            "tuna": {
                "name": "Canned Tuna",
                "protein_per_serving": 20,
                "reheats_well": False,
                "cold_friendly": True
            },
            "tofu": {
                "name": "Extra Firm Tofu",
                "protein_per_serving": 15,
                "reheats_well": True,
                "cold_friendly": True
            },
            "eggs": {
                "name": "Hard-boiled Eggs",
                "protein_per_serving": 12,  # 2 eggs
                "reheats_well": False,
                "cold_friendly": True
            },
            "rotisserie_chicken": {
                "name": "Rotisserie Chicken",
                "protein_per_serving": 24,
                "reheats_well": True,
                "cold_friendly": True
            },
            "pork_tenderloin": {
                "name": "Pork Tenderloin",
                "protein_per_serving": 22,
                "reheats_well": True,
                "cold_friendly": False
            }
        }
        
    def is_logged_in(self, page) -> bool:
        """Check if we're already logged in by looking for 'Shopping for:' text."""
        try:
            page.goto("https://www.farmtopeople.com")
            page.wait_for_load_state("networkidle")
            
            # Try different potential selectors for "Shopping for:" text
            selectors = [
                "#body > div:nth-child(2) > nav.nav_top-nav__7bJ7H.body-small.nav-breakpoint-no-display > div > div:nth-child(2) > div.centered-row.cursor-pointer.tracking-normal > span",
                "span:has-text('Shopping for:')",
                "div.centered-row.cursor-pointer span"
            ]
            
            for selector in selectors:
                element = page.locator(selector)
                if element.count() > 0 and "Shopping for:" in element.text_content():
                    return True
            
            return False
        except Exception as e:
            logger.warning(f"Error checking login status: {e}")
            return False

    def login(self, page, context):
        """Handle login process with session management."""
        try:
            logger.info("Checking if already logged in...")
            if self.is_logged_in(page):
                logger.info("Already logged in, no need to restore session")
                return
                
            # Attempt restoring a stored session if it exists
            if self.storage_state_path.exists():
                logger.info(f"Found stored session at {self.storage_state_path}")
                try:
                    context.storage_state(path=str(self.storage_state_path))
                    page.reload()  # Reload page after loading state
                    if self.is_logged_in(page):
                        logger.info("Successfully restored previous session")
                        return
                    else:
                        logger.warning("Stored session appears to be invalid")
                except Exception as e:
                    logger.error(f"Error restoring session: {e}")

            # Fresh login
            logger.info("Need to perform fresh login...")
            page.goto("https://www.farmtopeople.com/login")
            
            logger.info("Filling in email...")
            page.fill("input[type='email']", self.email)
            page.keyboard.press("Enter")
            
            logger.info("Waiting for password field...")
            page.wait_for_selector("input[type='password']")
            
            logger.info("Filling in password...")
            page.fill("input[placeholder='Password']", self.password)
            
            logger.info("Clicking login button...")
            page.click("button[native-type='button']")
            page.wait_for_load_state("networkidle")

            # Save the authentication state
            context.storage_state(path=str(self.storage_state_path))
            logger.info("Login successful and session state saved!")
            
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            raise

    def navigate_to_produce_box(self, page):
        """Navigate to the Seasonal Produce Box customization page."""
        try:
            logger.info("Looking for Seasonal Produce Box in your order...")
            
            # Go to the main page first
            page.goto("https://www.farmtopeople.com")
            page.wait_for_load_state("networkidle")
            
            # Open the cart
            try:
                # Try various possible cart button selectors
                cart_button_selectors = [
                    "div.cart-button.ml-auto.cursor-pointer",
                    "a.cart-button",
                    "a[href='/cart']",
                    "a:has(div.badge)",
                    "div.cart-button"
                ]
                
                clicked = False
                for selector in cart_button_selectors:
                    cart_button = page.locator(selector).first
                    if cart_button.count() > 0:
                        cart_button.click()
                        page.wait_for_timeout(2000)  # Wait a moment to see if sidebar appears
                        logger.info(f"Clicked cart button with selector: {selector}")
                        clicked = True
                        break
                
                if not clicked:
                    logger.warning("Could not find any cart button with known selectors")
                    
                # After clicking, verify cart sidebar is visible
                if page.locator("div.cart_cartContent__gLS77, div.cart-sidebar, aside.cart-sidebar").count() > 0:
                    logger.info("Cart sidebar is visible")
                else:
                    logger.warning("Cart sidebar not found after clicking cart button")
            except Exception as e:
                logger.warning(f"Error opening cart: {e}")
            
            # Try to find the Seasonal Produce Box in the cart area
            box_in_cart = False
            produce_box_items = page.locator("article.cart-order_cartOrderItem__CDYTs").all()
            
            for item in produce_box_items:
                # Check if we're in the right context (cart view)
                try:
                    name_elem = item.locator("a.web-link_unstyled-link__uJvxp.bold").first
                    if name_elem.count() > 0 and "Seasonal Produce Box - Small" in name_elem.text_content():
                        logger.info("Found Seasonal Produce Box in cart")
                        
                        # Look for customize button
                        customize_btn = item.locator("button:has-text('CUSTOMIZE')").first
                        if customize_btn.count() > 0:
                            customize_btn.click()
                            page.wait_for_load_state("networkidle")
                            logger.info("Clicked customize button")
                            box_in_cart = True
                            break
                except Exception as e:
                    logger.warning(f"Error checking element: {e}")
                    continue
            
            if not box_in_cart:
                logger.warning("Seasonal Produce Box not found in cart with customize option")
                
                # Try to navigate to the box from menu
                try:
                    # Click on Farm Boxes in the menu
                    farm_boxes = page.locator("text='Farm Boxes'").first
                    if farm_boxes.count() > 0:
                        farm_boxes.click()
                        page.wait_for_load_state("networkidle")
                        
                        # Look for Seasonal Produce Box product
                        produce_box = page.locator("text='Seasonal Produce Box - Small'").first
                        if produce_box.count() > 0:
                            produce_box.click()
                            page.wait_for_load_state("networkidle")
                            
                            # Add to cart or customize
                            add_btn = page.locator("button:has-text('Add to Cart')").first
                            if add_btn.count() > 0:
                                add_btn.click()
                                page.wait_for_load_state("networkidle")
                                
                                # Navigate again to find customize button
                                return self.navigate_to_produce_box(page)
                except Exception as e:
                    logger.error(f"Error navigating to Farm Boxes: {e}")
            
            # Check if we're on the customization page by looking for category tabs
            customization_page_selectors = [
                "button.tab-button",
                "div.box-customization-page",
                "div:has-text('Customize Your Box')"
            ]
            
            for selector in customization_page_selectors:
                if page.locator(selector).count() > 0:
                    logger.info(f"Successfully detected customization page with selector: {selector}")
                    return True
            
            logger.error("Failed to navigate to Seasonal Produce Box customization page")
            return False
                
        except Exception as e:
            logger.error(f"Error navigating to Seasonal Produce Box: {e}")
            return False
    
    def get_current_box_contents(self, page):
        """Get the current contents of the Seasonal Produce Box."""
        try:
            logger.info("Getting current box contents...")
            
            # Open the cart sidebar
            try:
                cart_button = page.locator("div.cart-button.ml-auto.cursor-pointer").first
                if cart_button.count() > 0:
                    cart_button.click()
                    logger.info("Clicked cart button")
                else:
                    logger.warning("Cart button not found, continuing with current page")
            except Exception as e:
                logger.warning(f"Error clicking cart button: {e}")
            
            # Wait for the cart sidebar to be visible
            page.wait_for_selector("div.cart_cartContent__gLS77", timeout=5000)
            
            # Get all items in the cart
            items = []
            
            # Find the Seasonal Produce Box and its items
            box_items = page.locator("article.cart-order_cartOrderItem__CDYTs").all()
            logger.info(f"Found {len(box_items)} potential items in sidebar")
            
            for i, item in enumerate(box_items):
                try:
                    # Check if this is our produce box
                    name_elem = item.locator("a.web-link_unstyled-link__uJvxp.bold").first
                    if name_elem.count() > 0:
                        name = name_elem.text_content().strip()
                        
                        # If this is the Seasonal Produce Box
                        if "Seasonal Produce Box - Small" in name:
                            logger.info(f"Found Seasonal Produce Box: {name}")
                            
                            # Get the sub-items of the box
                            sub_items = item.locator("div.cart-order_cart-order-line-item-subproduct-details__C2EIT.body-small").all()
                            for sub_item in sub_items:
                                try:
                                    sub_name_elem = sub_item.locator("a.web-link_unstyled-link__uJvxp.bold").first
                                    sub_qty_elem = sub_item.locator("p").first
                                    
                                    if sub_name_elem.count() > 0 and sub_qty_elem.count() > 0:
                                        sub_name = sub_name_elem.text_content().strip()
                                        sub_qty_text = sub_qty_elem.text_content().strip()
                                        
                                        # Extract quantity - usually in format like "1 head" or "3 pieces"
                                        qty_parts = sub_qty_text.split()
                                        quantity = int(qty_parts[0]) if qty_parts and qty_parts[0].isdigit() else 1
                                        
                                        # Get size/unit if available
                                        size = " ".join(qty_parts[1:]) if len(qty_parts) > 1 else ""
                                        
                                        items.append({
                                            "name": sub_name,
                                            "quantity": quantity,
                                            "size": size
                                        })
                                        logger.info(f"Found box item: {quantity} x {sub_name} ({size})")
                                except Exception as e:
                                    logger.warning(f"Error processing sub-item: {e}")
                        
                except Exception as e:
                    logger.warning(f"Error extracting item {i}: {e}")
            
            logger.info(f"Total items found in box: {len(items)}")
            return items
        
        except Exception as e:
            logger.error(f"Error getting box contents: {e}")
            return []
    
    def categorize_items(self, items):
        """Categorize items into proteins, produce, etc."""
        categorized = {
            "proteins": [],
            "produce": [],
            "dairy_eggs": [],
            "pantry": [],
            "other": []
        }
        
        for item in items:
            # Look up the item in our products database
            name = item["name"]
            matches = self.products_df[self.products_df["Name"].str.contains(name, case=False, regex=False)]
            
            if not matches.empty:
                category = matches.iloc[0]["Category"]
                if category == "meat-seafood":
                    categorized["proteins"].append(item)
                elif category == "produce":
                    categorized["produce"].append(item)
                elif category == "dairy-eggs":
                    categorized["dairy_eggs"].append(item)
                elif category == "pantry":
                    categorized["pantry"].append(item)
                else:
                    categorized["other"].append(item)
            else:
                # Try to guess category from the name
                if any(p in name.lower() for p in ["chicken", "beef", "pork", "fish", "turkey", "lamb", "bacon", "sausage"]):
                    categorized["proteins"].append(item)
                elif any(p in name.lower() for p in ["apple", "broccoli", "carrot", "lettuce", "potato", "onion", "garlic", "mushroom"]):
                    categorized["produce"].append(item)
                elif any(p in name.lower() for p in ["milk", "cheese", "yogurt", "butter", "egg"]):
                    categorized["dairy_eggs"].append(item)
                else:
                    categorized["other"].append(item)
        
        return categorized
    
    def suggest_meal_plan(self, categorized_items, office_meals, home_meals):
        """Suggest a meal plan based on the current box contents."""
        logger.info(f"Creating meal plan for {office_meals} office meals and {home_meals} home meals")
        
        # Calculate total meals needed
        total_meals = office_meals + home_meals
        
        # Count proteins and estimate meals possible
        proteins = categorized_items["proteins"]
        protein_count = sum(item["quantity"] for item in proteins)
        
        logger.info(f"Box contains {protein_count} protein items")
        
        if protein_count < total_meals:
            logger.info(f"Not enough proteins for all meals. Need {total_meals - protein_count} more.")
        
        # Create meal suggestions
        meal_plan = {
            "office_meals": [],
            "home_meals": [],
            "missing_items": [],
            "suggestions": []
        }
        
        # Assign proteins to meals
        protein_assigned = 0
        
        # First, assign proteins to home meals (usually require more cooking)
        for i in range(min(home_meals, protein_count)):
            if i < len(proteins):
                protein = proteins[i]
                meal_plan["home_meals"].append({
                    "day": f"Home Meal {i+1}",
                    "protein": protein["name"],
                    "sides": self._suggest_sides(categorized_items, protein["name"])
                })
                protein_assigned += 1
            else:
                meal_plan["home_meals"].append({
                    "day": f"Home Meal {i+1}",
                    "protein": "NEEDED",
                    "sides": self._suggest_sides(categorized_items)
                })
                meal_plan["missing_items"].append("Protein for home meal")
        
        # Then, assign remaining proteins to office meals
        for i in range(min(office_meals, protein_count - protein_assigned)):
            if protein_assigned + i < len(proteins):
                protein = proteins[protein_assigned + i]
                meal_plan["office_meals"].append({
                    "day": f"Office Meal {i+1}",
                    "protein": protein["name"],
                    "sides": self._suggest_sides(categorized_items, protein["name"], office_friendly=True)
                })
            else:
                meal_plan["office_meals"].append({
                    "day": f"Office Meal {i+1}",
                    "protein": "NEEDED",
                    "sides": self._suggest_sides(categorized_items, office_friendly=True)
                })
                meal_plan["missing_items"].append("Protein for office meal")
        
        # Add suggestions for additional purchases
        if len(meal_plan["missing_items"]) > 0:
            # Suggest additional proteins
            additional_proteins = self._suggest_additional_proteins(total_meals - protein_count)
            meal_plan["suggestions"].extend(additional_proteins)
        
        # Check produce sufficiency
        produce_items = sum(item["quantity"] for item in categorized_items["produce"])
        if produce_items < total_meals * 2:  # Assuming 2 veggie sides per meal
            produce_needed = (total_meals * 2) - produce_items
            meal_plan["missing_items"].append(f"Need {produce_needed} more produce items")
            meal_plan["suggestions"].append("Add more vegetables with long shelf life (carrots, cabbage, onions)")
        
        return meal_plan
    
    def _suggest_sides(self, categorized_items, protein_name=None, office_friendly=False):
        """Suggest side dishes based on the protein and available produce."""
        # Get available produce
        produce = categorized_items["produce"]
        
        # Choose sides based on protein type and office-friendliness
        sides = []
        
        # Filter for office-friendly items if needed
        if office_friendly:
            office_produce = [p for p in produce if self._is_office_friendly(p["name"])]
            produce_options = office_produce if office_produce else produce
        else:
            produce_options = produce
        
        # Try to pick complementary sides based on protein
        if protein_name and len(produce_options) >= 2:
            if any(p in protein_name.lower() for p in ["fish", "sea", "bass", "salmon"]):
                # Fish pairs well with greens and light veggies
                greens = [p for p in produce_options if any(g in p["name"].lower() for g in ["broccoli", "lettuce", "kale", "spinach"])]
                if greens:
                    sides.append(greens[0]["name"])
                
                light_veggies = [p for p in produce_options if any(v in p["name"].lower() for v in ["pepper", "tomato", "zucchini", "squash"])]
                if light_veggies:
                    sides.append(light_veggies[0]["name"])
            
            elif any(p in protein_name.lower() for p in ["beef", "pork", "lamb"]):
                # Red meat pairs well with hearty veggies
                hearty_veggies = [p for p in produce_options if any(v in p["name"].lower() for v in ["potato", "sweet potato", "carrot", "onion"])]
                if hearty_veggies:
                    sides.append(hearty_veggies[0]["name"])
                
                green_veggies = [p for p in produce_options if any(v in p["name"].lower() for v in ["broccoli", "brussels", "asparagus"])]
                if green_veggies:
                    sides.append(green_veggies[0]["name"])
            
            elif any(p in protein_name.lower() for p in ["chicken", "turkey"]):
                # Poultry is versatile
                sides = [p["name"] for p in produce_options[:2]]
        
        # If we couldn't assign specific sides, just pick the first two
        if len(sides) < 2 and len(produce_options) >= 2:
            sides = [p["name"] for p in produce_options[:2]]
        elif len(sides) < 2:
            sides.extend(["VEGETABLE NEEDED"] * (2 - len(sides)))
        
        return sides
    
    def _is_office_friendly(self, item_name):
        """Determine if an item is suitable for office meals."""
        # Items that travel well and can be reheated
        office_friendly = ["potato", "sweet potato", "carrot", "broccoli", 
                          "cabbage", "brussels", "cauliflower", "pepper"]
        
        # Items that don't travel well or aren't good reheated
        not_office_friendly = ["lettuce", "salad", "arugula", "spinach", "tomato"]
        
        item_lower = item_name.lower()
        
        if any(f in item_lower for f in office_friendly):
            return True
        if any(f in item_lower for f in not_office_friendly):
            return False
        
        # Default to True for other items
        return True
    
    def _suggest_whole_foods_proteins(self, produce_items, is_summer=False):
        """Suggest specific proteins from Whole Foods that pair well with current produce."""
        suggestions = []
        
        # Track produce types
        has_greens = any("lettuce" in item.lower() or "spinach" in item.lower() or "kale" in item.lower() 
                        for item in produce_items)
        has_root_veg = any("potato" in item.lower() or "carrot" in item.lower() or "sweet potato" in item.lower() 
                          for item in produce_items)
        has_cruciferous = any("broccoli" in item.lower() or "cauliflower" in item.lower() or "brussels" in item.lower() 
                             for item in produce_items)
                             
        # Proteins that reheat well for office lunches
        office_friendly = [
            "Ground turkey (93% lean) - High protein, reheats well in microwave",
            "Chicken breast - High protein, versatile for meal prep",
            "Chicken thighs (skinless) - More flavor than breast, still reheats well",
            "Pre-cooked rotisserie chicken - Convenient, no cooking needed"
        ]
        
        # Cold meal proteins for summer
        summer_proteins = [
            "Canned tuna - High protein, no reheating needed, good for cold salads",
            "Pre-cooked shrimp - Great for cold meals, high protein",
            "Hard-boiled eggs - Good addition to salads, already buying farm fresh eggs",
            "Tofu (extra firm) - Can be prepared ahead and eaten cold"
        ]
        
        # Proteins for specific produce
        if has_greens:
            suggestions.append("Salmon fillets - Pairs well with leafy greens")
            
        if has_root_veg:
            suggestions.append("Beef chuck roast - Slow cook with root vegetables")
            suggestions.append("Whole chicken - Roast with root vegetables")
            
        if has_cruciferous:
            suggestions.append("Pork tenderloin - Pairs well with broccoli/cauliflower")
        
        # Add office-friendly options
        suggestions.extend(office_friendly[:2])  # Add top 2 office-friendly options
        
        # Add summer proteins if requested
        if is_summer:
            suggestions.extend(summer_proteins[:2])  # Add top 2 summer proteins
            
        return suggestions
    
    def suggest_box_modifications(self, categorized_items, meal_plan):
        """Suggest modifications to the box based on the meal plan."""
        logger.info("Suggesting box modifications...")
        
        modifications = {
            "remove": [],
            "add": [],
            "reasoning": []
        }
        
        # Check for excess of certain items
        produce_counts = {}
        for item in categorized_items["produce"]:
            name = item["name"]
            if name in produce_counts:
                produce_counts[name] += item["quantity"]
            else:
                produce_counts[name] = item["quantity"]
        
        # Count how many times each produce is used in the meal plan
        produce_used = {}
        for meal in meal_plan["home_meals"] + meal_plan["office_meals"]:
            for side in meal["sides"]:
                if side != "VEGETABLE NEEDED":
                    if side in produce_used:
                        produce_used[side] += 1
                    else:
                        produce_used[side] = 1
        
        # Find excess produce (items we have more of than we'll use)
        for name, count in produce_counts.items():
            used = produce_used.get(name, 0)
            if count > used + 1:  # +1 buffer for snacks
                modifications["remove"].append(f"{name} (have {count}, will use ~{used})")
                modifications["reasoning"].append(f"Excess {name} could go to waste")
        
        # Find missing items needed for the meal plan
        for item in meal_plan["missing_items"]:
            if "produce" in item.lower() or "vegetable" in item.lower():
                # Suggest specific vegetables
                long_shelf_life = ["carrot", "cabbage", "onion", "potato", "sweet potato"]
                
                # Get vegetables with long shelf life from our database
                available_veggies = self.products_df[
                    (self.products_df["Category"] == "produce") & 
                    (~self.products_df["Is_Sold_Out"]) &
                    (self.products_df["Name"].str.contains("|".join(long_shelf_life), case=False))
                ]
                
                for _, veg in available_veggies.head(2).iterrows():
                    modifications["add"].append(f"{veg['Name']}")
                    modifications["reasoning"].append("Long shelf life for meal prep")
            
            elif "protein" in item.lower():
                # For proteins, recommendations already in meal_plan["suggestions"]
                for suggestion in meal_plan["suggestions"]:
                    if "Add " in suggestion and "protein" not in modifications["add"]:
                        modifications["add"].append(suggestion.replace("Add ", ""))
                        modifications["reasoning"].append("Additional protein for meal prep")
        
        return modifications
    
    def swap_item(self, page, item_to_remove, item_to_add):
        """Swap an item in the Seasonal Produce Box."""
        try:
            logger.info(f"Attempting to swap {item_to_remove} for {item_to_add}")
            
            # First, remove the item
            removed = False
            
            # Find all produce items that can be modified
            produce_items = page.locator("div.box-product-detail").all()
            
            for item in produce_items:
                item_text = item.text_content()
                if item_to_remove in item_text:
                    # Look for the remove button
                    remove_btn = item.locator("button:has-text('Remove')").first
                    if remove_btn.count() > 0:
                        remove_btn.click()
                        page.wait_for_timeout(1000)
                        logger.info(f"Removed {item_to_remove}")
                        removed = True
                        break
            
            if not removed:
                logger.warning(f"Could not find {item_to_remove} to remove")
                return False
            
            # Now find and add the new item
            # Look for the appropriate category tab
            category_tabs = page.locator("button.tab-button").all()
            clicked_tab = False
            
            # Try to click a category tab
            for tab in category_tabs:
                tab.click()
                page.wait_for_load_state("networkidle")
                logger.info(f"Clicked category tab: {tab.text_content().strip()}")
                clicked_tab = True
                
                # Look for the item to add in this category
                products = page.locator("article").all()  # Product cards
                
                for product in products:
                    product_text = product.text_content()
                    if item_to_add in product_text:
                        # Found the item, now click ADD or +
                        add_button = product.locator("button:has-text('ADD'), button:has-text('+')").first
                        if add_button.count() > 0:
                            add_button.click()
                            page.wait_for_timeout(1000)
                            logger.info(f"Added {item_to_add}")
                            return True
                
                # If we didn't find the item in this category, try the next one
            
            if not clicked_tab:
                logger.warning("Could not find any category tabs")
            
            logger.warning(f"Could not find {item_to_add} to add in any category")
            return False
            
        except Exception as e:
            logger.error(f"Error swapping items: {e}")
            return False
    
    def save_changes(self, page):
        """Save changes to the Seasonal Produce Box."""
        try:
            # Look for SAVE button which might have different formats
            save_button_selectors = [
                "button:has-text('SAVE')",
                "button.button-primary:has-text('Save')",
                "button[type='submit']:has-text('Save')",
                "button.primary-button"
            ]
            
            for selector in save_button_selectors:
                save_button = page.locator(selector).first
                if save_button.count() > 0:
                    save_button.click()
                    page.wait_for_load_state("networkidle")
                    logger.info(f"Clicked save button with selector: {selector}")
                    return True
            
            logger.warning("Could not find SAVE button with any known selector")
            return False
        except Exception as e:
            logger.error(f"Error saving changes: {e}")
            return False
    
    def print_meal_plan(self, meal_plan):
        """Print the meal plan in a readable format."""
        print("\n" + "="*50)
        print("📋 WEEKLY MEAL PLAN 📋")
        print("="*50)
        
        # Print home meals
        print("\n🏠 HOME MEALS:")
        for i, meal in enumerate(meal_plan["home_meals"]):
            print(f"\nMeal {i+1}:")
            print(f"  Protein: {meal['protein']}")
            print(f"  Sides: {' & '.join(meal['sides'])}")
        
        # Print office meals
        print("\n🏢 OFFICE MEALS:")
        for i, meal in enumerate(meal_plan["office_meals"]):
            print(f"\nMeal {i+1}:")
            print(f"  Protein: {meal['protein']}")
            print(f"  Sides: {' & '.join(meal['sides'])}")
        
        # Print missing items and suggestions
        if meal_plan["missing_items"]:
            print("\n⚠️ MISSING ITEMS:")
            for item in meal_plan["missing_items"]:
                print(f"  • {item}")
        
        if meal_plan["suggestions"]:
            print("\n💡 SUGGESTIONS:")
            for suggestion in meal_plan["suggestions"]:
                print(f"  • {suggestion}")
    
    def print_box_modifications(self, modifications):
        """Print suggested box modifications."""
        print("\n" + "="*50)
        print("🔄 SUGGESTED BOX MODIFICATIONS 🔄")
        print("="*50)
        
        if modifications["remove"]:
            print("\n❌ Consider Removing:")
            for i, item in enumerate(modifications["remove"]):
                reason = modifications["reasoning"][i] if i < len(modifications["reasoning"]) else ""
                print(f"  • {item} - {reason}")
        
        if modifications["add"]:
            print("\n✅ Consider Adding:")
            for i, item in enumerate(modifications["add"]):
                reason_idx = i + len(modifications["remove"]) if i + len(modifications["remove"]) < len(modifications["reasoning"]) else -1
                reason = modifications["reasoning"][reason_idx] if reason_idx >= 0 and reason_idx < len(modifications["reasoning"]) else ""
                print(f"  • {item} - {reason}")


def main():
    # Get user input for meal planning
    try:
        office_meals = int(input("How many meals do you need for the office this week? "))
        home_meals = int(input("How many meals do you need at home this week? "))
        is_summer = input("Are you interested in cold meal options for summer? (y/n) ").lower() == 'y'
    except ValueError:
        logger.error("Please enter valid numbers")
        return
    
    optimizer = FarmBoxOptimizer()
    optimizer.office_meals = office_meals
    optimizer.home_meals = home_meals
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state=str(optimizer.storage_state_path) if optimizer.storage_state_path.exists() else None
        )
        page = context.new_page()

        try:
            # Login
            optimizer.login(page, context)
            
            # Navigate to Seasonal Produce Box
            if optimizer.navigate_to_produce_box(page):
                # Get current box contents
                current_items = optimizer.get_current_box_contents(page)
                
                # Also get additional items in cart
                page.goto("https://www.farmtopeople.com")
                page.wait_for_load_state("networkidle")
                
                # Open the cart to look for additional items
                additional_items = []
                try:
                    # Click cart button
                    cart_button = page.locator("div.cart-button.ml-auto.cursor-pointer").first
                    if cart_button.count() > 0:
                        cart_button.click()
                        page.wait_for_selector("div.cart_cartContent__gLS77", timeout=5000)
                        
                        # Get all items in cart
                        cart_items = page.locator("article.cart-order_cartOrderItem__CDYTs").all()
                        
                        for item in cart_items:
                            name_elem = item.locator("a.web-link_unstyled-link__uJvxp.bold").first
                            if name_elem.count() > 0:
                                name = name_elem.text_content().strip()
                                # Skip the produce box
                                if "Seasonal Produce Box" not in name:
                                    quantity_elem = item.locator("p.mt-2").first
                                    quantity = quantity_elem.text_content().strip() if quantity_elem.count() > 0 else ""
                                    additional_items.append(f"{name} ({quantity})")
                except Exception as e:
                    logger.warning(f"Error getting additional items: {e}")
                
                if current_items:
                    # Categorize items
                    categorized_items = optimizer.categorize_items(current_items)
                    
                    # Extract just the names of produce items for protein pairing
                    produce_names = [item["name"] for item in categorized_items["produce"]]
                    
                    # Generate meal plan
                    meal_plan = optimizer.suggest_meal_plan(
                        categorized_items, 
                        office_meals, 
                        home_meals
                    )
                    
                    # Suggest box modifications
                    modifications = optimizer.suggest_box_modifications(
                        categorized_items,
                        meal_plan
                    )
                    
                    # Get Whole Foods protein suggestions
                    whole_foods_proteins = optimizer._suggest_whole_foods_proteins(
                        produce_names,
                        is_summer
                    )
                    
                    # Print meal plan and modifications
                    optimizer.print_meal_plan(meal_plan)
                    optimizer.print_box_modifications(modifications)
                    
                    # Print Whole Foods shopping list
                    print("\n" + "="*50)
                    print("🛒 WHOLE FOODS PROTEIN SHOPPING LIST 🛒")
                    print("="*50)
                    print("\nRecommended proteins that pair well with your produce:")
                    for protein in whole_foods_proteins:
                        print(f"  • {protein}")
                    
                    # Print additional cart items
                    if additional_items:
                        print("\nAdditional items already in your cart:")
                        for item in additional_items:
                            print(f"  • {item}")
                    
                    # Ask if user wants to make the suggested modifications
                    print("\nWould you like to make the suggested modifications to your box? (y/n)")
                    choice = input()
                    
                    if choice.lower() == 'y':
                        # Implement the modifications
                        for i, item_to_remove in enumerate(modifications["remove"]):
                            # Extract the item name from the string (before the parenthesis)
                            item_name = item_to_remove.split(" (")[0]
                            
                            if i < len(modifications["add"]):
                                item_to_add = modifications["add"][i]
                                # Extract the item name if it contains additional info
                                if " - " in item_to_add:
                                    item_to_add = item_to_add.split(" - ")[0]
                                
                                optimizer.swap_item(page, item_name, item_to_add)
                        
                        # Save changes
                        optimizer.save_changes(page)
                    else:
                        print("No modifications were made to your box.")
                    
                    # Keep browser open for user to make manual adjustments
                    print("\nThe browser will remain open for you to make manual adjustments.")
                    print("Press Enter when you're done to close the browser.")
                    input()
                
                else:
                    logger.error("Could not get current box contents")
            else:
                logger.error("Failed to navigate to Seasonal Produce Box")
        
        except Exception as e:
            logger.error(f"Script failed: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    main()