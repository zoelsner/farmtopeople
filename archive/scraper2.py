from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime
import logging
from pathlib import Path
import csv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Product:
    name: str
    price: str              # The main “price” (often from aria-label='unit price')
    vendor: Optional[str]
    category: str
    approx_range_and_cost: str = ""  # For lines like “1.6-2.1 lbs, avg $29.58”
    price_per_lb: str = ""           # For lines like “$15.99/ lb”
    is_subscribed: bool = False
    is_sold_out: bool = False
    scraped_at: datetime = datetime.now()

class FarmToPeopleScraper:
    def __init__(self):
        load_dotenv()
        self.email = os.getenv("EMAIL")
        self.password = os.getenv("PASSWORD")
        self.storage_state_path = Path("auth_state.json")

    def is_logged_in(self, page) -> bool:
        """Check if we're already logged in by looking for 'Shopping for:' text."""
        try:
            page.goto("https://www.farmtopeople.com")
            page.wait_for_load_state("networkidle")
            
            shopping_for = page.locator(
                "#body > div:nth-child(2) > nav.nav_top-nav__7bJ7H.body-small.nav-breakpoint-no-display"
                " > div > div:nth-child(2) > div.centered-row.cursor-pointer.tracking-normal > span"
            )
            return "Shopping for:" in shopping_for.text_content()
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

    def navigate_to_category(self, page, url: str):
        """Navigate to a specific category page."""
        try:
            logger.info(f"Navigating to category page {url}...")
            page.goto(url)
            page.wait_for_load_state("networkidle")
            logger.info("Successfully loaded category page")
        except Exception as e:
            logger.error(f"Failed to navigate to category page {url}: {e}")
            raise

    def scrape_products(self, page) -> List[Product]:
        """Scrape products from the current page, handling multiple <p class="weight"> lines & sold-out status."""
        try:
            logger.info("Starting to scrape products...")
            
            # Wait for product cards to load
            page.wait_for_selector("article[class*='product-tile_product-tile']")
            page.wait_for_timeout(2000)  # Let JS finish populating content

            product_cards = page.locator("article[class*='product-tile_product-tile']").all()
            logger.info(f"Found {len(product_cards)} product cards...")

            products = []
            for i, card in enumerate(product_cards):
                try:
                    # 1) Grab the product name from aria-label
                    name = card.get_attribute("aria-label") or ""
                    name = name.strip()
                    if not name:
                        continue  # skip if no aria-label

                    # 2) Vendor (producer)
                    vendor_locator = card.locator("a.product-tile_producer-name__ktFOG.producer-name.body-small")
                    vendor = vendor_locator.text_content().strip() if vendor_locator.count() > 0 else "N/A"

                    # 3) Price via aria-label='unit price'
                    price_locator = card.locator("span[aria-label='unit price']")
                    price = price_locator.text_content().strip() if price_locator.count() > 0 else "N/A"

                    # 4) Check for “Sold Out”
                    sold_out_button = card.locator("button.sold-out")
                    is_sold_out = sold_out_button.count() > 0

                    # 5) Check if subscribed
                    subscribed_element = card.locator("text=SUBSCRIBE, text=SUBSCRIBED")
                    is_subscribed = subscribed_element.count() > 0

                    # 6) Handle up to 2 <p class="weight"> lines
                    weight_locators = card.locator("p.weight")
                    wc = weight_locators.count()
                    approx_range_and_cost = ""
                    price_per_lb = ""
                    
                    if wc == 1:
                        single_line = weight_locators.first.text_content().strip()
                        # Decide if it’s a “$XX.XX/ lb” or “X-X lbs, avg $XX.XX”
                        if "/ lb" in single_line:
                            price_per_lb = single_line
                        else:
                            approx_range_and_cost = single_line
                    elif wc >= 2:
                        line1 = weight_locators.nth(0).text_content().strip()
                        line2 = weight_locators.nth(1).text_content().strip()
                        # You can decide which is which, or just store them in order
                        if "/ lb" in line1 and "avg" in line2:
                            price_per_lb = line1
                            approx_range_and_cost = line2
                        elif "avg" in line1 and "/ lb" in line2:
                            approx_range_and_cost = line1
                            price_per_lb = line2
                        else:
                            # fallback if the text doesn't match the usual pattern
                            approx_range_and_cost = line1
                            price_per_lb = line2

                    product = Product(
                        name=name,
                        price=price,
                        vendor=vendor,
                        category="PLACEHOLDER",  # We’ll overwrite from the outside loop
                        approx_range_and_cost=approx_range_and_cost,
                        price_per_lb=price_per_lb,
                        is_subscribed=is_subscribed,
                        is_sold_out=is_sold_out,
                        scraped_at=datetime.now()
                    )

                    # Avoid duplicates if any
                    if not any(p.name == product.name for p in products):
                        products.append(product)
                        logger.info(f"Scraped product: {product.name} - {product.price}")

                except Exception as e:
                    logger.error(f"Error processing product {i}: {e}")
                    continue

            logger.info(f"Total unique products found: {len(products)}")
            return products

        except Exception as e:
            logger.error(f"Error scraping products: {str(e)}")
            raise

def save_to_csv(products: List[Product], filename="farmtopeople_products.csv"):
    """Write or overwrite product data to a CSV file for analysis."""
    rows = []
    for p in products:
        rows.append({
            "Name": p.name,
            "Category": p.category,
            "Vendor": p.vendor,
            "Price": p.price,
            "ApproxRangeCost": p.approx_range_and_cost,
            "PricePerLb": p.price_per_lb,
            "Is_Subscribed": p.is_subscribed,
            "Is_Sold_Out": p.is_sold_out,
            "Scraped_At": p.scraped_at.isoformat()
        })

    fieldnames = [
        "Name", 
        "Category", 
        "Vendor", 
        "Price",
        "ApproxRangeCost",
        "PricePerLb",
        "Is_Subscribed",
        "Is_Sold_Out",
        "Scraped_At"
    ]

    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Saved {len(products)} products to CSV: {filename}")

def main():
    scraper = FarmToPeopleScraper()
    
    # Categories
    categories = [
        ("produce", "https://farmtopeople.com/shop/produce"),
        ("meat-seafood", "https://farmtopeople.com/shop/meat-seafood"),
        ("dairy-eggs", "https://farmtopeople.com/shop/dairy-eggs"),
        ("pantry", "https://farmtopeople.com/shop/pantry"),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state=str(scraper.storage_state_path) if scraper.storage_state_path.exists() else None
        )
        page = context.new_page()

        try:
            # Login (reuse session if possible)
            scraper.login(page, context)

            all_products = []
            # Loop over each category
            for cat_name, cat_url in categories:
                scraper.navigate_to_category(page, cat_url)
                products = scraper.scrape_products(page)
                # Assign correct category
                for prod in products:
                    prod.category = cat_name
                all_products.extend(products)

            logger.info(f"\nFinished scraping all categories. Total items: {len(all_products)}")
            # Save results to CSV
            save_to_csv(all_products, filename="farmtopeople_products.csv")

        except Exception as e:
            logger.error(f"Script failed: {e}")
        finally:
            # browser.close()  # Uncomment if you'd like to close the browser at the end
            pass

if __name__ == "__main__":
    main()